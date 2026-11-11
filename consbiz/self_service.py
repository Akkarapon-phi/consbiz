# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

"""Self Service (/conserp/self, www/self.html + public/js/self_app/) งานของพนักงานแต่ละคน

ครอบ DocType ของ HRMS ไม่เขียนระบบใหม่:
- ลงเวลา: Employee Checkin + รูปเซลฟี่ (ไฟล์ private) ต้องอยู่ในรัศมี Shift Location
  ของพนักงาน (Employee.custom_checkin_location) หรือของโครงการที่ประจำ (Employee.custom_project → Project.custom_checkin_location)
  พนักงานลงเวลาเองได้ทางแอปเท่านั้น (guard_checkin) ส่วน HR / เครื่องสแกน (ผู้ใช้ที่มี Role HR) บันทึกได้ตามปกติ
  รูปเซลฟี่ลบอัตโนมัติ (purge_selfies) เมื่อ Salary Slip ของวันนั้น Submit แล้วเกิน SELFIE_KEEP_DAYS วัน ยกเว้นติ๊ก "เก็บหลักฐาน"
- ลา: Leave Application (บันทึกเป็นสถานะ Open ให้ผู้อนุมัติของ HRMS อนุมัติ/Submit)
- สลิป: Salary Slip ที่ Submit แล้วของตัวเอง

ทุก API หาพนักงานจากผู้ใช้ที่ล็อกอิน (ไม่รับรหัสพนักงานจากภายนอก) จึงเขียน/อ่านได้เฉพาะของตัวเอง
"""

import base64
import re

import frappe
from frappe import _
from frappe.utils import add_days, cint, flt, get_datetime, getdate, now_datetime, nowdate

from consbiz import store_app

HR_ROLES = ("HR User", "HR Manager", "System Manager")
# ผู้อนุมัติใบลา + ยืนยันการลงเวลา (Role ของ HRMS) ตกลง 2026-11-11: ใช้ Role ทุกชนิดเอกสาร
# ผู้อนุมัติที่ประจำโครงการ (Employee.custom_project) เห็นเฉพาะพนักงานโครงการเดียวกัน ไม่ประจำ = ทุกคน
APPROVER_ROLE = "Leave Approver"
SELFIE_KEEP_DAYS = 90
SELFIE_MAX_BYTES = 400 * 1024
CHECKIN_DEVICE = "ConsERP"
HISTORY_DAYS = 31
# กดซ้ำ/สัญญาณช้าแล้วส่งซ้ำ: ห้ามลงเวลาซ้ำภายในกี่วินาที
MIN_GAP_SECONDS = 60
# GPS คลาดมากกว่านี้ (ม.) = ไม่แน่ใจว่าอยู่ในพื้นที่ ต้องให้หัวหน้ายืนยันเหมือนอยู่นอกรัศมี
ACCURACY_LIMIT = 100
# แจ้งลืมลงเวลาออกย้อนหลังได้กี่วัน (เกินนั้นให้ HR แก้ในระบบ) ตกลง 2026-11-11
MISSING_OUT_DAYS = 7
LIST_LIMIT = 60


# ---------------------------------------------------------------- พนักงาน / สิทธิ์


def is_hr(user=None):
	return bool(set(frappe.get_roles(user)) & set(HR_ROLES))


def employee_of(user=None):
	"""พนักงาน (Active) ที่ผูกกับผู้ใช้ ไม่มี = None"""
	user = user or frappe.session.user
	if user == "Guest":
		return None
	return frappe.db.get_value(
		"Employee",
		{"user_id": user, "status": "Active"},
		[
			"name",
			"employee_name",
			"company",
			"department",
			"designation",
			"image",
			"custom_project",
			"custom_checkin_location",
		],
		as_dict=True,
	)


def approver_project(user=None):
	"""โครงการที่ผู้อนุมัติประจำ (None = เห็นพนักงานทุกโครงการ)"""
	employee = employee_of(user)
	return (employee and employee.custom_project) or None


def is_approver(user=None):
	return is_hr(user) or APPROVER_ROLE in frappe.get_roles(user)


def scope_employees(user=None):
	"""พนักงานที่ผู้อนุมัติดูแล: None = ทุกคน (HR / ไม่ประจำโครงการ) ไม่รวมตัวเอง (กรองแยก)"""
	user = user or frappe.session.user
	if is_hr(user):
		return None
	project = approver_project(user)
	if not project:
		return None
	return frappe.get_all("Employee", filters={"custom_project": project}, pluck="name")


def scope_filters(filters, user=None):
	"""เพิ่มเงื่อนไขขอบเขตพนักงาน + ไม่รวมเอกสารของตัวเอง (อนุมัติของตัวเองไม่ได้)"""
	scope = scope_employees(user)
	mine = employee_of(user)
	if scope is not None:
		scope = [e for e in scope if not mine or e != mine.name]
		filters["employee"] = ("in", scope or [""])
	elif mine:
		filters["employee"] = ("!=", mine.name)
	return filters


def can_approve_employee(employee, user=None):
	"""อนุมัติเอกสาร HR ของพนักงานคนนี้ได้ไหม (ไม่รวมกติกาห้ามอนุมัติของตัวเอง)"""
	user = user or frappe.session.user
	if not is_approver(user):
		return False
	scope = scope_employees(user)
	return scope is None or employee in scope


