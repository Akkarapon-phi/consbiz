# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

import frappe
from frappe.tests import IntegrationTestCase

from consbiz.consbiz.doctype.labour_timesheet.test_labour_timesheet import COMPANY, make_settings

IGNORE_TEST_RECORD_DEPENDENCIES = ["Company", "Account", "Item"]


class IntegrationTestLabourSettings(IntegrationTestCase):
	def test_account_rules(self):
		make_settings()
		payable = frappe.db.get_value("Account", {"company": COMPANY, "account_type": "Payable", "is_group": 0})
		self.assertRaises(frappe.ValidationError, make_settings, wage_payable_account=payable)
		self.assertRaises(frappe.ValidationError, make_settings, wage_expense_account="Accrued Expenses - _TC")
