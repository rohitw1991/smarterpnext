cur_frm.cscript.work_order_changes = function(doc, cdt, cdn){

	var d =locals[cdt][cdn]
	if(d.work_order){
		frappe.route_options = { work_order: d.work_order, args: d};
		frappe.set_route("work-order");		
	}else{
		alert("Work order is not defined")
	}
	
}
