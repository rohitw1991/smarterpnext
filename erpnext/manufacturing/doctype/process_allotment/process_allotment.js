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
	d.trial_change_status='Yes'
	refresh_field('trials_transaction')
	// get_server_fields('on_status_trigger_method',d,'',doc, cdt, cdn, 1, function(){
	// 	refresh_field('wo_process')
	// })
}

cur_frm.fields_dict['serial_no'].get_query = function(doc) {
	return {
		filters: {
			"item_code": doc.item
		}
	}
}

var sn_list=[]
cur_frm.cscript.refresh = function(doc, cdt, cdn){
	sn_list=[];
	cur_frm.cscript.toogle_field(doc)
	get_server_fields('show_trials_details', '','',doc, cdt, cdn, 1, function(){
		refresh_field('trials_transaction')
	})
}

cur_frm.cscript.add = function(doc ,cdt , cdn){
	s = check_serial_exist(sn_list, doc.serial_no)
	if(s=='Done')
	{
		if (doc.serial_no && doc. serials_data){
			doc.serials_data = doc.serials_data + '\n' + doc.serial_no
		}
		else{
			doc.serials_data = doc.serial_no
		}
		sn_list.push(doc.serial_no)
	}
	else{
		alert("Serial no already exist")
	}
	refresh_field('serials_data')

}

function check_serial_exist(sn_list, serial_no){
	msg = "Done"
		for(var i=0;i<sn_list.length;i++){
			if (sn_list[i] == serial_no){
				msg="False"
			}
		}
	return msg
}

cur_frm.cscript.process_status= function(doc, cdt, cdn){
	doc.process_status_changes = 'Yes'
	refresh_field('process_status_changes')
}

cur_frm.cscript.emp_status= function(doc, cdt, cdn){
	doc.process_status = 'Open'
	cur_frm.cscript.toogle_field(doc)
	refresh_field(['process_status', 'completed_time', 'from_time'])
}

cur_frm.cscript.toogle_field = function(doc){
	hide_field(['wages', 'extra_charge_amount', 'latework', 'cost'])
	if (doc.emp_status=='Completed')
	{
		doc.process_status = 'Closed'
		hide_field(['estimated_time', 'start_date', 'end_date']);
		unhide_field(['from_time', 'completed_time', 'payment', 'extra_charge', 'deduct_late_work']);
	}else if(doc.emp_status=='Assigned'){
		unhide_field(['start_date', 'end_date', 'estimated_time'])
		hide_field(['from_time', 'completed_time', 'payment', 'extra_charge', 'deduct_late_work']);
		doc.completed_time = ''
		doc.from_time = ''
	}
}

cur_frm.cscript.assigned= function(doc, cdt, cdn){
	get_server_fields('assign_task_to_employee','','',doc, cdt, cdn,1, function(){
		refresh_field('employee_details')	
	})
	
}

cur_frm.cscript.deduct_late_work = function(doc){
	if(doc.deduct_late_work == 'Yes'){
		unhide_field(['latework', 'cost']);		
	}else{
		hide_field(['latework', 'cost']);
	}
}

cur_frm.cscript.work_qty = function(doc, cdt, cdn){
	get_server_fields('calculate_estimates_time','','',doc, cdt, cdn,1, function(){
		refresh_field('estimated_time')	
	})
	
}

cur_frm.cscript.payment = function(doc, cdt, cdn){
	if(doc.payment == 'Yes'){
		unhide_field('wages');		
	}else{
		hide_field('wages');	
	}
	
	get_server_fields('calculate_wages','','',doc, cdt, cdn,1, function(){
		refresh_field('wages')	
	})
}

cur_frm.cscript.latework = function(doc, cdt, cdn){
	get_server_fields('calc_late_work_amt','','',doc, cdt, cdn,1, function(){
		refresh_field('cost')	
	})
	
}

cur_frm.cscript.validate = function(doc, cdt, cdn){
	setTimeout(function(){refresh_field(['employee_details', 'task'])},1000)
	
}

cur_frm.cscript.extra_charge = function(doc){
	if(doc.extra_charge == 'Yes'){
		unhide_field('extra_charge_amount');		
	}else{
		hide_field('extra_charge_amount');	
	}
}


cur_frm.cscript.process_trials = function(doc, cdt, cdn){
	if(doc.process_trials){
		get_server_fields('get_trial_serial_no', '', '', doc, cdt, cdn, 1, function(){
			refresh_field(['serial_no_data', 'work_qty'])
		})
	}
}

cur_frm.fields_dict['serial_no'].get_query = function(doc) {
	return{
		query: "erpnext.accounts.accounts_custom_methods.get_serial_no",
		filters: {'branch': doc.branch, 'process': doc.process, 'work_order': doc.process_work_order, 'trial_no':doc.process_trials}
	}
}