# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import cstr, flt, getdate, comma_and, nowdate, cint, now
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
			if d.user:
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