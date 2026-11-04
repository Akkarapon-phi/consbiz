# Copyright (c) 2026, Siricons and Contributors
# See license.txt

# เงินประกันผลงาน (consbiz/retention.py): ที่มาของเงินประกัน RR / RP, ยอดรวม, สถานะ, การตรวจซ้ำ

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, nowdate

from consbiz import retention
from consbiz.utils import thai_baht_text

IGNORE_TEST_RECORD_DEPENDENCIES = ["Company", "Customer", "Supplier", "Project", "Account"]

COMPANY = "_Test Retention Company"
ABBR = "_TRC"
CUSTOMER = "_Test Retention Customer"
SUPPLIER = "_Test Retention Supplier"


def ensure_master(doctype, name, **values):
	if not frappe.db.exists(doctype, name):
		frappe.get_doc({"doctype": doctype, **values}).insert(ignore_permissions=True)
	return name


def setup_retention_masters():
	"""บริษัท / ลูกค้า / ผู้ขาย / บัญชีเงินประกัน / ปีบัญชี สำหรับเทสต์ (สร้างครั้งเดียวต่อไซต์)"""
	if not frappe.db.exists("Company", COMPANY):
		frappe.get_doc(
			{
				"doctype": "Company",
				"company_name": COMPANY,
				"abbr": ABBR,
				"default_currency": "THB",
				"country": "Thailand",
				"chart_of_accounts": "Standard",
			}
		).insert(ignore_permissions=True)
	year = nowdate()[:4]
	if not frappe.db.exists("Fiscal Year", {"year_start_date": f"{year}-01-01"}):
		frappe.get_doc(
			{
				"doctype": "Fiscal Year",
				"year": f"_Test Retention {year}",
				"year_start_date": f"{year}-01-01",
				"year_end_date": f"{year}-12-31",
			}
		).insert(ignore_permissions=True)

	accounts = {}
	for field, name, parent_name in (
		("custom_retention_receivable", "_Test Retention Receivable", "Current Assets"),
		("custom_retention_payable", "_Test Retention Payable", "Current Liabilities"),
	):
		account = f"{name} - {ABBR}"
		if not frappe.db.exists("Account", account):
			parent = frappe.db.get_value(
				"Account", {"company": COMPANY, "account_name": parent_name, "is_group": 1}, "name"
			)
			frappe.get_doc(
				{"doctype": "Account", "account_name": name, "parent_account": parent, "company": COMPANY}
			).insert(ignore_permissions=True)
		accounts[field] = account
	frappe.db.set_value("Company", COMPANY, accounts)

	customer_group = ensure_master(
		"Customer Group", "_Test Retention Group", customer_group_name="_Test Retention Group"
	)
	territory = ensure_master("Territory", "_Test Retention Territory", territory_name="_Test Retention Territory")
	ensure_master(
		"Customer",
		CUSTOMER,
		customer_name=CUSTOMER,
		customer_group=customer_group,
		territory=territory,
	)
	supplier_group = ensure_master(
		"Supplier Group", "_Test Retention Group", supplier_group_name="_Test Retention Group"
	)
	ensure_master("Supplier", SUPPLIER, supplier_name=SUPPLIER, supplier_group=supplier_group)
	return accounts


def cash_account():
	return frappe.db.get_value("Account", {"company": COMPANY, "account_type": "Cash", "is_group": 0}, "name")


def make_source(doctype="Retention Receivable", amounts=(1000,), due_date=None, submit=True):
	side = retention.SIDES[doctype]
	doc = frappe.new_doc(doctype)
	doc.company = COMPANY
	doc.set(side.party_field, CUSTOMER if doctype == "Retention Receivable" else SUPPLIER)
	doc.posting_date = nowdate()
	doc.due_date = due_date
	for amount in amounts:
		doc.append("retention_items", {"posting_date": nowdate(), "amount": amount})
	doc.insert()
	if submit:
		doc.submit()
	return doc


