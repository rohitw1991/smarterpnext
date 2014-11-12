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

def create_work_order(doc, data, serial_no, item_code):
	wo = frappe.new_doc('Work Order')
 	wo.item_code = item_code
 	wo.customer = doc.customer
 	wo.sales_invoice_no = doc.name
 	wo.customer_name = frappe.db.get_value('Customer',wo.customer,'customer_name')
 	wo.item_qty = data.tailoring_qty
 	wo.serial_no_data = serial_no
 	wo.branch = data.tailoring_warehouse
 	wo.save(ignore_permissions=True)
 	
 	create_work_order_style(data, wo.name, item_code)
 	create_work_order_measurement(data, wo.name, item_code)
 	create_process_wise_warehouse_detail(data, wo.name, item_code)
 	return wo.name

def create_work_order_style(data, wo_name, item_code):
 	if wo_name and item_code:
	 	styles = frappe.db.sql(""" select distinct style, abbreviation from `tabStyle Item` where parent = '%s'
	 		"""%(item_code),as_dict=1)
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

def create_work_order_measurement(data, wo_name, item_code):
	style_parm=[]
 	if wo_name and item_code:
	 	measurements = frappe.db.sql(""" select * from `tabMeasurement Item` where parent = '%s'
	 		"""%(item_code),as_dict=1)
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

def create_process_wise_warehouse_detail(data, wo_name, item_code):
	if wo_name:
		for proc_wh in frappe.db.sql("""select process_name, warehouse, idx from `tabProcess Item`  
			where parent = '%s'"""%item_code,as_list=1):
			mi = frappe.new_doc('Process Wise Warehouse Detail')
 			mi.process = proc_wh[0]
 			mi.warehouse = proc_wh[1]
 			mi.idx = proc_wh[2]
 			mi.parent = wo_name
 			mi.parentfield = 'process_wise_warehouse_detail'
 			mi.parenttype = 'Work Order'
 			mi.save(ignore_permissions =True)
 			

def create_process_allotment(data):
	process_list=[]
	i = 1
	process = frappe.db.sql(""" select distinct process_name,idx from `tabProcess Item` where parent = '%s' order by idx asc
		"""%(data.tailoring_item),as_dict = 1)
	if process:
		for s in process:
			pa = frappe.new_doc('Process Allotment')
		 	pa.sales_invoice_no = data.parent
		 	pa.process_no = i
		 	pa.process = s.process_name
		 	pa.process_work_order = data.tailor_work_order
		 	pa.status = 'Pending'
		 	pa.item = data.tailoring_item
		 	pa.branch = frappe.db.get_value('Process Wise Warehouse Detail',{'parent':data.tailor_work_order,'process':pa.process}, 'warehouse')
		 	pa.serials_data = data.serial_no_data
		 	pa.finished_good_qty = data.tailor_qty
		 	create_material_issue(data, pa)
		 	create_trials(data, pa)
		 	pa.save(ignore_permissions=True)
		 	i= i + 1
		 	process_list.append((pa.name).encode('ascii', 'ignore'))
 	return process_list

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
 		trials = frappe.db.sql("select * from `tabTrial Dates` where parent='%s' and process='%s' order by idx"%(data.trials, obj.process), as_dict=1)
 		if trials:
 			for trial in trials:
 				s = obj.append('trials_transaction',{})
				s.trial_no = trial.idx
				s.trial_date = trial.trial_date
				s.work_order = data.tailor_work_order
				s.status= 'Pending'
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

# def make_trial_transaction(data, args, trial):
# 	s = frappe.new_doc('Trials Transaction')
# 	s.trial_no = trial.trial_no
# 	s.trial_date = trial.trial_date
# 	s.work_order = data.tailor_work_order
# 	s.status= 'Pending'
# 	s.parent = args.get('parent')
# 	s.parenttype = args.get('parenttype')
# 	s.parentfield = 'trials_transaction'
# 	s.save(ignore_permissions=True)
# 	return "Done"

# def make_raw_material_entry(data, args):
# 	if args.get('type') =='invoice':
# 		raw_material = retrieve_fabric_raw_material(data, args)
# 	else:
# 		raw_material = frappe.db.sql("select raw_trial_no, raw_item_code, raw_item_sub_group from `tabRaw Material Item` where raw_process='%s' and raw_trial_no=%s and parent='%s'"%(args.get('process_name'),args.get('trial_no'),args.get('item')),as_dict=1)
# 	if raw_material:
# 		make_entry(raw_material, args)
	return "Done"

