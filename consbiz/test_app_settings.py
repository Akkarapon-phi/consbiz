# Copyright (c) 2026, Siricons and Contributors
# See license.txt

# หน้าตั้งค่า: สิทธิ์ของ Role ต่อหมวดในแอป (app_settings.py)

from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from consbiz import app_settings

ROLE = "_Test Settings Role"


class IntegrationTestAppSettings(IntegrationTestCase):
	def setUp(self):
		if not frappe.db.exists("Role", ROLE):
			frappe.get_doc({"doctype": "Role", "role_name": ROLE}).insert(ignore_permissions=True)

	def set(self, doctype, ptype, value, permlevel=0):
		return app_settings.set_role_permission(ROLE, doctype, permlevel, ptype, value)

	def test_setup_lists_modules_and_drops_submit_columns(self):
		setup = app_settings.get_permission_setup()
		self.assertIn(ROLE, [role["value"] for role in setup["roles"]])
		rows = {row["key"]: row for module in setup["modules"] for row in module["rows"]}
		self.assertIn("submit", rows["BOQ:0"]["columns"])
		self.assertNotIn("submit", rows["Construction Baseline:0"]["columns"])
		self.assertEqual(rows["Construction Management:1"]["columns"], ("read", "write"))

	def test_dependencies_turn_on_and_off_together(self):
		rule = self.set("BOQ", "cancel", 1)["BOQ:0"]
		self.assertEqual([rule[p] for p in ("read", "write", "submit", "cancel", "export")], [1, 1, 1, 1, 0])

		rule = self.set("BOQ", "write", 0)["BOQ:0"]
		self.assertEqual([rule[p] for p in ("read", "write", "submit", "cancel")], [1, 0, 0, 0])
		# ผู้ใช้ของ Role ได้สิทธิ์จริง (ล้าง cache แบบที่ทำหลัง commit)
		frappe.clear_cache(doctype="BOQ")
		user = self.user_with_role()
		self.assertTrue(frappe.has_permission("BOQ", "read", user=user))
		self.assertFalse(frappe.has_permission("BOQ", "write", user=user))

		# ปิดอ่าน = ไม่เหลือสิทธิ์ แถวของ Role หายไป
		self.assertNotIn("BOQ:0", self.set("BOQ", "read", 0))

	def test_higher_level_follows_level_zero(self):
		rules = self.set("Construction Management", "read", 1, permlevel=1)
		self.assertEqual(rules["Construction Management:0"]["read"], 1)
		self.assertEqual(rules["Construction Management:1"]["read"], 1)

		rules = self.set("Construction Management", "read", 0)
		self.assertNotIn("Construction Management:0", rules)
		self.assertNotIn("Construction Management:1", rules)

	def test_module_rules_and_remove_role(self):
		self.set("Purchase Order", "write", 1)
		self.set("Material Request", "read", 1)
		rules = app_settings.get_all_rules()[ROLE]
		self.assertEqual(rules["Purchase Order:0"]["write"], 1)
		self.assertEqual(rules["Material Request:0"]["read"], 1)
		# Role มาตรฐานของเอกสารที่ยังไม่เคยแก้ก็ต้องเห็น
		self.assertIn("BOQ:0", app_settings.get_all_rules()["System Manager"])

		left = app_settings.remove_role_from_module(ROLE, "office", "purchase")
		self.assertNotIn("Purchase Order:0", left)
		self.assertNotIn("Material Request:0", left)
		self.assertRaises(frappe.ValidationError, app_settings.remove_role_from_module, ROLE, "office", "nope")

	def test_rejects_outside_targets_and_non_managers(self):
		self.assertRaises(frappe.ValidationError, self.set, "User", "read", 1)
		self.assertRaises(frappe.ValidationError, self.set, "Construction Baseline", "submit", 1)
		self.assertRaises(frappe.ValidationError, app_settings.set_role_permission, "Administrator", "BOQ", 0, "read", 1)
		with patch("consbiz.app_settings.frappe.get_roles", return_value=["Projects Manager"]):
			self.assertRaises(frappe.PermissionError, self.set, "BOQ", "read", 1)
			self.assertRaises(frappe.PermissionError, app_settings.get_permission_setup)
			self.assertFalse(app_settings.can_manage())

	def user_with_role(self):
		email = "_test_settings_role@example.com"
		if not frappe.db.exists("User", email):
			frappe.get_doc(
				{
					"doctype": "User",
					"email": email,
					"first_name": "Settings",
					"send_welcome_email": 0,
					"roles": [{"role": ROLE}],
				}
			).insert(ignore_permissions=True)
		return email
