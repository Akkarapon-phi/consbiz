# Copyright (c) 2026, Siricons and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import getdate, nowdate

from consbiz.consbiz.doctype.construction_management.construction_management import (
	create_from_boq,
	get_schedule_data,
)

EXTRA_TEST_RECORD_DEPENDENCIES = []
IGNORE_TEST_RECORD_DEPENDENCIES = [
	"Construction Management",
	"Daily Report",
	"BOQ",
	"Customer",
	"Company",
	"Holiday List",
	"UOM",
	"Project",
]


class IntegrationTestVariationOrder(IntegrationTestCase):
	def setUp(self):
		boq = frappe.new_doc("BOQ")
		boq.naming_series = frappe.get_meta("BOQ").get_field("naming_series").options.split("\n")[0]
		boq.date = "2026-11-02"
		for row in (
			{"wbs": "1", "item_name": "หมวด"},
			{"wbs": "1.1", "item_name": "งานคอนกรีต", "quantity": 10, "material_rate": 300},
			{"wbs": "1.2", "item_name": "งานเหล็ก", "quantity": 4, "material_rate": 250},
		):
			boq.append("boq_details", row)
		boq.insert()
		# สัญญาเดิม 4000: 1.1 = 3000 (75%), 1.2 = 1000 (25%)
		self.plan = create_from_boq(boq.name)

	def make_order(self, items, submit=True, **values):
		order = frappe.new_doc("Variation Order")
		order.construction_management = self.plan
		order.title = "เปลี่ยนแปลงงาน"
		order.update(values)
		for item in items:
			order.append("items", item)
		order.insert()
		if submit:
			order.submit()
		return order

	def approve(self, order, date="2026-11-05"):
		order.reload()
		order.employer_status = "Approved"
		order.employer_approved_on = date
		order.save()

	def make_report(self, items, date="2026-11-02"):
		report = frappe.new_doc("Daily Report")
		report.construction_management = self.plan
		report.date = date
		for item in items:
			report.append("items", item)
		report.insert()
		report.submit()
		return report

	def get_plan(self):
		return frappe.get_doc("Construction Management", self.plan)

	def get_task(self, wbs):
		return next(row for row in self.get_plan().tasks if row.wbs == wbs)

	def test_addition_counted_after_approval(self):
		order = self.make_order(
			[
				{"variation_type": "Addition", "item_name": "รางระบายน้ำ", "qty": 5, "rate": 100},
				# เพิ่มปริมาณรายการเดิม: ราคาต่อหน่วยตั้งต้นจากงานเดิม
				{"variation_type": "Addition", "wbs": "1.1", "qty": 2},
			]
		)
		self.assertEqual([row.variation_wbs for row in order.items], ["VO.1", "VO.2"])
		self.assertEqual(order.items[1].rate, 300)
		self.assertEqual(order.addition_amount, 1100)
		self.assertEqual(order.revised_amount, 5100)

		plan = self.get_plan()
		self.assertEqual([row.wbs for row in plan.tasks], ["1", "1.1", "1.2", "VO", "VO.1", "VO.2"])
		group, _drain, extra = plan.tasks[3:]
		self.assertEqual(group.is_group, 1)
		self.assertEqual(group.amount, 1100)
		self.assertTrue(extra.item_name.startswith("(งานเพิ่ม)"))
		self.assertEqual(extra.source_wbs, "1.1")
		self.assertEqual(extra.variation_order, order.name)
		# ผู้ว่าจ้างยังไม่อนุมัติ: ลง Daily Report ได้ แต่ยังไม่นับในมูลค่าสัญญาและ %
		self.assertEqual(extra.weight, 0)
		self.assertFalse(extra.counted_from)
		self.assertEqual(plan.revised_amount, 4000)

		self.make_report([{"wbs": "1.1", "qty": 10}, {"wbs": "VO.2", "qty": 1}])
		self.assertAlmostEqual(self.get_plan().actual_progress, 75)

		# เกินปริมาณงานเดิม: แนะนำให้ลงในงานเพิ่มที่อ้างงานนั้น
		with self.assertRaisesRegex(frappe.ValidationError, "VO.2"):
			self.make_report([{"wbs": "1.1", "qty": 1}], date="2026-11-03")

		# อนุมัติแล้ว: มูลค่าสัญญา 5100 น้ำหนักทุกงานคิดใหม่ % = มูลค่าที่ทำแล้ว / สัญญาปรับปรุง
		self.approve(order)
		plan = self.get_plan()
		self.assertEqual(plan.total_amount, 4000)
		self.assertEqual(plan.variation_amount, 1100)
		self.assertEqual(plan.revised_amount, 5100)
		self.assertAlmostEqual(plan.tasks[1].weight, 3000 / 5100 * 100)
		self.assertAlmostEqual(plan.tasks[5].weight, 600 / 5100 * 100)
		self.assertEqual(getdate(plan.tasks[5].counted_from), getdate("2026-11-05"))
		self.assertAlmostEqual(sum(row.weight for row in plan.tasks if not row.is_group), 100)
		self.assertAlmostEqual(plan.actual_progress, 3300 / 5100 * 100)
		# % ตามสัญญาเดิมไว้อ้างอิง (ไม่รวมงานเพิ่ม)
		self.assertAlmostEqual(plan.contract_progress, 75)

		steps = get_schedule_data(self.plan)["variation_steps"]
		self.assertEqual([(getdate(s.date), s.amount) for s in steps], [(getdate("2026-11-05"), 1100)])

	def test_omission(self):
		report = self.make_report([{"wbs": "1.1", "qty": 3}])
		self.assertAlmostEqual(self.get_plan().actual_progress, 22.5)

		order = self.make_order([{"variation_type": "Omission", "wbs": "1.1", "qty": 4}])
		self.assertEqual(order.items[0].rate, 300)
		self.assertEqual(order.items[0].contract_qty, 10)
		self.assertEqual(order.omission_amount, 1200)
		self.assertEqual(order.net_amount, -1200)

		# Submit แล้วปริมาณลดทันที (Daily Report ลงเกินไม่ได้) แต่ยังไม่นับจนกว่าผู้ว่าจ้างอนุมัติ
		task = self.get_task("1.1")
		self.assertEqual(task.quantity, 6)
		self.assertEqual(task.contract_quantity, 10)
		self.assertEqual(task.amount, 1800)
		self.assertEqual(task.counted_amount, 3000)
		self.assertAlmostEqual(task.progress, 50)
		self.assertAlmostEqual(
			frappe.db.get_value("Construction Progress Entry", {"reference_name": report.name}, "percent"), 50
		)
		self.assertAlmostEqual(self.get_plan().actual_progress, 22.5)

		self.approve(order)
		plan = self.get_plan()
		self.assertEqual(plan.revised_amount, 2800)
		self.assertEqual(plan.tasks[1].counted_amount, 1800)
		self.assertAlmostEqual(plan.actual_progress, 900 / 2800 * 100)

		# ลดได้ไม่ต่ำกว่าที่ทำไปแล้ว: เหลือให้ลดได้อีก 10 - 4 - 3 = 3
		with self.assertRaises(frappe.ValidationError):
			self.make_order([{"variation_type": "Omission", "wbs": "1.1", "qty": 4}], submit=False)
		# งานลดต้องเลือกงานเดิม และห้ามลดงานเดียวกันซ้ำในฉบับเดียว
		with self.assertRaises(frappe.ValidationError):
			self.make_order([{"variation_type": "Omission", "item_name": "x", "qty": 1}], submit=False)
		with self.assertRaises(frappe.ValidationError):
			self.make_order(
				[
					{"variation_type": "Omission", "wbs": "1.2", "qty": 1},
					{"variation_type": "Omission", "wbs": "1.2", "qty": 1},
				],
				submit=False,
			)

		# ทำครบปริมาณที่เหลือ = งานนั้นครบ
		self.make_report([{"wbs": "1.1", "qty": 3}], date="2026-11-03")
		plan = self.get_plan()
		self.assertAlmostEqual(plan.tasks[1].progress, 100)
		self.assertAlmostEqual(plan.actual_progress, 1800 / 2800 * 100)

		# ยกเลิกงานลด: ปริมาณและมูลค่าสัญญากลับเป็นเดิม
		order.reload()
		order.cancel()
		plan = self.get_plan()
		self.assertEqual(plan.tasks[1].quantity, 10)
		self.assertAlmostEqual(plan.tasks[1].progress, 60)
		self.assertEqual(plan.revised_amount, 4000)
		self.assertAlmostEqual(plan.actual_progress, 45)

	def test_update_after_submit(self):
		order = self.make_order(
			[{"variation_type": "Addition", "item_name": "รั้วชั่วคราว", "qty": 5, "rate": 100}],
			is_provisional=1,
		)
		self.make_report([{"wbs": "VO.1", "qty": 2}])
		self.assertAlmostEqual(self.get_task("VO.1").progress, 40)

		order.reload()
		order.items[0].qty = 8
		order.items[0].rate = 120
		order.employer_status = "Approved"
		order.save()
		self.assertEqual(order.items[0].amount, 960)
		self.assertEqual(order.items[0].variation_wbs, "VO.1")
		# ไม่ใส่วันที่อนุมัติ = วันที่เปลี่ยนเป็น Approved
		self.assertEqual(getdate(order.employer_approved_on), getdate(nowdate()))
		task = self.get_task("VO.1")
		self.assertEqual(task.quantity, 8)
		self.assertEqual(task.amount, 960)
		self.assertAlmostEqual(task.progress, 25)
		self.assertEqual(self.get_plan().revised_amount, 4960)

		# ปริมาณใหม่ต้องไม่น้อยกว่าที่ทำไปแล้ว
		order.items[0].qty = 1
		with self.assertRaises(frappe.ValidationError):
			order.save()

		# กลับเป็นรออนุมัติ: เลิกนับในมูลค่าสัญญา
		order.reload()
		order.employer_status = "Pending"
		order.save()
		self.assertFalse(order.employer_approved_on)
		self.assertEqual(self.get_plan().revised_amount, 4000)

	def test_cancel_and_numbering(self):
		lump = self.make_order([{"variation_type": "Addition", "item_name": "งานป้ายโครงการ", "amount": 500}])
		task = self.get_task("VO.1")
		self.assertEqual(task.quantity, 0)
		self.assertEqual(task.amount, 500)

		# งานเพิ่มยังไม่มีความคืบหน้า ยกเลิกได้ แถวหายจากแผน
		lump.cancel()
		self.assertEqual([row.wbs for row in self.get_plan().tasks], ["1", "1.1", "1.2"])

		# ไม่ใช้เลข WBS ซ้ำกับฉบับที่ยกเลิก
		order = self.make_order([{"variation_type": "Addition", "item_name": "งานป้ายโครงการ", "amount": 600}])
		self.assertEqual(order.items[0].variation_wbs, "VO.2")
		self.make_report([{"wbs": "VO.2", "percent": 50}])
		self.assertAlmostEqual(self.get_task("VO.2").progress, 50)
		# มีความคืบหน้าแล้ว ยกเลิกไม่ได้
		order.reload()
		with self.assertRaises(frappe.ValidationError):
			order.cancel()

		# กรอกมูลค่าไม่ครบ
		with self.assertRaises(frappe.ValidationError):
			self.make_order([{"variation_type": "Addition", "item_name": "ไม่มีราคา", "qty": 1}], submit=False)
