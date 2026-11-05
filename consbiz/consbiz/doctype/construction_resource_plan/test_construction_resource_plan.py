# Copyright (c) 2026, Siricons and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import getdate

from consbiz.consbiz.doctype.construction_management.construction_management import (
	create_from_boq,
	get_schedule_data,
	save_tasks,
)
from consbiz.consbiz.doctype.construction_management.resources import get_overview
from consbiz.consbiz.doctype.construction_resource_plan.construction_resource_plan import (
	actual_resources,
	planned_resources,
)
from consbiz.consbiz.report.construction_resource_histogram.construction_resource_histogram import execute
from consbiz.tests.utils import insert_boq

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


class IntegrationTestConstructionResourcePlan(IntegrationTestCase):
	def setUp(self):
		boq = frappe.new_doc("BOQ")
		boq.naming_series = frappe.get_meta("BOQ").get_field("naming_series").options.split("\n")[0]
		boq.date = "2026-11-02"
		for row in (
			{"wbs": "1", "item_name": "หมวด", "quantity": 0},
			{"wbs": "1.1", "item_name": "งานขุดดิน", "quantity": 10, "total_amount": 3000},
			{"wbs": "1.2", "item_name": "งานคอนกรีต", "quantity": 0, "total_amount": 1000},
		):
			boq.append("boq_details", row)
		insert_boq(boq)
		self.plan = create_from_boq(boq.name)
		_group, a, b = frappe.get_doc("Construction Management", self.plan).tasks
		save_tasks(
			self.plan,
			frappe.as_json(
				[
					{"name": a.name, "start_date": "2026-11-02", "end_date": "2026-11-04"},
					{"name": b.name, "start_date": "2026-11-04", "end_date": "2026-11-05"},
				]
			),
			str(frappe.db.get_value("Construction Management", self.plan, "modified")),
		)

	def make_plan(self, items):
		doc = frappe.new_doc("Construction Resource Plan")
		doc.construction_management = self.plan
		for item in items:
			doc.append("items", item)
		return doc.insert()

	def test_planned_per_day(self):
		self.make_plan(
			[
				{"wbs": "1.1", "resource_type": "Labour", "resource": "คนงาน", "qty_per_day": 4},
				{"wbs": "1.1", "resource_type": "Equipment", "resource": "รถขุด", "qty_per_day": 1},
				{"wbs": "1.2", "resource_type": "Labour", "resource": "คนงาน", "qty_per_day": 6},
			]
		)
		planned = planned_resources(self.plan, "2026-11-01", "2026-11-30")
		# 4 พ.ย. ทั้งสองงานซ้อนกัน
		self.assertEqual(planned[("Labour", "คนงาน", getdate("2026-11-04"))], 10)
		self.assertEqual(planned[("Labour", "คนงาน", getdate("2026-11-05"))], 6)
		self.assertEqual(planned[("Equipment", "รถขุด", getdate("2026-11-02"))], 1)
		self.assertNotIn(("Equipment", "รถขุด", getdate("2026-11-05")), planned)

	def test_validation(self):
		with self.assertRaises(frappe.ValidationError):
			self.make_plan([{"wbs": "1", "resource_type": "Labour", "resource": "คนงาน", "qty_per_day": 1}])
		with self.assertRaises(frappe.ValidationError):
			self.make_plan([{"wbs": "1.1", "resource_type": "Labour", "resource": "คนงาน", "qty_per_day": 0}])
		row = {"wbs": "1.1", "resource_type": "Labour", "resource": "คนงาน", "qty_per_day": 1}
		with self.assertRaises(frappe.ValidationError):
			self.make_plan([row, row])

	def test_compare_with_daily_report(self):
		self.make_plan([{"wbs": "1.1", "resource_type": "Labour", "resource": "คนงาน", "qty_per_day": 4}])
		report = frappe.new_doc("Daily Report")
		report.construction_management = self.plan
		report.date = "2026-11-03"
		report.append("items", {"wbs": "1.1", "qty": 2})
		report.append("labour", {"role": "คนงาน", "qty": 3})
		report.insert()
		report.submit()

		actual = actual_resources(self.plan, "2026-11-01", "2026-11-30")
		self.assertEqual(actual[("Labour", "คนงาน", getdate("2026-11-03"))], 3)

		_columns, rows, _message, chart = execute(
			{
				"construction_management": self.plan,
				"from_date": "2026-11-01",
				"to_date": "2026-11-30",
				"periodicity": "Monthly",
			}
		)
		row = next(r for r in rows if r.resource == "คนงาน")
		self.assertEqual((row.planned, row.actual, row.variance), (12, 3, -9))
		self.assertEqual(len(chart["data"]["datasets"]), 2)

	def save_from_gantt(self, items, modified=None):
		"""บันทึกจากแผงด้านขวาของหน้า Gantt (ส่งรายการทั้งชุดพร้อมแผนงาน)"""
		return save_tasks(
			self.plan,
			"[]",
			str(frappe.db.get_value("Construction Management", self.plan, "modified")),
			resources=frappe.as_json({"modified": modified, "items": items}),
		)

	def test_save_from_gantt(self):
		tasks = {t.wbs: t.name for t in frappe.get_doc("Construction Management", self.plan).tasks}
		# ยังไม่มีแผน: สร้างให้
		data = self.save_from_gantt(
			[
				{
					"task": tasks["1.1"],
					"wbs": "1.1",
					"resource_type": "Labour",
					"resource": "คนงาน",
					"qty_per_day": 4,
					"lead_time_days": 3,
				},
				{
					"task": tasks["1.2"],
					"wbs": "1.2",
					"resource_type": "Equipment",
					"resource": "รถขุด",
					"qty_per_day": 1,
				},
			]
		)
		plan = data["resource_plan"]
		self.assertTrue(plan["exists"])
		self.assertEqual(
			[(r["wbs"], r["resource"], r["lead_time_days"]) for r in plan["items"]],
			[("1.1", "คนงาน", 3), ("1.2", "รถขุด", 0)],
		)

		# แก้แถวเดิม (name เดิม) และลบแถวที่ไม่ส่งมา
		first = {**plan["items"][0], "qty_per_day": 5}
		data = self.save_from_gantt([first], plan["modified"])
		self.assertEqual(
			[(r["name"], r["qty_per_day"]) for r in data["resource_plan"]["items"]], [(first["name"], 5)]
		)

		# แผนถูกแก้จากที่อื่นหลังเปิดหน้า Gantt
		with self.assertRaises(frappe.TimestampMismatchError):
			self.save_from_gantt([first], plan["modified"])
		# ค่าจากหน้า Gantt ผ่าน validate ของแผนด้วย
		with self.assertRaises(frappe.ValidationError):
			self.save_from_gantt([{**first, "qty_per_day": 0}], data["resource_plan"]["modified"])
		self.assertEqual(get_schedule_data(self.plan)["resource_plan"]["items"][0]["qty_per_day"], 5)

	def test_overview(self):
		self.make_plan(
			[
				{
					"wbs": "1.1",
					"resource_type": "Labour",
					"resource": "คนงาน",
					"qty_per_day": 4,
					"lead_time_days": 7,
				},
				{
					"wbs": "1.2",
					"resource_type": "Labour",
					"resource": "คนงาน",
					"qty_per_day": 6,
					"lead_time_days": 2,
				},
			]
		)
		overview = get_overview(self.plan, day="2026-10-25")
		(labour,) = overview["resources"]
		# 1.1 เริ่ม 2 พ.ย. จองก่อน 7 วัน = 26 ต.ค. (1.2 เริ่ม 4 พ.ย. จอง 2 พ.ย. ช้ากว่า)
		self.assertEqual(getdate(labour["book_by"]), getdate("2026-10-26"))
		self.assertEqual((labour["next_task"], labour["days_left"], labour["status"]), ("1.1", 1, "due"))
		# 2-3 พ.ย. 4 คน, 4 พ.ย. 4 + 6, 5 พ.ย. 6 คน
		self.assertEqual((labour["peak"], labour["total"]), (10, 24))
		self.assertEqual(
			(getdate(labour["start_date"]), getdate(labour["end_date"])),
			(getdate("2026-11-02"), getdate("2026-11-05")),
		)
		self.assertTrue(overview["chart"]["datasets"])

		# งานที่เริ่มแล้วไม่ต้องจอง
		labour = get_overview(self.plan, day="2026-11-03")["resources"][0]
		self.assertEqual((labour["next_task"], getdate(labour["book_by"])), ("1.2", getdate("2026-11-02")))
		self.assertEqual(labour["status"], "late")
