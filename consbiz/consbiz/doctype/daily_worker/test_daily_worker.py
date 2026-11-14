# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, nowdate

from consbiz.consbiz.doctype.labour_timesheet.test_labour_timesheet import COMPANY, make_project

IGNORE_TEST_RECORD_DEPENDENCIES = ["Project", "Company", "Supplier"]


class IntegrationTestDailyWorker(IntegrationTestCase):
	def make(self, **values):
		return frappe.get_doc(
			{
				"doctype": "Daily Worker",
				"worker_name": "_Test Daily Worker",
				"company": COMPANY,
				"project": make_project("_Test Labour Project"),
				"rates": [{"from_date": "2026-01-01", "daily_rate": 400}],
				**values,
			}
		)

	def test_current_rate_and_history(self):
		doc = self.make(rates=[
			{"from_date": add_days(nowdate(), 10), "daily_rate": 500},
			{"from_date": "2026-01-01", "daily_rate": 400},
		]).insert()
		self.assertEqual(doc.daily_rate, 400)
		self.assertEqual([row.daily_rate for row in doc.rates], [400, 500])
		self.assertEqual(doc.rate_on("2025-12-01"), 400)
		self.assertEqual(doc.rate_on(add_days(nowdate(), 10)), 500)

	def test_duplicate_rate_date_and_supplier_cleared(self):
		doc = self.make(rates=[
			{"from_date": "2026-01-01", "daily_rate": 400},
			{"from_date": "2026-01-01", "daily_rate": 450},
		])
		self.assertRaises(frappe.ValidationError, doc.insert)
		doc = self.make(payee_type="Company", supplier=None, ot_flat=0, ot_hourly_rate=80).insert()
		self.assertEqual(doc.ot_hourly_rate, 0)