# def retrieve_fabric_raw_material(data, args):
# 	return frappe.db.sql("""select '', name as raw_item_code, '' from `tabItem` 
# 	where name = '%s' union  
# 	select raw_trial_no, raw_item_code, raw_item_sub_group 
# 	from `tabRaw Material Item` where parent = '%s'"""%(args.get('item'),args.get('item')), as_dict=1)

# def make_entry(raw_material, args):
# 	for d in raw_material:
# 		s = frappe.new_doc('Issue Raw Material')
# 		s.issue_trial_no = d.raw_trial_no
# 		s.raw_material_item_code = d.raw_item_code
# 		s.raw_material_item_name = frappe.db.get_value('Item',s.raw_material_item_code,'item_name')
# 		s.raw_sub_group = d.raw_item_sub_group
# 		s.parent = args.get('parent')
# 		s.parenttype = args.get('parenttype')
# 		s.parentfield = 'issue_raw_material'
# 		s.uom = frappe.db.get_value('Item',s.raw_material_item_code,'stock_uom')
# 		s.save(ignore_permissions=True)
# 		return "Done"

def create_stock_entry(doc, data):
 	ste = frappe.new_doc('Stock Entry')
 	ste.purpose_type = 'Material Receipt'
 	ste.purpose ='Material Receipt'
 	make_stock_entry_of_child(ste,data)
 	ste.save(ignore_permissions=True)
 	st = frappe.get_doc('Stock Entry', ste.name)
 	st.submit()
 	return ste.name

def prepare_material_for_out(doc, data):
	ste = frappe.new_doc('Stock Entry')
 	ste.purpose_type = 'Material Receipt'
 	ste.purpose ='Material Receipt'
 	make_stock_entry_of_child(ste,data)
 	ste.save(ignore_permissions=True)

def make_stock_entry_of_child(obj, data):
 	if data.tailoring_item:
 		st = obj.append('mtn_details',{})
		st.t_warehouse = frappe.db.get_value('Branch',data.tailor_warehouse,'warehouse')
		st.item_code = data.tailoring_item
		st.serial_no = data.serial_no_data
		st.item_name = frappe.db.get_value('Item', st.item_code, 'item_name')
		st.description = frappe.db.get_value('Item', st.item_code, 'description')
		st.uom = frappe.db.get_value('Item', st.item_code, 'stock_uom')
		st.conversion_factor = 1
		st.qty = data.tailor_qty or 1
		st.transfer_qty = data.tailor_qty or 1
		st.incoming_rate = 1.00
		st.expense_account = 'Stock Adjustment - I'
		st.cost_center = 'Main - I'
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
	pd = create_production_dashboard( process, d, doc)
	if d.trials and pd:
		frappe.db.sql("update `tabTrials` set pdd = '%s' where name='%s'"%(pd, d.trials))

def create_production_dashboard( process, data, doc):
	pd = frappe.new_doc('Production Dashboard Details')
	pd.sales_invoice_no = doc.name
	pd.article_code = data.tailoring_item
	pd.article_qty = data.tailor_qty
	pd.fabric_code = data.tailor_fabric
	pd.warehouse = data.tailor_warehouse
	pd.fabric_qty = data.tailor_fabric_qty
	pd.serial_no = data.serial_no_data
	make_production_process_log(pd, process, data)
	serial_no_log(pd, data)
	pd.save(ignore_permissions=True)
	create_stock_entry(doc, data)
	prepare_material_for_out(doc,data)
	return pd.name

def make_production_process_log(obj, process_list, args):
	process_list =  "','".join(process_list)
	process = frappe.db.sql("""select a.name,a.sales_invoice_no, a.item, a.serials_data, 
		a.process, a.process_work_order, a.branch, b.trial_no, b.trial_date,
		b.work_order from `tabProcess Allotment` a left join `tabTrials Transaction` b on b.parent = a.name 
		where a.name in %s order by a.name, b.trial_no"""%("('"+process_list+"')"), as_dict=1)
	status = 'Pending'
	if process:
		for s in process:
			pl = obj.append('process_log',{})
			pl.process_data = s.name
			pl.process_name = s.process
			pl.branch = s.branch
			pl.trials = s.trial_no
			pl.status = status
			pl.pr_work_order = s.work_order or s.process_work_order

