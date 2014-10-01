# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import cstr, flt, getdate, comma_and

class WorkOrder(Document):

	def get_details(self, template):
		self.get_measurement_details(template)
		# self.get_process(template)
		# self.get_raw_material(template)
		return "Done"

	# def on_update(self):
	# 	item_name = frappe.db.sql("select item_name from `tabItem` where item_code='%s'"%(self.item_code))
	# 	for d in self.get('wo_process'):
	# 		task_list = frappe.db.sql("select name from `tabTask` where subject='%s'"%(d.process),as_list=1)
	# 		if not task_list:
	# 			c = frappe.new_doc('Task')
	# 			c.subject = d.process
	# 			c.process_name =d.process
	# 			c.item_name =item_name[0][0]
	# 			c.sales_order_number = self.sales_invoice_no
	# 			c.save()

	def get_measurement_details(self, template):
		self.set('measurement_item', [])
		args = frappe.db.sql("""select * from `tabMeasurement Item`
			where parent='%s'"""%(template),as_dict=1)
		if args:
			for data in args:
				mi = self.append('measurement_item', {})
				mi.parameter = data.parameter
				mi.abbreviation = data.abbreviation
				mi.image_view = data.image_view
				mi.value = data.value
				mi.default_value = data.default_value
		return "Done"

	def get_process(self, item):
		self.set('wo_process', [])
		args = frappe.db.sql("""select * from `tabProcess Item`
			where parent='%s'"""%(item),as_dict=1)
		if args:
			for data in args:
				prd = self.append('wo_process', {})
				prd.process = data.process_name
				prd.trial = data.trial
				prd.quality_check = data.quality_check
		return "Done"

	def get_raw_material(self, item):
		self.set('raw_material', [])
		args = frappe.db.sql("""select * from `tabRaw Material Item`
			where parent='%s'"""%(item),as_dict=1)
		if args:
			for data in args:
				prd = self.append('raw_material', {})
				prd.item_code = data.item
				prd.item_name = frappe.db.get_value('Item', data.item, 'item_name')
		return "Done"

	def apply_rules(self, args):
		for d in self.get('measurement_item'):
			measurement_formula_template = frappe.db.get_value('Item', args.get('item'),'measurement_formula_template')
			measurement_data = frappe.db.sql("select * from `tabMeasurement Rules` where parent='%s'"%(measurement_formula_template),as_dict=1)
			for data in measurement_data:
				if data.target_parameter == d.parameter and args.get('parameter') == data.parameter:
					value = (data.formula).replace('S',cstr(args.get('value')))
					d.value = cstr(eval(value))
		return "Done"

	def on_submit(self):
		self.update_status('Completed')
		self.set_work_order()

	def on_cancel(self):
		self.update_status('Pending')
		self.set_to_null()

	def update_status(self, status):
		frappe.db.sql(""" update `tabProduction Dashboard Details` 
					set work_order_status='%s'
					where sales_invoice_no='%s' and article_code='%s' 
					and work_order='%s'"""%(status,self.sales_invoice_no, self.item_code, self.name))

	def set_to_null(self):
		frappe.db.sql(""" update `tabProduction Dashboard Details` 
					set work_order=(select name from tabCustomer where 1=2)
					where sales_invoice_no='%s' and article_code='%s' 
					and work_order='%s'"""%(self.sales_invoice_no, self.item_code, self.name))

	def set_work_order(self):
		frappe.db.sql(""" update `tabProduction Dashboard Details` 
					set work_order= '%s', work_order_status ='Completed'
					where sales_invoice_no='%s' and article_code='%s' 
					"""%(self.name, self.sales_invoice_no, self.item_code))

