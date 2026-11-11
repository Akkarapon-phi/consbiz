# Copyright (c) 2026, Siricons and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from consbiz import store_app
from consbiz.consbiz.doctype.concrete_usage.concrete_usage import CONCRETE_GROUP
from consbiz.consbiz.doctype.construction_management.construction_management import create_from_boq
from consbiz.employer_supplied import employer_item
from consbiz.tests.test_employer_supplied import make_item
from consbiz.tests.utils import insert_boq

IGNORE_TEST_RECORD_DEPENDENCIES = [
	"Construction Management",
	"Item",
	"Item Group",
	"UOM",
	"BOQ",
	"Customer",
	"Company",
	"Holiday List",
	"Project",
	"Supplier",
]


class IntegrationTestConcreteUsage(IntegrationTestCase):
	def setUp(self):
		boq = frappe.new_doc("BOQ")
		boq.naming_series = frappe.get_meta("BOQ").get_field("naming_series").options.split("\n")[0]
		boq.date = "2026-11-02"
		for row in (
			{"wbs": "1", "item_name": "หมวด", "quantity": 0},
			{"wbs": "1.1", "item_name": "เทคอนกรีตฐานราก", "quantity": 10, "total_amount": 3000},
		):
			boq.append("boq_details", row)
		insert_boq(boq)
		self.plan = create_from_boq(boq.name)
		if not frappe.db.exists("Item Group", CONCRETE_GROUP):
			frappe.get_doc({"doctype": "Item Group", "item_group_name": CONCRETE_GROUP, "is_group": 0}).insert()
		self.concrete = make_item("_Test Concrete 240", item_group=CONCRETE_GROUP)

	def make_usage(self, tickets, **values):
		doc = frappe.new_doc("Concrete Usage")
		doc.update(
			{
				"construction_management": self.plan,
				"wbs": "1.1",
				"date": "2026-11-04",
				"concrete_item": self.concrete.name,
				**values,
			}
		)
		for ticket in tickets:
			doc.append("tickets", ticket)
		doc.flags.ignore_links = True
		return doc.insert()

	def test_totals_by_supply(self):
		doc = self.make_usage(
			[
				{"ticket_no": "T1", "qty": 6},
				{"ticket_no": "T2", "qty": 5.5, "employer_supplied": 1},
				{"ticket_no": "T3", "qty": 2, "remarks": "เศษ 0.5 คิว ไปเททางเดิน"},
			],
			planned_qty=12,
		)
		self.assertEqual(doc.task_name, "เทคอนกรีตฐานราก")
		self.assertEqual(
			(doc.total_qty, doc.employer_qty, doc.company_qty, doc.ticket_count), (13.5, 5.5, 8, 3)
		)
		self.assertEqual(doc.variance, 1.5)

	def test_keeps_base_item(self):
		doc = self.make_usage(
			[{"ticket_no": "T1", "qty": 1}], concrete_item=employer_item(self.concrete.name)
		)
		self.assertEqual(doc.concrete_item, self.concrete.name)

	def test_validation(self):
		with self.assertRaises(frappe.ValidationError):
			self.make_usage([{"ticket_no": "T1", "qty": 1}], wbs="1")
		with self.assertRaises(frappe.ValidationError):
			self.make_usage([{"ticket_no": "T1", "qty": 1}, {"ticket_no": "T1", "qty": 2}])
		with self.assertRaises(frappe.ValidationError):
			self.make_usage([{"ticket_no": "T1", "qty": 0}])

	def test_concrete_item_must_be_in_concrete_group(self):
		other = make_item("_Test Concrete Cutting Blade")
		with self.assertRaises(frappe.ValidationError):
			self.make_usage([{"ticket_no": "T1", "qty": 1}], concrete_item=other.name)

	def test_old_item_outside_group_still_saves(self):
		# ใบที่เลือก Item ไว้ก่อนย้ายเข้ากลุ่ม แก้ช่องอื่นได้ เปลี่ยน Item ใหม่ต้องเป็นคอนกรีต
		doc = self.make_usage([{"ticket_no": "T1", "qty": 1}])
		other = make_item("_Test Old Concrete")
		frappe.db.set_value("Concrete Usage", doc.name, "concrete_item", other.name)
		doc.reload()
		doc.location = "F2"
		doc.save()
		doc.concrete_item = make_item("_Test Pipe").name
		with self.assertRaises(frappe.ValidationError):
			doc.save()

	def test_search_lists_concrete_used_in_project_first(self):
		project = "_Test Concrete Project"
		other = make_item("_Test Concrete 180", item_group=CONCRETE_GROUP)
		blade = make_item("_Test Concrete Blade")
		doc = self.make_usage([{"ticket_no": "T1", "qty": 1}], concrete_item=other.name)
		frappe.db.set_value("Concrete Usage", doc.name, "project", project)
		with patch.object(store_app, "check_project"):
			rows = store_app.search_concrete(project, "_Test Concrete")
			setup_items = [r for r in store_app.search_concrete(project) if r["used"]][:1]
		codes = [r["value"] for r in rows]
		self.assertEqual(codes[0], other.name)
		self.assertIn(self.concrete.name, codes)
		self.assertNotIn(blade.name, codes)
		self.assertTrue(rows[0]["used"])
		self.assertEqual([r["value"] for r in setup_items], [other.name])
