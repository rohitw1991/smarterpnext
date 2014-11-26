# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import cstr, flt, getdate, comma_and, nowdate, cint, now, nowtime
from erpnext.accounts.accounts_custom_methods import delte_doctype_data
from tools.custom_data_methods import get_user_branch, get_branch_cost_center, get_branch_warehouse
import datetime

class ProcessAllotment(Document):
	def on_update(self):
		self.create_time_log()

	def show_trials_details(self):
		trials_data = frappe.db.sql("select * from `tabProcess Log` where (ifnull(status,'') = 'Open' or ifnull(status,'')='Closed') and process_name='%s' and process_data = '%s' order by trials"%(self.process, self.name), as_dict=1)
		for data in trials_data:
			td = self.append('trials_transaction', {})
			td.trial_no = data.trials
			td.status = data.status
			td.work_order = data.pr_work_order

	def create_time_log(self):
		if self.get('employee_details'):
			for data in self.get('employee_details'):
				if cint(data.idx) == cint(len(self.get('employee_details'))):
					status = 'Closed' if data.employee_status == 'Completed' else 'Open'
					frappe.db.sql("update `tabTask` set status ='%s' where name='%s'"%( status, data.tailor_task))
				if data.employee_status =='Completed' and not data.time_log_name:
					tl = frappe.new_doc('Time Log')
					tl.from_time = data.tailor_from_time
					tl.hours = flt(data.work_completed_time)/60
					tl.to_time = datetime.datetime.strptime(tl.from_time, '%Y-%m-%d %H:%M:%S') + datetime.timedelta(hours = flt(tl.hours))
					tl.activity_type = self.process
					tl.task = data.tailor_task
					tl.project = self.sales_invoice_no
					tl.submit()
					data.time_log_name = tl.name

	def get_details(self, item):
		self.set('wo_process', [])
		args = frappe.db.sql("""select * from `tabProcess Item`
			where parent='%s'"""%(item),as_dict=1)
		if args:
			for data in args:
				prd = self.append('wo_process', {})
				prd.process = data.process_name
				prd.trial = data.trial
				prd.status = 'Pending'
				prd.quality_check = data.quality_check
		return "Done"

	def validate(self):
		# self.assign_task()
		# self.update_process_status()
		# self.update_task()
		self.make_auto_ste()
		self.auto_ste_for_trials()

	def make_auto_ste(self):
		if self.process_status == 'Closed':
			self.validate_trials_closed()
			cond = "1=1"
			current_name, next_name = self.get_details(cond)
			target_branch = frappe.db.get_value('Process Log', next_name, 'branch')
			args = {'qty': self.finished_good_qty, 'serial_data': self.serials_data, 'work_order': self.process_work_order, 'item': self.item}
			parent = self.prepare_stock_entry_for_process(target_branch, args)
			if parent:
				self.update_status(current_name, next_name)
		
	def validate_trials_closed(self):
		count = frappe.db.sql("select ifnull(count(*),0) from `tabProcess Log` where process_data = '%s' and status = 'Open'"%(self.name))
		if count:
			if cint(count[0][0])!=0	and self.process_status == 'Closed':
				frappe.throw(_("You must have to closed all trials"))	

	def update_status(self, current_name, next_name):
		frappe.db.sql("""update `tabProcess Log` set status = 'Closed' where name='%s'"""%(current_name))
		frappe.db.sql("""update `tabProcess Log` set status = 'Open' where name='%s' and trials is null"""%(current_name))

	def prepare_stock_entry_for_process(self, target_branch, args):
		if self.branch != target_branch and not frappe.db.get_value('Stock Entry Detail', {'work_order': self.process_work_order, 'target_branch':target_branch, 'docstatus':0, 's_warehouse': get_branch_warehouse(self.branch)}, 'name'):
			parent = frappe.db.get_value('Stock Entry Detail', {'target_branch':target_branch, 'docstatus':0, 's_warehouse': get_branch_warehouse(self.branch)}, 'parent')			
			if parent:
				st = frappe.get_doc('Stock Entry', parent)
				self.stock_entry_of_child(st, args, target_branch)
			else:
				parent = self.make_stock_entry(target_branch, args)
			return parent

	def auto_ste_for_trials(self):
		for d in self.get('employee_details'):
			if d.tailor_process_trials and d.employee_status == 'Completed':
				cond = "trials ='%s'"%(d.tailor_process_trials)
				current_name, next_name = self.get_details(cond)
				trial_name = frappe.db.get_value('Trials',{'sales_invoice': self.sales_invoice_no, 'work_order': self.process_work_order}, 'name')
				target_branch = frappe.db.get_value('Trials Dates', {'parent': trial_name, 'process': self.process, 'trial': d.tailor_process_trials}, 'trial_branch')
				trials_serial_no = frappe.db.get_value('Trials', {'sales_invoice': self.sales_invoice_no, 'work_order': self.process_work_order}, 'trials_serial_no_status')
				args = {'qty': 1, 'serial_data': trials_serial_no, 'work_order': self.process_work_order, 'item': self.item}
				parent = self.prepare_stock_entry_for_process(target_branch)
				if parent:
					self.update_status(current_name, next_name)

	def make_stock_entry(self, t_branch, args):
		ste = frappe.new_doc('Stock Entry')
		ste.purpose_type = 'Material Out'
 		ste.purpose ='Material Issue' 		
 		self.stock_entry_of_child(ste, args, t_branch)
 		ste.save(ignore_permissions=True)
 		return ste.name

 	def stock_entry_of_child(self, obj, args, target_branch):
		ste = obj.append('mtn_details', {})
		ste.s_warehouse = get_branch_warehouse(self.branch)
		ste.target_branch = target_branch
		ste.t_warehouse = get_branch_warehouse(target_branch)
		ste.qty = args.get('qty')
		ste.serial_no = args.get('serial_data')
		ste.incoming_rate = 1.0
		ste.conversion_factor = 1.0
		ste.work_order = args.get('work_order')
		ste.item_code = args.get('item')
		ste.item_name = frappe.db.get_value('Item', ste.item_code, 'item_name')
		ste.stock_uom = frappe.db.get_value('Item', ste.item_code, 'stock_uom')
		company = frappe.db.get_value('GLobal Default', None, 'company')
		ste.expense_account = frappe.db.get_value('Company', company, 'default_expense_account')
		return "Done"

 	def get_details(self , cond):
 		name = frappe.db.sql("""SELECT ifnull(foo.name, '') AS current_name,  (SELECT  ifnull(name, '') FROM `tabProcess Log` 
 								WHERE name > foo.name AND parent = foo.parent order by process_data, trials limit 1) AS next_name
								FROM ( SELECT  name, parent  FROM  `tabProcess Log` WHERE   branch = '%s' 
								and status != 'Closed' and process_data = '%s' and %s ORDER BY idx limit 1) AS foo """%(self.branch, self.name, cond), as_dict=1)
 		return name[0].current_name, name[0].next_name if name else ''

 	def create_stock_entry():
 		pass


	def update_task(self):
		if not self.task and not self.get("__islocal"):
			self.task = self.create_task()
		if self.get('employee_details'):
			for d in self.get('employee_details'):
				if not d.tailor_task:
					d.tailor_task = self.task

	def assign_task(self):
		for d in self.get('wo_process'):
			if d.tailor_employee:
				self.validate_process(d.idx)
				task = frappe.db.get_value('Task',{'item_code':self.item,'process_name':d.process,'sales_order_number':self.sales_invoice_no},'name')
				if not task:
					d.task = self.create_task(d)
				assigned = frappe.db.get_value('ToDo',{'owner':d.user,'reference_name':d.task},'name')
				if not assigned:
					self.assigned_to_user(d)

	def create_task(self):
		self.validate_dates()
		tsk = frappe.new_doc('Task')
		tsk.subject = 'Do process %s for item %s'%(self.process, frappe.db.get_value('Item',self.item,'item_name'))
		tsk.project = self.sales_invoice_no
		tsk.exp_start_date = self.start_date
		tsk.exp_end_date = self.end_date
		tsk.status = 'Open'
		tsk.process_name = self.process
		tsk.item_code = self.item
		tsk.sales_order_number = self.sales_invoice_no
		tsk.save(ignore_permissions=True)
		return tsk.name

	def assigned_to_user(self, data):
		todo = frappe.new_doc('ToDo')
		todo.description = data.task_details or 'Do process %s for item %s'%(data.process, frappe.db.get_value('Item',self.item,'item_name'))
		todo.reference_type = 'Task'
		todo.reference_name = data.task
		todo.owner = data.user
		todo.save(ignore_permissions=True)
		return todo.name

	def validate_process(self, index):
		for data in self.get('wo_process'):
			if cint(data.idx)<index:
				if data.status == 'Pending' and cint(data.skip)!=1:
					frappe.throw(_("Previous Process is Pending, please check row {0} ").format(cint(data.idx)))

	def on_submit(self):
		self.check_status()
		self.change_status('Completed')
		# self.update_status()
		# self.make_stock_entry_for_finished_goods()

	def check_status(self):
		for d in self.get('wo_process'):
			if d.status =='Pending' and cint(d.skip)!=1:
				frappe.throw(_("Process is Pending, please check row {0} ").format(cint(d.idx)))

	def on_cancel(self):
		self.change_status('Pending')
		self.set_to_null()
		self.delete_dependecy()
	
	def change_status(self,status):
		frappe.db.sql(""" update `tabProduction Dashboard Details` 
					set process_status='%s' 
					where sales_invoice_no='%s' and article_code='%s' 
					and process_allotment='%s'"""%(status, self.sales_invoice_no, self.item, self.name))

	def set_to_null(self):
		frappe.db.sql(""" update `tabProduction Dashboard Details` 
					set process_allotment= (select name from tabCustomer where 1=2) 
					where sales_invoice_no='%s' and article_code='%s' 
					and process_allotment='%s'"""%( self.sales_invoice_no, self.item, self.name))

	def delete_dependecy(self):
		for d in self.get('wo_process'):
			if d.task and d.user:
				frappe.db.sql("delete from `tabToDo` where reference_type='%s' and owner='%s'"%(d.task, d.user))
				production_dict = self.get_dict(d.task, d.user)
				delte_doctype_data(production_dict)

	def get_dict(self, task, user):
		return {'Task':{'name':task}}

	# def update_status(self):
	# 	frappe.db.sql(""" update `tabProduction Dashboard Details` 
	# 				set process_allotment= '%s', process_status ='Completed'
	# 				where sales_invoice_no='%s' and article_code='%s' 
	# 				"""%(self.name, self.sales_invoice_no, self.item))

	def on_status_trigger_method(self, args):
		self.set_completion_date(args)
		self.update_process_status(args)

	def set_completion_date(self, args):
		for d in self.get('wo_process'):
			if cint(d.idx) == cint(args.idx) and d.status == 'Completed':
				d.completion_date = cstr(nowdate())
			else:
				d.completion_date = ''
		return True

	# def make_stock_entry(self):
	# 	if self.get('issue_raw_material'):
	# 		create_se(self.get('issue_raw_material'))

	def make_stock_entry_for_finished_goods(self):
		ste = frappe.new_doc('Stock Entry')
		ste.purpose = 'Manufacture/Repack'
		ste.save(ignore_permissions=True)
		self.make_child_entry(ste.name)
		ste = frappe.get_doc('Stock Entry',ste.name)
		ste.submit()
		self.make_gs_entry()
		return ste.name

	def make_child_entry(self, name):
		ste = frappe.new_doc('Stock Entry Detail')
		ste.t_warehouse = 'Finished Goods - I'
		ste.item_code = self.item
		ste.serial_no = self.serials_data
		ste.qty = self.finished_good_qty
		ste.parent = name
		ste.conversion_factor = 1
		ste.parenttype = 'Stock Entry'
		ste.uom = frappe.db.get_value('Item', ste.item_code, 'stock_uom')
		ste.stock_uom = frappe.db.get_value('Item', ste.item_code, 'stock_uom')
		ste.incoming_rate = 1.00
		ste.parentfield = 'mtn_details'
		ste.expense_account = 'Stock Adjustment - I'
		ste.cost_center = 'Main - I'
		ste.transfer_qty = self.finished_good_qty
		ste.save(ignore_permissions = True)
		return "Done"

	def make_gs_entry(self):
		if self.serials_data:
			parent = frappe.db.get_value('Production Dashboard Details',{'sales_invoice_no':self.sales_invoice_no,'article_code':self.item,'process_allotment':self.name},'name')
			sn = cstr(self.serials_data).splitlines()
			for s in sn:
				if not frappe.db.get_value('Production Status Detail',{'item_code':self.item, 'serial_no':s[0]},'name'):
					if parent:
						pd = frappe.new_doc('Production Status Detail')
						pd.item_code = self.item
						pd.serial_no = s
						pd.status = 'Ready'
						pd.parent = parent
						pd.save(ignore_permissions = True)
			if parent:
				frappe.db.sql("update `tabProduction Dashboard Details` set status='Completed', trial_no=0 where name='%s'"%(parent))
		return "Done"

	def update_process_status(self, args=None):
		self.update_parent_status()
		self.update_child_status()

	def update_parent_status(self):
		if self.process_status_changes=='Yes':
			cond = "a.parent=b.name and a.process_data='%s' and a.process_name='%s' and b.sales_invoice_no='%s'"%(self.name, self.process, self.sales_invoice_no)
			frappe.db.sql("update `tabProcess Log` a, `tabProduction Dashboard Details` b set a.status='%s' where %s"%(self.process_status,cond))
			if self.process_status=='Closed':
				self.open_next_status(cond)
			self.process_status_changes='No'
		
	def update_child_status(self):
		for s in self.get('trials_transaction'):
			if s.trial_change_status=='Yes':
				cond = "a.parent=b.name and a.process_data='%s' and a.process_name='%s' and a.trials='%s' and b.sales_invoice_no='%s'"%(self.name, self.process, s.trial_no, self.sales_invoice_no)
				frappe.db.sql("update `tabProcess Log` a, `tabProduction Dashboard Details` b set a.status='%s' where %s"%(s.status, cond))
				if s.status=='Closed':
					self.open_next_status(cond)
				s.trial_change_status='No'

	def open_next_status(self, cond):
		name = frappe.db.sql("""select a.* from `tabProcess Log` a, `tabProduction Dashboard Details` b where %s """%(cond), as_dict=1)
		if name:
			for s in name:
				frappe.db.sql("update `tabProcess Log` set status='Open' where idx=%s and parent='%s'"%(cint(s.idx)+1, s.parent))

	def assign_task_to_employee(self):
		emp = self.append('employee_details',{})
		emp.employee = self.process_tailor
		emp.employee_name = frappe.db.get_value('Employee', self.process_tailor, 'employee_name')
		emp.tailor_task = self.task
		emp.employee_status = self.emp_status
		emp.tailor_payment = self.payment
		emp.tailor_wages = self.wages
		emp.tailor_process_trials = self.process_trials
		emp.tailor_extra_wages = self.extra_charge
		emp.tailor_extra_amt = self.extra_charge_amount
		emp.tailor_from_time = self.from_time
		emp.work_estimated_time = self.estimated_time
		emp.work_completed_time = self.completed_time
		emp.assigned_work_qty = self.work_qty
		emp.deduct_late_work = self.deduct_late_work
		emp.latework = self.latework
		emp.cost = self.cost

		return "Done"

	def calculate_estimates_time(self):
		self.estimated_time = cint(self.work_qty) * cint(frappe.db.get_value('EmployeeSkill',{'parent':self.process_tailor, 'process':self.process, 'item_code': self.item},'time'))
		return "Done"

	def calculate_wages(self):
		self.wages = 0.0
		if self.payment == 'Yes':
			self.wages = cint(self.work_qty) * cint(frappe.db.get_value('EmployeeSkill',{'parent':self.process_tailor, 'process':self.process, 'item_code': self.item},'cost'))

	def calc_late_work_amt(self):
		self.cost = flt(self.latework) * flt(frappe.db.get_value('Item',self.item,"late_work_cost"))
		return "Done"

	def validate_dates(self):
		if not self.start_date and not self.end_date:
			frappe.throw(_('Start and End Date is necessary to create task'))

