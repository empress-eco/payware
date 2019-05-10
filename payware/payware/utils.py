from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from dateutil.relativedelta import relativedelta
from frappe.utils import cint, flt, nowdate, add_days, getdate, fmt_money, add_to_date, DATE_FORMAT, date_diff, rounded, add_months
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
			loan = frappe.get_doc("Loan", loan.loan)
			#frappe.msgprint("Loan Doc loaded: " + str(loan.name))
			for loan_repayment_schedule in loan.repayment_schedule:
				#frappe.msgprint("Loan Repayment Date " + str(loan_repayment_schedule.payment_date))
				if getdate(doc.start_date) <= getdate(loan_repayment_schedule.payment_date) <= getdate(doc.end_date):
					frappe.set_value("Repayment Schedule", loan_repayment_schedule.name, "paid", 1)
					#frappe.msgprint("Repayment Schedule of date " + str(loan_repayment_schedule.name) + " updated.")
	elif method == "on_cancel":
		for loan in doc.loans:
			#frappe.msgprint("Loan to be updated as paid: " + str(loan.loan))
			loan = frappe.get_doc("Loan", loan.loan)
			#frappe.msgprint("Loan Doc loaded: " + str(loan.name))
			for loan_repayment_schedule in loan.repayment_schedule:
				#frappe.msgprint("Loan Repayment Date " + str(loan_repayment_schedule.payment_date))
				if getdate(doc.start_date) <= getdate(loan_repayment_schedule.payment_date) <= getdate(doc.end_date):
					#frappe.msgprint("Repayment Schedule of date " + str(loan_repayment_schedule.name) + " updated.")
					frappe.set_value("Repayment Schedule", loan_repayment_schedule.name, "paid", 0)

@frappe.whitelist()
def create_loan_repayment_jv(doc, method):
	loan = frappe.get_doc("Loan", doc.loan)
	if method == "on_submit":
		cr_account = loan.payment_account
		dr_account = loan.loan_account
	elif method == "on_cancel":
		cr_account = loan.loan_account
		dr_account = loan.payment_account
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
			"reference_type": loan.doctype,
			"reference_name": loan.name
		},
		{
			"account": cr_account,
			"credit_in_account_currency": payment_amount,
			"reference_type": loan.doctype,
			"reference_name": loan.name
		}
	])
	journal_entry.save(ignore_permissions = True)


	# Create records in NFS child doctype of Loan doctype
	if method == "on_submit":
		frappe.msgprint("loan nfs repayment appending...")
		loan_nfs_row = loan.append("loan_repayments_not_from_salary")
		loan_nfs_row.nfs_loan_repayment = doc.name
		loan_nfs_row.company = doc.company
		loan_nfs_row.payment_date = doc.payment_date
		loan_nfs_row.payment_amount = doc.payment_amount
		loan.save()
	elif method == "on_cancel":
		# Delete record from loan related to this repayment
		for repayment in frappe.get_all("Loan NFS Repayments", "name", {"nfs_loan_repayment": doc.name}):
			#frappe.msgprint("doc.name: " + str(repayment.name) + " for loan repayment: " + doc.name)
			frappe.db.sql("""update `tabLoan NFS Repayments` set docstatus = 0 where name = %s""", repayment.name)
			frappe.delete_doc("Loan NFS Repayments", repayment.name)

	# Update loan of Repayment Schedule child doctype of Loan doctype and set the balances right as per date
	redo_repayment_schedule(doc, method)
	set_repayment_period(loan.name)
	calculate_totals(loan.name)
	
	if method == "on_submit":
		frappe.set_value(doc.doctype, doc.name, "journal_name", journal_entry.name)
		msg_to_print = doc.doctype + " journal " + journal_entry.name + " has been created."
	elif method == "on_cancel":
		msg_to_print = doc.doctype + " reverse journal " + journal_entry.name + " has been created."
	frappe.msgprint(msg_to_print)

