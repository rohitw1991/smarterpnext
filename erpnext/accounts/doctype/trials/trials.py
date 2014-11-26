# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import cint, cstr, flt

class Trials(Document):
	def validate(self):
		self.make_event_for_trials()
		# self.update_branch_of_warehouse()

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
			frappe.db.sql("update `tabProcess Log` set trials_date = '%s', skip_trial = %s where name = '%s'"%(args.trial_date, cint(args.skip_trial), name))
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
