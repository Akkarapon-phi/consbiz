# Copyright (c) 2026, Siricons and Contributors
# See license.txt

# อัปเดตแผนงานจาก BOQ ฉบับร่าง (boq_sync.py) และกติกาที่ผูกกับ BOQ

import frappe
from frappe.tests import IntegrationTestCase

from consbiz.consbiz.doctype.construction_management.boq_sync import apply_boq_sync, preview_boq_sync
from consbiz.consbiz.doctype.construction_management.construction_management import (
	create_from_boq,
	save_baseline,
)
from consbiz.consbiz.doctype.construction_management.structure import change_structure
from consbiz.tests.utils import insert_boq

EXTRA_TEST_RECORD_DEPENDENCIES = []
IGNORE_TEST_RECORD_DEPENDENCIES = ["BOQ", "Customer", "Company", "Holiday List", "UOM", "Project"]


class IntegrationTestBoqSync(IntegrationTestCase):
	def setUp(self):
		boq = frappe.new_doc("BOQ")
		boq.naming_series = frappe.get_meta("BOQ").get_field("naming_series").options.split("\n")[0]
		boq.date = "2026-11-02"
		for row in (
			{"wbs": "1", "item_name": "หมวด 1", "quantity": 0},
			{"wbs": "1.1", "item_name": "งาน ก", "quantity": 10, "total_amount": 3000},
			{"wbs": "1.2", "item_name": "งาน ข", "quantity": 10, "total_amount": 1000},
			{"wbs": "2", "item_name": "หมวด 2", "quantity": 0},
			{"wbs": "2.1", "item_name": "งาน ค", "quantity": 10, "total_amount": 500},
		):
			boq.append("boq_details", row)
		self.boq = insert_boq(boq)
		self.doc = frappe.get_doc("Construction Management", create_from_boq(boq.name))
		self.set_dates("งาน ข", "2026-12-01", "2026-12-05")

	def task(self, item_name):
		return next(row for row in self.doc.tasks if row.item_name == item_name)

	def boq_row(self, item_name):
		return next(row for row in self.boq.boq_details if row.item_name == item_name)

	def set_dates(self, item_name, start, end):
		self.doc.reload()
		row = self.task(item_name)
		row.start_date, row.end_date = start, end
		self.doc.save()

	def edit_boq(self, change):
		self.boq.reload()
		change()
		for idx, row in enumerate(self.boq.boq_details, 1):
			row.idx = idx
		self.boq.save()

	def add_boq_row(self, position, wbs, item_name):
		row = self.boq.append("boq_details", {"wbs": wbs, "item_name": item_name, "quantity": 2, "material_rate": 100})
		self.boq.boq_details.remove(row)
		self.boq.boq_details.insert(position, row)

	def preview(self):
		return preview_boq_sync(self.boq.name)

	def apply(self):
		apply_boq_sync(self.boq.name, self.preview()["modified"])
		self.doc.reload()

	def outline(self):
		return [(row.wbs, row.item_name) for row in self.doc.tasks]

	def change_plan(self, action, item_name_rows, item_name=None):
		self.doc.reload()
		names = [self.task(name).name for name in item_name_rows]
		change_structure(self.doc.name, str(self.doc.modified), action, frappe.as_json(names), item_name)
		self.doc.reload()

	def add_progress(self, item_name):
		self.doc.reload()
		frappe.get_doc(
			{
				"doctype": "Construction Progress Entry",
				"construction_management": self.doc.name,
				"task": self.task(item_name).name,
				"date": "2026-11-03",
				"qty": 1,
				"source": "Manual",
			}
		).insert()

	def test_new_plan_is_in_sync(self):
		preview = self.preview()
		self.assertTrue(preview["in_sync"])
		self.assertFalse(preview["can_apply"])

	def test_edit_updates_values_and_keeps_dates(self):
		self.edit_boq(lambda: setattr(self.boq_row("งาน ข"), "quantity", 20))
		preview = self.preview()
		self.assertEqual([row["item_name"] for row in preview["changed"]], ["งาน ข"])
		self.apply()
		row = self.task("งาน ข")
		self.assertEqual((row.quantity, row.amount), (20, 2000))
		self.assertEqual((str(row.start_date), str(row.end_date)), ("2026-12-01", "2026-12-05"))
		self.assertEqual(self.doc.total_amount, 5500)
		self.assertTrue(self.preview()["in_sync"])

	def test_added_row_follows_boq_order(self):
		self.edit_boq(lambda: self.add_boq_row(3, "1.3", "งานใหม่"))
		self.assertEqual([row["item_name"] for row in self.preview()["added"]], ["งานใหม่"])
		self.apply()
		self.assertEqual(self.outline()[3], ("1.3", "งานใหม่"))
		self.assertEqual(self.task("งานใหม่").start_date, self.doc.start_date)
		self.assertEqual(str(self.task("งาน ข").start_date), "2026-12-01")

	def test_removed_row_is_deleted_and_links_are_cleared(self):
		self.doc.reload()
		self.task("งาน ค").predecessors = frappe.as_json([{"task": self.task("งาน ข").name, "type": "FS", "lag": 0}])
		self.doc.save()
		self.edit_boq(lambda: self.boq.remove(self.boq_row("งาน ข")))
		self.assertEqual([row["item_name"] for row in self.preview()["removed"]], ["งาน ข"])
		self.apply()
		self.assertNotIn("งาน ข", [row.item_name for row in self.doc.tasks])
		self.assertFalse(self.task("งาน ค").predecessors)

	def test_replaced_rows_match_by_name_and_unit(self):
		def replace():
			rows = [
				{"wbs": r.wbs, "item_name": r.item_name, "quantity": r.quantity, "material_rate": r.material_rate}
				for r in self.boq.boq_details
			]
			self.boq.set("boq_details", [])
			for row in rows:
				self.boq.append("boq_details", row)

		old = self.doc.tasks[2].boq_detail
		self.edit_boq(replace)
		self.apply()
		row = self.task("งาน ข")
		self.assertNotEqual(row.boq_detail, old)
		self.assertEqual(row.boq_detail, self.boq_row("งาน ข").name)
		self.assertEqual(str(row.start_date), "2026-12-01")

	def test_row_added_in_plan_stays_after_its_boq_row(self):
		self.change_plan("add", ["งาน ก"], "งานวางแผน")
		self.edit_boq(lambda: self.add_boq_row(0, "1", "หมวดใหม่"))
		self.apply()
		self.assertEqual(
			[name for _wbs, name in self.outline()],
			["หมวดใหม่", "หมวด 1", "งาน ก", "งานวางแผน", "งาน ข", "หมวด 2", "งาน ค"],
		)
		self.assertEqual(self.task("งานวางแผน").wbs, "2.2")

	def test_header_added_in_plan_keeps_its_boq_child(self):
		self.change_plan("add", ["งาน ก"], "หัวข้อโซน")
		self.change_plan("indent", ["งาน ข"])
		self.edit_boq(lambda: setattr(self.boq_row("งาน ข"), "quantity", 20))
		self.apply()
		self.assertEqual(self.task("หัวข้อโซน").wbs, "1.2")
		self.assertEqual(self.task("งาน ข").wbs, "1.2.1")
		self.assertEqual(self.task("งาน ข").quantity, 20)
		self.assertTrue(self.preview()["in_sync"])

	def test_used_row_cannot_be_removed(self):
		self.add_progress("งาน ข")
		self.edit_boq(lambda: self.boq.remove(self.boq_row("งาน ข")))
		preview = self.preview()
		self.assertTrue(preview["blockers"])
		self.assertFalse(preview["can_apply"])
		with self.assertRaises(frappe.ValidationError):
			apply_boq_sync(self.boq.name, preview["modified"])

	def test_used_row_cannot_change_number(self):
		self.add_progress("งาน ค")
		self.edit_boq(lambda: self.add_boq_row(0, "1", "หมวดใหม่"))
		self.assertTrue(self.preview()["blockers"])

	def test_lump_sum_keeps_amount_from_plan(self):
		boq = frappe.new_doc("BOQ")
		boq.naming_series = self.boq.naming_series
		boq.date = "2026-11-02"
		boq.append("boq_details", {"wbs": "1", "item_name": "งานเหมา", "quantity": 0, "total_amount": 1000})
		boq.append("boq_details", {"wbs": "2", "item_name": "งานอื่น", "quantity": 1, "total_amount": 100})
		self.boq = insert_boq(boq)
		self.doc = frappe.get_doc("Construction Management", create_from_boq(boq.name))
		self.edit_boq(lambda: setattr(self.boq_row("งานอื่น"), "quantity", 2))
		self.apply()
		self.assertEqual(self.task("งานเหมา").amount, 1000)
		self.assertEqual(self.task("งานอื่น").amount, 200)

	def test_baseline_needs_submitted_boq(self):
		self.doc.reload()
		with self.assertRaises(frappe.ValidationError):
			save_baseline(self.doc.name, str(self.doc.modified), "ฉบับแรก")

	def test_confirmed_plan_cannot_be_updated(self):
		self.doc.reload()
		frappe.db.set_value("BOQ", self.boq.name, "docstatus", 1)
		save_baseline(self.doc.name, str(self.doc.modified), "ฉบับแรก")
		frappe.db.set_value("BOQ", self.boq.name, "docstatus", 0)
		preview = self.preview()
		self.assertTrue(preview["reason"])
		self.assertFalse(preview["can_apply"])

	def test_submitted_boq_cannot_update_plan(self):
		self.boq.reload()
		self.boq.submit()
		preview = self.preview()
		self.assertTrue(preview["reason"])
		with self.assertRaises(frappe.ValidationError):
			apply_boq_sync(self.boq.name, preview["modified"])

	def test_submit_needs_plan_in_sync(self):
		self.edit_boq(lambda: setattr(self.boq_row("งาน ข"), "quantity", 20))
		self.boq.reload()
		with self.assertRaises(frappe.ValidationError):
			self.boq.submit()
		self.apply()
		self.boq.reload()
		self.boq.submit()
		self.assertEqual(self.boq.docstatus, 1)

	def test_boq_with_plan_cannot_be_cancelled(self):
		self.boq.reload()
		self.boq.submit()
		self.boq.reload()
		with self.assertRaises(frappe.ValidationError):
			self.boq.cancel()
