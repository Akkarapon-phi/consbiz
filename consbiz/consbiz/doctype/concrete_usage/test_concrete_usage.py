# Copyright (c) 2026, Siricons and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from consbiz.consbiz.doctype.construction_management.construction_management import create_from_boq
from consbiz.employer_supplied import employer_item
from consbiz.tests.test_employer_supplied import make_item

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
		boq.insert()
		self.plan = create_from_boq(boq.name)
		self.concrete = make_item("_Test Concrete 240")

	def make_usage(self, tickets, **values):
		doc = frappe.new_doc("Concrete Usage")
		doc.update({"construction_management": self.plan, "wbs": "1.1", "date": "2026-11-04", "concrete_item": self.concrete.name, **values})
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
		self.assertEqual((doc.total_qty, doc.employer_qty, doc.company_qty, doc.ticket_count), (13.5, 5.5, 8, 3))
		self.assertEqual(doc.variance, 1.5)

	def test_keeps_base_item(self):
		doc = self.make_usage([{"ticket_no": "T1", "qty": 1}], concrete_item=employer_item(self.concrete.name))
		self.assertEqual(doc.concrete_item, self.concrete.name)

	def test_validation(self):
		with self.assertRaises(frappe.ValidationError):
			self.make_usage([{"ticket_no": "T1", "qty": 1}], wbs="1")
		with self.assertRaises(frappe.ValidationError):
			self.make_usage([{"ticket_no": "T1", "qty": 1}, {"ticket_no": "T1", "qty": 2}])
		with self.assertRaises(frappe.ValidationError):
			self.make_usage([{"ticket_no": "T1", "qty": 0}])
