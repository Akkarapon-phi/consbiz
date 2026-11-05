# Copyright (c) 2026, Siricons and Contributors
# See license.txt

# หน้าซองจดหมาย: สร้างจากใบนำส่งเอกสาร / ใบแจ้งหนี้ขาย (ที่อยู่ + ผู้ติดต่อผู้รับ, อ้างอิงเอกสารต้นทาง)

import frappe
from frappe.tests import IntegrationTestCase

from consbiz.consbiz.doctype.envelope.envelope import _from_sales_invoice, make_envelope
from consbiz.consbiz.doctype.retention_receivable.test_retention_receivable import (
	COMPANY,
	CUSTOMER,
	setup_retention_masters,
)
from consbiz.consbiz.doctype.transmittal.test_transmittal import make_transmittal

IGNORE_TEST_RECORD_DEPENDENCIES = [
	"Company",
	"Customer",
	"Supplier",
	"Project",
	"Account",
	"Mode of Payment",
	"Address",
	"Contact",
	"DocType",
	"User",
]


def ensure_address(title, link_doctype, link_name):
	name = frappe.db.get_value("Address", {"address_title": title})
	if name:
		return name
	return (
		frappe.get_doc(
			{
				"doctype": "Address",
				"address_title": title,
				"address_type": "Billing",
				"address_line1": "1 ถนนทดสอบ",
				"city": "กรุงเทพฯ",
				"country": "Thailand",
				"is_primary_address": 1,
				"links": [{"link_doctype": link_doctype, "link_name": link_name}],
			}
		)
		.insert(ignore_permissions=True)
		.name
	)


def ensure_contact(first_name, link_doctype, link_name):
	name = frappe.db.get_value("Contact", {"first_name": first_name})
	if name:
		return name
	return (
		frappe.get_doc(
			{
				"doctype": "Contact",
				"first_name": first_name,
				"is_primary_contact": 1,
				"links": [{"link_doctype": link_doctype, "link_name": link_name}],
			}
		)
		.insert(ignore_permissions=True)
		.name
	)


class IntegrationTestEnvelope(IntegrationTestCase):
	def setUp(self):
		setup_retention_masters()
		self.company_address = ensure_address("_Test Envelope Company", "Company", COMPANY)
		self.customer_address = ensure_address("_Test Envelope Customer", "Customer", CUSTOMER)
		self.contact = ensure_contact("_Test Envelope Contact", "Customer", CUSTOMER)

	def test_from_transmittal(self):
		transmittal = make_transmittal(rows=[{"document_no": "DOC-1"}])
		envelope = make_envelope("Transmittal", transmittal.name)
		self.assertEqual(envelope.company, COMPANY)
		self.assertEqual(envelope.get("from"), self.company_address)
		self.assertEqual(envelope.to, self.customer_address)
		self.assertEqual(envelope.receiver, self.contact)
		self.assertEqual(envelope.remark, transmittal.title)
		self.assertEqual(
			(envelope.reference_doctype, envelope.reference_name), ("Transmittal", transmittal.name)
		)

		envelope.insert()
		envelope.submit()
		self.assertEqual(
			frappe.get_all("Envelope", filters={"reference_name": transmittal.name}, pluck="name"),
			[envelope.name],
		)

	def test_transmittal_without_party(self):
		transmittal = make_transmittal(
			recipient_type="Accounting Office", party=None, recipient_name="สนง.บัญชี"
		)
		envelope = make_envelope("Transmittal", transmittal.name)
		self.assertIsNone(envelope.to)
		self.assertIsNone(envelope.receiver)

	def test_sales_invoice_prefers_invoice_address(self):
		invoice = frappe._dict(
			name="SINV-TEST-1", customer=CUSTOMER, customer_address="ADDR-ON-INVOICE", contact_person=None
		)
		values = _from_sales_invoice(invoice)
		self.assertEqual(values["to"], "ADDR-ON-INVOICE")
		self.assertEqual(values["receiver"], self.contact)
		self.assertIn("SINV-TEST-1", values["remark"])

		invoice.customer_address = None
		self.assertEqual(_from_sales_invoice(invoice)["to"], self.customer_address)

	def test_other_source_not_allowed(self):
		self.assertRaises(frappe.ValidationError, make_envelope, "Purchase Invoice", "X")
