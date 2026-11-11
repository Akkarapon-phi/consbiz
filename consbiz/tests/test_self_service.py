# Copyright (c) 2026, Siricons and Contributors
# See license.txt

# Self Service (consbiz/self_service.py): ลงเวลา GPS + เซลฟี่, ลา, สลิป ของพนักงานที่ล็อกอินเท่านั้น

import base64

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, get_last_day, getdate, nowdate

from consbiz import approvals, self_service

COMPANY = "_Test Company"
# จุดลงเวลา: รัศมี 200 ม. รอบพิกัดนี้ (0.001 องศาละติจูด ≈ 111 ม.)
SITE = (13.7563, 100.5018)


def jpeg():
	"""รูปเล็กๆ สุ่มพิกเซล ไม่ซ้ำกัน (Frappe ใช้ไฟล์เดิมเมื่อเนื้อไฟล์ซ้ำ)"""
	import os
	from io import BytesIO

	from PIL import Image

	out = BytesIO()
	Image.frombytes("RGB", (16, 16), os.urandom(16 * 16 * 3)).save(out, "JPEG")
	return "data:image/jpeg;base64," + base64.b64encode(out.getvalue()).decode()


PHOTO = jpeg()


def make_user(email):
	if not frappe.db.exists("User", email):
		frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": email.split("@")[0],
				"send_welcome_email": 0,
				"roles": [{"role": "Employee"}],
			}
		).insert(ignore_permissions=True)
	return email


def make_project(project_name):
	return frappe.db.get_value("Project", {"project_name": project_name}) or (
		frappe.get_doc(
			{
				"doctype": "Project",
				"project_name": project_name,
				"company": COMPANY,
				"custom_warehouse_name": f"{project_name} WH",
			}
		)
		.insert(ignore_permissions=True)
		.name
	)


def set_roles(email, *roles):
	"""ตั้ง Role (นอกจาก Employee) ของผู้ใช้ทดสอบให้ตรงตามที่ระบุ"""
	user = frappe.get_doc("User", email)
	user.set("roles", [r for r in user.roles if r.role == "Employee"])
	user.add_roles(*roles) if roles else user.save(ignore_permissions=True)


def make_employee(email, **values):
	make_user(email)
	name = frappe.db.get_value("Employee", {"user_id": email})
	if name:
		frappe.db.set_value("Employee", name, values)
		return name
	return (
		frappe.get_doc(
			{
				"doctype": "Employee",
				"first_name": email.split("@")[0],
				"company": COMPANY,
				"gender": "Male",
				"date_of_birth": "1990-01-01",
				"date_of_joining": "2020-01-01",
				"status": "Active",
				"user_id": email,
				"create_user_permission": 0,
				"holiday_list": "_Test Holiday List",
				**values,
			}
		)
		.insert(ignore_permissions=True)
		.name
	)


