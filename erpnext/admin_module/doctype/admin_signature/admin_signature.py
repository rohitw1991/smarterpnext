# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class AdminSignature(Document):
	def get_invoices_list(self):
		self.set('admin_note', [])
		inv = frappe.db.sql(""" select name from `tabSales Invoice` where docstatus = 1
			and ifnull(authenticated, 'No') = 'No'""", as_dict=1)
		if inv:
			for s in inv:
				ad = self.append('admin_note', {})
				ad.sales_invoice = s.name
		return "Done"

	def authenticate_inv(self):
		for s in self.get('admin_note'):
			if s.sales_invoice and s.note:
				frappe.db.sql(""" update `tabSales Invoice` set admin_authentication_note = '%s', authenticated='Yes'
					where name ='%s'"""%(s.note, s.sales_invoice))
		self.get_invoices_list()
		return "Done"