cur_frm.cscript.refresh = function(doc, cdt, cdn){
	get_server_fields('get_invoices_list','','', doc, cdt, cdn, 1 , function(){
		refresh_field('admin_note')
	})
}

cur_frm.cscript.update = function(doc, cdt, cdn){
	get_server_fields('authenticate_inv','','', doc, cdt, cdn, 1 , function(){
		refresh_field('admin_note')
	})
}