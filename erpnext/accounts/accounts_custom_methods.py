# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.widgets.reportview import get_match_cond
from frappe.utils import add_days, cint, cstr, date_diff, rounded, flt, getdate, nowdate, \
	get_first_day, get_last_day,money_in_words, now
from frappe import _
from frappe.model.db_query import DatabaseQuery
from frappe import msgprint, _, throw

def create_production_process(doc, method):
	for d in doc.get('sales_invoice_items_one'):
		work_order = d.tailoring_work_order if d.tailoring_work_order else create_work_order(d)
		process_allotment = create_process_allotment(d)
		stock_entry = create_stock_entry(d)
		if work_order and process_allotment and stock_entry:
			create_dashboard(work_order, process_allotment, stock_entry,d,doc)
			# frappe.db.sql("update `tabSales Invoice Item` set work_order='%s', stock_entry='%s' ,process_allotment='%s' where name='%s'"%(work_order,stock_entry,process_allotment,d.name))

def create_work_order(data):
	wo = frappe.new_doc('Work Order')
 	wo.sales_invoice_no = data.parent
 	wo.item_code = data.tailoring_item_code
 	wo.branch = data.tailoring_warehouse
 	wo.save(ignore_permissions=True)
 	
 	create_work_order_style(data, wo.name)
 	create_work_order_measurement(data, wo.name)
 	return wo.name

def create_work_order_style(data, wo_name):
 	if wo_name and data.tailoring_item_code:
	 	styles = frappe.db.sql(""" select distinct style, abbreviation from `tabStyle Item` where parent = '%s'
	 		"""%(data.tailoring_item_code),as_dict=1)
	 	if styles:
	 		for s in styles:
	 			ws = frappe.new_doc('WO Style')
	 			ws.field_name = s.style
	 			ws.abbreviation  = s.abbreviation
	 			ws.parent = wo_name
	 			ws.parentfield = 'wo_style'
	 			ws.parenttype = 'Work Order'
	 			ws.table_view = 'Right'
	 			ws.save(ignore_permissions =True)
	return True

def create_work_order_measurement(data, wo_name):
	style_parm=[]
 	if wo_name and data.tailoring_item_code:
	 	measurements = frappe.db.sql(""" select * from `tabMeasurement Item` where parent = '%s'
	 		"""%(data.tailoring_item_code),as_dict=1)
	 	if measurements:
	 		for s in measurements:
	 			if not s.parameter in style_parm:
		 			mi = frappe.new_doc('Measurement Item')
		 			mi.parameter = s.parameter
		 			mi.abbreviation = s.abbreviation
		 			mi.parent = wo_name
		 			mi.parentfield = 'measurement_item'
		 			mi.parenttype = 'Work Order'
		 			mi.save(ignore_permissions =True)
		 			style_parm.append(s.parameter)
	return True

def create_process_allotment(data):
 	pa = frappe.new_doc('Process Allotment')
 	pa.sales_invoice_no = data.parent
 	pa.item = data.tailoring_item_code
 	pa.branch = data.tailoring_warehouse
 	pa.save(ignore_permissions=True)
 	
 	assign_process(data, pa.name)
 	return pa.name

def assign_process(data, name):
 	if data.tailoring_item_code:
 		process = frappe.db.sql(""" select * from `tabProcess Item` where parent = '%s'
 			"""%(data.tailoring_item_code),as_dict = 1)
 		if process:
 			for s in process:
 				pr = frappe.new_doc('WO Process')
 				pr.process = s.process_name
 				pr.trial = s.trial
 				pr.quality_check = s.quality_check
 				pr.task_details = '-'
 				pr.parent = name
 				pr.parenttype = 'Process Allotment'
 				pr.parentfield = 'wo_process'
 				pr.save(ignore_permissions=True)
 	return True

def create_stock_entry(data):
 	ste = frappe.new_doc('Stock Entry')
 	ste.purpose ='Manufacture/Repack'
 	ste.save(ignore_permissions=True)
 	stock_entry_manufacture_repack(ste.name,data)
 	return ste.name

