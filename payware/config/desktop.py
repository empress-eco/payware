# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from frappe import _

def get_data():
	return [
		{
			"module_name": "Payware",
			"color": "grey",
			"icon": "octicon octicon-file-directory",
			"type": "module",
			"label": _("Payware")
		},
		{
			"module_name": "Tanzania Statutory Reports",
			"color": "red",
			"icon": "octicon octicon-file-directory",
			"type": "page",
			"link": "tzpayware",
			"label": _("TZ Statutory Reports")
		}
	]
