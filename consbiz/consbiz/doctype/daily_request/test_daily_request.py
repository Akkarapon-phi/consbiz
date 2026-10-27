# Copyright (c) 2026, Siricons and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import cint

from consbiz.consbiz.doctype.construction_management.construction_management import create_from_boq
from consbiz.consbiz.doctype.daily_report.daily_report import DEFAULT_LABOUR, get_default_resources
from consbiz.consbiz.doctype.daily_request.daily_request import make_daily_report, reject

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
	"User",
]


class IntegrationTestDailyRequest(IntegrationTestCase):
	def setUp(self):
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
		# งานทุกแถวเริ่มและจบวันที่ 2026-11-02 (วันเริ่มของ BOQ, 1 วัน)
		self.plan = create_from_boq(boq.name)

	def make_request(self, items, date="2026-11-02"):
		request = frappe.new_doc("Daily Request")
		request.construction_management = self.plan
		request.date = date
		request.approver = "Administrator"
		for item in items:
			request.append("items", item)
		request.append("labour", {"role": "ช่างไม้", "qty": 4})
		# แถวตั้งต้นที่ไม่กรอกจำนวนถูกลบตอนบันทึก
		request.append("labour", {"role": "วิศวกร"})
		request.append("equipment", {"equipment": "รถเครน"})
		request.insert()
		return request

	def test_planned_progress(self):
		request = self.make_request([{"wbs": "1.1", "qty": 3}, {"wbs": "1.2", "percent": 50}])
		qty_row, lump_row = request.items
		self.assertAlmostEqual(qty_row.percent, 30)
		self.assertEqual(qty_row.remaining_qty, 7)
		# น้ำหนัก 75% (3000/4000) x 30% และ 25% x 50%
		self.assertAlmostEqual(qty_row.weight, 75)
		self.assertAlmostEqual(qty_row.project_percent, 22.5)
		self.assertAlmostEqual(lump_row.project_percent, 12.5)
		self.assertAlmostEqual(request.planned_progress, 35)
		self.assertAlmostEqual(request.expected_progress, 35)
		# แผนสะสม ณ 2 พ.ย. = 100% (ยังไม่ตั้ง Baseline ใช้แผนปัจจุบัน)
		self.assertAlmostEqual(request.baseline_progress, 100)
		self.assertEqual(request.plan_basis, "Current Plan")
		self.assertAlmostEqual(request.progress_variance, -65)
		self.assertEqual(qty_row.in_plan, 1)
		self.assertEqual(request.status, "Pending")

		request.date = "2026-11-05"
		request.save()
		self.assertEqual(request.items[0].in_plan, 0)

	def open_todos(self, request):
		return frappe.get_all(
			"ToDo",
			filters={"reference_type": "Daily Request", "reference_name": request.name, "status": "Open"},
			pluck="allocated_to",
		)

	def test_default_resources(self):
		defaults = get_default_resources("Daily Request", self.plan)
		self.assertEqual(defaults["labour"], list(DEFAULT_LABOUR))
		self.assertTrue(defaults["equipment"])

		request = self.make_request([{"wbs": "1.2", "percent": 10}])
		self.assertEqual([row.role for row in request.labour], ["ช่างไม้"])
		self.assertFalse(request.equipment)
		# รายชื่อจากคำขอล่าสุดของแผนเดียวกันมาก่อนรายการมาตรฐาน
		self.assertEqual(get_default_resources("Daily Request", self.plan)["labour"][0], "ช่างไม้")

	def test_approver(self):
		request = frappe.new_doc("Daily Request")
		request.construction_management = self.plan
		request.date = "2026-11-02"
		request.approver = "Guest"
		request.append("items", {"wbs": "1.2", "percent": 10})
		# ผู้อนุมัติต้องมีสิทธิ์ Submit
		with self.assertRaises(frappe.ValidationError):
			request.insert()

		request = self.make_request([{"wbs": "1.2", "percent": 10}])
		self.assertEqual(request.approver_name, frappe.db.get_value("User", "Administrator", "full_name"))
		self.assertEqual(self.open_todos(request), ["Administrator"])
		request.submit()
		self.assertFalse(self.open_todos(request))

	def test_invalid_rows(self):
		# เกินปริมาณ BOQ
		with self.assertRaises(frappe.ValidationError):
			self.make_request([{"wbs": "1.1", "qty": 11}])
		# เลือกหัวข้อกลุ่มไม่ได้
		with self.assertRaises(frappe.ValidationError):
			self.make_request([{"wbs": "1", "percent": 10}])
		# งานซ้ำ
		with self.assertRaises(frappe.ValidationError):
			self.make_request([{"wbs": "1.2", "percent": 10}, {"wbs": "1.2", "percent": 20}])
		# ไม่ได้กรอกปริมาณ
		with self.assertRaises(frappe.ValidationError):
			self.make_request([{"wbs": "1.2"}])

	def test_reject_and_approve(self):
		request = self.make_request([{"wbs": "1.1", "qty": 3}])

		with self.assertRaises(frappe.ValidationError):
			reject(request.name, " ")
		reject(request.name, "ขาดแผนความปลอดภัย")
		request.reload()
		self.assertEqual(request.status, "Rejected")
		self.assertFalse(self.open_todos(request))
		self.assertEqual(request.rejection_reason, "ขาดแผนความปลอดภัย")

		# แก้แล้วบันทึกใหม่ = ส่งขออนุมัติอีกครั้ง
		request.safety_measures = "ใช้ Full body harness"
		request.save()
		self.assertEqual(request.status, "Pending")
		self.assertFalse(request.rejection_reason)
		self.assertEqual(self.open_todos(request), ["Administrator"])

		request.submit()
		self.assertEqual(request.status, "Approved")
		self.assertEqual(request.approved_by, frappe.session.user)
		# คำขออนุมัติไม่นับเป็นความคืบหน้าจริง
		self.assertFalse(frappe.db.exists("Construction Progress Entry", {"construction_management": self.plan}))

		request.cancel()
		self.assertEqual(frappe.db.get_value("Daily Request", request.name, "status"), "Cancelled")

	def test_make_daily_report(self):
		request = self.make_request([{"wbs": "1.1", "qty": 3, "remarks": "แผน"}])
		# ยังไม่อนุมัติ สร้าง Daily Report ไม่ได้
		with self.assertRaises(frappe.ValidationError):
			make_daily_report(request.name)
		request.submit()

		report = make_daily_report(request.name)
		self.assertEqual(report.daily_request, request.name)
		# ใช้ series ของ Daily Report ไม่ใช่ของคำขอ
		self.assertNotEqual(report.naming_series, request.naming_series)
		self.assertEqual(report.construction_management, self.plan)
		self.assertEqual(report.items[0].wbs, "1.1")
		self.assertEqual(report.items[0].qty, 3)
		self.assertFalse(report.items[0].remarks)
		self.assertEqual(report.labour[0].role, "ช่างไม้")
		report.items[0].qty = 2
		report.insert()
		self.assertTrue(report.name.startswith("DR-"))
		# 1 คำขอสร้าง Daily Report ได้ฉบับเดียว (นับฉบับ Draft ด้วย)
		with self.assertRaises(frappe.ValidationError):
			make_daily_report(request.name)
		duplicate = frappe.copy_doc(report)
		duplicate.daily_request = request.name
		with self.assertRaises(frappe.ValidationError):
			duplicate.insert()

		self.assertEqual(self.request_status(request), "Approved")
		report.submit()
		self.assertEqual(self.request_status(request), "Completed")
		self.assertAlmostEqual(frappe.db.get_value("Construction Management", self.plan, "actual_progress"), 15)
		with self.assertRaises(frappe.ValidationError):
			make_daily_report(request.name)
		# มี Daily Report ที่ Submit อ้างอยู่ ยกเลิกคำขอไม่ได้
		with self.assertRaises(frappe.LinkExistsError):
			frappe.get_doc("Daily Request", request.name).cancel()

		# ความคืบหน้าจริงที่เพิ่มขึ้นนับในคำขอฉบับถัดไป
		next_request = self.make_request([{"wbs": "1.1", "qty": 1}], date="2026-11-03")
		self.assertEqual(next_request.items[0].previous_qty, 2)
		self.assertAlmostEqual(next_request.current_progress, 15)
		self.assertAlmostEqual(next_request.expected_progress, 22.5)

		# ยกเลิก Daily Report แล้วคำขอกลับเป็น Approved สร้างใหม่ได้ ฉบับ Amend ยังอ้างคำขอเดิม
		report.cancel()
		self.assertEqual(self.request_status(request), "Approved")
		amended = frappe.copy_doc(report)
		amended.amended_from = report.name
		amended.insert()
		self.assertEqual(amended.daily_request, request.name)
		amended.delete()
		self.assertEqual(make_daily_report(request.name).daily_request, request.name)

	def request_status(self, request):
		return frappe.db.get_value("Daily Request", request.name, "status")

	def test_qty_rounded_on_screen(self):
		"""กรอกตามคงเหลือที่จอปัดทศนิยมแล้วเกินไม่ถึงครึ่งหน่วย = ทำครบพอดี ทั้ง Daily Request และ Daily Report"""
		half = 0.5 / 10 ** cint(frappe.new_doc("Daily Request Item").precision("qty") or 3)

		request = self.make_request(
			[{"wbs": "1.1", "qty": 10 + half * 0.8}, {"wbs": "1.2", "percent": 100 + half * 0.8}]
		)
		self.assertEqual(request.items[0].qty, 10)
		self.assertEqual(request.items[0].remaining_qty, 0)
		self.assertAlmostEqual(request.items[0].percent, 100)
		self.assertEqual(request.items[1].percent, 100)
		with self.assertRaises(frappe.ValidationError):
			self.make_request([{"wbs": "1.1", "qty": 10 + half * 2}])

		report = frappe.new_doc("Daily Report")
		report.construction_management = self.plan
		report.date = "2026-11-02"
		report.append("items", {"wbs": "1.1", "qty": 10 + half * 0.8})
		report.insert()
		self.assertEqual(report.items[0].qty, 10)
		report.submit()

	def test_print_format(self):
		request = self.make_request([{"wbs": "1.1", "qty": 3}], date="2026-11-03")
		html = frappe.get_print("Daily Request", request.name, "Daily Request", doc=request)
		# ลงนามทั้งสองฝั่งวันก่อนวันปฏิบัติงาน, แผนสะสม ณ 3 พ.ย. = 100% (ทุกงานจบ 2 พ.ย.)
		self.assertEqual(html.count("วันที่ 2 พฤศจิกายน 2569"), 2)
		self.assertIn("ช้ากว่าแผน", html)
		self.assertIn("(แผน 100.00%)", html)
		self.assertIn("การอนุมัติ", html)
		self.assertNotIn("มาตรการความปลอดภัย", html)