class IntegrationTestSelfService(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		location = frappe.get_doc(
			{
				"doctype": "Shift Location",
				"location_name": "_Test Self Site",
				"latitude": SITE[0],
				"longitude": SITE[1],
				"checkin_radius": 200,
			}
		).insert(ignore_if_duplicate=True)
		self.location = location.name
		# โครงการ/ข้อมูลอื่นค้างข้ามเทสต์ในคลาสเดียวกัน (rollback ตอนจบคลาส) จึงใช้ตัวเดิมถ้ามี
		self.project = frappe.db.get_value("Project", {"project_name": "_Test Self Service Project"}) or (
			frappe.get_doc(
				{
					"doctype": "Project",
					"project_name": "_Test Self Service Project",
					"company": COMPANY,
					"custom_warehouse_name": "_Test Self Service WH",
					"custom_checkin_location": self.location,
				}
			)
			.insert(ignore_permissions=True)
			.name
		)
		frappe.db.set_value("Project", self.project, "custom_checkin_location", self.location)
		self.user = "self-service-a@example.com"
		self.employee = make_employee(self.user, custom_project=self.project, custom_checkin_location=None)
		self.other = "self-service-b@example.com"
		self.other_employee = make_employee(self.other, custom_project=None)
		# B = ผู้อนุมัติ (Role Leave Approver) ไม่ประจำโครงการ จึงดูแลพนักงานทุกโครงการ
		set_roles(self.other, self_service.APPROVER_ROLE)
		# ข้อมูลของเทสต์ก่อนหน้าในคลาสเดียวกันยังไม่ rollback
		for doctype in ("Employee Checkin", "Leave Application", "Leave Allocation", "Salary Slip"):
			for employee in (self.employee, self.other_employee):
				frappe.db.delete(doctype, {"employee": employee})
		frappe.db.delete("Leave Ledger Entry", {"employee": self.employee})

	def tearDown(self):
		frappe.set_user("Administrator")

	def check_in(self, offset=0.0, log_type="IN", photo=None, accuracy=12, reason=None):
		# ลงเวลาซ้ำภายใน MIN_GAP_SECONDS ไม่ได้: เลื่อนครั้งก่อนๆ ย้อนไป 2 นาที (คงวันเดิม)
		frappe.db.sql(
			"update `tabEmployee Checkin` set time = time - interval 2 minute where employee in (%s, %s)",
			(self.employee, self.other_employee),
		)
		return self_service.check_in(
			log_type, SITE[0] + offset, SITE[1], accuracy=accuracy, photo=photo or jpeg(), reason=reason
		)

	def test_double_tap_is_rejected(self):
		frappe.set_user(self.user)
		self_service.check_in("IN", *SITE, photo=PHOTO)
		self.assertRaises(frappe.ValidationError, self_service.check_in, "OUT", *SITE, photo=PHOTO)

	# ------------------------------------------------------------ ลงเวลา

	def test_checkin_inside_radius_saves_private_selfie(self):
		frappe.set_user(self.user)
		result = self.check_in(0.001)
		frappe.set_user("Administrator")
		doc = frappe.get_doc("Employee Checkin", result["name"])
		self.assertEqual(doc.employee, self.employee)
		self.assertEqual(doc.custom_project, self.project)
		self.assertEqual(doc.device_id, self_service.CHECKIN_DEVICE)
		self.assertAlmostEqual(doc.custom_distance, 111, delta=2)
		file = frappe.get_doc("File", {"file_url": doc.custom_selfie})
		self.assertTrue(file.is_private)
		self.assertEqual((file.attached_to_doctype, file.attached_to_name), ("Employee Checkin", doc.name))

	def test_next_log_type_alternates(self):
		frappe.set_user(self.user)
		self.assertEqual(self_service.get_checkin_data()["next_log_type"], "IN")
		self.check_in()
		data = self_service.get_checkin_data()
		self.assertEqual(data["next_log_type"], "OUT")
		self.assertTrue(data["logs"][0].has_selfie)

	def test_checkin_outside_radius_or_without_selfie_is_rejected(self):
		frappe.set_user(self.user)
		self.assertRaises(frappe.ValidationError, self.check_in, 0.003)
		self.assertRaises(frappe.ValidationError, self_service.check_in, "IN", *SITE, photo=None)
		self.assertRaises(frappe.ValidationError, self.check_in, 0, "IN", "data:text/html;base64,PGI+")
		self.assertFalse(frappe.db.exists("Employee Checkin", {"employee": self.employee}))

	def test_shift_location_keeps_coordinate_decimals(self):
		# ค่าเริ่มต้นของระบบปัดทศนิยม 2 ตำแหน่ง (~1 กม.) Property Setter ของ consbiz ตั้ง 7 ตำแหน่ง
		for field in ("latitude", "longitude"):
			self.assertEqual(frappe.get_meta("Shift Location").get_field(field).precision, "7")
		frappe.db.set_value("Shift Location", self.location, "latitude", 13.7563123)
		doc = frappe.get_doc("Shift Location", self.location)
		doc.save()
		self.assertAlmostEqual(frappe.db.get_value("Shift Location", self.location, "latitude"), 13.7563123, places=7)
		frappe.db.set_value("Shift Location", self.location, "latitude", SITE[0])

	def test_location_issue_says_what_is_missing(self):
		frappe.set_user("Administrator")
		frappe.db.set_value("Project", self.project, "custom_checkin_location", None)
		frappe.set_user(self.user)
		data = self_service.get_checkin_data()
		self.assertIsNone(data["location"])
		self.assertIn(self.project, data["location_issue"])
		frappe.set_user(self.other)
		self.assertIn("โครงการที่ประจำ", self_service.get_checkin_data()["location_issue"])
		# รัศมี 0 = ไม่ตรวจระยะ จึงถือว่ายังไม่ได้ตั้ง
		frappe.set_user("Administrator")
		frappe.db.set_value("Project", self.project, "custom_checkin_location", self.location)
		frappe.db.set_value("Shift Location", self.location, "checkin_radius", 0)
		frappe.set_user(self.user)
		self.assertIn("รัศมี", self_service.get_checkin_data()["location_issue"])
		self.assertRaises(frappe.ValidationError, self.check_in)
		frappe.set_user("Administrator")
		frappe.db.set_value("Shift Location", self.location, "checkin_radius", 200)

	def test_employee_location_overrides_project(self):
		frappe.set_user(self.user)
		self.assertEqual(self_service.get_checkin_data()["location"].name, self.location)
		frappe.set_user("Administrator")
		frappe.db.set_value("Employee", self.employee, "custom_project", None)
		frappe.set_user(self.user)
		self.assertIsNone(self_service.get_checkin_data()["location"])
		self.assertRaises(frappe.ValidationError, self.check_in)
		frappe.set_user("Administrator")
		frappe.db.set_value("Employee", self.employee, "custom_checkin_location", self.location)
		frappe.set_user(self.user)
		self.assertTrue(self.check_in()["name"])

	def test_employee_cannot_bypass_app(self):
		checkin = {"doctype": "Employee Checkin", "employee": self.employee, "log_type": "IN", "time": frappe.utils.now_datetime()}
		frappe.set_user(self.user)
		self.assertRaises(frappe.PermissionError, frappe.get_doc(checkin).insert, ignore_permissions=True)
		frappe.set_user("Administrator")
		self.assertTrue(frappe.get_doc(checkin).insert().name)

	def test_user_without_employee_has_no_section(self):
		frappe.set_user(make_user("self-service-none@example.com"))
		self.assertEqual(self_service.self_sections(), [])
		self.assertRaises(frappe.PermissionError, self_service.get_checkin_data)

	def test_selfie_only_for_owner_approver_and_hr(self):
		frappe.set_user(self.user)
		name = self.check_in()["name"]
		self_service.selfie(name)
		self.assertEqual(frappe.local.response.display_content_as, "inline")
		frappe.set_user(self.other)
		self_service.selfie(name)
		frappe.set_user("Administrator")
		make_employee("self-service-c@example.com", custom_project=None)
		frappe.set_user("self-service-c@example.com")
		self.assertRaises(frappe.PermissionError, self_service.selfie, name)
		frappe.set_user("Administrator")
		self_service.selfie(name)

	# ------------------------------------------------------------ รอหัวหน้ายืนยัน

	def test_outside_radius_with_reason_waits_for_supervisor(self):
		frappe.set_user(self.user)
		result = self.check_in(0.003, reason="ไปรับของที่ร้านวัสดุ")
		self.assertTrue(result["pending"])
		row = frappe.db.get_value(
			"Employee Checkin",
			result["name"],
			["custom_approval_status", "skip_auto_attendance", "custom_reason", "custom_selfie"],
			as_dict=True,
		)
		self.assertEqual((row.custom_approval_status, row.skip_auto_attendance), ("Pending", 1))
		self.assertEqual(self_service.approvers_of(self.employee), [self.other])
		self.assertIn("ไปรับของ", row.custom_reason)
		self.assertTrue(row.custom_selfie)
		# GPS คลาดมากในรัศมีก็ต้องยืนยัน / ในรัศมีปกติไม่ต้อง
		self.assertRaises(frappe.ValidationError, self.check_in, 0, "OUT", None, 300)
		self.assertTrue(self.check_in(0, "OUT", accuracy=300, reason="ในอาคาร")["pending"])
		self.assertFalse(self.check_in(0, "IN")["pending"])

	def test_supervisor_reviews_checkin(self):
		frappe.set_user(self.user)
		name = self.check_in(0.003, reason="นอกไซต์")["name"]
		self.assertFalse(self_service.can_review())
		self.assertRaises(frappe.PermissionError, self_service.review_checkin, name, 1)

		frappe.set_user(self.other)
		self.assertTrue(self_service.can_review())
		self.assertEqual([r.name for r in self_service.get_reviews()], [name])
		self.assertEqual(approvals.get_summary()["checkin"], 1)
		self_service.selfie(name)
		self.assertRaises(frappe.ValidationError, self_service.review_checkin, name, 0)
		self_service.review_checkin(name, 1)
		row = frappe.db.get_value(
			"Employee Checkin", name, ["custom_approval_status", "custom_reviewed_by", "skip_auto_attendance"], as_dict=True
		)
		self.assertEqual((row.custom_approval_status, row.custom_reviewed_by, row.skip_auto_attendance), ("Approved", self.other, 0))
		self.assertRaises(frappe.ValidationError, self_service.review_checkin, name, 1)
		self.assertEqual(self_service.get_reviews(), [])

	def test_project_approver_sees_only_own_project(self):
		frappe.set_user(self.user)
		name = self.check_in(0.003, reason="นอกไซต์")["name"]
		frappe.set_user("Administrator")
		other_project = make_project("_Test Self Service Project 2")
		# ผู้อนุมัติประจำโครงการอื่น: ไม่เห็น ไม่ได้รับแจ้ง ยืนยันไม่ได้
		frappe.db.set_value("Employee", self.other_employee, "custom_project", other_project)
		self.assertEqual(self_service.approvers_of(self.employee), [])
		frappe.set_user(self.other)
		self.assertEqual(self_service.get_reviews(), [])
		self.assertRaises(frappe.PermissionError, self_service.review_checkin, name, 1)
		# ประจำโครงการเดียวกัน = เห็นและยืนยันได้
		frappe.set_user("Administrator")
		frappe.db.set_value("Employee", self.other_employee, "custom_project", self.project)
		self.assertEqual(self_service.approvers_of(self.employee), [self.other])
		frappe.set_user(self.other)
		self.assertEqual([r.name for r in self_service.get_reviews()], [name])
		self_service.review_checkin(name, 1)

	def test_cannot_review_own_checkin(self):
		frappe.set_user("Administrator")
		set_roles(self.user, self_service.APPROVER_ROLE)
		frappe.set_user(self.user)
		name = self.check_in(0.003, reason="นอกไซต์")["name"]
		self.assertEqual(self_service.get_reviews(), [])
		self.assertRaises(frappe.PermissionError, self_service.review_checkin, name, 1)
		frappe.set_user("Administrator")
		set_roles(self.user)

	def test_rejected_checkin_is_not_counted(self):
		frappe.set_user(self.user)
		name = self.check_in(0.003, reason="นอกไซต์")["name"]
		frappe.set_user(self.other)
		self_service.review_checkin(name, 0, "ไม่ได้อยู่หน้างาน")
		self.assertEqual(frappe.db.get_value("Employee Checkin", name, "skip_auto_attendance"), 1)
		frappe.set_user(self.user)
		# เข้างานที่ไม่ได้รับยืนยัน ไม่นับว่าวันนี้เข้างานแล้ว
		self.assertEqual(self_service.get_checkin_data()["next_log_type"], "IN")

	# ------------------------------------------------------------ ลืมลงเวลาออก

	def add_past_in(self, days_ago, hour="08:05:00"):
		frappe.set_user("Administrator")
		frappe.get_doc(
			{
				"doctype": "Employee Checkin",
				"employee": self.employee,
				"log_type": "IN",
				"time": f"{add_days(nowdate(), -days_ago)} {hour}",
			}
		).insert()
		frappe.set_user(self.user)

	def test_request_forgotten_checkout(self):
		self.add_past_in(1)
		self.add_past_in(self_service.MISSING_OUT_DAYS + 1)
		day = add_days(nowdate(), -1)
		missing = self_service.get_checkin_data()["missing_out"]
		self.assertEqual([str(m["date"]) for m in missing], [day])
		self.assertEqual(self_service.get_summary()["missing_out"], 1)

		self.assertRaises(frappe.ValidationError, self_service.request_checkout, day, "07:00", "ลืม")
		self.assertRaises(frappe.ValidationError, self_service.request_checkout, day, "17:00", "")
		old = add_days(nowdate(), -(self_service.MISSING_OUT_DAYS + 1))
		self.assertRaises(frappe.ValidationError, self_service.request_checkout, old, "17:00", "ลืม")

		name = self_service.request_checkout(day, "17:30", "แบตหมด")["name"]
		row = frappe.db.get_value(
			"Employee Checkin", name, ["log_type", "time", "custom_manual", "custom_approval_status"], as_dict=True
		)
		self.assertEqual((row.log_type, str(row.time), row.custom_manual), ("OUT", f"{day} 17:30:00", 1))
		self.assertEqual(row.custom_approval_status, "Pending")
		self.assertEqual(self_service.get_checkin_data()["missing_out"], [])
		self.assertRaises(frappe.ValidationError, self_service.request_checkout, day, "18:00", "ซ้ำ")

	# ------------------------------------------------------------ ลบรูปเซลฟี่

	def make_slip(self, posting_date):
		day = getdate(nowdate())
		slip = frappe.get_doc(
			{
				"doctype": "Salary Slip",
				"employee": self.employee,
				"company": COMPANY,
				"start_date": day.replace(day=1),
				"end_date": get_last_day(day),
				"posting_date": posting_date,
				"docstatus": 1,
			}
		)
		slip.name = frappe.generate_hash(length=12)
		slip.db_insert()
		return slip

	def test_purge_after_payroll_plus_90_days_keeps_evidence(self):
		frappe.set_user(self.user)
		purged = self.check_in()["name"]
		kept = self.check_in(log_type="OUT")["name"]
		frappe.set_user("Administrator")
		frappe.db.set_value("Employee Checkin", kept, "custom_keep_evidence", 1)

		slip = self.make_slip(nowdate())
		self.assertNotIn(purged, self_service.purgeable_checkins())
		slip.db_set("posting_date", add_days(nowdate(), -(self_service.SELFIE_KEEP_DAYS + 1)))
		self.assertEqual(self_service.purgeable_checkins(), [purged])

		url = frappe.db.get_value("Employee Checkin", purged, "custom_selfie")
		self_service.purge_selfies()
		row = frappe.db.get_value(
			"Employee Checkin", purged, ["custom_selfie", "custom_selfie_purged", "latitude", "time"], as_dict=True
		)
		self.assertFalse(row.custom_selfie)
		self.assertEqual(row.custom_selfie_purged, 1)
		self.assertTrue(row.latitude and row.time)
		self.assertFalse(frappe.db.exists("File", {"file_url": url}))
		self.assertTrue(frappe.db.get_value("Employee Checkin", kept, "custom_selfie"))

	# ------------------------------------------------------------ ลา

	def allocate(self, leave_type="_Test Leave Type", days=10):
		day = getdate(nowdate())
		frappe.get_doc(
			{
				"doctype": "Leave Allocation",
				"employee": self.employee,
				"leave_type": leave_type,
				"from_date": day.replace(month=1, day=1),
				"to_date": day.replace(month=12, day=31),
				"new_leaves_allocated": days,
			}
		).submit()

	def test_apply_and_withdraw_leave(self):
		self.allocate()
		day = add_days(nowdate(), 30)
		frappe.set_user(self.user)
		data = self_service.get_leave_data()
		self.assertIn("_Test Leave Type", data["leave_types"])
		result = self_service.apply_leave({"leave_type": "_Test Leave Type", "from_date": day, "to_date": day, "description": "ทดสอบ"})
		doc = frappe.get_doc("Leave Application", result["name"])
		self.assertEqual((doc.employee, doc.status, doc.docstatus), (self.employee, "Open", 0))

		frappe.set_user(self.other)
		self.assertRaises(frappe.PermissionError, self_service.delete_leave, doc.name)
		frappe.set_user(self.user)
		self_service.delete_leave(doc.name)
		self.assertFalse(frappe.db.exists("Leave Application", doc.name))

	def test_leave_type_without_allocation_is_rejected(self):
		frappe.set_user(self.user)
		self.assertRaises(
			frappe.ValidationError,
			self_service.apply_leave,
			{"leave_type": "_Test Leave Type", "from_date": nowdate(), "to_date": nowdate()},
		)

	# ------------------------------------------------------------ สลิป

	def test_slips_only_own_submitted(self):
		slip = self.make_slip(nowdate())
		frappe.set_user(self.user)
		self.assertEqual([s.name for s in self_service.get_slips()], [slip.name])
		frappe.set_user(self.other)
		self.assertEqual(self_service.get_slips(), [])
		self.assertRaises(frappe.PermissionError, self_service.get_slip, slip.name)
