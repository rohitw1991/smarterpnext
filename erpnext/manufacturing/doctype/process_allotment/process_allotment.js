cur_frm.add_fetch('raw_material_item_code', 'item_name', 'raw_material_item_name')
cur_frm.add_fetch('raw_material_item_code', 'stock_uom', 'uom')

cur_frm.fields_dict['sales_invoice_no'].get_query = function(doc) {
	return {
		filters: {
			"docstatus": 1,
		}
	}
}

cur_frm.cscript.item = function(doc, cdt, cdn){
	get_server_fields('get_details',doc.item,'',doc ,cdt, cdn,1, function(){
		refresh_field('wo_process')
	})
}


cur_frm.cscript.status = function(doc, cdt, cdn){
	var d = locals[cdt][cdn]
	get_server_fields('set_completion_date',d.idx,'',doc, cdt, cdn, 1, function(){
		refresh_field('wo_process')
	})
}