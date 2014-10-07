cur_frm.fields_dict.trials_transaction.grid.get_field("trial_good_serial_no").get_query = function(doc, cdt, cdn) {
	var d = locals[cdt][cdn]
	return {
		filters: {
			"item_code": d.trial_product
		}
	}
}