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
from frappe.model.naming import make_autoname

def create_production_process(doc, method):
	for d in doc.get('work_order_distribution'):
		process_allotment = create_process_allotment(d)
		if process_allotment:
			create_dashboard(process_allotment,d,doc)

def create_work_order(doc, data, serial_no):
	wo = frappe.new_doc('Work Order')
 	wo.item_code = data.tailoring_item_code
 	wo.customer = doc.customer
 	wo.customer_name = frappe.db.get_value('Customer',wo.customer,'customer_name')
 	wo.item_qty = data.tailoring_qty
 	wo.serial_no_data = serial_no
 	wo.branch = data.tailoring_warehouse
 	wo.save(ignore_permissions=True)
 	
 	create_work_order_style(data, wo.name)
 	create_work_order_measurement(data, wo.name)
 	create_process_wise_warehouse_detail(data, wo.name)
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

def create_process_wise_warehouse_detail(data, wo_name):
	if wo_name:
		for proc_wh in frappe.db.sql("""select process_name, warehouse from `tabProcess Item`  
			where parent = '%s'"""%data.tailoring_item_code,as_list=1, debug=1):
			mi = frappe.new_doc('Process Wise Warehouse Detail')
 			mi.process = proc_wh[0]
 			mi.warehouse = proc_wh[1]
 			mi.parent = wo_name
 			mi.parentfield = 'process_wise_warehouse_detail'
 			mi.parenttype = 'Work Order'
 			mi.save(ignore_permissions =True)
 			

def create_process_allotment(data):
	process = frappe.db.sql(""" select distinct process_name from `tabProcess Item` where parent = '%s' order by idx asc
		"""%(data.tailoring_item),as_dict = 1)
	if process:
		for s in process:
			pa = frappe.new_doc('Process Allotment')
		 	pa.sales_invoice_no = data.parent
		 	pa.process = s.process_name
		 	pa.status = 'Pending'
		 	pa.item = data.tailoring_item
		 	pa.branch = frappe.db.get_value('Process Wise Warehouse Detail',{'parent':data.tailor_work_order,'process':pa.process}, 'warehouse')
		 	pa.serials_data = data.serial_no_data
		 	pa.finished_good_qty = data.tailor_qty
		 	create_material_issue(data, pa)
		 	create_trials(data, pa)
		 	pa.save(ignore_permissions=True)
 	return pa.name

def create_material_issue(data, obj):
 	if data.tailoring_item:
 		rm = frappe.db.sql("select * from `tabRaw Material Item` where parent='%s' and raw_process='%s'"%(data.tailoring_item, obj.process),as_dict=1)
 		if rm:
 			for s in rm:
 				d = obj.append('issue_raw_material',{})
 				d.raw_material_item_code = s.raw_item_code
 				d.raw_material_item_name = frappe.db.get_value('Item',s.raw_item_code,'item_name')
 				d.raw_sub_group = s.raw_item_sub_group or frappe.db.get_value('Item',s.raw_item_code,'item_sub_group')
 				d.uom = frappe.db.get_value('Item',s.raw_item_code,'stock_uom')
 	return True

def create_trials(data, obj):
 	if data.trials:
 		trials = frappe.db.sql("select * from `tabTrial Dates` where parent='%s' and process='%s'"%(data.trials, obj.process), as_dict=1)
 		if trials:
 			for trial in trials:
 				s = obj.append('trials_transaction',{})
				s.trial_no = trial.idx
				s.trial_date = trial.trial_date
				s.work_order = data.tailor_work_order
				s.status= 'Pending'
				# s.parent = args.get('parent')
				# s.parenttype = args.get('parenttype')
				# s.parentfield = 'trials_transaction'
				# s.save(ignore_permissions=True)
	return "Done"

def make_trial(data, item_code, parent):
	s= frappe.new_doc('Trials Master')
	s.sales_invoice_no = data.parent
	s.customer = frappe.db.get_value('Sales Invoice',data.parent,'customer')
	s.item_code = item_code
	s.item_name = frappe.db.get_value('Item',s.item_code,'item_name')
	s.process = parent
	s.save(ignore_permissions=True)
	return s.name

def make_trial_transaction(data, args, trial):
	s = frappe.new_doc('Trials Transaction')
	s.trial_no = trial.trial_no
	s.trial_date = trial.trial_date
	s.work_order = data.tailor_work_order
	s.status= 'Pending'
	s.parent = args.get('parent')
	s.parenttype = args.get('parenttype')
	s.parentfield = 'trials_transaction'
	s.save(ignore_permissions=True)
	return "Done"

def make_raw_material_entry(data, args):
	if args.get('type') =='invoice':
		raw_material = retrieve_fabric_raw_material(data, args)
	else:
		raw_material = frappe.db.sql("select raw_trial_no, raw_item_code, raw_item_sub_group from `tabRaw Material Item` where raw_process='%s' and raw_trial_no=%s and parent='%s'"%(args.get('process_name'),args.get('trial_no'),args.get('item')),as_dict=1)
	if raw_material:
		make_entry(raw_material, args)
	return "Done"

