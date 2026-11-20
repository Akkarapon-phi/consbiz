# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

"""ใบเตือน (หนังสือเตือนพนักงาน) ตกลง 2026-11-17 หน้าจอในแอป = หมวดบุคคล กลุ่มพนักงาน (hr-warnings, consbiz/hr_docs.py)
ยืนยัน (Submit) = ออกหนังสือแล้ว หลังยืนยันแก้ได้เฉพาะการรับทราบ (acknowledged / acknowledged_date / refused)
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, nowdate

# ระดับ → ข้อความในหนังสือ (ตรงกับ LEVEL ในแอป)
LEVEL_LABEL = {"Verbal": "ตักเตือนด้วยวาจา", "Written 1": "หนังสือเตือนครั้งที่ 1", "Written 2": "หนังสือเตือนครั้งที่ 2", "Final": "หนังสือเตือนครั้งสุดท้าย"}
CATEGORY_LABEL = {"Late": "มาสาย", "Absence": "ขาดงาน", "Misconduct": "ประพฤติผิดวินัย", "Safety": "ความปลอดภัย", "Performance": "ผลงาน", "Other": "อื่นๆ"}


class EmployeeWarning(Document):
	def validate(self):
		if self.incident_date and getdate(self.incident_date) > getdate(self.date or nowdate()):
			frappe.throw(_("วันที่เกิดเหตุต้องไม่หลังวันที่ออกหนังสือ"))
		if self.acknowledged and self.refused:
			frappe.throw(_("เลือกได้อย่างเดียว: รับทราบ หรือ ไม่ยอมลงชื่อ"))
		if self.acknowledged and not self.acknowledged_date:
			self.acknowledged_date = nowdate()
		if not self.acknowledged:
			self.acknowledged_date = None
		if not self.issued_by:
			self.issued_by = frappe.session.user

	def before_update_after_submit(self):
		# แก้การรับทราบหลังยืนยัน: ตรวจ/เติมวันที่รับทราบแบบเดียวกับตอนบันทึก
		self.validate()

	def previous_warnings(self):
		"""ใบเตือนที่ยืนยันแล้วของพนักงานคนนี้ (ใช้ในหนังสือ/หน้าจอ)"""
		return frappe.get_all(
			"Employee Warning",
			filters={"employee": self.employee, "docstatus": 1, "name": ("!=", self.name or "")},
			fields=["name", "date", "level", "category"],
			order_by="date desc",
		)
