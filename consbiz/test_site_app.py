# Copyright (c) 2026, Siricons and Contributors
# See license.txt

# แอปหน้างาน (site_app.py): หมวดงานตามสิทธิ์, หน้าหลัก/รายการของหมวดควบคุมงาน

import json
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from consbiz import site_app

# import ก่อน patch: ถ้า dashboard ถูก import ครั้งแรกระหว่าง patch จะจำ analyse ตัวปลอมไว้ตลอด
from consbiz.consbiz.doctype.construction_management import dashboard  # noqa: F401
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
		# หน้างาน: ขอซื้ออย่างเดียว (สั่งซื้อ/แจ้งหนี้/ขาย อยู่แอปออฟฟิศ)
		boot = site_app.boot_data()
		self.assertEqual(boot["sections"], ["store", "work", "pm", "resources", "buy"])
		self.assertTrue(boot["can"]["daily_report"])
		self.assertTrue(boot["can"]["finance"])
		self.assertEqual([a["key"] for a in boot["apps"]], ["site", "office"])

		office = site_app.office_boot_data()
		self.assertEqual(office["sections"], ["purchase", "sales", "boq"])
		self.assertTrue(office["companies"])
		self.assertEqual([a["key"] for a in office["apps"]], ["site", "office"])
		# Desktop: หมวดของทุกแอป มีทั้งขอซื้อของหน้างานและจัดซื้อของออฟฟิศ
		modules = [(m["app"], m["section"]) for m in office["modules"]]
		self.assertIn(("site", "buy"), modules)
		self.assertIn(("office", "purchase"), modules)
		self.assertIn({"app": "office", "section": "sales", "url": "/conserp/sales"}, office["modules"])
		self.assertIn({"app": "site", "section": "store", "url": "/conserp/store"}, boot["modules"])
		self.assertEqual(boot["modules"], office["modules"])

	def test_my_profile_returns_session_user(self):
		self.addCleanup(frappe.set_user, frappe.session.user)
		frappe.set_user("test@example.com")
		profile = site_app.get_my_profile()
		self.assertEqual(profile.email, "test@example.com")
		# คืนเฉพาะช่องที่กำหนด ไม่มีช่องอื่นของ User ติดมา
		self.assertEqual(set(profile), set(site_app.PROFILE_FIELDS))

	def test_apps_follow_permissions(self):
		# มีจัดซื้อของออฟฟิศก็ยังเห็นขอซื้อของหน้างาน
		self.assertIn("buy", [m["section"] for m in site_app.app_modules(site_app.sections_by_app())])
		# ไม่มีสิทธิ์เอกสารซื้อ-ขายเลย = ไม่เห็นแอปออฟฟิศ
		# ไม่มีหมวดหน้างานเลย = ไม่เห็นแอปหน้างาน
		with patch.dict(site_app.APP_SECTIONS, {"office": lambda: []}):
			by_app = site_app.sections_by_app()
			self.assertEqual([a["key"] for a in site_app.available_apps(by_app)], ["site"])
			self.assertIn("buy", [m["section"] for m in site_app.app_modules(by_app)])
		by_app = site_app.sections_by_app(("site", []))
		self.assertEqual([a["key"] for a in site_app.available_apps(by_app)], ["office"])
		self.assertTrue(all(m["app"] == "office" for m in site_app.app_modules(by_app)))

	def test_office_icon_in_saved_layouts(self):
		from consbiz.patches import add_consoffice_to_desktop_layouts as patch_module

		# ไซต์เทสต์บางไซต์ไม่มี Desktop Icon ของแอป (migrate ไม่ได้สร้าง): สร้างจากไฟล์เดียวกับที่ migrate ใช้
		if not frappe.db.exists("Desktop Icon", "ConsOffice"):
			path = frappe.get_app_path("consbiz", "desktop_icon", "consoffice.json")
			frappe.get_doc(json.loads(frappe.read_file(path))).insert(ignore_permissions=True)
		layout = frappe.get_doc(
			{
				"doctype": "Desktop Layout",
				"user": "Administrator",
				"layout": json.dumps([{"name": "ConsBiz"}, {"name": "ConsERP"}, {"name": "Home"}]),
			}
		)
		if frappe.db.exists("Desktop Layout", "Administrator"):
			layout = frappe.get_doc("Desktop Layout", "Administrator")
			layout.layout = json.dumps([{"name": "ConsBiz"}, {"name": "ConsERP"}, {"name": "Home"}])
			layout.save()
		else:
			layout.insert()
		patch_module.execute()
		patch_module.execute()  # รันซ้ำไม่ใส่ซ้ำ
		names = [i["name"] for i in json.loads(frappe.db.get_value("Desktop Layout", layout.name, "layout"))]
		self.assertEqual(names, ["ConsBiz", "ConsERP", "ConsOffice", "Home"])

	def test_project_without_plan(self):
		summary = site_app.get_work_summary(self.project)
		self.assertIsNone(summary["construction_management"])
		self.assertIsNone(summary["progress"])
		self.assertIsNone(site_app.get_calendar(self.project, "2026-11-01"))
		self.assertIsNone(site_app.get_pm_summary(self.project))
		self.assertIsNone(site_app.get_plan(self.project))
		self.assertEqual(site_app.get_inspections(self.project, "punch"), [])
		self.assertRaises(frappe.ValidationError, site_app.get_report_form, self.project, "Daily Report")

	def test_late_tasks_are_not_truncated(self):
		"""ภาพรวมแบ่งหน้าตารางในเครื่อง: API ต้องส่งงานที่ช้าครบ เรียงงานวิกฤตและช้ามากก่อน"""
		make_plan(self.project)
		base = {"status": "behind", "variance": -10, "actual_pct": 10, "plan_pct": 20}
		tasks = [
			frappe._dict(base, wbs=f"1.{i}", item_name=f"งาน {i}", delay_days=i, critical=0)
			for i in range(1, 9)
		]
		tasks.append(frappe._dict(base, wbs="2.1", item_name="งานวิกฤต", delay_days=1, critical=1))
		tasks.append(frappe._dict(base, wbs="3.1", item_name="เสร็จแล้ว", status="done", delay_days=9, critical=1))
		with patch(
			"consbiz.consbiz.doctype.construction_management.delay.analyse", return_value={"tasks": tasks}
		):
			summary = site_app.get_work_summary(self.project)
		self.assertEqual(summary["late_count"], 9)
		self.assertEqual(len(summary["late_tasks"]), 9)
		self.assertEqual([t["wbs"] for t in summary["late_tasks"][:2]], ["2.1", "1.8"])

	def test_pm_summary_matches_work_summary(self):
		"""ภาพรวมของแผนงานใช้งานที่ช้ากว่าแผน/ความคืบหน้าหมวดชุดเดียวกับควบคุมงาน"""
		make_plan(self.project)
		tasks = [
			frappe._dict(
				status="behind",
				variance=-10,
				actual_pct=10,
				plan_pct=20,
				wbs="1.1",
				item_name="งานช้า",
				delay_days=3,
				critical=1,
			)
		]
		rows = dashboard.late_tasks(tasks)
		self.assertEqual([(r["wbs"], r["delay_days"]) for r in rows], [("1.1", 3)])
		work = site_app.get_work_summary(self.project)
		pm = site_app.get_pm_summary(self.project)
		self.assertEqual([c["wbs"] for c in pm["categories"]], ["1"])
		self.assertEqual(pm["categories"], work["categories"])
		self.assertEqual(pm["late_tasks"], work["late_tasks"])

	def test_category_progress(self):
		def row(name, wbs, indent, amount=0, is_group=0, **kw):
			return frappe._dict(
				name=name, wbs=wbs, item_name=wbs, indent=indent, amount=amount, is_group=is_group, **kw
			)

		doc = frappe._dict(
			name="plan",
			tasks=[
				row("a", "1", 0, is_group=1),
				row("b", "1.1", 1, 100),
				row("c", "1.2", 1, 300),
				row("d", "2", 0, is_group=1),
				row("e", "2.1", 1),
				row("f", "2.2", 1),
				row("g", "VO", 0, is_group=1),
				row("h", "VO.1", 1, 500, is_variation=1),
				row("i", "VO.2", 1, 500, is_variation=1, counted_from="2026-12-01"),
				row("j", "3", 0, 200),
			],
		)
		done = {"b": {"percent": 100}, "e": {"percent": 50}, "i": {"percent": 100}, "j": {"percent": 10}}
		with patch(
			"consbiz.consbiz.doctype.construction_management.dashboard.actual_by_task", return_value=done
		):
			result = dashboard.category_progress(doc, frappe.utils.getdate("2026-11-10"))
		# งานเพิ่มยังไม่อนุมัติ/ยังไม่ถึงวันอนุมัติไม่นับ จึงไม่มีหมวด VO
		self.assertEqual([(c["wbs"], c["percent"]) for c in result], [("1", 25), ("2", 25), ("3", 10)])

	def test_report_list_and_bulk_print(self):
		make_plan(self.project)
		form = site_app.get_report_form(self.project, "Daily Request", date="2026-11-02")
		doc = form["doc"]
		doc.update({"approver": "Administrator", "items": [{"wbs": "1.1", "qty": 3}]})
		first = self.save("Daily Request", doc)["name"]
		doc.update({"date": "2026-11-03"})
		second = self.save("Daily Request", doc)["name"]

		result = site_app.get_report_list(self.project, "drq")
		self.assertEqual([r.name for r in result["rows"]], [second, first])
		self.assertEqual(result["rows"][0].status_label, "รออนุมัติ")
		self.assertEqual(result["print_limit"], site_app.BULK_PRINT_LIMIT)
		self.assertEqual(site_app.get_report_list(self.project, "dr")["rows"], [])
		self.assertRaises(frappe.ValidationError, site_app.get_report_list, self.project, "x")

		# รวมเป็นไฟล์เดียวตามลำดับที่ส่งมา ด้วย Print Format ของเอกสาร
		names = json.dumps([first, second])
		with (
			patch("frappe.utils.print_format.validate_print_permission") as permission,
			patch("frappe.get_print") as get_print,
		):
			site_app.reports_pdf("Daily Request", names)
		self.assertEqual(permission.call_count, 2)
		self.assertEqual([c.args[:3] for c in get_print.call_args_list], [
			("Daily Request", first, "Daily Request"),
			("Daily Request", second, "Daily Request"),
		])
		self.assertEqual(frappe.local.response.type, "pdf")

		self.assertRaises(frappe.ValidationError, site_app.reports_pdf, "Sales Invoice", names)
		self.assertRaises(frappe.ValidationError, site_app.reports_pdf, "Daily Request", "[]")
		too_many = json.dumps(["x"] * (site_app.BULK_PRINT_LIMIT + 1))
		self.assertRaises(frappe.ValidationError, site_app.reports_pdf, "Daily Request", too_many)

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

	def test_doc_project_for_notifications(self):
		make_plan(self.project)
		doc = site_app.get_report_form(self.project, "Daily Request", date="2026-11-02")["doc"]
		doc.update({"approver": "Administrator", "items": [{"wbs": "1.1", "qty": 3}]})
		name = self.save("Daily Request", doc)["name"]
		self.assertEqual(site_app.get_doc_project("Daily Request", name), self.project)

		# โครงการปิดแล้วไม่อยู่ในตัวเลือกของแอป = ให้เปิดระบบเต็ม
		frappe.db.set_value("Project", self.project, "status", "Completed")
		self.assertIsNone(site_app.get_doc_project("Daily Request", name))
		frappe.db.set_value("Project", self.project, "status", "Open")

		self.assertRaises(frappe.ValidationError, site_app.get_doc_project, "User", "Administrator")

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
		self.assertIn("material_plan", site_app.get_resource_board(self.project))
		self.assertIn("months", site_app.get_project_finance(self.project))

	def test_document_tabs(self):
		self.assertRaises(frappe.PermissionError, site_app.get_pm_document_rows, self.project, "User")
		self.assertEqual(site_app.get_pm_document_rows(self.project, "Variation Order"), [])

		plan = make_plan(self.project)
		for doctype, values in (
			("Variation Order", {"title": "งานเพิ่ม", "date": "2026-11-03", "net_amount": 500}),
			("Extension of Time", {"title": "ฝนตก", "date": "2026-11-03", "cause": "Other", "requested_days": 3}),
		):
			doc = frappe.new_doc(doctype)
			doc.update({"construction_management": plan, "project": self.project, **values})
			doc.naming_series = doc.meta.get_field("naming_series").options.split("\n")[0]
			doc.flags.ignore_validate = True
			doc.insert(ignore_mandatory=True)
			self.assertEqual(site_app.get_pm_document_rows(self.project, doctype)[0].status_label, "ร่าง")
			frappe.db.set_value(doctype, doc.name, {"docstatus": 1, "employer_status": "Approved"})
			self.assertEqual(site_app.get_pm_document_rows(self.project, doctype)[0].status_label, "อนุมัติแล้ว")

		self.assertEqual(site_app.get_pm_document_rows(self.project, "Variation Order")[0].net_amount, 500)
		# ผู้ไม่เห็นงบต้นทุนไม่ได้รับมูลค่างานเพิ่ม-ลด
		with patch("consbiz.site_app.can_view_finance", return_value=False):
			self.assertNotIn("net_amount", site_app.get_pm_document_rows(self.project, "Variation Order")[0])
		# เอกสารที่ไม่มีขั้นตอน Submit ไม่มีป้ายสถานะ
		self.assertEqual(site_app.get_pm_document_rows(self.project, "Construction Baseline"), [])

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