def approvers_of(employee):
	"""ผู้ใช้ที่อนุมัติเอกสารของพนักงานได้ (Role APPROVER_ROLE ในขอบเขต) ใช้ส่งแจ้งเตือน ไม่รวม HR และตัวเอง"""
	from frappe.utils.user import get_users_with_role

	project, own = frappe.db.get_value("Employee", employee, ["custom_project", "user_id"])
	return sorted(
		user
		for user in get_users_with_role(APPROVER_ROLE)
		if user != own and approver_project(user) in (None, project)
	)


def approver_label(employee):
	"""ชื่อผู้อนุมัติที่แสดงให้พนักงาน: มีคนเดียว = ชื่อ, หลายคน/ไม่มี = None (หน้าจอเขียน "หัวหน้า")"""
	users = approvers_of(employee)
	return frappe.db.get_value("User", users[0], "full_name") if len(users) == 1 else None


def my_employee():
	employee = employee_of()
	if not employee:
		frappe.throw(_("บัญชีนี้ยังไม่ได้ผูกกับพนักงาน ติดต่อฝ่ายบุคคล"), frappe.PermissionError)
	return employee


def self_sections():
	"""หมวดของ bundle self_app (ชื่อหมวดตรงกับ _SELF_SECTIONS ใน hooks.py)
	self = พนักงานทุกคนที่ผูกกับผู้ใช้ / approve = โมดูลอนุมัติ (consbiz/approvals.py) ผู้ที่อนุมัติเอกสารอย่างน้อย 1 ชนิดได้"""
	from consbiz.approvals import approve_sections

	return (["self"] if employee_of() else []) + approve_sections()


def approve_rights():
	"""สิทธิ์ของโมดูลอนุมัติแต่ละชนิด (boot.can.approve_<ชนิด>)"""
	from consbiz.approvals import can_approve_any

	return {f"approve_{kind}": allowed for kind, allowed in can_approve_any().items()}


def boot_data():
	from consbiz.site_app import add_apps

	user = frappe.get_cached_doc("User", frappe.session.user)
	employee = employee_of()
	sections = self_sections()
	boot = {
		"user": user.name,
		"full_name": user.full_name or user.name,
		"user_image": user.user_image,
		"can": approve_rights(),
		"today": nowdate(),
		"desk": user.user_type == "System User",
		"sections": sections,
		"employee": employee,
	}
	add_apps(boot, ("self", sections))
	return boot


# ---------------------------------------------------------------- ลงเวลา


def resolve_location(employee):
	"""(จุดลงเวลา, เหตุผลที่ยังลงเวลาไม่ได้) ใช้ Employee.custom_checkin_location ก่อน ว่าง = ของโครงการที่ประจำ
	จุดลงเวลา = {name, location_name, latitude, longitude, radius} รัศมีต้องมากกว่า 0 (0 = ไม่ตรวจระยะ ซึ่งข้าม GPS)"""
	location = employee.custom_checkin_location
	if not location:
		if not employee.custom_project:
			return None, _("ยังไม่ได้ตั้งโครงการที่ประจำหรือจุดลงเวลาของคุณ ติดต่อฝ่ายบุคคล")
		location = frappe.db.get_value("Project", employee.custom_project, "custom_checkin_location")
		if not location:
			return None, _("โครงการ {0} ยังไม่ได้ตั้งจุดลงเวลา ติดต่อฝ่ายบุคคล").format(employee.custom_project)
	row = frappe.db.get_value(
		"Shift Location",
		location,
		["name", "location_name", "latitude", "longitude", "checkin_radius"],
		as_dict=True,
	)
	if not row:
		return None, _("ไม่พบจุดลงเวลา {0} ติดต่อฝ่ายบุคคล").format(location)
	label = row.location_name or row.name
	if not (flt(row.latitude) or flt(row.longitude)):
		return None, _("จุดลงเวลา {0} ยังไม่มีพิกัด ติดต่อฝ่ายบุคคล").format(label)
	row.radius = cint(row.pop("checkin_radius"))
	if row.radius <= 0:
		return None, _("จุดลงเวลา {0} ยังไม่ได้กำหนดรัศมี ติดต่อฝ่ายบุคคล").format(label)
	return row, None


def distance_m(location, latitude, longitude):
	from hrms.hr.utils import get_distance_between_coordinates

	return get_distance_between_coordinates(
		flt(location.latitude), flt(location.longitude), flt(latitude), flt(longitude)
	)


def checkin_rows(employee, since):
	return frappe.get_all(
		"Employee Checkin",
		filters={"employee": employee, "time": (">=", since)},
		fields=[
			"name",
			"log_type",
			"time",
			"custom_project as project",
			"custom_distance as distance",
			"custom_selfie",
			"custom_selfie_purged as purged",
			"custom_gps_accuracy as accuracy",
			"custom_approval_status as approval",
			"custom_reason as reason",
			"custom_review_note as review_note",
			"custom_manual as manual",
			"shift",
		],
		order_by="time desc",
		limit_page_length=500,
	)


def project_info(project):
	if not project:
		return None
	return frappe.db.get_value("Project", project, ["name", "project_name"], as_dict=True)