def create_se(raw_material):
	count = 0
	se = frappe.new_doc('Stock Entry')
	se.naming_series = 'STE-'
	se.purpose = 'Material Issue'
	se.posting_date = nowdate()
	se.posting_time = nowtime().split('.')[0]
	se.company = frappe.db.get_value("Global Defaults", None, 'default_company')
	se.fiscal_year = frappe.db.get_value("Global Defaults", None, 'current_fiscal_year')
	se.save()
	for item in raw_material:
		if cint(item.selected) == 1 and item.status!='Completed':
			sed = frappe.new_doc('Stock Entry Detail')
			sed.s_warehouse = get_warehouse()
			sed.parentfield = 'mtn_details'
			sed.parenttype = 'Stock Entry'
			sed.item_code = item.raw_material_item_code
			sed.item_name = frappe.db.get_value("Item", item.raw_material_item_code, 'item_name')
			sed.description = frappe.db.get_value("Item", item.raw_material_item_code, 'description')
			sed.stock_uom = item.uom
			sed.uom = item.uom
			sed.conversion_factor = 1
			sed.incoming_rate = 0.0
			sed.qty = flt(item.qty)
			sed.transfer_qty = flt(item.qty) * 1
			sed.serial_no = item.serial_no
			sed.parent = se.name
			sed.save()
			frappe.db.sql("update `tabIssue Raw Material` set status = 'Completed', selected=1 where name = '%s'"%(item.name))
			frappe.db.sql("commit")
			count += 1
	if count == 0:
		frappe.db.sql("delete from `tabStock Entry` where name = '%s'"%se.name)
		frappe.db.sql("update tabSeries set current = current-1 where name = 'STE-'")
		frappe.db.sql("commit")
	else:
		frappe.msgprint("Material Issue Stock Entry %s has been created for above items"%se.name)

def get_warehouse():
	return "Finished Goods - I"
	# warehouse = frappe.db.sql(""" select b.warehouse from tabBranch b, tabEmployee e 
	# 	where b.name = e.branch and e.user_id = '%s'"""%(frappe.session.user))

	# return ((len(warehouse[0]) > 1 ) and warehouse[0] or warehouse[0][0]) if warehouse else None