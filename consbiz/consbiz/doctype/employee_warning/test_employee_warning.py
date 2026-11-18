# Copyright (c) 2026, Siricons and Contributors
# See license.txt

# ใบเตือน: ตรวจวันที่เกิดเหตุ, รับทราบ/ไม่ยอมลงชื่อเลือกได้อย่างเดียว, แก้การรับทราบหลังยืนยันได้

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, nowdate

from consbiz.tests.test_self_service import make_employee

IGNORE_TEST_RECORD_DEPENDENCIES = ["Employee", "Company", "User"]


class IntegrationTestEmployeeWarning(IntegrationTestCase):
	def make(self, **values):
		return frappe.get_doc(
			{
				"doctype": "Employee Warning",
				"employee": make_employee("warning-emp@example.com"),
				"date": nowdate(),
				"level": "Written 1",
				"category": "Late",
				"description": "มาสายเกิน 3 ครั้งในเดือน",
				**values,
			}
		)

	def test_incident_after_issue_date(self):
		with self.assertRaises(frappe.ValidationError):
			self.make(incident_date=add_days(nowdate(), 1)).insert()

	def test_acknowledge_after_submit(self):
		doc = self.make().insert()
		doc.submit()
		doc.acknowledged = 1
		doc.save()
		self.assertTrue(doc.acknowledged_date)
		doc.refused = 1
		with self.assertRaises(frappe.ValidationError):
			doc.save()
