# Copyright (c) 2026, Siricons and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import getdate

from consbiz.consbiz.doctype.construction_management.construction_management import (
	add_working_days,
	count_working_days,
)

EXTRA_TEST_RECORD_DEPENDENCIES = []
IGNORE_TEST_RECORD_DEPENDENCIES = ["BOQ", "Customer", "Company", "Holiday List", "UOM", "Project"]


class IntegrationTestConstructionManagement(IntegrationTestCase):
	def make_schedule(self, tasks):
		doc = frappe.new_doc("Construction Management")
		doc.start_date = "2026-11-02"
		for task in tasks:
			doc.append("tasks", task)
		doc.flags.ignore_links = True
		# ไม่ insert: ทดสอบเฉพาะการคำนวณใน validate (ข้ามเช็ก BOQ ที่ใช้งานซ้ำ)
		doc.status = "Inactive"
		doc.run_method("validate")
		return doc

	def test_structure_weight_and_rollup(self):
		doc = self.make_schedule(
			[
				{"wbs": "1", "item_name": "งานเตรียมการ"},
				{"wbs": "1.1", "amount": 1000, "start_date": "2026-11-02", "end_date": "2026-11-05"},
				{"wbs": "1.2", "amount": 3000, "start_date": "2026-11-04", "duration": 3},
				{"wbs": "2", "item_name": "งานโครงสร้าง"},
				{"wbs": "2.1", "amount": 6000, "start_date": "2026-11-10", "end_date": "2026-11-10"},
			]
		)
		g1, t11, t12, g2, _t21 = doc.tasks

		self.assertEqual([r.indent for r in doc.tasks], [0, 1, 1, 0, 1])
		self.assertEqual([r.is_group for r in doc.tasks], [1, 0, 0, 1, 0])
		self.assertEqual(doc.total_amount, 10000)
		self.assertAlmostEqual(t11.weight, 10)
		self.assertAlmostEqual(g1.weight, 40)
		self.assertAlmostEqual(g2.weight, 60)
		self.assertEqual(g1.amount, 4000)

		self.assertEqual(t11.duration, 4)
		self.assertEqual(getdate(t12.end_date), getdate("2026-11-06"))
		self.assertEqual(getdate(g1.start_date), getdate("2026-11-02"))
		self.assertEqual(getdate(g1.end_date), getdate("2026-11-06"))
		self.assertEqual(g1.duration, 5)

	def test_contract_duration(self):
		doc = self.make_schedule(
			[{"wbs": "1", "amount": 1, "start_date": "2026-11-02", "end_date": "2026-11-05"}]
		)
		self.assertEqual(doc.duration, 0)
		doc.finish_date = "2026-11-30"
		doc.run_method("validate")
		# 2 - 30 พ.ย. นับรวมวันแรก = 29 วัน
		self.assertEqual(doc.duration, 29)
		doc.finish_date = "2026-11-01"
		with self.assertRaises(frappe.ValidationError):
			doc.run_method("validate")

	def test_end_before_start(self):
		with self.assertRaises(frappe.ValidationError):
			self.make_schedule(
				[{"wbs": "1", "amount": 1, "start_date": "2026-11-05", "end_date": "2026-11-04"}]
			)

	def test_working_days(self):
		# 2026-11-07 และ 2026-11-08 เป็นเสาร์-อาทิตย์
		holidays = {getdate("2026-11-07"), getdate("2026-11-08")}
		self.assertEqual(count_working_days("2026-11-06", "2026-11-09", holidays), 2)
		self.assertEqual(count_working_days("2026-11-06", "2026-11-09", set()), 4)
		self.assertEqual(add_working_days("2026-11-06", 2, holidays), getdate("2026-11-09"))
		self.assertEqual(add_working_days("2026-11-07", 1, holidays), getdate("2026-11-09"))


