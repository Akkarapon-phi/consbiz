# Copyright (c) 2026, Siricons and Contributors
# See license.txt

# แผนตัดเหล็กในแอปหน้างาน (bar_cut_app.py): บันทึก = คำนวณ, รายการตามโครงการ, ความยาวตัดก่อนเพิ่ม, เหล็กไม่พอแจ้ง error
# ใช้รูปทรง / ประเภทเหล็กมาตรฐานจาก patch seed (เหมือน test_bar_cut_plan.py)

import frappe
from frappe.tests import IntegrationTestCase

from consbiz import bar_cut_app
from consbiz.test_store_app import setup_store


class IntegrationTestBarCutApp(IntegrationTestCase):
	def setUp(self):
		self.project = setup_store()

	def new_plan(self, **values):
		data = bar_cut_app.get_plan(project=self.project)["doc"]
		data.update(bar_cut_app.get_setup()["defaults"])
		data.update(title="คาน B1", stock=[], **values)
		return data

	def test_save_calculates_and_lists(self):
		data = self.new_plan(items=[{"shape": "11", "rebar_type": "DB12", "a": 1000, "b": 500, "qty": 4}])
		view = bar_cut_app.save_plan(frappe.as_json(data))
		doc = view["doc"]
		self.assertEqual(doc["items"][0]["cut_length"], 1480)
		self.assertTrue(doc["patterns"])
		self.assertIsInstance(doc["patterns"][0]["pieces"], list)
		self.assertTrue(view["pdf_url"])

		row = next(r for r in bar_cut_app.get_plans(self.project) if r.name == doc["name"])
		self.assertEqual(row.pieces, 4)

	def test_preview(self):
		result = bar_cut_app.preview("11", "DB12", frappe.as_json({"a": 1000, "b": 500}))
		self.assertEqual(result["cut_length"], 1480)

	def test_not_enough_stock(self):
		data = self.new_plan(
			items=[{"shape": "00", "rebar_type": "DB12", "a": 2000, "qty": 1}],
			stock=[{"rebar_type": "DB12", "length": 1, "qty": 1}],
		)
		with self.assertRaises(frappe.ValidationError):
			bar_cut_app.save_plan(frappe.as_json(data))