class IntegrationTestRetentionReceivable(IntegrationTestCase):
	def setUp(self):
		setup_retention_masters()

	def test_thai_baht_text(self):
		self.assertEqual(thai_baht_text(0), "ศูนย์บาทถ้วน")
		self.assertEqual(thai_baht_text(21.5), "ยี่สิบเอ็ดบาทห้าสิบสตางค์")
		self.assertEqual(thai_baht_text(1_000_101), "หนึ่งล้านหนึ่งร้อยเอ็ดบาทถ้วน")
		self.assertEqual(thai_baht_text(-11), "ติดลบสิบเอ็ดบาทถ้วน")

	def test_totals_and_status(self):
		doc = make_source(amounts=(1000, 250.5), submit=False)
		self.assertEqual(doc.grand_total, 1250.5)
		self.assertEqual(doc.in_words, thai_baht_text(1250.5))
		self.assertEqual(doc.status, "Draft")

		doc.submit()
		doc.reload()
		self.assertEqual((doc.status, doc.outstanding_amount, doc.billed_amount), ("Active", 1250.5, 0))

	def test_amount_from_percent(self):
		doc = frappe.new_doc("Retention Receivable")
		doc.update({"company": COMPANY, "customer": CUSTOMER, "posting_date": nowdate()})
		doc.append("retention_items", {"base_amount": 20000, "retention_percent": 5})
		doc.insert()
		self.assertEqual(doc.retention_items[0].amount, 1000)
		self.assertEqual(doc.grand_total, 1000)

	def test_due_date_editable_after_submit(self):
		doc = make_source(due_date=add_days(nowdate(), 30))
		self.assertEqual(frappe.db.get_value(doc.doctype, doc.name, "status"), "Active")

		doc.reload()
		doc.due_date = add_days(nowdate(), -1)
		doc.save()
		self.assertEqual(frappe.db.get_value(doc.doctype, doc.name, "status"), "Overdue")

	def test_source_status(self):
		past = add_days(nowdate(), -1)
		self.assertEqual(retention.source_status(1, 100, 0, 0, None), "Active")
		self.assertEqual(retention.source_status(1, 100, 0, 0, past), "Overdue")
		self.assertEqual(retention.source_status(1, 100, 40, 0, None), "Partly Billed")
		self.assertEqual(retention.source_status(1, 100, 40, 0, past), "Overdue")
		self.assertEqual(retention.source_status(1, 100, 100, 40, past), "Billed")
		self.assertEqual(retention.source_status(1, 100, 100, 100, past), "Paid")
		self.assertEqual(retention.source_status(2, 100, 0, 0, None), "Cancelled")

	def test_mapping_from_invoice(self):
		invoice = frappe._dict(
			doctype="Sales Invoice",
			name="SINV-TEST-1",
			company=COMPANY,
			customer=CUSTOMER,
			posting_date=nowdate(),
			project=None,
			po_no="PO-123",
			net_total=50000,
			custom_subject_to_retention=1,
			custom_retention_percent=5,
			custom_retention_amount=2500,
			items=[frappe._dict(project=None)],
		)
		self.assertTrue(retention.has_retention(invoice))
		doc = retention.make_source_from_invoice(invoice)
		self.assertEqual((doc.doctype, doc.customer, doc.customer_po), ("Retention Receivable", CUSTOMER, "PO-123"))
		row = doc.retention_items[0]
		self.assertEqual((row.sales_invoice_no, row.base_amount, row.amount), ("SINV-TEST-1", 50000, 2500))

		invoice.custom_retention_amount = 0
		self.assertFalse(retention.has_retention(invoice))

	def test_cannot_cancel_when_claimed(self):
		source = make_source()
		claim = retention.make_retention_invoice(source.name)
		claim.insert()
		self.assertRaises(frappe.ValidationError, source.cancel)
