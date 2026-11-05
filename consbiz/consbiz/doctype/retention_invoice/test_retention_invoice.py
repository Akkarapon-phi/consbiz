# Copyright (c) 2026, Siricons and Contributors
# See license.txt

# ใบวางบิลเงินประกันผลงาน (consbiz/retention.py): เบิกบางส่วน, กันเบิกเกิน, JE รับเงินคืน, สถานะ RR

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, getdate, nowdate

from consbiz import retention
from consbiz.consbiz.doctype.retention_receivable.test_retention_receivable import (
	COMPANY,
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
	"DocType",
	"Journal Entry",
]


def make_claim(source, amount=None, submit=True):
	doc = retention.make_claim(source.doctype, source.name)
	if amount is not None:
		doc.retention_items[0].amount = amount
	doc.insert()
	if submit:
		doc.submit()
	return doc


def status(doc):
	return frappe.db.get_value(doc.doctype, doc.name, "status")


def gl(voucher_no):
	return {
		row.account: row.debit - row.credit
		for row in frappe.get_all(
			"GL Entry",
			filters={"voucher_no": voucher_no, "is_cancelled": 0},
			fields=["account", "debit", "credit"],
		)
	}


class IntegrationTestRetentionInvoice(IntegrationTestCase):
	def setUp(self):
		self.accounts = setup_retention_masters()

	def test_partial_claims(self):
		source = make_source(amounts=(1000,))
		first = make_claim(source, 400)
		self.assertEqual(first.retention_items[0].retention_doctype, "Retention Receivable")
		self.assertEqual(first.retention_items[0].outstanding_amount, 1000)
		self.assertEqual(first.grand_total, 400)
		self.assertEqual(status(first), "Unpaid")
		source.reload()
		self.assertEqual(
			(source.status, source.billed_amount, source.outstanding_amount), ("Partly Billed", 400, 600)
		)

		# ค่าเริ่มต้นของใบถัดไป = ยอดคงเหลือ
		second = make_claim(source)
		self.assertEqual(second.retention_items[0].amount, 600)
		source.reload()
		self.assertEqual((source.status, source.outstanding_amount), ("Billed", 0))
		self.assertRaises(frappe.ValidationError, retention.make_claim, source.doctype, source.name)

		second.cancel()
		source.reload()
		self.assertEqual((source.status, source.outstanding_amount), ("Partly Billed", 600))

	def test_over_claim_counts_drafts(self):
		source = make_source(amounts=(1000,))
		make_claim(source, 700, submit=False)
		doc = retention.make_claim(source.doctype, source.name)
		self.assertEqual(doc.retention_items[0].amount, 300)
		doc.retention_items[0].amount = 301
		self.assertRaises(frappe.ValidationError, doc.insert)

	def test_rejects_other_party_and_duplicates(self):
		source = make_source()
		doc = retention.make_claim(source.doctype, source.name)
		doc.append("retention_items", {"retention_reference": source.name, "amount": 1})
		self.assertRaises(frappe.ValidationError, doc.insert)

		draft = make_source(submit=False)
		doc = retention.make_claim(source.doctype, source.name)
		doc.append("retention_items", {"retention_reference": draft.name, "amount": 1})
		self.assertRaises(frappe.ValidationError, doc.insert)

	def test_due_date_from_credit_days(self):
		source = make_source()
		doc = retention.make_claim(source.doctype, source.name)
		doc.credit_day = 15
		doc.insert()
		self.assertEqual(getdate(doc.due_date), getdate(add_days(doc.posting_date, 15)))

	def test_journal_entry_receives_cash(self):
		source = make_source(amounts=(1000,))
		claim = make_claim(source)
		cash = cash_account()

		je_name = retention.make_journal_entry(claim.doctype, claim.name, cash)
		self.assertEqual(frappe.db.get_value(claim.doctype, claim.name, "journal_entry"), je_name)
		# เรียกซ้ำตอน JE ยังเป็นร่าง ได้ใบเดิม
		self.assertEqual(retention.make_journal_entry(claim.doctype, claim.name, cash), je_name)

		je = frappe.get_doc("Journal Entry", je_name)
		je.submit()
		# รับเงินคืน: Dr. เงินสด / Cr. เงินประกันผลงานรอเรียกเก็บ
		self.assertEqual(gl(je_name), {cash: 1000, self.accounts["custom_retention_receivable"]: -1000})
		self.assertEqual(status(claim), "Paid")
		source.reload()
		self.assertEqual((source.status, source.paid_amount), ("Paid", 1000))

		# ยกเลิก RI ไม่ได้จนกว่าจะยกเลิก JE
		claim.reload()
		self.assertRaises(frappe.ValidationError, claim.cancel)

		je.reload()
		je.cancel()
		self.assertEqual(status(claim), "Unpaid")
		source.reload()
		self.assertEqual((source.status, source.paid_amount), ("Billed", 0))

		# JE เดิมถูกยกเลิกแล้ว สร้างใบใหม่ได้
		self.assertNotEqual(retention.make_journal_entry(claim.doctype, claim.name, cash), je_name)

	def test_cancel_claim_deletes_draft_journal_entry(self):
		claim = make_claim(make_source())
		je_name = retention.make_journal_entry(claim.doctype, claim.name, cash_account())
		claim.reload()
		claim.cancel()
		self.assertFalse(frappe.db.exists("Journal Entry", je_name))
		self.assertEqual(status(claim), "Cancelled")

	def test_delete_draft_journal_entry_unlinks(self):
		claim = make_claim(make_source())
		je_name = retention.make_journal_entry(claim.doctype, claim.name, cash_account())
		frappe.delete_doc("Journal Entry", je_name)
		self.assertIsNone(frappe.db.get_value(claim.doctype, claim.name, "journal_entry"))

	def test_rejects_non_cash_account(self):
		claim = make_claim(make_source())
		self.assertRaises(
			frappe.ValidationError,
			retention.make_journal_entry,
			claim.doctype,
			claim.name,
			self.accounts["custom_retention_receivable"],
		)

	def test_update_overdue(self):
		source = make_source(due_date=add_days(nowdate(), 5))
		claim = make_claim(source, 100)
		frappe.db.set_value(source.doctype, source.name, "due_date", add_days(nowdate(), -1))
		frappe.db.set_value(claim.doctype, claim.name, "due_date", add_days(nowdate(), -1))
		retention.update_overdue()
		self.assertEqual(status(source), "Overdue")
		self.assertEqual(status(claim), "Overdue")

	def test_open_retentions(self):
		source = make_source(amounts=(1000,))
		make_claim(source, 250, submit=False)
		rows = retention.get_open_retentions("Retention Invoice", COMPANY, source.customer)
		row = next(r for r in rows if r.name == source.name)
		self.assertEqual(row.remaining, 750)
