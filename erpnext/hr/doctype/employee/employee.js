// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide("erpnext.hr");
erpnext.hr.EmployeeController = frappe.ui.form.Controller.extend({
	setup: function() {
		this.frm.fields_dict.user_id.get_query = function(doc, cdt, cdn) {
			return { query:"frappe.core.doctype.user.user.user_query"} }
		this.frm.fields_dict.reports_to.get_query = function(doc, cdt, cdn) {
			return { query: "erpnext.controllers.queries.employee_query"} }
	},

	onload: function(doc, dt, dn) {

		// cur_frm.cscript.skill_onload(doc, dt, dn)
	
		if(this.frm.doc.__islocal) this.frm.set_value("employee_name", "");

		this.frm.set_query("leave_approver", "employee_leave_approvers", function() {
			return {
				filters: [["UserRole", "role", "=", "Leave Approver"]]
			}
		});
	},

	refresh: function() {
		var me = this;
		erpnext.toggle_naming_series();
		if(!this.frm.doc.__islocal && this.frm.doc.__onload &&
			!this.frm.doc.__onload.salary_structure_exists) {
			    cur_frm.add_custom_button(__('Make Salary Structure'), function() {
					me.make_salary_structure(this); }, frappe.boot.doctype_icons["Salary Structure"]);
		}
		
	},

	validate:function(doc, dt, dn){

		cur_frm.cscript.skill_validate(doc, dt, dn)
	},

	date_of_birth: function() {
		return cur_frm.call({
			method: "get_retirement_date",
			args: {date_of_birth: this.frm.doc.date_of_birth}
		});
	},

	salutation: function() {
		if(this.frm.doc.salutation) {
			this.frm.set_value("gender", {
				"Mr": "Male",
				"Ms": "Female"
			}[this.frm.doc.salutation]);
		}
	},


	make_salary_structure: function(btn) {
		frappe.model.open_mapped_doc({
			method: "erpnext.hr.doctype.employee.employee.make_salary_structure",
			frm: cur_frm
		});
	}
});
cur_frm.cscript = new erpnext.hr.EmployeeController({frm: cur_frm});



cur_frm.cscript.skill_onload = function(doc, dt, dn) {
		console.log("in the onload")
		if(!cur_frm.skill_editor) {
			var skill_area = $('<div style="min-height: 300px">')
				.appendTo(cur_frm.fields_dict.skills_html.wrapper);
			cur_frm.skill_editor = new frappe.SkillEditor(skill_area);
		} else {
			cur_frm.skill_editor.show();
		}
}


cur_frm.cscript.skill_validate = function(doc) {
	console.log("in the skill_validate")
	if(cur_frm.skill_editor) {
		cur_frm.skill_editor.set_skills_in_table()
	}
}


frappe.SkillEditor = Class.extend({
	init: function(wrapper) {
		var me = this;
		this.wrapper = wrapper;
		$(wrapper).html('<div class="help">Loading...</div>')
		return frappe.call({
			method: 'erpnext.hr.doctype.employee.employee.get_all_skills',
			callback: function(r) {
				me.skills = r.message;
				console.log(me.skills)
				me.show_skills();

				// refresh call could've already happened
				// when all role checkboxes weren't created
				if(cur_frm.doc) {
					cur_frm.skill_editor.show();
				}
			}
		});
	},
	show_skills: function() {
		var me = this;
		$(this.wrapper).empty();
		var skill_toolbar = $('<p><button class="btn btn-default btn-add"></button>\
			<button class="btn btn-default btn-remove"></button></p>').appendTo($(this.wrapper));

		skill_toolbar.find(".btn-add")
			.html(__('Add all Skills'))
			.on("click", function() {
			$(me.wrapper).find('input[type="checkbox"]').each(function(i, check) {
				if(!$(check).is(":checked")) {
					check.checked = true;
				}
			});
		});

		skill_toolbar.find(".btn-remove")
			.html(__('Clear all skills'))
			.on("click", function() {
			$(me.wrapper).find('input[type="checkbox"]').each(function(i, check) {
				if($(check).is(":checked")) {
					check.checked = false;
				}
			});
		});

		$.each(this.skills, function(i, skill) {
			// console.log(skill)
			$(me.wrapper).append(repl('<div class="user-role" \
				data-user-role="%(skill)s">\
				<input type="checkbox" style="margin-top:0px;">%(skill)s</div>', {skill: skill}));
		});

		$(this.wrapper).find('input[type="checkbox"]').change(function() {
			cur_frm.dirty();
		});
	
	},

	show: function() {
		var me = this;

		// uncheck all roles
		$(this.wrapper).find('input[type="checkbox"]')
			.each(function(i, checkbox) { checkbox.checked = false; });

		// set user roles as checked
		$.each((cur_frm.doc.employeeskills || []), function(i, user_skill) {

				var checkbox = $(me.wrapper)
					.find('[data-user-role="'+user_skill.skill+'"] input[type="checkbox"]').get(0);
				if(checkbox) checkbox.checked = true;
			});
	},
	set_skills_in_table: function() {
		var opts = this.get_skills();
		var existing_roles_map = {};
		var existing_roles_list = [];

		$.each((cur_frm.doc.employeeskills || []), function(i, user_skill) {
			// console.log(user_skill)
				existing_roles_map[user_skill.skill] = user_skill.name;
				existing_roles_list.push(user_skill.skill);
			});

		// remove unchecked roles
		$.each(opts.unchecked_roles, function(i, skill) {
			if(existing_roles_list.indexOf(skill)!=-1) {
				frappe.model.clear_doc("EmployeeSkill", existing_roles_map[skill]);
			}
		});

		// add new roles that are checked
		$.each(opts.checked_roles, function(i, skill) {
			if(existing_roles_list.indexOf(skill)==-1) {
				var user_skill = frappe.model.add_child(cur_frm.doc, "EmployeeSkill", "employeeskills");
				console.log(user_skill)
				user_skill.skill = skill;
			}
		});

		refresh_field("employeeskills");
	},

	get_skills: function() {
		var checked_roles = [];
		var unchecked_roles = [];
		$(this.wrapper).find('[data-user-role]').each(function() {
			if($(this).find('input[type="checkbox"]:checked').length) {
				checked_roles.push($(this).attr('data-user-role'));
			} else {
				unchecked_roles.push($(this).attr('data-user-role'));
			}
		});

		return {
			checked_roles: checked_roles,
			unchecked_roles: unchecked_roles
		}
	},

});