class IntegrationTestConstructionProgress(IntegrationTestCase):
	def setUp(self):
		from consbiz.consbiz.doctype.construction_management.construction_management import create_from_boq

		boq = frappe.new_doc("BOQ")
		boq.naming_series = frappe.get_meta("BOQ").get_field("naming_series").options.split("\n")[0]
		boq.date = "2026-11-02"
		for row in (
			{"wbs": "1", "item_name": "หมวด", "quantity": 0},
			{"wbs": "1.1", "item_name": "งานมีปริมาณ", "quantity": 10, "total_amount": 3000},
			{"wbs": "1.2", "item_name": "งานเหมา", "quantity": 0, "total_amount": 1000},
		):
			boq.append("boq_details", row)
		boq.insert()
		self.doc = frappe.get_doc("Construction Management", create_from_boq(boq.name))
		self.group, self.qty_task, self.lump_task = self.doc.tasks

	def save(self, progress, tasks=None):
		from consbiz.consbiz.doctype.construction_management.construction_management import save_tasks

		self.doc.reload()
		data = save_tasks(
			self.doc.name, frappe.as_json(tasks or []), str(self.doc.modified), frappe.as_json(progress)
		)
		self.doc.reload()
		return data

	def test_progress_totals(self):
		self.save(
			[
				{"task": self.qty_task.name, "date": "2026-11-03", "qty": 4},
				{"task": self.qty_task.name, "date": "2026-11-04", "qty": 1},
				{"task": self.lump_task.name, "date": "2026-11-04", "percent": 20},
			]
		)
		qty_task, lump_task = self.doc.tasks[1], self.doc.tasks[2]
		self.assertEqual(qty_task.actual_qty, 5)
		self.assertAlmostEqual(qty_task.progress, 50)
		self.assertAlmostEqual(lump_task.progress, 20)
		# 75% x 50% + 25% x 20%
		self.assertAlmostEqual(self.doc.actual_progress, 42.5)
		self.assertAlmostEqual(self.doc.tasks[0].progress, 42.5)

		# ค่า 0 ลบรายการของวันนั้น
		self.save([{"task": self.qty_task.name, "date": "2026-11-04", "qty": 0}])
		self.assertEqual(self.doc.tasks[1].actual_qty, 4)

	def test_progress_cannot_exceed_quantity(self):
		with self.assertRaises(frappe.ValidationError):
			self.save([{"task": self.qty_task.name, "date": "2026-11-03", "qty": 11}])

	def test_baseline(self):
		from consbiz.consbiz.doctype.construction_management.construction_management import set_baseline

		set_baseline(self.doc.name, str(self.doc.modified))
		self.doc.reload()
		self.assertEqual(self.doc.tasks[1].baseline_start_date, self.doc.tasks[1].start_date)
		self.assertEqual(self.doc.tasks[0].baseline_end_date, self.doc.tasks[0].end_date)
		self.assertTrue(self.doc.baseline_date)

	def make_report(self, items, date="2026-11-05"):
		report = frappe.new_doc("Daily Report")
		report.construction_management = self.doc.name
		report.date = date
		for item in items:
			report.append("items", item)
		report.insert()
		return report

	def test_daily_report(self):
		report = self.make_report([{"wbs": "1.1", "qty": 3}, {"wbs": "1.2", "percent": 50}])
		self.assertAlmostEqual(report.items[0].percent, 30)
		self.assertEqual(report.items[0].remaining_qty, 7)
		report.submit()
		self.doc.reload()
		self.assertEqual(self.doc.tasks[1].actual_qty, 3)
		self.assertAlmostEqual(self.doc.tasks[2].progress, 50)

		# รวมกับฉบับก่อนแล้วเกินปริมาณ BOQ
		with self.assertRaises(frappe.ValidationError):
			self.make_report([{"wbs": "1.1", "qty": 8}], date="2026-11-06")
		# เลือกหัวข้อกลุ่มไม่ได้
		with self.assertRaises(frappe.ValidationError):
			self.make_report([{"wbs": "1", "percent": 10}], date="2026-11-06")

		# รายการจาก Daily Report ลบตรงไม่ได้ ต้อง Cancel
		entry = frappe.get_last_doc("Construction Progress Entry", {"reference_name": report.name})
		with self.assertRaises(frappe.ValidationError):
			entry.delete()

		report.cancel()
		self.doc.reload()
		self.assertEqual(self.doc.tasks[1].actual_qty, 0)
		self.assertFalse(frappe.db.exists("Construction Progress Entry", {"reference_name": report.name}))

	def test_plan_distribution(self):
		self.save(
			[],
			tasks=[
				{
					"name": self.qty_task.name,
					"start_date": "2026-11-01",
					"end_date": "2026-11-30",
					"plan_distribution": {"unit": "mweek", "weights": [10, 20, 30, 40]},
				}
			],
		)
		self.assertEqual(frappe.parse_json(self.doc.tasks[1].plan_distribution)["weights"], [10, 20, 30, 40])

		with self.assertRaises(frappe.ValidationError):
			self.save(
				[],
				tasks=[
					{
						"name": self.qty_task.name,
						"start_date": "2026-11-01",
						"end_date": "2026-11-30",
						"plan_distribution": {"unit": "mweek", "weights": [10, 20, 30, 30]},
					}
				],
			)

		# Baseline เก็บ % ที่กำหนดเองไปด้วย
		from consbiz.consbiz.doctype.construction_management.construction_management import set_baseline

		set_baseline(self.doc.name, str(self.doc.modified))
		self.doc.reload()
		self.assertEqual(self.doc.tasks[1].baseline_distribution, self.doc.tasks[1].plan_distribution)
