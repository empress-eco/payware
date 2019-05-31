from __future__ import unicode_literals
import json
import frappe
from frappe.model.document import Document
from dateutil.relativedelta import relativedelta
from frappe.utils import cint, format_datetime,get_datetime_str,now_datetime,add_days,today,formatdate,date_diff,getdate,add_months,flt, nowdate, fmt_money, add_to_date, DATE_FORMAT, rounded
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

@frappe.whitelist()
def create_additional_salary_journal(doc, method):
	if (frappe.get_value("Salary Component", doc.salary_component, "create_cash_journal")):
		salary_component = frappe.get_doc("Salary Component", doc.salary_component)
		cash_account = frappe.db.get_single_value("Payware Settings", "default_account_for_additional_component_cash_journal")
		component_account = frappe.db.get_value("Salary Component Account", {"parent": doc.salary_component, "company": doc.company}, "default_account")
		#frappe.msgprint("Expense account is: " + str(component_account))
		if method == "on_submit":
			dr_account = component_account
			cr_account = cash_account
		elif method == "on_cancel":
			dr_account = cash_account
			cr_account = component_account
		else:
			frappe.msgprint("Unknown method on create_additional_salary_journal")
			return

		#frappe.msgprint("Method fired: " + method)
		precision = frappe.get_precision("Journal Entry Account", "debit_in_account_currency")
		journal_entry = frappe.new_doc('Journal Entry')
		journal_entry.voucher_type = 'Cash Entry'
		journal_entry.user_remark = _('{0} - {1} - Additional salary {2} for {3}').format(doc.doctype, doc.name, doc.salary_component, doc.employee_name)
		journal_entry.company = doc.company
		journal_entry.posting_date = doc.payroll_date

		payment_amount = flt(doc.amount, precision)

		journal_entry.set("accounts", [
			{
				"account": dr_account,
				"debit_in_account_currency": payment_amount
			},
			{
				"account": cr_account,
				"credit_in_account_currency": payment_amount
			}
		])
		journal_entry.save(ignore_permissions = True)

		if method == "on_submit":
			frappe.set_value(doc.doctype, doc.name, "journal_name", journal_entry.name)
			msg_to_print = doc.doctype + " journal " + journal_entry.name + " has been created."
		elif method == "on_cancel":
			msg_to_print = doc.doctype + " reverse journal " + journal_entry.name + " has been created."
		frappe.msgprint(msg_to_print)

@frappe.whitelist()
def generate_additional_salary_records():
	today_date = today()
	additional_salary_list = frappe.get_all("Additional Salary", filters={"docstatus": "1", "auto_repeat_frequency": ("!=", "None"), "auto_repeat_end_date": ("!=", None), "auto_repeat_end_date": ("<=", today_date)}, fields="name")
	#frappe.msgprint("Additional Salary List lookedup: " + str(additional_salary_list))
	if additional_salary_list:
		#frappe.msgprint("In the salary loop")
		for additional_salary_doc in additional_salary_list:
			cur_additional_salary_doc = frappe.get_doc("Additional Salary", additional_salary_doc.name)
			#frappe.msgprint("New Additional Salary Doc loaded: ")
			#frappe.msgprint(str(cur_additional_salary_doc.auto_repeat_end_date) + " auto repeat end date loaded.")
			#frappe.msgprint(str(cur_additional_salary_doc.last_transaction_date) + " last transaction date loaded.")
			#frappe.msgprint(str(cur_additional_salary_doc.auto_repeat_frequency) + " auto repeat frequency loaded.")
			cur_additional_salary_doc.last_transaction_date
			if cur_additional_salary_doc.last_transaction_date == None:
				#frappe.msgprint("Blank last transaction date found for " + cur_additional_salary_doc.name + ". Setting payroll date of original transaction")
				cur_additional_salary_doc.last_transaction_date = cur_additional_salary_doc.payroll_date
			if cur_additional_salary_doc.auto_repeat_frequency == "Weekly":
				next_date = add_days(getdate(cur_additional_salary_doc.last_transaction_date), 7)
			else:
				#frappe.msgprint("auto_repeat_frequency must be Monthly or Annually")
				frequency_factor = auto_repeat_frequency.get(cur_additional_salary_doc.auto_repeat_frequency, "Invalid frequency")
				if frequency_factor == "Invalid frequency":
					frappe.throw("Invalid frequency: {0} not found. Contact the developers!".format(cur_additional_salary_doc.auto_repeat_frequency))
				next_date = add_months(getdate(cur_additional_salary_doc.last_transaction_date), frequency_factor)
			if next_date <= today_date:
				#frappe.msgprint("New additional salary will be created for " + cur_additional_salary_doc.auto_repeat_frequency + " dated " + str(next_date))
				additional_salary = frappe.new_doc('Additional Salary')
				additional_salary.employee = cur_additional_salary_doc.employee
				additional_salary.payroll_date = next_date
				additional_salary.salary_component = cur_additional_salary_doc.salary_component
				additional_salary.employee_name = cur_additional_salary_doc.employee_name
				additional_salary.amount = cur_additional_salary_doc.amount
				additional_salary.company = cur_additional_salary_doc.company
				additional_salary.overwrite_salary_structure_amount = cur_additional_salary_doc.overwrite_salary_structure_amount
				additional_salary.type = cur_additional_salary_doc.type
				additional_salary.auto_repeat_frequency = "None"
				additional_salary.auto_created_based_on = cur_additional_salary_doc.name
				additional_salaryauto_repeat_end_date = None
				additional_salarylast_transaction_date = None
				additional_salary.save(ignore_permissions = True)
				frappe.set_value("Additional Salary", cur_additional_salary_doc.name, "last_transaction_date", next_date)
