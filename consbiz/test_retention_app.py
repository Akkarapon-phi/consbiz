# Copyright (c) 2026, Siricons and Contributors
# See license.txt

# หน้าจอเงินประกันผลงานของแอปออฟฟิศ (retention_app.py): รายการรวม 2 ชนิดต่อฝั่ง, ใบขอคืนจากเงินประกัน,
# บันทึก/ยืนยัน, บันทึกรับเงิน (JE) แล้วสถานะ Paid, แก้วันครบกำหนดคืน, ตัวเลขเมนู

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, nowdate

from consbiz import retention_app
from consbiz.consbiz.doctype.retention_receivable.test_retention_receivable import (
	COMPANY,
	CUSTOMER,
	cash_account,
	make_source,
	setup_retention_masters,
)


class IntegrationTestRetentionApp(IntegrationTestCase):
	def setUp(self):
		setup_retention_masters()

	def test_list_has_sources_and_claims(self):
		source = make_source(amounts=(1000,), due_date=add_days(nowdate(), -1))
		rows = retention_app.get_list("acc-retention-in", company=COMPANY)
		row = next(r for r in rows if r.name == source.name)
		self.assertEqual(row.type, "rr")
		self.assertEqual(row.status, "Overdue")
		self.assertEqual(row.amount, 1000)
		self.assertGreaterEqual(retention_app.get_summary(company=COMPANY)["retention_in"]["due"], 1)
		with self.assertRaises(frappe.PermissionError):
			retention_app.get_list("unknown")

	def test_claim_from_source_and_pay(self):
		source = make_source(amounts=(1000,))
		new = retention_app.get_doc("ri", source=source.name)
		self.assertEqual(new["doc"]["party"], CUSTOMER)
		self.assertEqual(new["doc"]["items"][0]["amount"], 1000)

		data = new["doc"]
		data["items"][0]["amount"] = 400
		saved = retention_app.save_claim("ri", frappe.as_json(data))
		name = saved["doc"]["name"]
		self.assertEqual(saved["doc"]["grand_total"], 400)
		self.assertTrue(saved["can_submit"])

		view = retention_app.submit_doc("ri", name)
		self.assertEqual(view["doc"]["status"], "Unpaid")
		self.assertTrue(view["can_pay"])
		self.assertEqual(retention_app.get_doc("rr", source.name)["remaining"], 600)

		paid = retention_app.record_payment("ri", name, cash_account())
		self.assertEqual(frappe.db.get_value("Journal Entry", paid["journal_entry"], "docstatus"), 1)
		self.assertEqual(paid["view"]["doc"]["status"], "Paid")
		self.assertEqual(frappe.db.get_value("Retention Receivable", source.name, "paid_amount"), 400)

	def test_set_due_date(self):
		source = make_source(amounts=(500,), due_date=add_days(nowdate(), -1))
		self.assertEqual(frappe.db.get_value("Retention Receivable", source.name, "status"), "Overdue")
		view = retention_app.set_due_date("rr", source.name, add_days(nowdate(), 30))
		self.assertEqual(view["doc"]["status"], "Active")

	def test_source_cannot_be_created_in_app(self):
		with self.assertRaises(frappe.ValidationError):
			retention_app.get_doc("rr")
