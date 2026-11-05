# Copyright (c) 2026, Siricons and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import getdate

from consbiz.consbiz.doctype.construction_management.construction_management import (
	create_from_boq,
	get_schedule_data,
)
from consbiz.tests.utils import insert_boq

EXTRA_TEST_RECORD_DEPENDENCIES = []
IGNORE_TEST_RECORD_DEPENDENCIES = [
	"Construction Management",
	"Variation Order",
	"BOQ",
	"Customer",
	"Company",
	"Holiday List",
	"UOM",
	"Project",
]


class IntegrationTestExtensionofTime(IntegrationTestCase):
	def setUp(self):
		boq = frappe.new_doc("BOQ")
		boq.naming_series = frappe.get_meta("BOQ").get_field("naming_series").options.split("\n")[0]
		boq.date = "2026-11-02"
		for row in (
			{"wbs": "1", "item_name": "หมวด"},
			{"wbs": "1.1", "item_name": "งานคอนกรีต", "quantity": 10, "material_rate": 300},
		):
			boq.append("boq_details", row)
		insert_boq(boq)
		self.plan = create_from_boq(boq.name)
		plan = self.get_plan()
		plan.start_date = "2026-11-01"
		plan.finish_date = "2026-11-30"
		plan.save()

	def make_extension(self, days=10, submit=True, **values):
		doc = frappe.new_doc("Extension of Time")
		doc.construction_management = self.plan
		doc.title = "ผู้ว่าจ้างส่งมอบพื้นที่ล่าช้า"
		doc.cause = "Employer Delay"
		doc.date = "2026-11-10"
		doc.event_start = "2026-11-03"
		doc.event_end = "2026-11-08"
		doc.requested_days = days
		doc.update(values)
		doc.insert()
		if submit:
			doc.submit()
		return doc

	def approve(self, doc, days=None, status="Approved"):
		doc.reload()
		doc.employer_status = status
		doc.approved_days = days
		doc.save()
		return doc

	def get_plan(self):
		return frappe.get_doc("Construction Management", self.plan)

	def test_finish_moves_after_approval_only(self):
		doc = self.make_extension(10)
		plan = self.get_plan()
		self.assertEqual(plan.extension_days, 0)
		self.assertEqual(getdate(plan.revised_finish_date), getdate("2026-11-30"))
		self.assertEqual(getdate(doc.notice_deadline), getdate("2026-11-23"))

		# อนุมัติไม่ระบุจำนวนวัน = เท่าที่ขอ นับวันปฏิทิน
		doc = self.approve(doc)
		self.assertEqual(doc.approved_days, 10)
		self.assertEqual(getdate(doc.revised_finish_date), getdate("2026-12-10"))
		plan = self.get_plan()
		self.assertEqual(plan.extension_days, 10)
		self.assertEqual(getdate(plan.finish_date), getdate("2026-11-30"))
		self.assertEqual(getdate(plan.revised_finish_date), getdate("2026-12-10"))
		self.assertEqual(plan.revised_duration, 40)

		data = get_schedule_data(self.plan)
		self.assertEqual(data["extension_days"], 10)
		self.assertEqual([e.name for e in data["extensions"]], [doc.name])

	def test_partial_approval_and_multiple_extensions(self):
		first = self.approve(self.make_extension(10), days=6)
		second = self.approve(self.make_extension(5))
		self.assertEqual(second.previous_extension_days, 6)
		self.assertEqual(getdate(second.revised_finish_date), getdate("2026-12-11"))
		self.assertEqual(self.get_plan().extension_days, 11)

		# ลดจำนวนวันหลังอนุมัติ แผนงานคำนวณใหม่
		self.approve(first, days=2)
		self.assertEqual(getdate(self.get_plan().revised_finish_date), getdate("2026-12-07"))

	def test_rejected_and_cancelled_not_counted(self):
		rejected = self.approve(self.make_extension(10), status="Rejected")
		self.assertEqual(rejected.approved_days, 0)
		approved = self.approve(self.make_extension(4))
		self.assertEqual(self.get_plan().extension_days, 4)

		approved.reload()
		approved.cancel()
		plan = self.get_plan()
		self.assertEqual(plan.extension_days, 0)
		self.assertEqual(getdate(plan.revised_finish_date), getdate("2026-11-30"))

	def test_plan_tasks_not_moved(self):
		before = [(row.start_date, row.end_date) for row in self.get_plan().tasks]
		self.approve(self.make_extension(10))
		self.assertEqual([(row.start_date, row.end_date) for row in self.get_plan().tasks], before)

	def test_days_from_variation_order(self):
		order = frappe.new_doc("Variation Order")
		order.construction_management = self.plan
		order.title = "งานเพิ่ม"
		order.extension_days = 7
		order.append(
			"items", {"variation_type": "Addition", "item_name": "รางระบายน้ำ", "qty": 1, "rate": 100}
		)
		order.insert()
		order.submit()

		doc = self.make_extension(0, submit=False, cause="Variation Order", variation_order=order.name)
		self.assertEqual(doc.requested_days, 7)

	def test_validation(self):
		with self.assertRaises(frappe.ValidationError):
			self.make_extension(0)
		with self.assertRaises(frappe.ValidationError):
			self.make_extension(5, event_start="2026-11-09", event_end="2026-11-08")
		with self.assertRaises(frappe.ValidationError):
			self.make_extension(5, cause="Variation Order")
