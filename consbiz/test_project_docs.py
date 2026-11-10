# Copyright (c) 2026, Siricons and Contributors
# See license.txt

# เอกสารโครงการในแอป (project_docs.py): สร้าง/ส่ง/แก้หลังส่ง ของงานลด-เพิ่ม, EOT, ขอตรวจงาน, Punch List

import json
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from consbiz import project_docs
from consbiz.test_site_app import make_plan
from consbiz.test_store_app import setup_store


class IntegrationTestProjectDocs(IntegrationTestCase):
	def setUp(self):
		self.project = setup_store()
		for name in frappe.get_all("Construction Management", {"project": self.project}, pluck="name"):
			frappe.db.set_value("Construction Management", name, "project", None)
		self.plan = make_plan(self.project)

	def save(self, kind, data, submit=0):
		return project_docs.save_doc(kind, json.dumps(data), project=self.project, submit=submit)

	def update(self, kind, name, data):
		return project_docs.update_submitted(kind, name, json.dumps(data))

	def test_unknown_kind(self):
		self.assertRaises(frappe.PermissionError, project_docs.get_view, "user", "Administrator")

	def test_form_defaults(self):
		form = project_docs.get_form("inspection", project=self.project)
		self.assertEqual(form["doc"]["construction_management"], self.plan)
		self.assertIn("1.1", [option["value"] for option in form["setup"]["wbs"]])
		self.assertIn("1.1", [t["wbs"] for t in project_docs.get_form("vo", project=self.project)["setup"]["tasks"]])

	def test_punch_list_close_item(self):
		saved = self.save(
			"punch",
			{"title": "ส่งมอบ", "date": "2026-11-05", "items": [{"description": "สีลอก", "wbs": "1.1"}]},
			submit=1,
		)
		doc = frappe.get_doc("Punch List", saved["name"])
		self.assertEqual((doc.docstatus, doc.status, doc.open_items), (1, "Open", 1))

		view = self.update("punch", doc.name, {"items": [{"name": doc.items[0].name, "status": "Closed"}]})
		self.assertEqual(view["doc"]["status"], "Closed")
		self.assertEqual(view["doc"]["status_label"], "ปิดแล้ว")
		self.assertTrue(view["doc"]["items"][0]["closed_on"])

	def test_inspection_reinspect(self):
		saved = self.save(
			"inspection", {"title": "ตรวจเหล็ก", "wbs": "1.1", "request_date": "2026-11-05"}, submit=1
		)
		view = self.update("inspection", saved["name"], {"result": "Failed", "comments": "ระยะไม่ได้"})
		self.assertEqual(view["doc"]["status_label"], "ไม่ผ่าน")
		self.assertTrue(view["can_reinspect"])
		self.assertIsNone(view["reinspection"])

		source = project_docs.get_form("inspection", project=self.project, source=saved["name"])["doc"]
		self.assertEqual(source["reinspection_of"], saved["name"])
		again = self.save(
			"inspection",
			{
				"title": source["title"],
				"wbs": "1.1",
				"request_date": "2026-11-06",
				"reinspection_of": saved["name"],
			},
		)
		self.assertEqual(project_docs.get_view("inspection", saved["name"])["reinspection"], again["name"])

	def test_variation_order(self):
		saved = self.save(
			"vo",
			{
				"title": "งานเพิ่มผนัง",
				"date": "2026-11-05",
				"items": [
					{"variation_type": "Addition", "item_name": "ผนังเพิ่ม", "qty": 2, "rate": 100},
					{"variation_type": "Omission", "wbs": "1.1", "qty": 1},
				],
			},
		)
		view = project_docs.get_view("vo", saved["name"])
		self.assertTrue(view["can_edit"] and view["can_submit"])
		# ยอดคำนวณใน validate: งานลด = 1 x ราคาในแผน 300
		self.assertEqual(view["doc"]["net_amount"], 200 - 300)

		project_docs.submit_doc("vo", saved["name"])
		plan = frappe.get_doc("Construction Management", self.plan)
		self.assertIn("VO.1", [row.wbs for row in plan.tasks])

		view = self.update("vo", saved["name"], {"employer_status": "Approved"})
		self.assertEqual(view["doc"]["status_label"], "อนุมัติแล้ว")
		self.assertTrue(view["doc"]["employer_approved_on"])

		# ผู้ไม่เห็นงบต้นทุน: ดูได้โดยไม่มีมูลค่า แก้ไม่ได้
		with patch("consbiz.project_docs.can_view_finance", return_value=False):
			hidden = project_docs.get_view("vo", saved["name"])
			self.assertNotIn("net_amount", hidden["doc"])
			self.assertNotIn("rate", hidden["doc"]["items"][0])
			self.assertFalse(hidden["can_update"])
			self.assertRaises(frappe.PermissionError, project_docs.get_form, "vo", project=self.project)
			self.assertRaises(frappe.PermissionError, self.update, "vo", saved["name"], {"remarks": "x"})

	def test_extension_of_time(self):
		frappe.db.set_value("Construction Management", self.plan, "finish_date", "2026-12-31")
		saved = self.save(
			"eot",
			{
				"title": "ฝนตก",
				"cause": "Other",
				"date": "2026-11-05",
				"event_start": "2026-11-01",
				"requested_days": 5,
				# ช่องที่ฟอร์มไม่ได้เปิด: ต้องไม่ถูกบันทึกจากข้อมูลที่ส่งมา
				"approved_days": 99,
				"employer_status": "Approved",
			},
		)
		doc = frappe.get_doc("Extension of Time", saved["name"])
		self.assertEqual((doc.employer_status, doc.approved_days), ("Pending", 0))

		project_docs.submit_doc("eot", doc.name)
		view = self.update("eot", doc.name, {"employer_status": "Approved", "approved_days": 3})
		self.assertEqual(str(view["doc"]["revised_finish_date"]), "2027-01-03")

	def test_attach_only_own_unattached_files(self):
		doc = frappe.get_doc("Punch List", self.save("punch", self.punch_data())["name"])
		mine = self.file("mine.txt")
		other = self.file("other.txt")
		frappe.db.set_value("File", other, "owner", "guest@example.com")

		project_docs.attach_new_files([mine, other], doc)
		self.assertEqual(frappe.db.get_value("File", mine, "attached_to_name"), doc.name)
		self.assertIsNone(frappe.db.get_value("File", other, "attached_to_name"))

	def punch_data(self):
		return {"title": "ไฟล์", "date": "2026-11-05", "items": [{"description": "แถว"}]}

	def file(self, name):
		return (
			frappe.get_doc({"doctype": "File", "file_name": name, "content": name, "is_private": 1}).insert().name
		)
