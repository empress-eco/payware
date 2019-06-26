from __future__ import unicode_literals
from frappe import _
import frappe


def get_data():
	config = [
		{
			"label": _("Payware Documents"),
			"items": [
				{
					"type": "doctype",
					"name": "Loan Repayment Not From Salary",
					"onboard": 0,
				},
				{
					"type": "doctype",
					"name": "NSSF Payments",
					"onboard": 0,
				},
			]
		},
		{
			"label": _("Payware Masters"),
			"items": [
				{
					"type": "doctype",
					"name": "Payware Settings",
					"onboard": 1,
				},
			]
		},
		{
			"label": _("TRA Statutory Reports"),
			"items": [
				{
					"type": "report",
					"name": "ITX 215.01.E - PAYE Withheld Part 1",
					"doctype": "Salary Slip",
					"is_query_report": True,
				},
				{
					"type": "report",
					"name": "ITX 215.01.E - PAYE Withheld Part 2",
					"doctype": "Salary Slip",
					"is_query_report": True,
				},
				{
					"type": "report",
					"name": "ITX 219.01.E - SDL - Monthly Return",
					"doctype": "Salary Slip",
					"is_query_report": True,
				},
				{
					"type": "report",
					"name": "ITX 220.01.E - Employer's Half Year Certificate",
					"doctype": "Salary Slip",
					"is_query_report": True,
				},
			]
		},
		{
			"label": _("Other Statutory Reports"),
			"items": [
				{
					"type": "report",
					"name": "NSSF-CON.05",
					"label": _("NSSF-CON.05 - NSSF Monthly Returns"),
					"doctype": "Salary Slip",
					"is_query_report": True,
				},
				{
					"type": "report",
					"name": "WCF-3",
					"label": _("WCF-3 - WCF Monthly Returns"),
					"doctype": "Salary Slip",
					"is_query_report": True,
				},
			]
		},
		{
			"label": _("Reports"),
			"items": [
				{
					"type": "report",
					"name": "SDL Report",
					"doctype": "Salary Slip",
					"is_query_report": True,
				},
			]
		},
	]
	return config
