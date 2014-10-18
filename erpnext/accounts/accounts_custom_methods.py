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
	for d in doc.get('work_order_distribution'):
		# work_order = d.tailoring_work_order if d.tailoring_work_order else create_work_order(d)
		process_allotment = create_process_allotment(d)
		# stock_entry = create_stock_entry(d)
		if process_allotment:
			create_dashboard(process_allotment,d,doc)
			# frappe.db.sql("update `tabSales Invoice Item` set work_order='%s', stock_entry='%s' ,process_allotment='%s' where name='%s'"%(work_order,stock_entry,process_allotment,d.name))

def create_work_order(doc, data):
	wo = frappe.new_doc('Work Order')
 	# wo.sales_invoice_no = doc.name
 	wo.item_code = data.tailoring_item_code
 	wo.customer = doc.customer
 	wo.customer_name = frappe.db.get_value('Customer',wo.customer,'customer_name')
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
 	pa = frappe.new_doc('Process Allotment')
 	pa.sales_invoice_no = data.parent
 	pa.item = data.tailoring_item
 	pa.branch = data.tailor_warehouse
 	pa.finished_good_qty = data.tailor_qty
 	pa.work_order = data.tailor_work_order
 	pa.save(ignore_permissions=True)
 	
 	assign_process(data, pa.name)
 	return pa.name

def assign_process(data, name):
 	if data.tailoring_item:
 		process = frappe.db.sql(""" select distinct process_name from `tabProcess Item` where parent = '%s' order by idx asc
 			"""%(data.tailoring_item),as_dict = 1)
 		if process:
 			for s in process:
 				pr = frappe.new_doc('Process Allotment Log')
 				pr.priority = frappe.db.get_value('Process Item', {'parent':data.tailoring_item,'process_name':s.process_name},'idx')
 				pr.process_log = s.process_name
 				pr.parent = name
 				pr.parenttype = 'Process Allotment'
 				pr.parentfield = 'process_allotment_log'
 				
 				if data.trials:
 					trials = frappe.db.sql("select * from `tabTrial Dates` where process='%s' and parent='%s' order by trial_no"%(s.process_name,data.trials),as_dict=1)
	 				trials_name = ''
	 				if trials:
	 					for trial in trials:
	 						trials_name =frappe.db.get_value('Trials Master',{'sales_invoice_no':data.parent,'process':name,'item_code':data.tailoring_item},'name')
	 						if not trials_name:
	 							trials_name = make_trial(data,data.tailoring_item, name)
	 						if frappe.db.get_value('Process Item',{'parent':data.tailoring_item,'process_name':s.process_name,'trial_no':trial.trial_no,'actual_fabric':1},'name'):
	 							dict_data = {'parent':trials_name, 'trial_no':trial.trial_no,'process_name':s.process_name,'item':data.tailor_fabric,'parenttype':'Trials Master','type':'invoice'}
	 						else:
	 							dict_data = {'parent':trials_name, 'trial_no':trial.trial_no,'process_name':s.process_name,'item':data.tailoring_item,'parenttype':'Trials Master','type':'item'}
	 						make_trial_transaction(data, dict_data, trial)
	 						make_raw_material_entry(data, dict_data)
	 						frappe.db.sql("update `tabTrials Master` set process='%s' where name='%s'"%(name, trials_name))
	 			if trials_name:
 					pr.trials_log = trials_name 				
 				pr.save(ignore_permissions=True)
 				
 				if frappe.db.get_value('Process Item',{'parent':data.tailoring_item,'process_name':s.process_name,'trial_no':'0','actual_fabric':1},'name'):
 					dict_data = {'parent':trials_name, 'trial_no':'0','process_name':s.process_name,'item':data.tailor_fabric,'parenttype':'Process Allotment','type':'invoice'}
 				else:
 					dict_data = {'parent':name, 'trial_no':'0','process_name':s.process_name,'item':data.tailoring_item,'parenttype':'Process Allotment','type':'item'}
 				make_raw_material_entry(data, dict_data)
 	return True

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
	e = doc.append('work_order_distribution', {})
	e.tailoring_item = d.tailoring_item_code
	e.tailor_item_name = d.tailoring_item_name
	e.tailor_qty = qty
	e.tailor_fabric= d.fabric_code
	e.tailor_fabric_qty = d.fabric_qty
	e.tailor_warehouse = d.tailoring_warehouse
	if not e.tailor_work_order:
		e.tailor_work_order = create_work_order(doc, d)
	if not e.trials:
		e.trials = make_schedule_for_trials(doc, d)
	return "Done"

def make_schedule_for_trials(doc, args):
	if cint(frappe.db.get_value('Process Item',{'parent':args.tailoring_item_code,'trial_no':1},'trial_no')) > 0:
		s =frappe.new_doc('Trials')
		s.item_code = args.tailoring_item_code
		s.item_name = args.tailoring_item_name
		s.save(ignore_permissions=True)
		schedules_date(s.name, s.item_code)
		return s.name

def schedules_date(parent, item):
	trials = frappe.db.sql("select process_name, trial_no from `tabProcess Item` where parent='%s' and ifnull(trial_no,0)>0 order by trial_no"%(item), as_dict=1)
	if trials:
		for t in trials:
			d = frappe.new_doc('Trial Dates')
			d.process = t.process_name
			d.trial_no = t.trial_no
			d.idx = t.trial_no
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