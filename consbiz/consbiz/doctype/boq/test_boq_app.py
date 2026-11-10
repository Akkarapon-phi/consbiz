# Copyright (c) 2026, Siricons and Contributors
# See license.txt

# API หมวด BOQ ของแอปออฟฟิศ (consbiz/boq_app.py)

import frappe
from frappe.tests import IntegrationTestCase

from consbiz import boq_app

EXTRA_TEST_RECORD_DEPENDENCIES = []
IGNORE_TEST_RECORD_DEPENDENCIES = ["Customer", "Company", "Holiday List", "UOM", "Project"]
ROWS = [
	{"wbs": "1", "item_name": "หมวด"},
	{"wbs": "1.1", "item_name": "งาน ก", "quantity": 10, "material_rate": 100, "labour_rate": 20},
	{"wbs": "1.2", "item_name": "งาน ข", "quantity": 2, "material_rate": 50},
]


class IntegrationTestBoqApp(IntegrationTestCase):
	def create(self, rows=None):
		return boq_app.save_boq(frappe.as_json({"date": "2026-11-02", "rows": rows or ROWS}))

	def test_save_calculates_totals(self):
		boq = self.create()
		self.assertEqual(boq["grand_total"], 1300)
		self.assertEqual(boq["rows"][1]["total_amount"], 1200)
		self.assertEqual(boq["docstatus"], 0)

	def test_save_replaces_rows(self):
		boq = self.create()
		boq["rows"] = boq["rows"][:2]
		saved = boq_app.save_boq(frappe.as_json(boq))
		self.assertEqual(len(saved["rows"]), 2)
		self.assertEqual(saved["grand_total"], 1200)

	def test_stale_save_is_rejected(self):
		boq = self.create()
		boq["modified"] = "2000-01-01 00:00:00"
		with self.assertRaises(frappe.ValidationError):
			boq_app.save_boq(frappe.as_json(boq))

	def test_save_keeps_row_names(self):
		boq = self.create()
		names = [row["name"] for row in boq["rows"]]
		boq["rows"][1]["quantity"] = 20
		boq["rows"].append({"wbs": "1.3", "item_name": "งาน ค", "quantity": 1, "material_rate": 5})
		saved = boq_app.save_boq(frappe.as_json(boq))
		self.assertEqual([row["name"] for row in saved["rows"]][:3], names)
		self.assertEqual(saved["rows"][1]["total_amount"], 2400)
		self.assertNotIn(saved["rows"][3]["name"], names)

	def test_save_ignores_row_name_of_another_boq(self):
		other = self.create()
		boq = self.create()
		boq["rows"][1]["name"] = other["rows"][1]["name"]
		saved = boq_app.save_boq(frappe.as_json(boq))
		self.assertNotEqual(saved["rows"][1]["name"], other["rows"][1]["name"])
		self.assertEqual(frappe.db.get_value("BOQ Item Detail", other["rows"][1]["name"], "parent"), other["name"])

	def test_plan_can_start_from_draft_boq(self):
		boq = self.create()
		plan = boq_app.create_plan(boq["name"])
		self.assertEqual(frappe.db.get_value("Construction Management", plan, "boq"), boq["name"])
		with self.assertRaises(frappe.ValidationError):
			boq_app.create_plan(boq["name"])

	def test_plan_from_free_text_project_has_no_project_yet(self):
		"""BOQ เสนอราคาพิมพ์ชื่อโครงการเองได้ ยังไม่มี Project จริงก็สร้างแผนได้"""
		boq = boq_app.save_boq(frappe.as_json({"date": "2026-11-02", "project": "อาคารที่ยังไม่เปิดโครงการ", "rows": ROWS}))
		self.assertEqual(boq["project"], "อาคารที่ยังไม่เปิดโครงการ")
		plan = boq_app.create_plan(boq["name"])
		self.assertFalse(frappe.db.get_value("Construction Management", plan, "project"))

	def test_item_search_returns_description(self):
		meta = frappe.get_meta("BOQ Item")
		item = frappe.get_doc(
			{
				"doctype": "BOQ Item",
				"naming_series": meta.get_field("naming_series").options.split("\n")[0],
				"item_name": "ทดสอบค้นหา BOQ",
				"description": "<p>คำอธิบายรายการ</p>",
			}
		).insert()
		found = next(row for row in boq_app.search("BOQ Item", "ทดสอบค้นหา BOQ") if row["value"] == item.name)
		self.assertEqual(found["description"], "<p>คำอธิบายรายการ</p>")

	def test_cancelled_boq_cannot_start_a_plan(self):
		boq = self.create()
		boq_app.submit_boq(boq["name"])
		boq_app.cancel_boq(boq["name"])
		with self.assertRaises(frappe.ValidationError):
			boq_app.create_plan(boq["name"])

	def test_cannot_cancel_boq_with_plan(self):
		boq = self.create()
		boq_app.submit_boq(boq["name"])
		boq_app.create_plan(boq["name"])
		with self.assertRaises(frappe.ValidationError):
			boq_app.cancel_boq(boq["name"])

	def test_cancel_and_amend(self):
		boq = self.create()
		boq_app.submit_boq(boq["name"])
		cancelled = boq_app.cancel_boq(boq["name"])
		self.assertEqual(cancelled["docstatus"], 2)
		amended = boq_app.amend_boq(boq["name"])
		self.assertEqual(amended["docstatus"], 0)
		self.assertEqual(amended["amended_from"], boq["name"])
		self.assertEqual(len(amended["rows"]), 3)

	def test_delete_only_draft(self):
		boq = self.create()
		boq_app.submit_boq(boq["name"])
		with self.assertRaises(frappe.ValidationError):
			boq_app.delete_boq(boq["name"])

	def test_user_without_role_is_denied(self):
		boq = self.create()
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user("Guest")
		with self.assertRaises(frappe.PermissionError):
			boq_app.get_boq(boq["name"])
		with self.assertRaises(frappe.PermissionError):
			boq_app.get_boqs()
