# Copyright (c) 2026, Siricons and Contributors
# See license.txt

# เงินประกันผลงานจ่าย (consbiz/retention.py): สร้างจาก Purchase Invoice

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import nowdate

from consbiz import retention
from consbiz.consbiz.doctype.retention_receivable.test_retention_receivable import (
	COMPANY,
	SUPPLIER,
	make_source,
	setup_retention_masters,
)

IGNORE_TEST_RECORD_DEPENDENCIES = [
	"Company",
	"Supplier",
	"Project",
	"Account",
	"Purchase Order",
	"Purchase Invoice",
	"Sales Invoice",
]


class IntegrationTestRetentionPayable(IntegrationTestCase):
	def setUp(self):
		setup_retention_masters()

	def test_mapping_from_purchase_invoice(self):
		invoice = frappe._dict(
			doctype="Purchase Invoice",
			name="PINV-TEST-1",
			company=COMPANY,
			supplier=SUPPLIER,
			posting_date=nowdate(),
			project=None,
			bill_no="INV-889",
			net_total=10000,
			custom_subject_to_retention=1,
			custom_retention_percent=10,
			custom_retention_amount=1000,
			items=[frappe._dict(project="_Test Retention Project", purchase_order="PO-0001")],
		)
		doc = retention.make_source_from_invoice(invoice)
		self.assertEqual((doc.doctype, doc.supplier, doc.po), ("Retention Payable", SUPPLIER, "PO-0001"))
		self.assertEqual(doc.project, "_Test Retention Project")
		row = doc.retention_items[0]
		self.assertEqual(
			(row.purchase_invoice_no, row.reference_no, row.amount), ("PINV-TEST-1", "INV-889", 1000)
		)

	def test_status_flow(self):
		doc = make_source("Retention Payable", amounts=(500,))
		doc.reload()
		self.assertEqual((doc.status, doc.outstanding_amount), ("Active", 500))
		doc.cancel()
		self.assertEqual(frappe.db.get_value(doc.doctype, doc.name, "status"), "Cancelled")
