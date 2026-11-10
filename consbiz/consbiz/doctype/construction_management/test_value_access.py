# Copyright (c) 2026, Siricons and Contributors
# See license.txt

# ผู้ไม่มีสิทธิ์เห็นมูลค่า (permlevel 1 ของ CM) ต้องไม่ได้รับจำนวนเงินจาก API ของแผนงาน

import frappe
from frappe.tests import IntegrationTestCase

from consbiz.consbiz.doctype.construction_management.construction_management import (
	create_from_boq,
	get_schedule_data,
)
from consbiz.consbiz.doctype.construction_management.dashboard import get_dashboard
from consbiz.tests.utils import insert_boq

EXTRA_TEST_RECORD_DEPENDENCIES = []
IGNORE_TEST_RECORD_DEPENDENCIES = ["BOQ", "Customer", "Company", "Holiday List", "UOM", "Project"]
USER = "test-projects-user@example.com"


class IntegrationTestValueAccess(IntegrationTestCase):
	def setUp(self):
		boq = frappe.new_doc("BOQ")
		boq.naming_series = frappe.get_meta("BOQ").get_field("naming_series").options.split("\n")[0]
		boq.date = "2026-11-02"
		for row in (
			{"wbs": "1", "item_name": "หมวด", "quantity": 0},
			{"wbs": "1.1", "item_name": "งาน ก", "quantity": 10, "total_amount": 3000},
			{"wbs": "1.2", "item_name": "งาน ข", "quantity": 10, "total_amount": 1000},
		):
			boq.append("boq_details", row)
		insert_boq(boq)
		self.name = create_from_boq(boq.name)
		if not frappe.db.exists("User", USER):
			frappe.get_doc(
				{"doctype": "User", "email": USER, "first_name": "Projects", "send_welcome_email": 0}
			).insert(ignore_permissions=True)
		frappe.get_doc("User", USER).add_roles("Projects User")
		self.addCleanup(frappe.set_user, "Administrator")

	def test_manager_sees_money(self):
		data = get_schedule_data(self.name)
		self.assertTrue(data["can_view_value"])
		self.assertEqual(data["total_amount"], 4000)
		self.assertEqual(data["tasks"][1]["amount"], 3000)
		self.assertEqual(get_dashboard(self.name)["contract"]["revised_amount"], 4000)

	def test_projects_user_gets_share_of_contract_only(self):
		frappe.set_user(USER)
		data = get_schedule_data(self.name)
		self.assertFalse(data["can_view_value"])
		self.assertAlmostEqual(data["total_amount"], 100)
		self.assertAlmostEqual(data["tasks"][1]["amount"], 75)
		self.assertAlmostEqual(data["tasks"][1]["weight"], 75)

	def test_projects_user_dashboard_has_no_money(self):
		frappe.set_user(USER)
		data = get_dashboard(self.name)
		self.assertFalse(data["show_values"])
		self.assertIsNone(data["contract"]["revised_amount"])
		self.assertIsNone(data["schedule"]["penalty"])

	def test_projects_user_can_read_doc_without_money_fields(self):
		frappe.set_user(USER)
		doc = frappe.get_doc("Construction Management", self.name)
		doc.apply_fieldlevel_read_permissions()
		self.assertFalse(doc.get("total_amount"))
		self.assertFalse(doc.tasks[1].get("amount"))

	def test_projects_user_save_keeps_money(self):
		from consbiz.consbiz.doctype.construction_management.construction_management import save_tasks

		frappe.set_user(USER)
		doc = frappe.get_doc("Construction Management", self.name)
		save_tasks(
			self.name,
			frappe.as_json(
				[{"name": doc.tasks[1].name, "start_date": "2026-11-03", "end_date": "2026-11-05"}]
			),
			str(doc.modified),
		)
		frappe.set_user("Administrator")
		doc.reload()
		self.assertEqual(doc.tasks[1].amount, 3000)
		self.assertEqual(doc.total_amount, 4000)
