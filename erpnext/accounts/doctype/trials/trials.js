cur_frm.cscript.work_order_changes = function(doc, cdt, cdn){

	var d =locals[cdt][cdn]
	if(d.work_order){
		frappe.route_options = { work_order: d.work_order, args: d};
		frappe.set_route("work-order");		
	}else{
		alert("Work order is not defined")
	}
	
}


cur_frm.fields_dict['trial_serial_no'].get_query = function(doc, cdt, cdn) {
      	return {
      		query : "tools.tools_management.custom_methods.get_serial_no",
      		filters : {
      			'serial_no':doc.serial_no_data
      		}
      	}
}

cur_frm.cscript.trial_serial_no = function(doc, cdt, cdn) {
    get_server_fields('update_status', '','',doc, cdt, cdn, 1, function(){
		// hide_field('trial_serial_no');
		refresh_field('trials_serial_no_status')
	})  	
}

cur_frm.cscript.validate= function(doc){
	if(doc.trials_serial_no_status){
		hide_field('trial_serial_no');
	}
}

cur_frm.cscript.refresh= function(doc){
	if(doc.trials_serial_no_status){
		hide_field('trial_serial_no');
	}
}	