def retrieve_fabric_raw_material(data, args):
	return frappe.db.sql("""select '', name as raw_item_code, '' from `tabItem` 
	where name = '%s' union  
	select raw_trial_no, raw_item_code, raw_item_sub_group 
	from `tabRaw Material Item` where parent = '%s'"""%(args.get('item'),args.get('item')), as_dict=1)

def make_entry(raw_material, args):
	for d in raw_material:
		s = frappe.new_doc('Issue Raw Material')
		s.issue_trial_no = d.raw_trial_no
		s.raw_material_item_code = d.raw_item_code
		s.raw_material_item_name = frappe.db.get_value('Item',s.raw_material_item_code,'item_name')
		s.raw_sub_group = d.raw_item_sub_group
		s.parent = args.get('parent')
		s.parenttype = args.get('parenttype')
		s.parentfield = 'issue_raw_material'
		s.uom = frappe.db.get_value('Item',s.raw_material_item_code,'stock_uom')
		s.save(ignore_permissions=True)
	return "Done"

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

def create_dashboard(process, d ,doc):
	production_dict = get_production_dict( process, d, doc)
	production = frappe.get_doc(production_dict).insert(ignore_permissions=True)

def get_production_dict( process, data, doc):
		return {
					"doctype": "Production Dashboard Details",
					"sales_invoice_no": doc.name,
					"article_code": data.tailoring_item,
					"process_allotment": process,
					"fabric_code": data.tailor_fabric,
					"fabric_qty": data.tailor_fabric_qty,
					#"article_qty":data.tailoring_qty,
					#"size": data.tailoring_size,
					"process_status":'Pending',
					"warehouse": data.tailor_warehouse
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

def add_data_in_work_order_assignment(doc, method):
	if not doc.get('work_order_distribution'):
		doc.set('work_order_distribution',[])
	for d in doc.get('sales_invoice_items_one'):
		if cint(d.check_split_qty)==1:
			split_qty = eval(d.split_qty_dict)
			for s in split_qty:
				make_order(doc,d, s)
		else:
			make_order(doc, d, d.tailoring_qty)
	validate_work_order_assignment(doc)
	return "Done"

def make_order(doc, d, qty):
	if not frappe.db.get_value('Work Order Distribution', {'refer_doc':d.name},'refer_doc'):
		e = doc.append('work_order_distribution', {})
		e.tailoring_item = d.tailoring_item_code
		e.tailor_item_name = d.tailoring_item_name
		e.tailor_qty = qty
		e.serial_no_data = generate_serial_no(d.tailoring_item_code, qty)
		e.tailor_fabric= d.fabric_code
		e.refer_doc = d.name
		e.tailor_fabric_qty = d.fabric_qty
		e.tailor_warehouse = d.tailoring_warehouse
		if not e.tailor_work_order:
			e.tailor_work_order = create_work_order(doc, d, e.serial_no_data)
		if not e.trials:
			e.trials = make_schedule_for_trials(doc, d, e.tailor_work_order)
	return "Done"

def make_schedule_for_trials(doc, args, work_order):
	s =frappe.new_doc('Trials')
	s.item_code = args.tailoring_item_code
	s.item_name = args.tailoring_item_name
	s.work_order = work_order
	s.save(ignore_permissions=True)
	schedules_date(s.name, s.item_code)
	return s.name

def schedules_date(parent, item):
	trials = frappe.db.sql("select branch_dict from `tabProcess Item` where parent='%s' order by idx"%(item), as_dict=1)
	if trials:
		for t in trials:
			if t.branch_dict:
				branch_dict = eval(t.branch_dict)
				for s in range(0, len(branch_dict)):
					d = frappe.new_doc('Trial Dates')
					d.process = branch_dict.get(cstr(s)).get('process')
					d.trial_no = branch_dict.get(cstr(s)).get('trial')
					d.idx = cstr(s + 1)
					d.parent = parent
					d.parenttype = 'Trials'
					d.parentfield = 'trial_dates'
					d.save(ignore_permissions=True)
	return "Done"

def validate_work_order_assignment(doc):
	if doc.get('work_order_distribution') and doc.get('sales_invoice_items_one'):
		for d in doc.get('sales_invoice_items_one'):
			if d.tailoring_item_code and d.tailoring_qty:
				check_work_order_assignment(doc, d.tailoring_item_code, d.tailoring_qty)

def check_work_order_assignment(doc, item_code, qty):
	count = 0
	for d in doc.get('work_order_distribution'):
		if d.tailoring_item == item_code:
			count += cint(d.tailor_qty)
	frappe.errprint([qty, count])
	if cint(qty) !=  count:
		frappe.throw(_("Qty should be equal"))

def create_serial_no(doc, method):
	for d in doc.get('work_order_distribution'):
		if not d.serial_no_data:
			d.serial_no_data = generate_serial_no(d.tailoring_item, d.tailor_qty)

def generate_serial_no(item_code, qty):
	serial_no =''
	while cint(qty) > 0:
		sn =frappe.new_doc('Serial No')
		sn.name = make_autoname(frappe.db.get_value('Item', item_code,'serial_no_series') or 'SN.######') 
		sn.serial_no = sn.name
		sn.item_code = item_code
		sn.status = 'Available'
		sn.save(ignore_permissions=True)
		serial_no += '\n' + sn.name 
		qty = qty -1
	return serial_no