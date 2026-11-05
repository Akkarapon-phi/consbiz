# Copyright (c) 2026, Siricons and Contributors
# See license.txt

# ใบเบิกจ่ายเงินประกันผลงานคืน ผรม. (consbiz/retention.py): สถานะ Retention Payable และ JE จ่ายเงิน

import frappe
from frappe.tests import IntegrationTestCase

from consbiz import retention
from consbiz.consbiz.doctype.retention_invoice.test_retention_invoice import gl, make_claim, status
from consbiz.consbiz.doctype.retention_receivable.test_retention_receivable import (
	cash_account,
	make_source,
	setup_retention_masters,
)

IGNORE_TEST_RECORD_DEPENDENCIES = [
	"Company",
	"Customer",
	"Supplier",
	"Project",
	"Account",
	"Mode of Payment",
	"Bank Account",
	"DocType",
	"Journal Entry",
	"Purchase Order",
]


class IntegrationTestRetentionRelease(IntegrationTestCase):
	def setUp(self):
		self.accounts = setup_retention_masters()

	def test_release_and_pay(self):
		source = make_source("Retention Payable", amounts=(600, 400))
		self.assertEqual(status(source), "Active")

		release = make_claim(source)
		self.assertEqual((release.doctype, release.grand_total), ("Retention Release", 1000))
		self.assertEqual(status(release), "Unpaid")
		self.assertEqual(status(source), "Billed")

		cash = cash_account()
		je = frappe.get_doc(
			"Journal Entry", retention.make_journal_entry(release.doctype, release.name, cash)
		)
		je.submit()
		# จ่ายคืน: Dr. เงินประกันผลงานค้างจ่าย / Cr. เงินสด
		self.assertEqual(gl(je.name), {self.accounts["custom_retention_payable"]: 1000, cash: -1000})
		self.assertEqual(status(release), "Paid")
		self.assertEqual(status(source), "Paid")
