# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

# การหักคืนในใบลงเวลาอยู่ในเทสต์ของ Labour Timesheet (test_advances_deducted_oldest_first)

import frappe
from frappe.tests import IntegrationTestCase

from consbiz.consbiz.doctype.labour_timesheet.test_labour_timesheet import (
	make_advance,
	make_project,
	make_settings,
	make_worker,
)

IGNORE_TEST_RECORD_DEPENDENCIES = ["Project", "Company", "Account", "Journal Entry", "Daily Worker"]


class IntegrationTestLabourAdvance(IntegrationTestCase):
	def setUp(self):
		self.project = make_project("_Test Labour Project")
		frappe.db.delete("Labour Advance", {"project": self.project})
		frappe.db.delete("Daily Worker", {"project": self.project})
		make_settings()

	def test_submit_posts_journal_entry_and_cancel_reverses(self):
		worker = make_worker(self.project, "_Test Advance Worker").name
		doc = make_advance(worker, 750)
		self.assertEqual((doc.status, doc.outstanding_amount), ("Unpaid", 750))
		je = frappe.get_doc("Journal Entry", doc.journal_entry)
		self.assertEqual(
			{(a.account, a.debit, a.credit) for a in je.accounts},
			{("Prepaid Expenses - _TC", 750, 0), ("_Test Cash - _TC", 0, 750)},
		)
		doc.cancel()
		self.assertEqual(frappe.db.get_value("Journal Entry", je.name, "docstatus"), 2)
		self.assertEqual(frappe.db.get_value("Labour Advance", doc.name, "status"), "Cancelled")

	def test_paid_from_must_be_cash_or_bank(self):
		worker = make_worker(self.project, "_Test Advance Worker 2").name
		doc = frappe.get_doc(
			{
				"doctype": "Labour Advance",
				"worker": worker,
				"date": "2026-09-01",
				"amount": 100,
				"paid_from_account": "Prepaid Expenses - _TC",
			}
		)
		self.assertRaises(frappe.ValidationError, doc.insert)
