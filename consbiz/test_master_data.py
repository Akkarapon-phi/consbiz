# Copyright (c) 2026, Siricons and Contributors
# See license.txt

# ข้อมูลหลักในแอปออฟฟิศ (master_data.py): เลขพนักงานตามปีที่เริ่มงาน, ช่องที่แก้ได้ตอนสร้างเท่านั้น,
# หน่วยแปลงของสินค้า, ที่อยู่หลักของลูกค้า, ตัวย่อโครงการ และการค้นหาช่อง Link เฉพาะ DocType ในฟอร์ม

import frappe
from frappe.tests import IntegrationTestCase

from consbiz import master_data
from consbiz.tests.test_self_service import COMPANY


def save(kind, **values):
	data = master_data.get_doc(kind, company=COMPANY)["doc"]
	data.update(values)
	return master_data.save_doc(kind, frappe.as_json(data))


class IntegrationTestMasterData(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")

	def test_employee_series_and_create_only(self):
		view = save(
			"md-employees",
			first_name="ทดสอบ",
			last_name="ข้อมูลหลัก",
			gender="Male",
			date_of_birth="1990-01-01",
			date_of_joining="2026-03-01",
			status="Active",
		)
		self.assertTrue(view["doc"]["name"].startswith("EMP-26"))

		data = view["doc"]
		data.update(company="_Test Other Company", status="Left", relieving_date="2026-12-31")
		view = master_data.save_doc("md-employees", frappe.as_json(data))
		self.assertEqual(view["doc"]["company"], COMPANY)
		self.assertEqual(view["doc"]["status"], "Left")

		data = view["doc"]
		data["custom_id_card"] = "123"
		with self.assertRaises(frappe.ValidationError):
			master_data.save_doc("md-employees", frappe.as_json(data))

	def test_item_uoms(self):
		for uom in ("_Test MD Kg", "_Test MD Bar"):
			if not frappe.db.exists("UOM", uom):
				frappe.get_doc({"doctype": "UOM", "uom_name": uom}).insert()
		group = frappe.db.get_value("Item Group", {"is_group": 0}, "name")
		view = save(
			"md-items",
			item_name="_Test MD เหล็ก",
			item_group=group,
			stock_uom="_Test MD Kg",
			purchase_uom="_Test MD Bar",
			uoms=[{"uom": "_Test MD Bar", "conversion_factor": 10.66}],
		)
		item = frappe.get_doc("Item", view["doc"]["name"])
		self.assertEqual(
			{row.uom: row.conversion_factor for row in item.uoms}, {"_Test MD Bar": 10.66, "_Test MD Kg": 1}
		)
		self.assertNotIn(item.name, [r.name for r in master_data.get_list("md-items") if r.custom_base_item])

	def test_customer_address(self):
		view = save(
			"md-customers",
			customer_name="_Test MD ลูกค้า",
			customer_type="Company",
			tax_id="1234567890123",
			**{"address.address_line1": "1 ถนนทดสอบ", "address.city": "เมือง"},
		)
		address = view["doc"]["address"]
		self.assertTrue(address)
		self.assertEqual(frappe.db.get_value("Address", address, "tax_id"), "1234567890123")

		data = view["doc"]
		data["address.city"] = "เมืองใหม่"
		view = master_data.save_doc("md-customers", frappe.as_json(data))
		self.assertEqual(view["doc"]["address"], address)
		self.assertEqual(view["doc"]["address.city"], "เมืองใหม่")

	def test_project_requires_abbr(self):
		with self.assertRaises(frappe.ValidationError):
			save("md-projects", project_name="_Test MD โครงการ ไม่มีตัวย่อ")
		view = save("md-projects", project_name="_Test MD โครงการ", custom_abbr="tmd")
		self.assertIn("TMD", view["doc"]["name"])

	def test_search_only_form_doctypes(self):
		self.assertIsInstance(master_data.search("md-employees", "Department", ""), list)
		with self.assertRaises(frappe.PermissionError):
			master_data.search("md-employees", "Item", "")
