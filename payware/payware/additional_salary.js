frappe.ui.form.on('Additional Salary', {
	refresh: function(frm) {
		cur_frm.add_custom_button(__("Generate Additional Salary Records"), function() {
			generate_additional_salary_records();
		});
	}
});
var generate_additional_salary_records = function(){
	frappe.call({
		method: "payware.payware.utils.generate_additional_salary_records",
		args: {},
		callback: function(){
			cur_frm.reload_doc();
		}
	});
};
