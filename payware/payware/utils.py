from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from dateutil.relativedelta import relativedelta
from frappe.utils import cint, flt, nowdate, add_days, getdate, fmt_money, add_to_date, DATE_FORMAT, date_diff
from frappe import _
from erpnext.accounts.utils import get_fiscal_year
from erpnext.hr.doctype.employee.employee import get_holiday_list_for_employee

@frappe.whitelist()
def create_disbursement_journal_entry(doc, method):
	#frappe.msgprint("Method fired: " + method)
	precision = frappe.get_precision("Journal Entry Account", "debit_in_account_currency")

	journal_entry = frappe.new_doc('Journal Entry')
	journal_entry.voucher_type = 'Bank Entry'
	journal_entry.user_remark = _('Payment of {0} disbursed on {1} starting from {2}')\
		.format(doc.name, doc.disbursement_date, doc.repayment_start_date)
	journal_entry.company = doc.company
	journal_entry.posting_date = doc.disbursement_date

	payment_amount = flt(doc.loan_amount, precision)

	journal_entry.set("accounts", [
		{
			"account": doc.loan_account,
			"credit_in_account_currency": payment_amount,
			"reference_type": doc.doctype,
			"reference_name": doc.name
		},
		{
			"account": doc.payment_account,
			"debit_in_account_currency": payment_amount,
			"reference_type": doc.doctype,
			"reference_name": doc.name
		}
	])
	journal_entry.save(ignore_permissions = True)
	frappe.msgprint("Disbursement Journal: " + journal_entry.name + " has been created.")

@frappe.whitelist()
def set_loan_paid(doc, method)
	frappe.msgprint("Method fired: " + str(method) + " on doc: " + str(doc))
	if method == "on_submit"
		frappe.msgprint("Code for setting the loan to paid goes here.")

@frappe.whitelist()
def set_loan_unpaid(doc, method)
	frappe.msgprint("Method fired: " + str(method) + " on doc: " + str(doc))
	if method == "on_cancel"
		frappe.msgprint("Code for setting the loan to unpaid goes here.")
