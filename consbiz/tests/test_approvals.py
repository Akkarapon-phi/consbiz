# Copyright (c) 2026, Siricons and Contributors
# See license.txt

# โมดูลอนุมัติ (consbiz/approvals.py): รวมเอกสารรออนุมัติ + อนุมัติใบลา

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, getdate, nowdate

from consbiz import approvals, self_service
from consbiz.tests.test_self_service import make_employee, make_project, make_user, set_roles

EMPLOYEE = "approve-emp@example.com"
APPROVER = "approve-boss@example.com"
OUTSIDER = "approve-none@example.com"
LEAVE_TYPE = "_Test Leave Type"


class IntegrationTestApprovals(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		# โครงการของเทสต์เอง: ผู้อนุมัติประจำโครงการเห็นเฉพาะพนักงานโครงการนี้ (ไม่ปนกับข้อมูลค้างของเทสต์อื่น)
		self.project = make_project("_Test Approvals Project")
		self.approver_employee = make_employee(APPROVER, custom_project=self.project)
		self.employee = make_employee(EMPLOYEE, custom_project=self.project)
		# ผู้อนุมัติใบลา/ลงเวลา = Role Leave Approver (ไม่ใช้ leave_approver / Reports To ของพนักงาน)
		set_roles(APPROVER, self_service.APPROVER_ROLE)
		make_user(OUTSIDER)
		for doctype in ("Leave Application", "Leave Allocation", "Leave Ledger Entry", "Employee Checkin"):
			frappe.db.delete(doctype, {"employee": ("in", [self.employee, self.approver_employee])})
		day = getdate(nowdate())
		frappe.get_doc(
			{
				"doctype": "Leave Allocation",
				"employee": self.employee,
				"leave_type": LEAVE_TYPE,
				"from_date": day.replace(month=1, day=1),
				"to_date": day.replace(month=12, day=31),
				"new_leaves_allocated": 10,
			}
		).submit()

	def tearDown(self):
		frappe.set_user("Administrator")

	def as_user(self, user, fn, *args, **kwargs):
		frappe.set_user(user)
		try:
			return fn(*args, **kwargs)
		finally:
			frappe.set_user("Administrator")

	def apply(self):
		day = add_days(nowdate(), 20)
		return self.as_user(
			EMPLOYEE, self_service.apply_leave, {"leave_type": LEAVE_TYPE, "from_date": day, "to_date": day}
		)["name"]

	def test_sections_by_rights(self):
		self.assertEqual(self.as_user(OUTSIDER, approvals.approve_sections), [])
		self.assertEqual(self.as_user(APPROVER, approvals.approve_sections), ["approve"])
		self.assertEqual(self.as_user(EMPLOYEE, self_service.self_sections), ["self"])
		self.assertRaises(frappe.PermissionError, self.as_user, OUTSIDER, approvals.get_inbox)

	def test_inbox_collects_leave_and_checkin(self):
		name = self.apply()
		# แจ้งลืมลงเวลาออกของเมื่อวาน (ไม่ต้องใช้ GPS)
		frappe.get_doc(
			{"doctype": "Employee Checkin", "employee": self.employee, "log_type": "IN", "time": f"{add_days(nowdate(), -1)} 08:00:00"}
		).insert()
		self.as_user(EMPLOYEE, self_service.request_checkout, add_days(nowdate(), -1), "17:00", "ลืม")

		inbox = self.as_user(APPROVER, approvals.get_inbox)
		self.assertEqual([r.name for r in inbox["leave"]], [name])
		self.assertEqual(inbox["leave"][0].balance, 10)
		self.assertEqual(len(inbox["checkin"]), 1)
		summary = self.as_user(APPROVER, approvals.get_summary)
		self.assertEqual((summary["leave"], summary["checkin"], summary["total"], summary["hr"]), (1, 1, 2, 2))
		# เมนูย่อยรายโมดูล + หน้าของโมดูลถามแบบเงียบ (ไม่มีสิทธิ์ = ค่าว่าง ไม่ error)
		self.assertEqual(len(self.as_user(APPROVER, approvals.get_inbox, "hr")["leave"]), 1)
		self.assertRaises(frappe.ValidationError, self.as_user, APPROVER, approvals.get_inbox, "unknown")
		self.assertEqual(self.as_user(OUTSIDER, approvals.get_inbox, "hr", 1), {"can": {"leave": False, "checkin": False, "advance": False, "claim": False}})

	def test_leave_approval(self):
		name = self.apply()
		self.assertRaises(frappe.PermissionError, self.as_user, OUTSIDER, approvals.review_leave, name, 1)
		self.assertRaises(frappe.PermissionError, self.as_user, EMPLOYEE, approvals.review_leave, name, 1)
		self.assertEqual(self.as_user(APPROVER, approvals.review_leave, name, 1), "Approved")
		doc = frappe.get_doc("Leave Application", name)
		self.assertEqual((doc.status, doc.docstatus, doc.leave_approver), ("Approved", 1, APPROVER))
		self.assertRaises(frappe.ValidationError, self.as_user, APPROVER, approvals.review_leave, name, 1)
		history = self.as_user(APPROVER, approvals.get_history)
		self.assertEqual([r.name for r in history["leave"]], [name])

	def test_leave_rejection_needs_reason(self):
		name = self.apply()
		self.assertRaises(frappe.ValidationError, self.as_user, APPROVER, approvals.review_leave, name, 0)
		self.assertEqual(self.as_user(APPROVER, approvals.review_leave, name, 0, "ช่วงนั้นงานเร่ง"), "Rejected")
		self.assertEqual(frappe.db.get_value("Leave Application", name, ["status", "docstatus"]), ("Rejected", 1))
		self.assertTrue(
			frappe.db.exists("Comment", {"reference_name": name, "content": ("like", "%ช่วงนั้นงานเร่ง%")})
		)

	def test_leave_notifies_approvers_in_scope(self):
		name = self.apply()
		self.assertEqual(frappe.db.get_value("Leave Application", name, "leave_approver"), APPROVER)
		self.assertEqual(self.as_user(EMPLOYEE, self_service.get_leave_data)["leave_approver_name"], frappe.db.get_value("User", APPROVER, "full_name"))
		# ผู้อนุมัติประจำโครงการอื่น ไม่เห็นใบลาของพนักงานที่ไม่ได้อยู่โครงการเดียวกัน
		frappe.db.set_value("Employee", self.approver_employee, "custom_project", make_project("_Test Approvals Project 2"))
		self.assertEqual(self.as_user(APPROVER, approvals.get_inbox)["leave"], [])
		self.assertRaises(frappe.PermissionError, self.as_user, APPROVER, approvals.review_leave, name, 1)

	def test_leave_context_for_approver_only(self):
		name = self.apply()
		day = frappe.db.get_value("Leave Application", name, "from_date")
		ctx = self.as_user(APPROVER, approvals.get_context, self.employee, "leave", day, day)
		self.assertIn(LEAVE_TYPE, [b["leave_type"] for b in ctx["leave"]["balances"]])
		self.assertEqual([r.name for r in ctx["leave"]["recent"]], [name])
		self.assertIsNotNone(ctx["leave"]["attendance"])
		self.assertNotIn("money", ctx)
		self.assertRaises(frappe.PermissionError, self.as_user, OUTSIDER, approvals.get_context, self.employee, "leave")
		# ผู้อนุมัติการลา (ไม่มี Role การเบิก) ไม่เห็นข้อมูลเงิน
		self.assertRaises(frappe.PermissionError, self.as_user, APPROVER, approvals.get_context, self.employee, "advance")
