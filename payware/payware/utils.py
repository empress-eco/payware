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
def set_loan_paid(doc, method):
	#frappe.msgprint("Method fired: " + str(method) + " on doc: " + str(doc))
	if method == "on_submit":
		for loan in doc.loans:
			#frappe.msgprint("Loan to be updated as paid: " + str(loan.loan))
			loan_doc = frappe.get_doc("Loan", loan.loan)
			#frappe.msgprint("Loan Doc loaded: " + str(loan_doc.name))
			for loan_repayment_schedule in loan_doc.repayment_schedule:
				#frappe.msgprint("Loan Repayment Date " + str(loan_repayment_schedule.payment_date))
				if getdate(doc.start_date) <= getdate(loan_repayment_schedule.payment_date) <= getdate(doc.end_date):
					frappe.set_value("Repayment Schedule", loan_repayment_schedule.name, "paid", 1)
					#frappe.msgprint("Repayment Schedule of date " + str(loan_repayment_schedule.name) + " updated.")
	elif method == "on_cancel":
		for loan in doc.loans:
			#frappe.msgprint("Loan to be updated as paid: " + str(loan.loan))
			loan_doc = frappe.get_doc("Loan", loan.loan)
			#frappe.msgprint("Loan Doc loaded: " + str(loan_doc.name))
			for loan_repayment_schedule in loan_doc.repayment_schedule:
				#frappe.msgprint("Loan Repayment Date " + str(loan_repayment_schedule.payment_date))
				if getdate(doc.start_date) <= getdate(loan_repayment_schedule.payment_date) <= getdate(doc.end_date):
					frappe.set_value("Repayment Schedule", loan_repayment_schedule.name, "paid", 0)
					#frappe.msgprint("Repayment Schedule of date " + str(loan_repayment_schedule.name) + " updated.")


@frappe.whitelist()
def create_loan_repayment_jv(doc, method):
	if method == "on_submit":
		loan_doc = frappe.get_doc("Loan", doc.loan)
		cr_account = loan_doc.payment_account
		dr_account = loan_doc.loan_account
	elif method == "on_cancel":
		loan_doc = frappe.get_doc("Loan", doc.loan)
		cr_account = loan_doc.loan_account
		dr_account = loan_doc.payment_account
	else:
		frappe.msgprint("Unknown method on create_loan_repayment_jv")
		return
	#frappe.msgprint("Method fired: " + method)
	precision = frappe.get_precision("Journal Entry Account", "debit_in_account_currency")

	journal_entry = frappe.new_doc('Journal Entry')
	journal_entry.voucher_type = 'Bank Entry'
	journal_entry.user_remark = _('{0} - {1} on {2}').format(doc.doctype, doc.name, doc.payment_date)
	journal_entry.company = doc.company
	journal_entry.posting_date = doc.payment_date

	payment_amount = flt(doc.payment_amount, precision)

	journal_entry.set("accounts", [
		{
			"account": dr_account,
			"debit_in_account_currency": payment_amount,
			"reference_type": loan_doc.doctype,
			"reference_name": loan_doc.name
		},
		{
			"account": cr_account,
			"credit_in_account_currency": payment_amount,
			"reference_type": loan_doc.doctype,
			"reference_name": loan_doc.name
		}
	])
	
	# Create records in NFS child doctype of Loan doctype
	'''
	doc = frappe.get_doc("Sales Order")
	row = doc.append("items", {})
	row.item_code = "Test Item"
	row.qty = 2
	
	or you can also use the following format

	doc = frappe.get_doc("Sales Order")
	row = doc.append("items", {
		"item_code": "Test Item",
		"qty": 2
	})
	'''
	loan_nfs_row = loan_doc.append("loan_repayments_not_from_salary")
	Loan NFS Repayments
	# Update total_payments of Loan doctype
	frappe.set_value("Loan", loan_doc.name, "total_payments", total_payments -= payment_account)
	# Update balance of loan of Repayment Schedule child doctype of Loan doctype 
	
	journal_entry.save(ignore_permissions = True)
	frappe.set_value(doc.doctype, doc.name, "journal_name", journal_entry.name)
	if method == "on_submit":
		msg_to_print = doc.doctype + " journal " + journal_entry.name + " has been created."
	elif method == "on_cancel":
		msg_to_print = doc.doctype + " reverse journal " + journal_entry.name + " has been created."
	frappe.msgprint(msg_to_print)