def stock_entry_manufacture_repack(name, data):
 	if data.tailoring_item_code:
 		raw_material = frappe.db.sql(""" select * from `tabRaw Material Item` where parent = '%s'
 			"""%(data.tailoring_item_code),as_dict = 1)
 		if raw_material:
 			for s in raw_material:
 				create_stock(name , s.item,'Finished Goods - I','source')
 		if data.fabric_code:
 			create_stock(name , data.fabric_code,'Finished Goods - I','source',data.fabric_qty)
 		if data.tailoring_item_code :
 			create_stock(name , data.tailoring_item_code,data.tailoring_warehouse,'target')

 	return True

def create_stock(name, item_code, warehouse, warehouse_type , qty=None):
 	if item_code:
		ste = frappe.new_doc('Stock Entry Detail')
		if warehouse_type=='source':
			ste.s_warehouse = warehouse
		else:
			ste.t_warehouse = warehouse
		ste.item_code = item_code 
		ste.item_name = frappe.db.get_value('Item', ste.item_code, 'item_name')
		ste.description = frappe.db.get_value('Item', ste.item_code, 'description')
		ste.uom = frappe.db.get_value('Item', ste.item_code, 'stock_uom')
		ste.conversion_factor = 1
		ste.qty = qty or 1
		ste.transfer_qty=qty or 1
		ste.parent =name
		ste.parenttype='Stock Entry'
		ste.parentfield = 'mtn_details'
		ste.save(ignore_permissions=True)

	return True

def create_dashboard(work_order, process, stock_entry, d ,doc):
	production_dict = get_production_dict(work_order, process, stock_entry,d, doc)
	production = frappe.get_doc(production_dict).insert(ignore_permissions=True)

def get_production_dict(work_order, process, stock_entry, data, doc):
		return {
					"doctype": "Production Dashboard Details",
					"sales_invoice_no": doc.name,
					"article_code": data.tailoring_item_code,
					"process_allotment": process,
					"stock_entry": stock_entry,
					"fabric_code": data.fabric_code,
					"fabric_qty": data.fabric_qty,
					"article_qty":data.tailoring_qty,
					"size": data.tailoring_size,
					"work_order":work_order,
					"process_status":'Pending',
					"warehouse": data.tailoring_warehouse
				}

def delete_production_process(doc, method):
	for d in doc.get('entries'):
		production_dict = get_dict(doc.name)
		delte_doctype_data(production_dict)

def get_dict(invoice_no):
	return {'Production Dashboard Details':{'sales_invoice_no':invoice_no}}

def delte_doctype_data(production_dict):
	for doctype in production_dict:
		for field in production_dict[doctype]:
			frappe.db.sql("Delete from `tab%s` where %s = '%s'"%(doctype, field, production_dict[doctype][field]))

def validate_sales_invoice(doc, method):
	validate_work_order_assignment(doc)

def add_data_in_work_order_assignment(doc):
	if not doc.get('work_order_distribution'):
		doc.set('work_order_distribution',[])
		for d in doc.get('sales_invoice_items_one'):
			e = doc.append('work_order_distribution', {})
			e.tailoring_item = d.tailoring_item_code
			e.tailor_item_name = d.tailoring_item_name
			e.tailor_qty = d.tailoring_qty
			if not e.tailor_work_order:
				e.tailor_work_order = create_work_order(d)
	return "Done"

def validate_work_order_assignment(doc):
	if doc.get('work_order_distribution') and doc.get('sales_invoice_items_one'):
		for d in doc.get('sales_invoice_items_one'):
			if d.tailoring_item_code and d.tailoring_qty:
				check_work_order_assignment(doc, d.tailoring_item_code, d.tailoring_qty)
	elif not doc.get('work_order_distribution') and not doc.get("__islocal"):
		frappe.throw(_('Mandatory Table: work order distribution'))

def check_work_order_assignment(doc, item_code, qty):
	count = 0
	for d in doc.get('work_order_distribution'):
		if d.tailoring_item == item_code:
			count += cint(d.qty)
	if cint(d.qty) !=  count:
		frappe.throw(_("Qty should be equal"))