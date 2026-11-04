# Copyright (c) 2026, Siricons and Contributors
# See license.txt

# ใบนำส่งเอกสาร: สถานะจากวันที่ส่ง/รับ, ผู้รับ, ดึงเอกสาร (ไม่ซ้ำผู้รับเดิม), แจ้งในเอกสารต้นทาง

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, nowdate

from consbiz.consbiz.doctype.retention_invoice.test_retention_invoice import make_claim
from consbiz.consbiz.doctype.retention_receivable.test_retention_receivable import (
	COMPANY,
	CUSTOMER,
	make_source,
	setup_retention_masters,
)
from consbiz.consbiz.doctype.transmittal.transmittal import (
	get_documents,
	get_reference_details,
	get_transmittals_for,
)
from consbiz.patches.merge_transmittals import parse_qty

IGNORE_TEST_RECORD_DEPENDENCIES = ["Company", "Customer", "Supplier", "Project", "Account", "Mode of Payment"]


def make_transmittal(recipient_type="Customer", party=CUSTOMER, rows=(), submit=True, **values):
	doc = frappe.new_doc("Transmittal")
	doc.update(
		{
			"company": COMPANY,
			"title": "_Test Transmittal",
			"date": nowdate(),
			"recipient_type": recipient_type,
			"party": party if recipient_type in ("Customer", "Supplier") else None,
			**values,
		}
	)
	for row in rows:
		doc.append("transmittal_list", row)
	doc.insert()
	if submit:
		doc.submit()
	return doc


class IntegrationTestTransmittal(IntegrationTestCase):
	def setUp(self):
		setup_retention_masters()

	def test_status_follows_dates(self):
		doc = make_transmittal(submit=False, rows=[{"document_no": "DOC-1", "qty": 5, "unit": "ฉบับ"}])
		self.assertEqual(doc.status, "Draft")
		self.assertEqual(doc.party_type, "Customer")
		self.assertEqual(doc.recipient_name, CUSTOMER)

		doc.submit()
		self.assertEqual(frappe.db.get_value("Transmittal", doc.name, "status"), "To Send")

		doc.reload()
		doc.sent_date = nowdate()
		doc.save()
		self.assertEqual(doc.status, "Sent")

		doc.received_date = add_days(nowdate(), -1)
		self.assertRaises(frappe.ValidationError, doc.save)

		doc.reload()
		doc.received_by = "คุณสมชาย"
		doc.received_date = nowdate()
		doc.save()
		self.assertEqual(doc.status, "Received")

		doc.cancel()
		self.assertEqual(frappe.db.get_value("Transmittal", doc.name, "status"), "Cancelled")

	def test_received_needs_sent_date(self):
		doc = make_transmittal()
		doc.received_date = nowdate()
		self.assertRaises(frappe.ValidationError, doc.save)

	def test_accounting_office_has_no_party(self):
		doc = make_transmittal(
			recipient_type="Accounting Office", party=None, recipient_name="สำนักงานบัญชี ก", submit=False
		)
		doc.party = CUSTOMER
		doc.save()
		self.assertIsNone(doc.party_type)
		self.assertIsNone(doc.party)
		self.assertEqual(doc.recipient_name, "สำนักงานบัญชี ก")

	def test_get_documents_skips_sent_to_same_recipient(self):
		invoice = make_claim(make_source(amounts=(1500,)))
		row = get_reference_details("Retention Invoice", invoice.name)
		self.assertEqual(row["reference_name"], invoice.name)
		self.assertEqual(row["document_no"], invoice.name)
		self.assertEqual(row["amount"], 1500)
		self.assertIn(CUSTOMER, row["description"])

		def found(recipient_type, party=None, include_sent=0):
			rows = get_documents(
				"Retention Invoice",
				COMPANY,
				recipient_type=recipient_type,
				party=party,
				from_date=nowdate(),
				to_date=nowdate(),
				include_sent=include_sent,
			)
			return invoice.name in [r["reference_name"] for r in rows]

		self.assertTrue(found("Customer", CUSTOMER))

		transmittal = make_transmittal(rows=[row])
		self.assertFalse(found("Customer", CUSTOMER))
		self.assertTrue(found("Customer", CUSTOMER, include_sent=1))
		# ส่งใบเดียวกันให้สำนักงานบัญชีได้
		self.assertTrue(found("Accounting Office"))

		self.assertEqual([t.name for t in get_transmittals_for("Retention Invoice", invoice.name)], [transmittal.name])

		# ยกเลิกใบนำส่งแล้วดึงได้อีก
		transmittal.cancel()
		self.assertTrue(found("Customer", CUSTOMER))
		self.assertEqual(get_transmittals_for("Retention Invoice", invoice.name), [])

	def test_parse_old_amount(self):
		self.assertEqual(parse_qty("5", None, None), (5, None, None))
		self.assertEqual(parse_qty(" 817.00 ", "ลบ.ม.", None), (817, "ลบ.ม.", None))
		self.assertEqual(parse_qty("7380กก.", None, None), (7380, "กก.", None))
		self.assertEqual(parse_qty("1,250", None, "x"), (1250, None, "x"))
		self.assertEqual(parse_qty("5 - 6", None, "x"), (0, None, "x 5 - 6"))
		self.assertEqual(parse_qty("ไม่ระบุ", None, None), (0, None, "ไม่ระบุ"))
		self.assertEqual(parse_qty("", "ชุด", None), (0, "ชุด", None))
