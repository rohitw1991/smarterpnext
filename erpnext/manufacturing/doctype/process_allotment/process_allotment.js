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
	if (doc.emp_status=='Completed')
	{
		doc.process_status = 'Closed'	
	}
	doc.completed_time = ''
	doc.from_time = ''
	refresh_field(['process_status', 'completed_time', 'from_time'])
}

cur_frm.cscript.assigned= function(doc, cdt, cdn){
	get_server_fields('assign_task_to_employee','','',doc, cdt, cdn,1, function(){
		refresh_field('employee_details')	
	})
	
}

cur_frm.cscript.work_qty = function(doc, cdt, cdn){
	get_server_fields('calculate_estimates_time','','',doc, cdt, cdn,1, function(){
		refresh_field('estimated_time')	
	})
	
}

cur_frm.cscript.payment = function(doc, cdt, cdn){
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