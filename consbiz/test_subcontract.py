# Copyright (c) 2026, Siricons and Contributors
# See license.txt

# สัญญาจ้างเหมาช่วง + ใบเบิกงวด (subcontract.py): ยอดเบิก, เพดานเงินประกัน, งวดงาน, ปริมาณเกินสัญญา, ปิดสัญญา
# ใบงานเพิ่ม (subcontract_variation.py) แบบยังไม่มี PO (PO + PDF ฉบับเดิมตรวจบนไซต์ทดสอบด้วยมือ)

import frappe
from frappe.tests import IntegrationTestCase

from consbiz.test_store_app import setup_store

SUPPLIER = "_Test Subcontractor"


def make_supplier():
	if not frappe.db.exists("Supplier", SUPPLIER):
		frappe.get_doc({"doctype": "Supplier", "supplier_name": SUPPLIER}).insert(ignore_permissions=True)
	return SUPPLIER


class IntegrationTestSubcontract(IntegrationTestCase):
	def setUp(self):
		self.project = setup_store()
		self.supplier = make_supplier()

	def agreement(self, method="Measured", **kw):
		values = {
			"doctype": "Subcontract Agreement",
			"title": "งานโครงสร้าง",
			"supplier": self.supplier,
			"project": self.project,
			"contract_date": "2026-11-01",
			"billing_method": method,
			"retention_percent": 5,
			"retention_cap_percent": 3,
			"wht_percent": 3,
			"penalty_per_day": 1000,
			"items": [
				{"item_name": "งานเสา", "qty": 10, "rate": 10000},
				{"item_name": "งานคาน", "qty": 20, "rate": 5000},
			],
		}
		values.update(kw)
		doc = frappe.get_doc(values)
		doc.insert()
		doc.submit()
		return doc

	def claim(self, agreement, rows=None, **kw):
		doc = frappe.get_doc(
			{
				"doctype": "Subcontract Claim",
				"subcontract_agreement": agreement.name,
				"items": [{"agreement_item": agreement.items[i].name, "qty": q} for i, q in (rows or [])],
				**kw,
			}
		)
		doc.insert()
		return doc

	def test_agreement_totals_and_company(self):
		doc = self.agreement()
		self.assertEqual(doc.total_amount, 200000)
		self.assertEqual(doc.status, "Active")
		self.assertEqual(doc.company, frappe.db.get_value("Project", self.project, "company"))

	def test_measured_claims_and_retention_cap(self):
		agreement = self.agreement()
		first = self.claim(agreement, [(0, 5)], penalty_days=2)
		self.assertEqual(first.claim_no, 1)
		self.assertEqual(first.gross_amount, 50000)
		self.assertEqual(first.retention_amount, 2500)
		self.assertEqual(first.wht_amount, 1500)
		self.assertEqual(first.penalty_amount, 2000)
		self.assertEqual(first.net_amount, 44000)
		first.submit()

		# กรอกงวดนี้: เกินคงเหลือ (เบิกแล้ว 5 จาก 10) / ติดลบ
		self.assertRaises(frappe.ValidationError, self.claim, agreement, [(0, 6)])
		self.assertRaises(frappe.ValidationError, self.claim, agreement, [(0, -1), (1, 1)])

		second = self.claim(agreement, [(0, 5), (1, 20)])
		self.assertEqual(
			[(r.previous_qty, r.qty, r.cumulative_qty, r.remaining_qty) for r in second.items],
			[(5, 5, 10, 0), (0, 20, 20, 0)],
		)
		self.assertEqual(second.claim_no, 2)
		self.assertEqual(second.gross_amount, 150000)
		# เพดาน 3% ของ 200,000 = 6,000 หักไปแล้ว 2,500
		self.assertEqual(second.retention_amount, 3500)
		second.submit()
		agreement.reload()
		self.assertEqual(agreement.status, "Completed")
		self.assertEqual(agreement.retention_held, 6000)
		self.assertEqual(agreement.items[0].claimed_qty, 10)

		second.cancel()
		agreement.reload()
		self.assertEqual(agreement.status, "Active")
		self.assertEqual(agreement.claimed_amount, 50000)

	def test_milestones(self):
		self.assertRaises(
			frappe.ValidationError,
			self.agreement,
			"Milestone",
			milestones=[{"description": "งวด 1", "percent": 50}],
		)
		agreement = self.agreement(
			"Milestone",
			retention_cap_percent=0,
			milestones=[{"description": "งวด 1", "percent": 30}, {"description": "งวด 2", "percent": 70}],
		)
		first = self.claim(agreement, milestone=agreement.milestones[0].name)
		self.assertEqual(first.gross_amount, 60000)
		self.assertEqual([r.qty for r in first.items], [3, 6])
		first.submit()
		# งวดที่เบิกแล้วใช้ซ้ำไม่ได้
		self.assertRaises(
			frappe.ValidationError, self.claim, agreement, milestone=agreement.milestones[0].name
		)
		last = self.claim(agreement, milestone=agreement.milestones[1].name)
		# งวดสุดท้ายเบิกส่วนที่เหลือทั้งหมด
		self.assertEqual([r.cumulative_qty for r in last.items], [10, 20])
		last.submit()
		agreement.reload()
		self.assertEqual(agreement.status, "Completed")

	def test_close_agreement(self):
		from consbiz import subcontract

		agreement = self.agreement(warranty_days=365)
		self.claim(agreement, [(0, 4)]).submit()
		self.assertRaises(frappe.ValidationError, subcontract.close_agreement, agreement.name, "")
		draft = self.claim(agreement, [(0, 1)])
		# มีใบเบิกร่าง = ปิดไม่ได้
		self.assertRaises(frappe.ValidationError, subcontract.close_agreement, agreement.name, "จบงาน")
		draft.delete()
		subcontract.close_agreement(agreement.name, "งานจบตามที่วัดได้จริง")
		agreement.reload()
		self.assertEqual(agreement.status, "Closed")
		self.assertTrue(agreement.warranty_end)
		self.assertRaises(frappe.ValidationError, self.claim, agreement, [(0, 1)])
		subcontract.reopen_agreement(agreement.name)
		agreement.reload()
		self.assertEqual(agreement.status, "Active")

	def variation(self, agreement, rows):
		doc = frappe.get_doc(
			{
				"doctype": "Subcontract Variation",
				"subcontract_agreement": agreement.name,
				"posting_date": "2026-11-15",
				"reason": "ผู้ว่าจ้างสั่งเพิ่ม",
				"items": [{"item_name": name, "qty": q, "rate": rate} for name, q, rate in rows],
			}
		)
		doc.insert()
		return doc

	def test_variation_appendix(self):
		agreement = self.agreement()
		self.claim(agreement, [(0, 10)]).submit()
		# เบิกครบแถวแรกแล้ว เกินต้องทำใบงานเพิ่ม
		self.assertRaises(frappe.ValidationError, self.claim, agreement, [(0, 1)])
		variation = self.variation(agreement, [("งานเสาเพิ่ม", 2, 10000), ("งานพื้น", 5, 2000)])
		self.assertEqual(variation.revision_no, 1)
		self.assertEqual(variation.addition_amount, 30000)
		self.assertEqual(variation.revised_amount, 230000)
		variation.submit()
		agreement.reload()
		# งานหลักไม่เปลี่ยน งานเพิ่มเป็นแถวแนบท้าย
		self.assertEqual([r.qty for r in agreement.items], [10, 20, 2, 5])
		self.assertEqual([r.variation for r in agreement.items][2:], [variation.name] * 2)
		self.assertEqual(agreement.original_amount, 200000)
		self.assertEqual(agreement.variation_amount, 30000)
		self.assertEqual(agreement.total_amount, 230000)
		self.assertEqual(agreement.revision, 1)
		claim = self.claim(agreement, [(2, 2), (3, 5)])
		self.assertEqual(claim.gross_amount, 30000)
		claim.submit()
		# เบิกแถวแนบท้ายไปแล้ว ยกเลิกใบงานเพิ่มไม่ได้
		self.assertRaises(
			frappe.ValidationError, frappe.get_doc("Subcontract Variation", variation.name).cancel
		)
		claim.cancel()
		frappe.get_doc("Subcontract Variation", variation.name).cancel()
		agreement.reload()
		self.assertEqual(agreement.total_amount, 200000)
		self.assertEqual(agreement.revision, 0)
		self.assertEqual(len(agreement.items), 2)

	def test_milestone_with_appendix(self):
		agreement = self.agreement(
			"Milestone",
			retention_cap_percent=0,
			milestones=[{"description": "งวด 1", "percent": 30}, {"description": "งวด 2", "percent": 70}],
		)
		self.variation(agreement, [("งานเพิ่ม", 4, 1000)]).submit()
		agreement.reload()
		# % งวดคิดจากงานหลักเท่านั้น (200,000) งานเพิ่มเบิกตามปริมาณในใบเดียวกันได้
		first = self.claim(agreement, [(2, 1)], milestone=agreement.milestones[0].name)
		self.assertEqual([r.qty for r in first.items], [3, 6, 1])
		self.assertEqual(first.gross_amount, 60000 + 1000)
		first.submit()
		# ไม่เลือกงวด = เบิกเฉพาะงานเพิ่ม งานหลักคงเดิม
		only = self.claim(agreement, [(2, 3)])
		self.assertEqual([r.qty for r in only.items], [0, 0, 3])
		self.assertEqual(only.gross_amount, 3000)