def serial_no_log(obj, data):
	sn = cstr(data.serial_no_data).split('\n')
	for s in sn:
		sn = obj.append('production_status_detail')
		sn.item_code = data.tailoring_item
		sn.serial_no = s
		sn.branch = data.tailor_warehouse
		sn.status = 'Ready'

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
				if s:
					prepare_data_for_order(doc,d, split_qty[s]['qty'])
		else:
			prepare_data_for_order(doc, d, d.tailoring_qty)
	validate_work_order_assignment(doc)
	return "Done"

def prepare_data_for_order(doc, d, qty):
	if cint(frappe.db.get_value('Item', d.tailoring_item_code, 'is_clubbed_product')) == 1:
		sales_bom_items = frappe.db.sql("""Select * FROM `tabSales BOM Item` WHERE 
			parent ='%s' and parenttype = 'Sales Bom'"""%(d.tailoring_item_code), as_dict=1)
		for item in sales_bom_items:
			make_order(doc, d, qty, item.item_code)
	else:
		make_order(doc, d,qty, d.tailoring_item_code)

def make_order(doc, d, qty, item_code):
	if not frappe.db.get_value('Work Order Distribution', {'refer_doc':d.name},'refer_doc'):
		e = doc.append('work_order_distribution', {})
		e.tailoring_item = item_code
		e.tailor_item_name = frappe.db.get_value('Item', item_code, 'item_name')
		e.tailor_qty = qty
		e.serial_no_data = generate_serial_no(doc, item_code, qty)
		e.tailor_fabric= d.fabric_code
		e.refer_doc = d.name
		e.tailor_fabric_qty = d.fabric_qty
		e.tailor_warehouse = d.tailoring_branch
		if not e.tailor_work_order:
			e.tailor_work_order = create_work_order(doc, d, e.serial_no_data, item_code)
		if not e.trials:
			e.trials = make_schedule_for_trials(doc, d, e.tailor_work_order, item_code)
		doc.save(ignore_permissions=True)
	return "Done"

def make_schedule_for_trials(doc, args, work_order, item_code):
	s =frappe.new_doc('Trials')
	s.item_code = item_code
	s.sales_invoice = doc.name
	s.customer = frappe.db.get_value('Sales Invoice', doc.name, 'customer')
	s.item_name = frappe.db.get_value('Item', item_code, 'item_name')
	s.work_order = work_order
	s.save(ignore_permissions=True)
	schedules_date(s.name, item_code)
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
				pass
				# check_work_order_assignment(doc, d.tailoring_item_code, d.tailoring_qty)

def check_work_order_assignment(doc, item_code, qty):
	count = 0
	for d in doc.get('work_order_distribution'):
		if d.tailoring_item == item_code:
			count += cint(d.tailor_qty)
	if cint(qty) !=  count:
		frappe.throw(_("Qty should be equal"))

def create_serial_no(doc, method):
	for d in doc.get('work_order_distribution'):
		if not d.serial_no_data:
			d.serial_no_data = generate_serial_no(doc,d.tailoring_item, d.tailor_qty)

def generate_serial_no(doc, item_code, qty):
	serial_no =''
	temp_qty = qty
	while cint(qty) > 0:
		sn =frappe.new_doc('Serial No')
		sn.name = make_autoname(str(doc.name) + '/.###') 
		sn.serial_no = sn.name
		sn.item_code = item_code
		sn.status = 'Available'
		sn.save(ignore_permissions=True)
		if cint(temp_qty) == qty:
			serial_no = sn.name
		else:
			serial_no += '\n' + sn.name 
		qty = cint(qty) -1
	return serial_no

@frappe.whitelist()
def get_process_detail(name):
	branch = frappe.db.get_value('User',frappe.session.user,'branch')
	return frappe.db.sql("""select process_data, process_name, 
		ifnull(trials,'No') as trials, status from `tabProcess Log` 
		where parent ='%s' and branch = '%s' 
		order by process_data, trials"""%(name, branch),as_dict=1)