# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import cint, cstr, flt
from tools.custom_data_methods import get_user_branch, get_branch_cost_center, get_branch_warehouse, update_serial_no

class Trials(Document):
	def validate(self):
		self.make_event_for_trials()
		self.autoOperation()
		self.update_trials_status()
		# self.update_branch_of_warehouse()


	def update_trials_status(self):
		for d in self.get('trial_dates'):
			if cint(d.skip_trial) == 1:
				frappe.db.sql("update `tabProcess Log` set status='Closed' where parent='%s' and trials is null and status!='Closed'"%(self.pdd))

	def autoOperation(self):
		for d in self.get('trial_dates'):
			self.make_auto_ste(d)

	def make_auto_ste(self, trial_data):
		data = frappe.db.get_value('Process Log', {'parent': self.pdd, 'process_name': trial_data.process, 'trials': trial_data.trial_no}, '*')
		if data:
			reverse_entry = data.reverse_entry if data.reverse_entry else ''
			if trial_data.production_status == 'Closed' and reverse_entry == 'Pending' and trial_data.trial_branch != data.branch:
				branch = data.branch
				msg = cstr(trial_data.trial_no) + ' ' +cstr(trial_data.production_status)
				self.prepare_for_ste(trial_data, branch, data, msg)
			elif cint(self.finished_all_trials) == 1:
				branch = self.get_target_branch(trial_data)
				if branch != trial_data.trial_branch and not frappe.db.get_value('Stock Entry Detail', {'work_order': self.work_order, 'target_branch':branch, 'docstatus':0, 's_warehouse': get_branch_warehouse(get_user_branch())}, 'name'):
					msg = 'Trials Get Finished'
					self.prepare_for_ste(trial_data, branch, data, msg)
				else:
					self.OpenNextTrial(trial_data)
			else:
				self.OpenNextTrial(trial_data)


	def prepare_for_ste(self, trial_data, branch, data, msg):
		parent = frappe.db.get_value('Stock Entry Detail', {'target_branch':data.branch, 'docstatus':0, 's_warehouse': get_branch_warehouse(trial_data.trial_branch)}, 'parent')
		args = {'qty': 1, 'serial_data': self.trials_serial_no_status, 'work_order': self.work_order, 'item': self.item_code, 'trials': trial_data.next_trial_no}	
		if parent:
			st = frappe.get_doc('Stock Entry', parent)
			self.stock_entry_of_child(st, args, branch)
			st.save(ignore_permissions=True)
		else:
			parent = self.make_stock_entry(branch, args)
		if parent:
			update_serial_no(self.pdd, self.trials_serial_no_status, msg)
			frappe.db.sql(""" update `tabProcess Log` set reverse_entry = 'Done' where name ='%s'"""%(data.name))
			

	def get_target_branch(self, args):
		name = frappe.db.sql("""select branch from `tabProcess Log` where 
			idx > (select idx from `tabProcess Log` where parent = '%s' and process_name = '%s' 
			order by idx desc limit 1) and parent = '%s' limit 1 """%(self.pdd, args.process, self.pdd), as_dict=1, debug=1)
 		if name:
 			return name[0].branch

	def make_stock_entry(self, t_branch, args):
		ste = frappe.new_doc('Stock Entry')
		ste.purpose_type = 'Material Out'
		ste.branch = get_user_branch()
 		ste.purpose ='Material Issue' 		
 		self.stock_entry_of_child(ste, args, t_branch)
 		ste.save(ignore_permissions=True)
 		return ste.name

 	def stock_entry_of_child(self, obj, args, target_branch):
		ste = obj.append('mtn_details', {})
		ste.s_warehouse = get_branch_warehouse(get_user_branch())
		ste.target_branch = target_branch
		ste.t_warehouse = get_branch_warehouse(target_branch)
		ste.qty = args.get('qty')
		ste.serial_no = args.get('serial_data')
		ste.incoming_rate = 1.0
		ste.conversion_factor = 1.0
		ste.has_trials = 'Yes'
		ste.work_order = args.get('work_order')
		ste.item_code = args.get('item')
		ste.item_name = frappe.db.get_value('Item', ste.item_code, 'item_name')
		ste.stock_uom = frappe.db.get_value('Item', ste.item_code, 'stock_uom')
		company = frappe.db.get_value('GLobal Default', None, 'company')
		ste.expense_account = frappe.db.get_value('Company', company, 'default_expense_account')
		return "Done"

	def OpenNextTrial(self, args):
		if (not args.production_status or args.production_status != 'Closed') and args.work_status == 'Open':
			frappe.db.sql(""" update `tabProcess Log` set status = 'Open' where parent = '%s'
				and process_name = '%s' and trials = '%s'"""%(self.pdd, args.process, args.trial_no))

	def update_status(self):
		if self.trial_serial_no:  
			self.trials_serial_no_status = self.trial_serial_no

	def make_event_for_trials(self):
		for d in self.get('trial_dates'):
			self.add_trials(d)
			# self.create_event(d)

	def add_trials(self,args):
		name = frappe.db.get_value('Process Log', {'process_name': args.process, 'trials': args.trial_no, 'parent':self.pdd},'name')
		if name and args.trial_date:
			frappe.db.sql("update `tabProcess Log` set trials_date = '%s', skip_trial = %s, pr_work_order='%s' where name = '%s'"%(args.trial_date, cint(args.skip_trial), self.work_order, name))
		elif not name and args.trial_date:
			max_id = frappe.db.sql("select ifnull(max(idx),'') from `tabProcess Log` where parent='%s'"%(self.pdd), as_list =1)
			pl = frappe.new_doc('Process Log')
			pl.process_data = frappe.db.get_value('Process Log', {'process_name': args.process, 'trials': cstr(cint(args.trial_no) - 1), 'parent':self.pdd},'process_data')
			pl.skip_trial = cint(args.skip_trial)
			pl.process_name = args.process
			pl.trials_date = args.trial_date
			pl.branch = args.trial_branch
			pl.trials = cint(args.trial_no)
			pl.parent = self.pdd
			if max_id:
				pl.idx = cint(max_id[0][0]) + 1
			pl.parenttype = 'Production Dashboard Details'
			pl.parentfield = 'process_log'
			pl.save(ignore_permissions=True)
	
	def create_event(self, args):
		if not args.event:
			evt = frappe.new_doc('Event')
			evt.branch = args.trial_branch 
			evt.subject = args.subject
			evt.starts_on = args.trial_date
			evt.ends_on = args.to_time
			self.make_appointment_list(evt)
			evt.save(ignore_permissions = True)
			args.event = evt.name
		else:
			frappe.db.sql("""update `tabEvent` set branch = '%s', starts_on = '%s', ends_on = '%s',
				subject = '%s' where name='%s'"""%(args.trial_branch, args.trial_date, args.to_time, args.subject, args.event))

	def make_appointment_list(self, obj):
		if self.customer:
			apl = obj.append('appointment_list',{})
			apl.customer = self.customer
			return "Done"

@frappe.whitelist()
def get_serial_no_data(work_order):
	return frappe.db.get_value('Work Order', work_order, 'serial_no_data') if work_order else ''
