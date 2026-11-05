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
from consbiz.consbiz.report.construction_delay_analysis.construction_delay_analysis import execute
from consbiz.tests.utils import insert_boq

EXTRA_TEST_RECORD_DEPENDENCIES = []


class IntegrationTestConstructionDelayAnalysis(IntegrationTestCase):
	def setUp(self):
		boq = frappe.new_doc("BOQ")
		boq.naming_series = frappe.get_meta("BOQ").get_field("naming_series").options.split("\n")[0]
		boq.date = "2026-11-02"
		for row in (
			{"wbs": "1", "item_name": "หมวด", "quantity": 0},
			{"wbs": "1.1", "item_name": "งานมีปริมาณ", "quantity": 10, "total_amount": 3000},
			{"wbs": "1.2", "item_name": "งานเหมา", "quantity": 0, "total_amount": 1000},
			{"wbs": "1.3", "item_name": "งานต่อจาก 1.2", "quantity": 0, "total_amount": 1000},
		):
			boq.append("boq_details", row)
		insert_boq(boq)
		self.plan = create_from_boq(boq.name)
		doc = frappe.get_doc("Construction Management", self.plan)
		doc.start_date = "2026-11-02"
		doc.finish_date = "2026-11-10"
		doc.penalty_per_day = 100
		doc.save()
		_group, a, b, c = doc.tasks
		self.names = {"1.1": a.name, "1.2": b.name, "1.3": c.name}
		# นับวันปฏิทิน: 1.1 = 2-11 พ.ย., 1.2 = 3-4 พ.ย., 1.3 ต่อจาก 1.2 (FS) 5 วัน = 5-9 พ.ย.
		save_tasks(
			self.plan,
			frappe.as_json(
				[
					{"name": a.name, "start_date": "2026-11-02", "end_date": "2026-11-11"},
					{"name": b.name, "start_date": "2026-11-03", "end_date": "2026-11-04"},
					{
						"name": c.name,
						"start_date": "2026-11-05",
						"end_date": "2026-11-09",
						"predecessors": frappe.as_json([{"task": b.name, "type": "FS", "lag": 0}]),
					},
				]
			),
			str(frappe.db.get_value("Construction Management", self.plan, "modified")),
			frappe.as_json([{"task": a.name, "date": "2026-11-06", "qty": 5}]),
		)

	def report(self, **filters):
		_columns, rows, message, _chart, summary = execute(
			{"construction_management": self.plan, "date": "2026-11-06", **filters}
		)
		return {row.wbs: row for row in rows}, message, summary

	def test_delay_forecast_and_penalty(self):
		rows, message, summary = self.report(only_issues=0)
		a, b, c = rows["1.1"], rows["1.2"], rows["1.3"]

		# 1.1 ทำได้ 50% ตามแผน งานที่เหลือ 5 วันนับจากวันถัดไป
		self.assertEqual(a.status, "on_track")
		self.assertAlmostEqual(a.plan_pct, 50)
		self.assertEqual(a.forecast_end, getdate("2026-11-11"))
		self.assertTrue(a.critical)
		# 1.2 เลยวันจบแล้วยังไม่เริ่ม เริ่มได้วันถัดไป
		self.assertEqual(b.status, "overdue")
		self.assertEqual(b.forecast_end, getdate("2026-11-08"))
		self.assertEqual(b.delay_days, 4)
		self.assertEqual(b.total_float, 2)
		# 1.3 ควรเริ่มแล้ว เลื่อนตาม forecast ของงานก่อนหน้า
		self.assertEqual(c.status, "not_started")
		self.assertEqual(c.forecast_end, getdate("2026-11-13"))
		self.assertEqual(c.delay_days, 4)

		values = {item["label"]: item["value"] for item in summary}
		self.assertEqual(values["คาดว่าเสร็จ"], getdate("2026-11-13"))
		self.assertEqual(values["เกินกำหนด (วัน)"], 3)
		self.assertEqual(values["ค่าปรับคาดการณ์"], 300)
		self.assertIsNone(message)
		self.assertEqual(
			getdate(get_schedule_data(self.plan)["forecast_finish"]) >= getdate("2026-11-13"), True
		)

	def test_only_issues_and_extension(self):
		# ค่าเริ่มต้น "เฉพาะงานที่มีปัญหา" อยู่ที่ตัวกรองของหน้ารายงาน (JS) จึงส่งเองในเทสต์
		rows, _message, _summary = self.report(only_issues=1)
		self.assertEqual(sorted(rows), ["1.2", "1.3"])

		# EOT 3 วัน: เสร็จตามที่คาดพอดี ไม่มีค่าปรับ
		eot = frappe.new_doc("Extension of Time")
		eot.update(
			{
				"construction_management": self.plan,
				"title": "ส่งมอบพื้นที่ล่าช้า",
				"cause": "Employer Delay",
				"event_start": "2026-11-03",
				"requested_days": 3,
			}
		)
		eot.insert()
		eot.submit()
		eot.employer_status = "Approved"
		eot.save()
		values = {item["label"]: item["value"] for item in self.report()[2]}
		self.assertEqual(values["เกินกำหนด (วัน)"], 0)
		self.assertEqual(values["ค่าปรับคาดการณ์"], 0)

	def test_penalty_limit_warning(self):
		frappe.db.set_value("Construction Management", self.plan, "penalty_per_day", 1000)
		# 3 วัน x 1000 = 3000 จากสัญญา 5000 = 60% เกินเพดาน 10%
		self.assertIn("60", self.report()[1])
