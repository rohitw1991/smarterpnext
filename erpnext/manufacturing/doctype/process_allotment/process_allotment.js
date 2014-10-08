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
	console.log(sn_list)
		for(var i=0;i<sn_list.length;i++){
			if (sn_list[i] == serial_no){
				msg="False"
			}
		}
	return msg
}