@frappe.whitelist()
def get_checkin_data():
	"""หน้าลงเวลา: พนักงาน, จุดลงเวลา, ประวัติ HISTORY_DAYS วัน (ล่าสุดก่อน), ลงครั้งถัดไปเป็นเข้า/ออก"""
	employee = my_employee()
	location, issue = resolve_location(employee)
	rows = checkin_rows(employee.name, add_days(nowdate(), -HISTORY_DAYS))
	for row in rows:
		row.has_selfie = bool(row.pop("custom_selfie"))
	today = [r for r in rows if getdate(r.time) == getdate() and r.approval != "Rejected"]
	return {
		"employee": employee,
		"project": project_info(employee.custom_project),
		"location": location,
		"location_issue": issue,
		"next_log_type": "OUT" if today and today[0].log_type == "IN" else "IN",
		"logs": rows,
		"missing_out": missing_checkouts(rows),
		"approver_name": approver_label(employee.name),
		"accuracy_limit": ACCURACY_LIMIT,
		"now": now_datetime(),
	}


def decode_photo(photo):
	"""data URL ของรูป (ย่อในเครื่องแล้ว) → (นามสกุล, bytes)"""
	match = re.match(r"^data:image/(jpeg|png|webp);base64,(.+)$", photo or "", re.S)
	if not match:
		frappe.throw(_("ต้องถ่ายรูปเซลฟี่ก่อนลงเวลา"))
	try:
		content = base64.b64decode(match.group(2), validate=True)
	except ValueError:
		frappe.throw(_("รูปเซลฟี่ไม่ถูกต้อง ถ่ายใหม่อีกครั้ง"))
	if len(content) > SELFIE_MAX_BYTES:
		frappe.throw(_("รูปใหญ่เกินไป ({0} KB) ถ่ายใหม่อีกครั้ง").format(len(content) // 1024))
	try:
		from io import BytesIO

		from PIL import Image

		Image.open(BytesIO(content)).verify()
	except Exception:
		frappe.throw(_("รูปเซลฟี่ไม่ถูกต้อง ถ่ายใหม่อีกครั้ง"))
	return {"jpeg": "jpg"}.get(match.group(1), match.group(1)), content


def needs_approval_reason(location, distance, accuracy):
	"""เหตุที่ต้องให้หัวหน้ายืนยัน (ไม่มี = ลงเวลาได้ทันที)"""
	place = location.location_name or location.name
	if distance > location.radius:
		return _("อยู่นอกพื้นที่ลงเวลา ห่างจาก {0} {1} ม. (ไม่เกิน {2} ม.)").format(
			place, round(distance), location.radius
		)
	if accuracy not in (None, "") and flt(accuracy) > ACCURACY_LIMIT:
		return _("GPS คลาดเคลื่อน ±{0} ม. (เกิน {1} ม.)").format(round(flt(accuracy)), ACCURACY_LIMIT)
	return None


def insert_checkin(values):
	doc = frappe.get_doc({"doctype": "Employee Checkin", **values})
	frappe.flags.consbiz_self_checkin = True
	try:
		doc.insert(ignore_permissions=True)
	finally:
		frappe.flags.consbiz_self_checkin = False
	return doc


def pending_values(employee, reason, manual=0):
	"""ค่าของรายการที่รอหัวหน้ายืนยัน: HRMS ไม่นำไปคิด Attendance จนกว่าจะยืนยัน (skip_auto_attendance)"""
	return {
		"custom_approval_status": "Pending",
		"custom_reason": reason,
		"custom_manual": manual,
		"skip_auto_attendance": 1,
	}


def notify_approver(doc, employee):
	from consbiz import self_advance

	subject = (
		_("{0} แจ้งลืมลงเวลาออก ขอให้ยืนยัน")
		if doc.custom_manual
		else _("{0} ลงเวลานอกพื้นที่ ขอให้ยืนยัน")
	).format(employee.employee_name)
	self_advance.notify_users(approvers_of(employee.name), doc, subject)


@frappe.whitelist(methods=["POST"])
def check_in(log_type, latitude, longitude, accuracy=None, photo=None, reason=None):
	"""ลงเวลาเข้า/ออก ต้องมีรูปเซลฟี่ เวลาใช้ของ server
	นอกรัศมีหรือ GPS คลาดเกิน ACCURACY_LIMIT: ต้องมีเหตุผล แล้วรอหัวหน้ายืนยัน (ระหว่างรอไม่นับ Attendance)"""
	employee = my_employee()
	if log_type not in ("IN", "OUT"):
		frappe.throw(_("ประเภทการลงเวลาไม่ถูกต้อง"))
	if latitude in (None, "") or longitude in (None, ""):
		frappe.throw(_("ไม่พบตำแหน่ง GPS เปิดการเข้าถึงตำแหน่งแล้วลองใหม่"))
	location, issue = resolve_location(employee)
	if not location:
		frappe.throw(issue)
	distance = distance_m(location, latitude, longitude)
	problem = needs_approval_reason(location, distance, accuracy)
	reason = (reason or "").strip()
	if problem and not reason:
		frappe.throw(_("{0} ระบุเหตุผลเพื่อส่งให้หัวหน้ายืนยัน").format(problem))
	extension, content = decode_photo(photo)
	now = now_datetime()
	last = frappe.db.get_value("Employee Checkin", {"employee": employee.name}, "time", order_by="time desc")
	if last and abs((now - get_datetime(last)).total_seconds()) < MIN_GAP_SECONDS:
		frappe.throw(
			_("เพิ่งลงเวลาไปเมื่อ {0} น. รอสักครู่แล้วลองใหม่").format(get_datetime(last).strftime("%H:%M"))
		)

	doc = insert_checkin(
		{
			"employee": employee.name,
			"log_type": log_type,
			"time": now,
			"device_id": CHECKIN_DEVICE,
			"latitude": flt(latitude),
			"longitude": flt(longitude),
			"custom_project": employee.custom_project,
			"custom_distance": round(distance),
			"custom_gps_accuracy": round(flt(accuracy)) if accuracy not in (None, "") else None,
			**(pending_values(employee, f"{problem}: {reason}") if problem else {}),
		}
	)

	from frappe.utils.file_manager import save_file

	saved = save_file(
		f"selfie-{doc.name}.{extension}",
		content,
		"Employee Checkin",
		doc.name,
		df="custom_selfie",
		is_private=1,
	)
	doc.db_set("custom_selfie", saved.file_url, update_modified=False)
	if problem:
		notify_approver(doc, employee)
	return {
		"name": doc.name,
		"log_type": doc.log_type,
		"time": doc.time,
		"distance": round(distance),
		"pending": bool(problem),
	}


# ---------------------------------------------------------------- ลืมลงเวลาออก


def missing_checkouts(rows):
	"""วันที่ผ่านมา (ไม่เกิน MISSING_OUT_DAYS วัน ไม่รวมวันนี้) ที่รายการสุดท้ายของวันเป็นเข้างาน
	rows = ประวัติล่าสุดก่อน (ไม่นับรายการที่ไม่ได้รับยืนยัน) กะข้ามเที่ยงคืนยังไม่รองรับ"""
	first = getdate(add_days(nowdate(), -MISSING_OUT_DAYS))
	today = getdate()
	last_of_day = {}
	for row in rows:
		day = getdate(row.time)
		if first <= day < today and row.approval != "Rejected" and day not in last_of_day:
			last_of_day[day] = row
	return [
		{"date": day, "check_in": row.time}
		for day, row in sorted(last_of_day.items(), reverse=True)
		if row.log_type == "IN"
	]


@frappe.whitelist(methods=["POST"])
def request_checkout(date, time, reason):
	"""แจ้งเวลาออกของวันที่ลืมลงเวลาออก: สร้างรายการออกงาน (ไม่มี GPS/รูป) รอหัวหน้ายืนยัน"""
	employee = my_employee()
	reason = (reason or "").strip()
	if not reason:
		frappe.throw(_("ระบุเหตุผลที่ลืมลงเวลาออก"))
	day = getdate(date)
	rows = checkin_rows(employee.name, add_days(nowdate(), -MISSING_OUT_DAYS))
	missing = next((m for m in missing_checkouts(rows) if m["date"] == day), None)
	if not missing:
		frappe.throw(
			_("วันที่ {0} ไม่มีรายการที่ต้องแจ้งเวลาออก (แจ้งย้อนหลังได้ไม่เกิน {1} วัน)").format(
				frappe.format(day, "Date"), MISSING_OUT_DAYS
			)
		)
	if not re.match(r"^\d{1,2}:\d{2}(:\d{2})?$", time or ""):
		frappe.throw(_("ระบุเวลาออกงาน"))
	out_time = get_datetime(f"{day} {time}")
	if out_time <= get_datetime(missing["check_in"]):
		frappe.throw(
			_("เวลาออกต้องหลังเวลาเข้างาน ({0} น.)").format(get_datetime(missing["check_in"]).strftime("%H:%M"))
		)
	doc = insert_checkin(
		{
			"employee": employee.name,
			"log_type": "OUT",
			"time": out_time,
			"device_id": f"{CHECKIN_DEVICE} (แจ้งย้อนหลัง)",
			"custom_project": employee.custom_project,
			**pending_values(employee, reason, manual=1),
		}
	)
	notify_approver(doc, employee)
	return {"name": doc.name, "time": doc.time}


# ---------------------------------------------------------------- ยืนยันการลงเวลา (หัวหน้า / HR)


def can_review(user=None):
	"""ยืนยันการลงเวลาได้: Role APPROVER_ROLE หรือ HR"""
	return is_approver(user)


def review_filters():
	return scope_filters({"custom_approval_status": "Pending"})


@frappe.whitelist()
def get_reviews(status="Pending"):
	"""รายการลงเวลาที่รอ/ผ่านการยืนยันของผู้ใช้ (HR เห็นทุกคน)"""
	if not can_review():
		frappe.throw(_("ไม่มีสิทธิ์ยืนยันการลงเวลา"), frappe.PermissionError)
	filters = review_filters()
	if status != "Pending":
		filters["custom_approval_status"] = ("in", ["Approved", "Rejected"])
		filters["time"] = (">=", add_days(nowdate(), -HISTORY_DAYS))
	rows = frappe.get_all(
		"Employee Checkin",
		filters=filters,
		fields=[
			"name",
			"employee",
			"employee_name",
			"log_type",
			"time",
			"custom_project as project",
			"custom_distance as distance",
			"custom_gps_accuracy as accuracy",
			"custom_reason as reason",
			"custom_manual as manual",
			"custom_selfie",
			"custom_approval_status as approval",
			"custom_reviewed_by as reviewed_by",
			"custom_review_note as review_note",
		],
		order_by="time desc",
		limit_page_length=200,
	)
	for row in rows:
		row.has_selfie = bool(row.pop("custom_selfie"))
	return rows


@frappe.whitelist()
def get_summary(project=None):
	"""ตัวเลขบนเมนู: รอยืนยัน (ของผู้ยืนยัน) / วันที่ลืมลงเวลาออก (ของตัวเอง)"""
	employee = employee_of()
	missing = 0
	if employee:
		missing = len(missing_checkouts(checkin_rows(employee.name, add_days(nowdate(), -MISSING_OUT_DAYS))))
	overdue = 0
	if employee:
		overdue = frappe.db.count(
			"Employee Advance",
			{
				"employee": employee.name,
				"docstatus": 1,
				"custom_advance_type": "Expense Advance",
				"custom_clear_due_date": ("<", nowdate()),
				"status": ("in", ["Paid", "Partially Paid"]),
			},
		)
	return {"missing_out": missing, "overdue_clearing": overdue}


@frappe.whitelist(methods=["POST"])
def review_checkin(name, approve, note=None):
	"""ยืนยัน = นับเข้า Attendance ตามปกติ / ไม่ยืนยัน = ไม่นับ (คง skip_auto_attendance) ยืนยันของตัวเองไม่ได้"""
	row = frappe.db.get_value(
		"Employee Checkin",
		name,
		["employee", "custom_approval_status", "time", "log_type"],
		as_dict=True,
	)
	if not row:
		frappe.throw(_("ไม่พบรายการลงเวลา"), frappe.DoesNotExistError)
	if not can_approve_employee(row.employee):
		frappe.throw(_("ไม่มีสิทธิ์ยืนยันรายการนี้"), frappe.PermissionError)
	mine = employee_of()
	if mine and mine.name == row.employee:
		frappe.throw(_("ยืนยันการลงเวลาของตัวเองไม่ได้"), frappe.PermissionError)
	if row.custom_approval_status != "Pending":
		frappe.throw(_("รายการนี้พิจารณาแล้ว"))
	approve = cint(approve)
	note = (note or "").strip()
	if not approve and not note:
		frappe.throw(_("ระบุเหตุผลที่ไม่ยืนยัน"))
	frappe.db.set_value(
		"Employee Checkin",
		name,
		{
			"custom_approval_status": "Approved" if approve else "Rejected",
			"custom_reviewed_by": frappe.session.user,
			"custom_review_note": note,
			"skip_auto_attendance": 0 if approve else 1,
		},
	)
	user = frappe.db.get_value("Employee", row.employee, "user_id")
	if user and user != frappe.session.user:
		from frappe.desk.doctype.notification_log.notification_log import enqueue_create_notification

		enqueue_create_notification(
			user,
			{
				"type": "Alert",
				"document_type": "Employee Checkin",
				"document_name": name,
				"subject": (_("การลงเวลา {0} ได้รับการยืนยันแล้ว") if approve else _("การลงเวลา {0} ไม่ได้รับการยืนยัน")).format(
					get_datetime(row.time).strftime("%d/%m %H:%M")
				),
				"from_user": frappe.session.user,
			},
		)


def guard_checkin(doc, method=None):
	"""doc_events Employee Checkin.validate: พนักงานลงเวลาเองได้ผ่านแอปเท่านั้น (ตรวจ GPS + เซลฟี่)
	HR / ผู้ดูแล / งานเบื้องหลัง (Administrator) บันทึกและแก้ได้ตามปกติ"""
	if frappe.flags.consbiz_self_checkin or frappe.session.user == "Administrator" or is_hr():
		return
	frappe.throw(_("ลงเวลาผ่านแอป ConsERP (Self Service) เท่านั้น"), frappe.PermissionError)


def can_see_checkin(name):
	employee = frappe.db.get_value("Employee Checkin", name, "employee")
	if not employee:
		return False
	if is_hr():
		return True
	mine = employee_of()
	if mine and mine.name == employee:
		return True
	# ผู้ยืนยันที่ดูแลพนักงานคนนี้ดูรูปได้
	return can_approve_employee(employee)


@frappe.whitelist()
def selfie(name):
	"""รูปเซลฟี่ของการลงเวลา: เจ้าตัวและ HR เท่านั้น (ไฟล์ private ไม่ผ่านสิทธิ์ของ Employee Checkin โดยตรง)"""
	if not can_see_checkin(name):
		frappe.throw(_("ไม่มีสิทธิ์ดูรูปนี้"), frappe.PermissionError)
	file_url = frappe.db.get_value("Employee Checkin", name, "custom_selfie")
	file_name = file_url and frappe.db.get_value(
		"File", {"file_url": file_url, "attached_to_doctype": "Employee Checkin", "attached_to_name": name}
	)
	if not file_name:
		frappe.throw(_("รูปถูกลบตามระยะเวลาเก็บแล้ว"), frappe.DoesNotExistError)
	file = frappe.get_doc("File", file_name)
	frappe.local.response.filename = file.file_name
	frappe.local.response.filecontent = file.get_content()
	frappe.local.response.type = "download"
	frappe.local.response.display_content_as = "inline"
	frappe.local.response.content_type = "image/jpeg" if file.file_name.endswith(".jpg") else None


def purgeable_checkins(today=None):
	"""Checkin ที่รูปเซลฟี่ถึงเวลาลบ: วันลงเวลาอยู่ในงวดของ Salary Slip (Submit) ของพนักงานคนนั้น
	ที่ posting_date เก่ากว่า SELFIE_KEEP_DAYS วัน และ HR ไม่ได้ติ๊กเก็บหลักฐาน"""
	cutoff = add_days(today or nowdate(), -SELFIE_KEEP_DAYS)
	checkin = frappe.qb.DocType("Employee Checkin")
	slip = frappe.qb.DocType("Salary Slip")
	from frappe.query_builder.functions import Date

	return (
		frappe.qb.from_(checkin)
		.join(slip)
		.on(
			(slip.employee == checkin.employee)
			& (slip.docstatus == 1)
			& (slip.start_date <= Date(checkin.time))
			& (slip.end_date >= Date(checkin.time))
			& (slip.posting_date <= cutoff)
		)
		.where(
			(checkin.custom_selfie.isnotnull())
			& (checkin.custom_selfie != "")
			& (checkin.custom_keep_evidence == 0)
		)
		.select(checkin.name)
		.distinct()
		.run(pluck=True)
	)


def purge_selfies():
	"""scheduler รายวัน: ลบเฉพาะไฟล์รูป เวลาและพิกัดของ Employee Checkin ยังอยู่"""
	for name in purgeable_checkins():
		for file_name in frappe.get_all(
			"File",
			filters={
				"attached_to_doctype": "Employee Checkin",
				"attached_to_name": name,
				"attached_to_field": "custom_selfie",
			},
			pluck="name",
		):
			frappe.delete_doc("File", file_name, ignore_permissions=True, force=True)
		frappe.db.set_value(
			"Employee Checkin",
			name,
			{"custom_selfie": None, "custom_selfie_purged": 1},
			update_modified=False,
		)


# ---------------------------------------------------------------- ลา


LEAVE_FIELDS = [
	"name",
	"leave_type",
	"from_date",
	"to_date",
	"half_day",
	"half_day_date",
	"total_leave_days",
	"description",
	"status",
	"docstatus",
	"leave_approver",
	"leave_approver_name",
	"posting_date",
]


def leave_types(allocation):
	"""ประเภทลาที่ขอได้: มียอดจัดสรร + ประเภทลาไม่รับค่าจ้าง (ไม่ต้องจัดสรร)"""
	names = list(allocation)
	names += [n for n in frappe.get_all("Leave Type", filters={"is_lwp": 1}, pluck="name") if n not in names]
	return names


@frappe.whitelist()
def get_leave_data():
	from hrms.hr.doctype.leave_application.leave_application import get_leave_details

	employee = my_employee()
	details = get_leave_details(employee.name, nowdate())
	allocation = details["leave_allocation"]
	applications = frappe.get_all(
		"Leave Application",
		filters={"employee": employee.name},
		fields=LEAVE_FIELDS,
		order_by="from_date desc, creation desc",
		limit_page_length=LIST_LIMIT,
	)
	for row in applications:
		row.can_delete = row.docstatus == 0 and row.status == "Open"
	return {
		"balances": [{"leave_type": name, **values} for name, values in allocation.items()],
		"leave_types": leave_types(allocation),
		"lwps": details["lwps"],
		"leave_approver_name": approver_label(employee.name),
		"approver_count": len(approvers_of(employee.name)),
		"applications": applications,
	}


def clean_leave(data):
	data = frappe.parse_json(data) if isinstance(data, str) else frappe._dict(data or {})
	if not data.get("leave_type") or not data.get("from_date") or not data.get("to_date"):
		frappe.throw(_("กรอกประเภทการลาและวันที่ให้ครบ"))
	half_day = cint(data.get("half_day"))
	return frappe._dict(
		leave_type=data.leave_type,
		from_date=getdate(data.from_date),
		to_date=getdate(data.to_date),
		half_day=half_day,
		half_day_date=getdate(data.get("half_day_date") or data.from_date) if half_day else None,
		description=(data.get("description") or "").strip(),
	)


@frappe.whitelist()
def leave_days(data):
	"""จำนวนวันลา (หักวันหยุดตาม Leave Type) แสดงก่อนส่ง"""
	from hrms.hr.doctype.leave_application.leave_application import get_number_of_leave_days

	employee = my_employee()
	values = clean_leave(data)
	if values.to_date < values.from_date:
		return 0
	return get_number_of_leave_days(
		employee.name,
		values.leave_type,
		values.from_date,
		values.to_date,
		values.half_day,
		values.half_day_date,
	)


@frappe.whitelist(methods=["POST"])
def apply_leave(data, files=None):
	"""ส่งใบลา (Leave Application สถานะ Open) อนุมัติได้ทุกคนที่มี Role APPROVER_ROLE ในขอบเขต (approvers_of)
	leave_approver ตั้งเป็นคนแรกไว้ก่อน (HR Settings อาจบังคับ) ตอนอนุมัติเปลี่ยนเป็นผู้อนุมัติจริง"""
	from hrms.hr.doctype.leave_application.leave_application import get_leave_approver, get_leave_details

	employee = my_employee()
	values = clean_leave(data)
	if values.leave_type not in leave_types(get_leave_details(employee.name, nowdate())["leave_allocation"]):
		frappe.throw(_("ประเภทการลา {0} ยังไม่มีสิทธิ์ลา ติดต่อฝ่ายบุคคล").format(values.leave_type))
	approver = next(iter(approvers_of(employee.name)), None) or get_leave_approver(employee.name)
	if not approver and frappe.db.get_single_value("HR Settings", "leave_approver_mandatory_in_leave_application"):
		frappe.throw(_("ยังไม่มีผู้อนุมัติการลา (Role {0}) ติดต่อฝ่ายบุคคล").format(APPROVER_ROLE))
	doc = frappe.get_doc(
		{
			"doctype": "Leave Application",
			"employee": employee.name,
			"company": employee.company,
			"status": "Open",
			"posting_date": nowdate(),
			"leave_approver": approver,
			"follow_via_email": 1,
			**values,
		}
	)
	doc.insert(ignore_permissions=True)
	attach_own_files(files, "Leave Application", doc.name)
	from consbiz import self_advance

	self_advance.notify_users(
		approvers_of(employee.name),
		doc,
		_("{0} ขอลา {1} {2} วัน รออนุมัติ").format(employee.employee_name, doc.leave_type, doc.total_leave_days),
	)
	return {"name": doc.name, "total_leave_days": doc.total_leave_days}


def attach_own_files(files, doctype, name):
	"""แนบไฟล์ที่ผู้ใช้เพิ่งอัปโหลดเอง (ยังไม่ผูกเอกสาร) ไม่ให้ดึงไฟล์ของคนอื่นมาผูก"""
	files = frappe.parse_json(files) if isinstance(files, str) else files
	own = frappe.get_all(
		"File",
		filters={
			"name": ("in", list(files or []) or [""]),
			"owner": frappe.session.user,
			"attached_to_name": ("is", "not set"),
		},
		pluck="name",
	)
	store_app.attach_files(own, doctype, name)


@frappe.whitelist(methods=["POST"])
def delete_leave(name):
	"""ถอนใบลาที่ยังไม่อนุมัติ (ร่าง สถานะ Open) ของตัวเอง"""
	employee = my_employee()
	row = frappe.db.get_value("Leave Application", name, ["employee", "docstatus", "status"], as_dict=True)
	if not row or row.employee != employee.name:
		frappe.throw(_("ไม่พบใบลา"), frappe.PermissionError)
	if row.docstatus != 0 or row.status != "Open":
		frappe.throw(_("ใบลาที่พิจารณาแล้วถอนไม่ได้ ติดต่อฝ่ายบุคคล"))
	frappe.delete_doc("Leave Application", name, ignore_permissions=True)


# ---------------------------------------------------------------- สลิปเงินเดือน


SLIP_FIELDS = [
	"name",
	"posting_date",
	"start_date",
	"end_date",
	"currency",
	"gross_pay",
	"total_deduction",
	"net_pay",
	"rounded_total",
	"payment_days",
	"total_working_days",
]


def my_slip(name):
	employee = my_employee()
	slip = frappe.db.get_value("Salary Slip", name, ["employee", "docstatus"], as_dict=True)
	if not slip or slip.employee != employee.name or slip.docstatus != 1:
		frappe.throw(_("ไม่พบสลิปเงินเดือน"), frappe.PermissionError)
	return frappe.get_doc("Salary Slip", name)


@frappe.whitelist()
def get_slips():
	employee = my_employee()
	return frappe.get_all(
		"Salary Slip",
		filters={"employee": employee.name, "docstatus": 1},
		fields=SLIP_FIELDS,
		order_by="start_date desc",
		limit_page_length=LIST_LIMIT,
	)


@frappe.whitelist()
def get_slip(name):
	doc = my_slip(name)
	data = {field: doc.get(field) for field in SLIP_FIELDS}

	def rows(table):
		return [{"component": r.salary_component, "amount": flt(r.amount)} for r in table if flt(r.amount)]

	data.update(earnings=rows(doc.earnings), deductions=rows(doc.deductions), pdf_url=slip_pdf_url(doc.name))
	return data


def slip_pdf_url(name):
	from urllib.parse import urlencode

	return "/api/method/consbiz.self_service.slip_pdf?" + urlencode({"name": name})


@frappe.whitelist()
def slip_pdf(name):
	"""PDF สลิปของตัวเอง (พนักงานอาจไม่มี User Permission ของ Salary Slip จึงตรวจเจ้าของเองแล้วข้ามสิทธิ์พิมพ์)"""
	from consbiz.site_app import print_options

	doc = my_slip(name)
	# Print Format ตั้งต้นของ Salary Slip และตัวสร้าง PDF แบบปุ่ม PDF ของระบบเต็ม
	print_format = frappe.get_meta("Salary Slip").default_print_format or print_options("Salary Slip")[0]
	generator = (
		print_format and frappe.db.get_value("Print Format", print_format, "pdf_generator")
	) or print_options("Salary Slip")[1]
	frappe.flags.ignore_print_permissions = True
	try:
		pdf = frappe.get_print(
			"Salary Slip", doc.name, print_format=print_format, doc=doc, as_pdf=True, pdf_generator=generator
		)
	finally:
		frappe.flags.ignore_print_permissions = False
	frappe.local.response.filename = f"{doc.name.replace('/', '-')}.pdf"
	frappe.local.response.filecontent = pdf
	frappe.local.response.type = "pdf"


# ---------------------------------------------------------------- วันหยุดประจำสัปดาห์ (Weekly Day Off)

# ลงล่วงหน้าได้กี่สัปดาห์ (นับสัปดาห์นี้)
DAY_OFF_WEEKS = 8


def day_off_api():
	from consbiz.consbiz.doctype.weekly_day_off import weekly_day_off

	return weekly_day_off


def week_info(employee, week_start, mine):
	wdo = day_off_api()
	today = getdate()
	cap = wdo.capacity(employee.custom_project)
	taken = wdo.booked(employee.custom_project, week_start, employee.name)
	days = {}
	for day in ("Saturday", "Sunday"):
		limit = cap[day]
		date = wdo.off_date_of(week_start, day)
		days[day] = {
			"date": date,
			"taken": taken[day],
			"limit": limit,
			"full": limit is not None and taken[day] >= limit,
			# เลือก/เปลี่ยนได้ถึงวันหยุดนั้น (ของเดิมที่ผ่านไปแล้วก็ห้ามเปลี่ยน)
			"open": date >= today,
		}
	locked = bool(mine and mine.off_date < today)
	return {"week_start": week_start, "mine": mine and mine.day_off, "locked": locked, "days": days}


@frappe.whitelist()
def get_day_off():
	"""วันหยุดของฉัน DAY_OFF_WEEKS สัปดาห์ (สัปดาห์นี้ก่อน) พร้อมที่ว่างของแต่ละวัน"""
	wdo = day_off_api()
	employee = my_employee()
	first = wdo.week_start_of(nowdate())
	weeks = [getdate(add_days(first, 7 * i)) for i in range(DAY_OFF_WEEKS)]
	mine = {
		getdate(r.week_start): r
		for r in frappe.get_all(
			"Weekly Day Off",
			filters={"employee": employee.name, "week_start": ("between", [weeks[0], weeks[-1]])},
			fields=["week_start", "day_off", "off_date"],
		)
	}
	cap = wdo.capacity(employee.custom_project)
	return {
		"project": project_info(employee.custom_project),
		"team_size": wdo.team_size(employee.custom_project),
		"capacity": cap,
		"weeks": [week_info(employee, week, mine.get(week)) for week in weeks],
	}


@frappe.whitelist(methods=["POST"])
def book_day_off(week_start, day_off=None):
	"""ลง/เปลี่ยน/ยกเลิก (day_off ว่าง) วันหยุดของสัปดาห์ ใครลงก่อนได้ก่อนตามโควตาของโครงการ มีผลทันที"""
	wdo = day_off_api()
	employee = my_employee()
	week = wdo.week_start_of(week_start)
	today = getdate()
	first = wdo.week_start_of(nowdate())
	if week < first or week > getdate(add_days(first, 7 * (DAY_OFF_WEEKS - 1))):
		frappe.throw(_("ลงวันหยุดได้ตั้งแต่สัปดาห์นี้ถึงอีก {0} สัปดาห์").format(DAY_OFF_WEEKS - 1))
	if day_off and day_off not in wdo.DAY_OFFSET:
		frappe.throw(_("วันหยุดต้องเป็นเสาร์หรืออาทิตย์"))
	# ล็อกแถวโครงการ: คนในทีมเดียวกันลงพร้อมกันต้องรอกันทีละคน (กันได้เกินโควตา)
	if employee.custom_project:
		frappe.db.get_value("Project", employee.custom_project, "name", for_update=True)
	name = frappe.db.get_value("Weekly Day Off", {"employee": employee.name, "week_start": week})
	current = name and frappe.get_doc("Weekly Day Off", name)
	if current and current.off_date < today:
		frappe.throw(_("วันหยุดของสัปดาห์นี้ผ่านไปแล้ว เปลี่ยนไม่ได้ ติดต่อฝ่ายบุคคล"))
	if not day_off:
		if current:
			current.flags.from_self_service = True
			current.delete(ignore_permissions=True)
		return week_info(employee, week, None)
	if wdo.off_date_of(week, day_off) < today:
		frappe.throw(_("วัน{0}ของสัปดาห์นี้ผ่านไปแล้ว").format(wdo.DAY_LABEL[day_off]))
	limit = wdo.capacity(employee.custom_project)[day_off]
	if limit is not None and wdo.booked(employee.custom_project, week, employee.name)[day_off] >= limit:
		frappe.throw(_("วัน{0}ของสัปดาห์นี้เต็มแล้ว ({1} คน) เลือกอีกวัน").format(wdo.DAY_LABEL[day_off], limit))
	doc = current or frappe.new_doc("Weekly Day Off")
	doc.update({"employee": employee.name, "week_start": week, "day_off": day_off})
	if doc.is_new():
		doc.project = employee.custom_project
	doc.flags.from_self_service = True
	doc.save(ignore_permissions=True)
	return week_info(employee, week, doc)


@frappe.whitelist()
def get_team_day_off(week_start=None):
	"""ตารางวันหยุดของทีม (พนักงาน Active ในโครงการเดียวกัน) ของสัปดาห์ แสดงชื่อเท่านั้น"""
	wdo = day_off_api()
	employee = my_employee()
	week = wdo.week_start_of(week_start or nowdate())
	if not employee.custom_project:
		return {"week_start": week, "project": None, "Saturday": [], "Sunday": [], "none": []}
	team = frappe.get_all(
		"Employee",
		filters={"custom_project": employee.custom_project, "status": "Active"},
		fields=["name", "employee_name", "designation", "image"],
		order_by="employee_name asc",
	)
	picks = dict(
		frappe.get_all(
			"Weekly Day Off",
			filters={"project": employee.custom_project, "week_start": week},
			fields=["employee", "day_off"],
			as_list=True,
		)
	)
	out = {"week_start": week, "project": project_info(employee.custom_project), "Saturday": [], "Sunday": [], "none": []}
	for person in team:
		person.me = person.name == employee.name
		out[picks.get(person.name, "none")].append(person)
	out["capacity"] = wdo.capacity(employee.custom_project)
	return out
