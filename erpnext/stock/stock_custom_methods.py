# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.widgets.reportview import get_match_cond
from frappe.utils import add_days, cint, cstr, date_diff, rounded, flt, getdate, nowdate, \
	get_first_day, get_last_day,money_in_words, now
from frappe import _
from frappe.model.db_query import DatabaseQuery

def update_status(doc, method):
	change_stock_entry_status(doc, 'Completed')

def change_stock_entry_status(doc, status):
	frappe.db.sql(""" update `tabProduction Dashboard Details` 
					set rm_status='%s', cut_order_status='%s'
					where stock_entry='%s'"""%(status, status ,doc.name))

def cancel_status(doc, method):
	change_stock_entry_status(doc, 'Pending')
	# set_to_null(doc)

def set_to_null(self):
	frappe.db.sql(""" update `tabProduction Dashboard Details` 
				set stock_entry=(select name from tabCustomer where 1=2)
				where sales_invoice_no='%s' and article_code='%s' 
				and work_order='%s'"""%(self.sales_invoice_no, self.item_code, self.name))

def stock_out_entry(doc, method):
	if doc.purpose_type == 'Material Out':
		in_entry  = make_stock_entry_for_in(doc)
	pass

def make_stock_entry_for_in(doc):
	branch_list = {}
	for s in doc.get('mtn_details'):
		if branch_list and branch_list.get(s.target_branch):
			make_stock_entry_for_child(s, branch_list[s.target_branch])
		else:
			name = make_stock_entry(doc, s.target_branch)
			make_stock_entry_for_child(s, name)
		branch_list.setdefault(s.target_branch, name)
	return name

def make_stock_entry(doc, target_branch):
	se = frappe.new_doc('Stock Entry')
	se.purpose_type = 'Material In'
	se.purpose = 'Material Receipt'
	se.stock_in = doc.name
	se.branch = target_branch
	se.save(ignore_permissions=True)
	return se.name

def make_stock_entry_for_child(s, name):
	sed = frappe.new_doc('Stock Entry Detail')
	sed.item_code = s.item_code
	sed.t_warehouse = frappe.db.get_value('Branches', s.target_branch, 'warehouse')
	sed.source_warehouse = s.s_warehouse
	sed.item_name = s.item_name
	sed.description = s.description
	sed.qty = s.qty
	sed.conversion_factor = s.conversion_factor
	sed.uom = s.uom
	sed.incoming_rate = s.incoming_rate
	sed.serial_no = s.serial_no
	sed.batch_no = s.batch_no
	sed.expense_account = s.expense_account
	sed.cost_center = s.cost_center
	sed.transfer_qty = s.transfer_qty
	sed.parenttype = s.parenttype
	sed.parentfield = s.parentfield
	sed.parent = name
	sed.save(ignore_permissions=True)
	return "Done"

def in_stock_entry(doc, method):
	pass

@frappe.whitelist()
def get_details(item_name):
	return frappe.db.sql("""select file_url,attached_to_name from `tabFile Data` 
		where attached_to_name ='%s'"""%(item_name),as_list=1)

def item_validate_methods(doc, method):
	manage_price_list(doc)
	make_sales_bom(doc)


def manage_price_list(doc):
	for d in doc.get('costing_item'):
		update_price_list(d)

def update_price_list(args):
	data = args
	args = eval(args.costing_dict)
	parent_list = []
	for s in range(0, len(args)):
		parent = frappe.db.get_value('Item Price', {'item_code':data.get('parent'), 'price_list':args.get(str(s)).get('price_list')},'name')
		if not parent:
			parent = make_item_price(data.get('parent'), args.get(str(s)).get('price_list'))
		parent_list.append(parent.encode('ascii', 'ignore'))
		update_item_price(parent, data, args.get(str(s)).get('rate'))
	delete_non_present_entry(parent_list, data)
	return "Done"

def make_item_price(item_code, price_list):
	ip = frappe.new_doc('Item Price')
	ip.price_list = price_list
	ip.item_code = item_code
	ip.item_name = frappe.db.get_value('Item Name', item_code, 'item_name')
	ip.price_list_rate = 1.00
	ip.currency = frappe.db.get_value('Price List', price_list, 'currency')  
	ip.save(ignore_permissions=True)
	return ip.name

def update_item_price(parent,data, rate):
	frappe.errprint(parent)
	name = frappe.db.get_value('Customer Rate', {'parent':parent, 'branch': data.get('branch'), 'size': data.get('size')}, 'name')
	item_price_dict = get_dict(parent, data, rate)
	if not name:
		name = frappe.get_doc(item_price_dict).insert()
	elif name:
		frappe.db.sql("update `tabCustomer Rate` set rate='%s' where name='%s'"%(rate, name))
	return True

def get_dict(parent, data, rate):
	return {
				"doctype": "Customer Rate",
				"parent": parent,
				"branch": data.get('branch'),
				"parenttype": "Item Price",
				'parentfield': "customer_rate",
				"size":data.get('size'),
				"rate": rate,
			}

def delete_non_present_entry(parent, data):
	parent =  "','".join(parent)
	frappe.db.sql("delete from `tabCustomer Rate` where parent not in %s and branch='%s' and size='%s'"%("('"+parent+"')", data.branch, data.size), debug=1)

def make_sales_bom(doc):
	doc.name
	# parent = frappe.db.get_value('Sales Bom' {'new_item_code', })
	# if cint(doc.is_clubbed_product) == 1 && 