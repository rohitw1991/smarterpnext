cur_frm.cscript.onload= function(doc ,cdt,cdn){
	get_server_fields('get_invoice_details', '','',doc,cdt,cdn , 1 , function(){
		refresh_field('production_details')
	})
}

cur_frm.cscript.sales_invoice_no = function(doc, cdt, cdn){
	get_server_fields('get_invoice_details', doc.sales_invoice_no,'',doc,cdt,cdn , 1 , function(){
		refresh_field('production_details')
	})	
}

cur_frm.cscript.search = function(doc, cdt, cdn){
	console.log(doc.sales_invoice_no)
	cur_frm.cscript.sales_invoice_no(doc, cdt, cdn)
}

cur_frm.cscript.select = function(doc, cdt, cdn){
	var d =locals[cdt][cdn]
	get_server_fields('save_data',d,'',doc, cdt,cdn,1,function(){
		refresh_field('production_details')
	})
}

cur_frm.cscript.refresh = function(doc, cdt, cdn){
	get_server_fields('clear_data','','',doc, cdt,cdn,1,function(){
		refresh_field('production_details')
	})
}

cur_frm.fields_dict['sales_invoice_no'].get_query = function(doc) {
	return {
		filters: {
			"docstatus": 1,
		}
	}
}

cur_frm.fields_dict.production_details.grid.get_field("process_allotment").get_query = function(doc, cdt, cdn) {
	var d = locals[cdt][cdn]
	return {
		filters: {
			"sales_invoice_no": d.sales_invoice,
			"docstatus": 0 || 1,
			"item": d.article_code
		}
	}
}

cur_frm.fields_dict.production_details.grid.get_field("work_order").get_query = function(doc, cdt, cdn) {
	var d = locals[cdt][cdn]
	return {
		filters: {
			"sales_invoice_no": d.sales_invoice,
			"docstatus": 0 || 1,
			"item_code": d.article_code
		}
	}
}
