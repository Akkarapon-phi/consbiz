# Copyright (c) 2026, Siricons and Contributors
# See license.txt

# เอกสารพนักงานในหมวดบุคคล (hr_docs.py): สัญญาจ้าง (วันสิ้นสุดทดลองงาน, ผลทดลองงานแก้หลังยืนยันได้, ตัวเลขรอประเมิน)
# และ 50 ทวิ พนักงาน (เติมข้อมูลพนักงาน, ภาษีที่หัก = ฐาน x อัตรา)

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, nowdate

from consbiz import hr_docs
from consbiz.tests.test_self_service import COMPANY, make_employee


class IntegrationTestHrDocs(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self.employee = make_employee("hr-docs@example.com")

	def test_contract_probation(self):
		data = hr_docs.get_doc("hr-contracts", company=COMPANY)["doc"]
		start = add_days(nowdate(), -200)
		data.update(employee=self.employee, date=start, base=15000, prob_start_date=start, prob_days="119")
		view = hr_docs.save_doc("hr-contracts", frappe.as_json(data))
		self.assertEqual(str(view["doc"]["prob_end_date"]), str(add_days(start, 118)))

		view = hr_docs.submit_doc("hr-contracts", view["doc"]["name"])
		self.assertEqual(view["doc"]["status_tone"], "amber")
		self.assertTrue(view["can_edit_after"])
		self.assertGreaterEqual(hr_docs.get_summary()["probation_due"]["count"], 1)

		data = view["doc"]
		data["probation"] = "ผ่าน"
		data["base"] = 99999  # ช่องอื่นหลังยืนยันไม่เปลี่ยน
		view = hr_docs.save_doc("hr-contracts", frappe.as_json(data))
		self.assertEqual(view["doc"]["probation"], "ผ่าน")
		self.assertEqual(view["doc"]["base"], 15000)

	def test_wht_fills_employee_and_tax(self):
		data = hr_docs.get_doc("hr-wht", company=COMPANY)["doc"]
		data.update(
			employee=self.employee,
			income_tax_form="PND3",
			address="ที่อยู่ทดสอบ",
			company_address="ที่อยู่บริษัททดสอบ",
			items=[{"type_of_income": "1", "description": "เงินเดือน", "tax_base": 30000, "tax_rate": 3}],
		)
		view = hr_docs.save_doc("hr-wht", frappe.as_json(data))
		self.assertTrue(view["doc"]["full_name"])
		self.assertEqual(view["doc"]["items"][0]["tax_amount"], 900)

		data = view["doc"]
		data["items"] = []
		with self.assertRaises(frappe.ValidationError):
			hr_docs.save_doc("hr-wht", frappe.as_json(data))
