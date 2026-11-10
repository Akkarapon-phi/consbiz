# Copyright (c) 2026, Siricons and Contributors
# See license.txt

# แก้โครงสร้างงานของแผน (structure.py)

import frappe
from frappe.tests import IntegrationTestCase

from consbiz.consbiz.doctype.construction_management.construction_management import (
	create_from_boq,
	get_schedule_data,
	save_baseline,
	save_tasks,
)
from consbiz.consbiz.doctype.construction_management.structure import change_structure, unconfirm_plan
from consbiz.consbiz.doctype.daily_report.daily_report import get_tasks
from consbiz.tests.utils import insert_boq

EXTRA_TEST_RECORD_DEPENDENCIES = []
IGNORE_TEST_RECORD_DEPENDENCIES = ["BOQ", "Customer", "Company", "Holiday List", "UOM", "Project"]


class IntegrationTestPlanStructure(IntegrationTestCase):
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
		insert_boq(boq)
		self.doc = frappe.get_doc("Construction Management", create_from_boq(boq.name))

	def task(self, wbs):
		return next(row for row in self.doc.tasks if row.wbs == wbs)

	def change(self, action, wbs=(), item_name=None):
		self.doc.reload()
		names = [self.task(w).name for w in wbs]
		change_structure(self.doc.name, str(self.doc.modified), action, frappe.as_json(names), item_name)
		self.doc.reload()

	def outline(self):
		return [(row.wbs, row.item_name) for row in self.doc.tasks]

	def test_add_task_has_no_value_and_renumbers_while_planning(self):
		self.change("add", ["1.1"], "งานใหม่")
		self.assertEqual(
			self.outline()[:4],
			[("1", "หมวด 1"), ("1.1", "งาน ก"), ("1.2", "งานใหม่"), ("1.3", "งาน ข")],
		)
		new = self.task("1.2")
		self.assertFalse(new.boq_detail)
		self.assertEqual((new.amount, new.weight), (0, 0))
		self.assertEqual(self.doc.total_amount, 4500)

	def test_add_task_without_selection_goes_last(self):
		self.change("add", [], "งานท้าย")
		self.assertEqual(self.outline()[-1], ("3", "งานท้าย"))

	def test_add_child_under_group(self):
		self.change("add_child", ["2"], "งานย่อย")
		self.assertEqual(self.outline()[-2:], [("2.1", "งาน ค"), ("2.2", "งานย่อย")])

	def test_valued_task_cannot_become_a_group(self):
		with self.assertRaises(frappe.ValidationError):
			self.change("add_child", ["1.1"], "งานย่อย")
		with self.assertRaises(frappe.ValidationError):
			self.change("indent", ["1.2"])

	def test_new_task_can_group_boq_tasks(self):
		self.change("add", ["1.1"], "หัวกลุ่ม")
		self.change("indent", ["1.3"])
		group = self.task("1.2")
		self.assertTrue(group.is_group)
		self.assertEqual(group.amount, 1000)
		self.assertEqual(self.task("1.2.1").item_name, "งาน ข")
		self.assertEqual(self.doc.total_amount, 4500)

	def test_outdent_keeps_order_of_selected_tasks(self):
		self.change("add", ["1.2"], "ก")
		self.change("add", ["1.3"], "ข")
		self.change("add_child", ["2"], "ค")
		self.change("outdent", ["1.3", "1.4"])
		self.assertEqual(
			self.outline(),
			[
				("1", "หมวด 1"),
				("1.1", "งาน ก"),
				("1.2", "งาน ข"),
				("2", "ก"),
				("3", "ข"),
				("4", "หมวด 2"),
				("4.1", "งาน ค"),
				("4.2", "ค"),
			],
		)

	def test_boq_group_must_keep_a_child(self):
		with self.assertRaises(frappe.ValidationError):
			self.change("outdent", ["2.1"])

	def test_delete_only_new_tasks(self):
		with self.assertRaises(frappe.ValidationError):
			self.change("delete", ["1.1"])
		self.change("add", ["1.2"], "ลบได้")
		self.change("delete", ["1.3"])
		self.assertEqual(len(self.doc.tasks), 5)

	def test_group_cannot_be_deleted_without_its_children(self):
		self.change("add", ["2.1"], "หัว")
		self.change("add_child", ["2.2"], "ลูก")
		with self.assertRaises(frappe.ValidationError):
			self.change("delete", ["2.2"])
		self.change("delete", ["2.2", "2.2.1"])
		self.assertEqual(len(self.doc.tasks), 5)

	def confirm(self):
		self.doc.reload()
		frappe.db.set_value("BOQ", self.doc.boq, "docstatus", 1)
		save_baseline(self.doc.name, str(self.doc.modified), "ฉบับแรก")
		self.doc.reload()

	def add_progress(self):
		self.doc.reload()
		frappe.get_doc(
			{
				"doctype": "Construction Progress Entry",
				"construction_management": self.doc.name,
				"task": self.task("1.1").name,
				"date": "2026-11-03",
				"qty": 1,
				"source": "Manual",
			}
		).insert()

	def unconfirm(self):
		self.doc.reload()
		unconfirm_plan(self.doc.name, str(self.doc.modified))
		self.doc.reload()

	def test_baseline_closes_every_structure_action(self):
		self.change("add", ["2.1"], "งานเพิ่มเอง")
		self.confirm()
		for action, wbs, item_name in (
			("add", ["1.1"], "งานใหม่"),
			("add_child", ["2"], "งานย่อย"),
			("indent", ["2.2"], None),
			("outdent", ["2.2"], None),
			("delete", ["2.2"], None),
		):
			with self.assertRaises(frappe.ValidationError):
				self.change(action, wbs, item_name)
		self.assertEqual(len(self.doc.tasks), 6)

	def test_unconfirm_clears_baselines_and_reopens_structure(self):
		self.confirm()
		self.assertTrue(get_schedule_data(self.doc.name)["can_unconfirm"])
		self.unconfirm()
		self.assertFalse(self.doc.active_baseline)
		self.assertFalse(self.doc.baseline_date)
		self.assertFalse(self.task("1.1").baseline_start_date)
		self.assertFalse(frappe.db.exists("Construction Baseline", {"construction_management": self.doc.name}))
		self.assertFalse(get_schedule_data(self.doc.name)["can_unconfirm"])
		self.change("add", ["1.1"], "งานแทรก")
		self.assertEqual(self.task("1.2").item_name, "งานแทรก")

	def test_cannot_unconfirm_plan_in_use(self):
		self.confirm()
		self.add_progress()
		self.assertFalse(get_schedule_data(self.doc.name)["can_unconfirm"])
		with self.assertRaises(frappe.ValidationError):
			self.unconfirm()
		self.assertTrue(frappe.db.exists("Construction Baseline", {"construction_management": self.doc.name}))

	def test_cannot_unconfirm_plan_without_baseline(self):
		with self.assertRaises(frappe.ValidationError):
			self.unconfirm()

	def test_reference_from_document_keeps_numbers_before_baseline(self):
		self.add_progress()
		with self.assertRaises(frappe.ValidationError):
			self.change("indent", ["1.1"])
		self.change("add", ["1.1"], "งานแทรก")
		self.assertEqual(self.task("1.3").item_name, "งานแทรก")

	def planning_task(self):
		self.change("add", ["2.1"], "งานวางแผน")
		return self.task("2.2")

	def test_planning_task_is_not_offered_for_reports(self):
		self.planning_task()
		wbs = [task["wbs"] for task in get_tasks(self.doc.name)]
		self.assertIn("2.1", wbs)
		self.assertNotIn("2.2", wbs)

	def test_reports_reject_planning_task(self):
		self.planning_task()
		for doctype in ("Daily Report", "Daily Request"):
			report = frappe.new_doc(doctype)
			report.construction_management = self.doc.name
			report.date = "2026-11-03"
			report.approver = "Administrator"
			report.append("items", {"wbs": "2.2", "percent": 10})
			with self.assertRaisesRegex(frappe.ValidationError, "งานวางแผน"):
				report.validate()

	def test_planner_updates_planning_task_without_moving_project(self):
		task = self.planning_task()
		before = self.doc.actual_progress
		save_tasks(
			self.doc.name,
			"[]",
			str(self.doc.modified),
			progress=frappe.as_json([{"task": task.name, "date": "2026-11-03", "qty": 0, "percent": 50}]),
		)
		self.doc.reload()
		self.assertEqual(self.task("2.2").progress, 50)
		self.assertEqual(self.doc.actual_progress, before)

	def test_boq_number_stays_when_plan_is_renumbered(self):
		self.change("add", ["1.1"], "งานใหม่")
		rows = {task["item_name"]: task for task in get_schedule_data(self.doc.name)["tasks"]}
		self.assertEqual((rows["งาน ข"]["wbs"], rows["งาน ข"]["boq_wbs"]), ("1.3", "1.2"))
		self.assertIsNone(rows["งานใหม่"]["boq_wbs"])

	def test_stale_plan_is_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			change_structure(self.doc.name, "2000-01-01 00:00:00", "add", "[]", "งาน")
