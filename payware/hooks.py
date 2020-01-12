# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from . import __version__ as app_version

app_name = "payware"
app_title = "Payware"
app_publisher = "Aakvatech"
app_description = "Payware Payroll System"
app_icon = "octicon octicon-file-directory"
app_color = "grey"
app_email = "info@aakvatech.com"
app_license = "MIT"

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/payware/css/payware.css"
# app_include_js = "/assets/payware/js/payware.js"

# include js, css files in header of web template
# web_include_css = "/assets/payware/css/payware.css"
# web_include_js = "/assets/payware/js/payware.js"

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {
	"Loan" : "payware/loan.js",
	"Additional Salary" : "payware/additional_salary.js",
}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
#	"Role": "home_page"
# }

# Website user home page (by function)
# get_website_user_home_page = "payware.utils.get_home_page"

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Installation
# ------------

# before_install = "payware.install.before_install"
# after_install = "payware.install.after_install"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "payware.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

fixtures = [
	{"doctype":"Print Format", "filters": [{"module":"Payware"}]},
	{"doctype":"Report", "filters": [{"module":"Payware"}]},
	{"doctype":"Custom Field", "filters": [["_user_tags", "like", ("%payware%")]]},
	{"doctype":"Property Setter", "filters": [["_user_tags", "like", ("%payware%")]]},
]

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"Loan": {
		"on_submit": "payware.payware.utils.create_disbursement_journal_entry",
		"validate": "payware.payware.utils.validate_loan"
	},
	"Salary Slip": {
		"on_submit": "payware.payware.utils.set_loan_paid",
		"on_cancel": "payware.payware.utils.set_loan_paid",
		"before_insert": "payware.payware.salary_slip_hook.generate_component_in_salary_slip_insert",
		"before_save": "payware.payware.salary_slip_hook.generate_component_in_salary_slip_update"
	},
	"Loan Repayment Not From Salary": {
		"on_submit": "payware.payware.utils.create_loan_repayment_jv",
		"validate": "payware.payware.utils.validate_loan_repayment_nfs",
		"on_cancel": "payware.payware.utils.create_loan_repayment_jv"
	},
	"Additional Salary": {
		"on_submit": "payware.payware.utils.create_additional_salary_journal",
		"on_cancel": "payware.payware.utils.create_additional_salary_journal"
	},
	"Employee": {
		"validate": "payware.payware.doctype.biometric_settings.biometric_settings.check_employee_bio_info"
	},
}

# Scheduled Tasks
# ---------------

scheduler_events = {
# 	"all": [
# 		"payware.tasks.all"
# 	],
 	"daily": [
 		"payware.payware.utils.generate_additional_salary_records",
		 "payware.payware.doctype.biometric_settings.biometric_settings.auto_shift_assignment_for_active_today"

 	],
	"hourly": [
		"payware.payware.doctype.biometric_settings.biometric_settings.auto_get_transactions",
		"payware.payware.doctype.biometric_settings.biometric_settings.auto_make_employee_checkin"
	]
# 	"weekly": [
# 		"payware.tasks.weekly"
# 	]
# 	"monthly": [
# 		"payware.tasks.monthly"
# 	]
}

# Testing
# -------

# before_tests = "payware.install.before_tests"

# Overriding Whitelisted Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "payware.event.get_events"
# }