@frappe.whitelist()
def redo_repayment_schedule(doc, method):
	#frappe.msgprint("loan repayment schedule redone started")
	loan_docname = frappe.get_value("Loan Repayment Not From Salary", doc.name, "loan")
	# Identify pending schedule and remove those lines from schedule
	#frappe.msgprint("This is the parameter passed: " + str(loan_docname))
	loan = frappe.get_doc("Loan", str(loan_docname))
	#frappe.msgprint("This is the loan object: " + str(loan.name))
	#frappe.msgprint("This is the repayment schedule length: " + str(len(loan.repayment_schedule)))

	repayment_schedule_list = frappe.get_all("Repayment Schedule", fields=["name", "parent", "paid", "total_payment", "payment_date"], filters={"parent": loan.name})

	payment_date = loan.repayment_start_date
	# Delete all non-paid records from schedule
	for repayment_schedule in repayment_schedule_list:
		if repayment_schedule.paid == 0:
			frappe.db.sql("""update `tabRepayment Schedule` set docstatus = 0 where name = %s""", repayment_schedule.name)
			#frappe.msgprint("repayment schedule being cleared for record: " + str(repayment_schedule.name))
			frappe.delete_doc("Repayment Schedule", repayment_schedule.name)

	# Reload the loan doc after deleting records
	loan = frappe.get_doc("Loan", str(loan_docname))

	# Find total of repayments made
	#frappe.msgprint("finding total repayemnts made")
	total_repayments = 0
	repayment_schedule_list = frappe.get_all("Repayment Schedule", fields=["name", "parent", "paid", "total_payment", "payment_date"], filters={"parent": loan.name})
	for repayment_schedule in repayment_schedule_list:
		total_repayments += repayment_schedule.total_payment

	# Find total of NFS repayments made
	#frappe.msgprint("finding total repayemnts made")
	total_nfs_repayments = 0
	nfs_repayment_schedule_list = frappe.get_all("Loan NFS Repayments", fields=["parent", "payment_amount"], filters={"parent": loan.name})
	for nfs_repayment_schedule in nfs_repayment_schedule_list:
		total_nfs_repayments += nfs_repayment_schedule.payment_amount

	# Find new balance_amount
	balance_amount = loan.loan_amount - total_repayments - total_nfs_repayments
	frappe.msgprint("Repayments records balance: " + str(balance_amount) + " with total repayments = " + str(total_repayments) + " and total nfs repayments = " + str(total_nfs_repayments))

	# Find next payment date
	for repayment_schedule in repayment_schedule_list:
		last_payment_date = repayment_schedule.payment_date
	payment_date = add_months(last_payment_date, 1)

	# Insert rows starting balance_amount till it is 0
	while(balance_amount > 0):
		#frappe.msgprint("Creating repayments records with balance: " + str(balance_amount))
		interest_amount = rounded(balance_amount * flt(loan.rate_of_interest) / (12*100))
		principal_amount = loan.monthly_repayment_amount - interest_amount
		balance_amount = rounded(balance_amount + interest_amount - loan.monthly_repayment_amount)

		if balance_amount < 0:
			principal_amount += balance_amount
			balance_amount = 0.0

		total_payment = principal_amount + interest_amount

		loan_repay_row = loan.append("repayment_schedule")
		loan_repay_row.payment_date = payment_date
		loan_repay_row.principal_amount = principal_amount
		loan_repay_row.interest_amount = interest_amount
		loan_repay_row.total_payment = total_payment
		loan_repay_row.balance_loan_amount = balance_amount

		next_payment_date = add_months(payment_date, 1)

		payment_date = next_payment_date
	#frappe.msgprint("loan repayment schedule redone ended")
	loan.save()

@frappe.whitelist()
def set_repayment_period(loan_docname):
	loan = frappe.get_doc("Loan", str(loan_docname))
	if loan.repayment_method == "Repay Fixed Amount per Period":
		# Filter out the scheudles that are marked as skip
		loan.repayment_periods = len(loan.repayment_schedule)
	loan.save()

@frappe.whitelist()
def calculate_totals(loan_docname):
	loan = frappe.get_doc("Loan", loan_docname)
	loan.total_payment = 0
	loan.total_interest_payable = 0
	loan.total_amount_paid = 0
	for data in loan.repayment_schedule:
		loan.total_payment += data.total_payment
		loan.total_interest_payable +=data.interest_amount
		if data.paid:
			loan.total_amount_paid += data.total_payment
	loan.save()
