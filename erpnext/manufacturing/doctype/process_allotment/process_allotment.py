# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import cstr, flt, getdate, comma_and, nowdate, cint, now, nowtime
from erpnext.accounts.accounts_custom_methods import delte_doctype_data

class ProcessAllotment(Document):
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
		self.assign_task()

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

	def create_task(self, data):
		tsk = frappe.new_doc('Task')
		tsk.subject = data.task_details or 'Do process %s for item %s'%(data.process, frappe.db.get_value('Item',self.item,'item_name'))
		tsk.project = self.sales_invoice_no
		tsk.exp_start_date = data.expected_start_date
		tsk.exp_end_date = data.expected_end_date
		tsk.process_name = data.process
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
		self.update_status()
		self.make_stock_entry_for_finished_goods()

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

	def update_status(self):
		frappe.db.sql(""" update `tabProduction Dashboard Details` 
					set process_allotment= '%s', process_status ='Completed'
					where sales_invoice_no='%s' and article_code='%s' 
					"""%(self.name, self.sales_invoice_no, self.item))

	def set_completion_date(self, index):
		for d in self.get('wo_process'):
			if cint(d.idx) == index and d.status == 'Completed':
				d.completion_date = cstr(nowdate())
			else:
				d.completion_date = ''
		return True

	def make_stock_entry(self):
		if self.get('issue_raw_material'):
			frappe.errprint("debug step 1")
			create_se(self.get('issue_raw_material'))

	def make_stock_entry_for_finished_goods(self):
		ste = frappe.new_doc('Stock Entry')
		ste.purpose = 'Manufacture/Repack'
		ste.save(ignore_permissions=True)
		self.make_child_entry(ste.name)
		ste = frappe.get('Stock Entry',ste.name)
		ste.submit()
		self.make_gs_entry(args)
		return ste.name

	def make_child_entry(self, name):
		ste = frappe.new_doc('Stock Entry Detail')
		ste.t_warehouse = 'Finished Goods - I'
		ste.item_code = self.item
		ste.serial_no = self.serials_data
		ste.qty = self.finished_good_qty
		ste.parent = name
		ste.conversion_factor = 1
		ste.expense_account = 'Stock Adjustment - I'
		ste.cost_center = 'Main - I'
		ste.transfer_qty = self.finished_good_qty
		ste.save(ignore_permissions = True)
		return "Done"

	def make_gs_entry(self):
		if self.serials_data:
			parent = frappe.db.get_value('Production Dashboard Details',{'sales_invoice_no':self.sales_invoice_no,'article_code':self.item,'process_allotment':self.name},'name')
			sn = cstr(serials_data).splitlines()
			for s in sn:
				if not frappe.db.get_value('Production Status Detail',{'item_code':self.item, 'serial_no':s[0]},'name'):
					if parent:
						pd = frappe.new_doc('Production Status Detail')
						pd.item_code = self.item
						pd.serial_no = s[0]
						pd.status = 'Ready'
						pd.parent = parent
						pd.save(ignore_permissions = True)
			if parent:
				frappe.db.sql("update `tabProduction Dashboard Details` set status='Completed', trial_no=0 where name='%s'"%(parent))
		return "Done"

def create_se(raw_material):
	frappe.errprint([nowdate(), nowtime()])
	se = frappe.new_doc('Stock Entry')
	se.naming_series = 'STE-'
	se.purpose = 'Material Issue'
	se.posting_date = nowdate()
	se.posting_time = nowtime().split('.')[0]
	se.company = frappe.db.get_value("Global Defaults", None, 'default_company')
	se.fiscal_year = frappe.db.get_value("Global Defaults", None, 'current_fiscal_year')
	se.save()
	
	for item in raw_material:
		if cint(item.select) == 1:
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

def get_warehouse():
	return "Finished Goods - I"
	# warehouse = frappe.db.sql(""" select b.warehouse from tabBranch b, tabEmployee e 
	# 	where b.name = e.branch and e.user_id = '%s'"""%(frappe.session.user))

	# return ((len(warehouse[0]) > 1 ) and warehouse[0] or warehouse[0][0]) if warehouse else None