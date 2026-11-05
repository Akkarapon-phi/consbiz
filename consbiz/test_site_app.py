# Copyright (c) 2026, Siricons and Contributors
# See license.txt

# แอปหน้างาน (site_app.py): หมวดงานตามสิทธิ์, หน้าหลัก/รายการของหมวดควบคุมงาน

import json

import frappe
from frappe.tests import IntegrationTestCase

from consbiz import site_app
from consbiz.consbiz.doctype.construction_management.construction_management import create_from_boq
from consbiz.test_store_app import setup_store
from consbiz.tests.utils import insert_boq


def make_plan(project):
	boq = frappe.new_doc("BOQ")
	boq.naming_series = frappe.get_meta("BOQ").get_field("naming_series").options.split("\n")[0]
	boq.date = "2026-11-02"
	boq.project = project
	for row in (
		{"wbs": "1", "item_name": "หมวด", "quantity": 0},
		{"wbs": "1.1", "item_name": "งานมีปริมาณ", "quantity": 10, "total_amount": 3000},
	):
		boq.append("boq_details", row)
	insert_boq(boq)
	plan = create_from_boq(boq.name)
	frappe.db.set_value("Construction Management", plan, "project", project)
	return plan


class IntegrationTestSiteApp(IntegrationTestCase):
	def setUp(self):
		self.project = setup_store()
		# 1 โครงการใช้แผนงานเดียว (construction_management_of): ลบแผนของเทสต์รอบก่อน
		for name in frappe.get_all("Construction Management", {"project": self.project}, pluck="name"):
			frappe.db.set_value("Construction Management", name, "project", None)

	def test_sections_follow_permissions(self):
		boot = site_app.boot_data()
		self.assertEqual(boot["sections"], ["store", "work", "pm", "buy", "sell"])
		self.assertTrue(boot["can"]["daily_report"])

	def test_project_without_plan(self):
		summary = site_app.get_work_summary(self.project)
		self.assertIsNone(summary["construction_management"])
		self.assertIsNone(summary["progress"])
		self.assertIsNone(site_app.get_calendar(self.project, "2026-11-01"))
		self.assertIsNone(site_app.get_pm_summary(self.project))
		self.assertIsNone(site_app.get_plan(self.project))
		self.assertEqual(site_app.get_inspections(self.project, "punch"), [])
		self.assertRaises(frappe.ValidationError, site_app.get_report_form, self.project, "Daily Report")

	def save(self, doctype, data, submit=0):
		return site_app.save_report(self.project, doctype, json.dumps(data, default=str), submit=submit)

	def test_request_flow(self):
		plan = make_plan(self.project)
		form = site_app.get_report_form(self.project, "Daily Request", date="2026-11-02")
		doc = form["doc"]
		self.assertIsNone(doc["name"])
		self.assertEqual(doc["approver"], None)
		self.assertIn("1.1", [t["wbs"] for t in form["tasks"]])
		# รายชื่อคน/เครื่องจักรตั้งต้น จำนวน 0 (ไม่ได้กรอก = ไม่บันทึก)
		self.assertTrue(doc["labour"] and not any(r["qty"] for r in doc["labour"]))

		doc.update({"approver": "Administrator", "items": [{"wbs": "1.1", "qty": 3}]})
		doc["labour"][0]["qty"] = 4
		result = self.save("Daily Request", doc)
		request = frappe.get_doc("Daily Request", result["name"])
		self.assertEqual((request.docstatus, request.status), (0, "Pending"))
		self.assertEqual(len(request.labour), 1)
		self.assertEqual(len(request.equipment), 0)

		# Draft สถานะ Pending = รออนุมัติ
		summary = site_app.get_work_summary(self.project)
		self.assertEqual(summary["construction_management"], plan)
		self.assertEqual(summary["requests_pending"], 1)
		self.assertTrue(summary["curve"])
		calendar = site_app.get_calendar(self.project, "2026-11-01")
		row = next(r for r in calendar["requests"] if r.name == request.name)
		self.assertEqual((row.status_label, row.status_tone), ("รออนุมัติ", "amber"))

		view = site_app.get_report_form(self.project, "Daily Request", name=request.name, view=1)
		self.assertTrue(view["can_approve"])
		self.assertNotIn("tasks", view)

		site_app.reject_request(request.name, "เลื่อนไปพรุ่งนี้")
		self.assertEqual(frappe.db.get_value("Daily Request", request.name, "status"), "Rejected")
		# แก้แล้วบันทึกใหม่ = ส่งขออนุมัติอีกครั้ง
		doc["name"] = request.name
		self.save("Daily Request", doc)
		self.assertEqual(frappe.db.get_value("Daily Request", request.name, "status"), "Pending")

		site_app.approve_request(request.name)
		view = site_app.get_report_form(self.project, "Daily Request", name=request.name, view=1)
		self.assertEqual(view["doc"]["status"], "Approved")
		self.assertTrue(view["can_make_report"])
		self.assertEqual(site_app.get_work_summary(self.project)["requests_ready"][0].name, request.name)

		# รายงานจากคำขอ: ดึงงาน คน และเครื่องจักรมาให้
		form = site_app.get_report_form(self.project, "Daily Report", from_request=request.name)
		report = form["doc"]
		self.assertEqual(report["daily_request"], request.name)
		self.assertEqual([r["wbs"] for r in report["items"]], ["1.1"])
		report["items"][0].update({"qty": 2, "location": "ชั้น 2 โซน A"})
		result = self.save("Daily Report", report, submit=1)
		self.assertEqual(
			frappe.db.get_value("Daily Report Item", {"parent": result["name"]}, "location"), "ชั้น 2 โซน A"
		)
		self.assertIn(
			"download_pdf",
			site_app.get_report_form(self.project, "Daily Report", name=result["name"], view=1)["pdf_url"],
		)
		self.assertEqual(result["docstatus"], 1)
		self.assertEqual(frappe.db.get_value("Daily Request", request.name, "status"), "Completed")
		self.assertEqual(
			site_app.get_report_form(self.project, "Daily Request", name=request.name, view=1)["report"],
			result["name"],
		)
		# ส่งแล้วแก้ไม่ได้
		report["name"] = result["name"]
		self.assertRaises(frappe.ValidationError, self.save, "Daily Report", report)

	def test_report_over_quantity(self):
		make_plan(self.project)
		doc = site_app.get_report_form(self.project, "Daily Report", date="2026-11-02")["doc"]
		doc["items"] = [{"wbs": "1.1", "qty": 11}]
		self.assertRaises(frappe.ValidationError, self.save, "Daily Report", doc)

	def test_plan_rows(self):
		plan = make_plan(self.project)
		data = site_app.get_plan(self.project)
		self.assertEqual(data["construction_management"], plan)
		group, task = data["rows"]
		# หัวข้อได้วันที่และ % จากงานย่อย
		self.assertEqual((group["is_group"], group["start"], group["end"]), (1, task["start"], task["end"]))
		self.assertEqual(group["actual"], task["actual"])
		self.assertIn(task["status"], ("done", "not_due", "on_track", "behind", "not_started", "overdue"))
		self.assertEqual(site_app.get_pm_summary(self.project)["construction_management"], plan)
		self.assertIn("groups", site_app.get_lookahead(self.project, date="2026-11-02"))
		self.assertIn("materials", site_app.get_resources(self.project))

	def test_status_labels(self):
		rows = [
			frappe._dict(docstatus=1, result="Failed"),
			frappe._dict(docstatus=1, result=None),
			frappe._dict(docstatus=0, result="Pending"),
		]
		site_app.with_status("Inspection Request", rows, "result")
		self.assertEqual(
			[(r.status_label, r.status_tone) for r in rows],
			[("ไม่ผ่าน", "rose"), ("ส่งแล้ว", "green"), ("ร่าง", "gray")],
		)
