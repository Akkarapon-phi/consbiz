# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

"""Self Service (ตกลง 2026-11-17): หน้าแรก (แดชบอร์ด) + แจ้งมาทำงาน (Attendance Request) + เงินเดือน

- หน้าแรก (หน้า checkin ของ self_app): ทักทาย ลงเวลา ปฏิทินวันทำงานของเดือน (สถานะชุดเดียวกับหน้าสรุปวันทำงานของ HR:
  hr_attendance.build) ลา/ขาด/สาย ของเดือนและของปี รายการของฉันที่รออนุมัติ และสิ่งที่ควรทำ (suggestions)
- แจ้งมาทำงาน = Attendance Request ของ HRMS (มาทำงาน/ปฏิบัติงานนอกสถานที่ = On Duty, ทำงานที่บ้าน = Work From Home)
  ใช้เมื่อไม่ได้ลงเวลา แจ้งย้อนหลังได้ ATTENDANCE_REQUEST_DAYS วัน ผู้อนุมัติ = Role Leave Approver ตามขอบเขตโครงการ
  (เหมือนใบลา) อนุมัติ = Submit (HRMS สร้าง Attendance) ไม่อนุมัติ = คงร่าง custom_approval_status Rejected + เหตุผล
  แจ้งใหม่ช่วงที่ทับใบที่ไม่อนุมัติ = ลบใบเดิมของตัวเองก่อน (HRMS ห้ามคำขอทับกัน)
- เงินเดือน: ค่าจ้างปัจจุบัน + ที่จะปรับ (Salary Structure Assignment ที่ from_date ในอนาคต) เงินได้สะสม/ประกันสังคมสะสม
  ของปี (สลิปที่ Submit แล้ว) + รายการสลิป (self_service.get_slips)

ทุก API หาพนักงานจากผู้ใช้ที่ล็อกอิน (self_service.my_employee) เหมือนส่วนอื่นของ Self Service
"""

import frappe
from frappe import _
from frappe.utils import add_days, cint, date_diff, flt, getdate, nowdate

from consbiz import hr_attendance, self_advance, self_service

# แจ้งมาทำงานย้อนหลังได้กี่วัน (เท่ากับแจ้งลืมลงเวลาออก) เกินนั้นติดต่อ HR
ATTENDANCE_REQUEST_DAYS = self_service.MISSING_OUT_DAYS
REQUEST_REASONS = ("On Duty", "Work From Home")
REQUEST_FIELDS = [
	"name",
	"from_date",
	"to_date",
	"half_day",
	"half_day_date",
	"reason",
	"explanation",
	"docstatus",
	"custom_approval_status as approval",
	"custom_review_note as review_note",
	"creation",
]
SSO_ABBR = "SSF"


# ---------------------------------------------------------------- หน้าแรก


def month_or_now(month):
	month = (month or "")[:7] or nowdate()[:7]
	try:
		getdate(f"{month}-01")
	except Exception:
		frappe.throw(_("เดือนไม่ถูกต้อง"))
	return month


def month_calendar(employee, month):
	"""สถานะรายวันของเดือน (ชุดเดียวกับหน้าสรุปวันทำงานของ HR) + ลงเวลา/คำขอของแต่ละวัน"""
	start, end, rows = hr_attendance.build(employee.company, month, employee=employee.name)
	days = rows[0]["days"] if rows else {}
	totals = rows[0]["totals"] if rows else hr_attendance.totals_of({})
	requests = frappe.get_all(
		"Attendance Request",
		filters={"employee": employee.name, "docstatus": ("<", 2), "from_date": ("<=", end), "to_date": (">=", start)},
		fields=REQUEST_FIELDS,
	)
	for row in requests:
		day = getdate(row.from_date)
		while day <= getdate(row.to_date):
			cell = days.get(str(day))
			if cell is not None and row.docstatus == 0 and row.approval != "Rejected":
				cell["request"] = row.name
			day = add_days(day, 1)
	window = getdate(add_days(nowdate(), -ATTENDANCE_REQUEST_DAYS))
	for key, cell in days.items():
		# วันขาดในช่วงที่แจ้งได้ = เสนอให้แจ้งมาทำงาน
		if cell["s"] == "absent" and getdate(key) >= window and not cell.get("request"):
			cell["can_request"] = 1
	return {"month": month, "start": start, "end": end, "days": days, "totals": totals}


def year_totals(employee):
	"""ลา/ขาด/สาย ตั้งแต่ต้นปีถึงเดือนนี้ (สถานะชุดเดียวกับปฏิทิน) ลา = จำนวนใบลาที่อนุมัติ + วัน"""
	today = getdate()
	out = {"absent": 0, "half": 0, "late_count": 0, "late_min": 0, "present": 0}
	for m in range(1, today.month + 1):
		_start, _end, rows = hr_attendance.build(employee.company, f"{today.year}-{m:02d}", employee=employee.name)
		if rows:
			for key in out:
				out[key] += rows[0]["totals"].get(key, 0)
	leaves = frappe.get_all(
		"Leave Application",
		filters={
			"employee": employee.name,
			"docstatus": 1,
			"status": "Approved",
			"from_date": ("between", [f"{today.year}-01-01", f"{today.year}-12-31"]),
		},
		fields=["total_leave_days"],
	)
	out["leave_count"] = len(leaves)
	out["leave_days"] = sum(flt(l.total_leave_days) for l in leaves)
	return out


def my_pending(employee):
	"""เอกสารของฉันที่ยังรอพิจารณา (หน้าแรกแสดงเป็นรายการ แตะ = ไปหน้าของชนิดนั้น)"""
	out = []
	for row in frappe.get_all(
		"Leave Application",
		filters={"employee": employee.name, "docstatus": 0, "status": "Open"},
		fields=["name", "leave_type", "from_date", "to_date", "total_leave_days"],
		order_by="from_date asc",
	):
		out.append({"kind": "leave", "name": row.name, "date": row.from_date, "to_date": row.to_date, "title": row.leave_type, "days": row.total_leave_days})
	for row in frappe.get_all(
		"Employee Checkin",
		filters={"employee": employee.name, "custom_approval_status": "Pending"},
		fields=["name", "log_type", "time", "custom_manual as manual"],
		order_by="time asc",
	):
		out.append({"kind": "checkin", "name": row.name, "date": row.time, "log_type": row.log_type, "manual": row.manual})
	for row in frappe.get_all(
		"Attendance Request",
		filters={"employee": employee.name, "docstatus": 0, "custom_approval_status": ("!=", "Rejected")},
		fields=["name", "from_date", "to_date", "reason"],
		order_by="from_date asc",
	):
		out.append({"kind": "attendance", "name": row.name, "date": row.from_date, "to_date": row.to_date, "reason": row.reason})
	for row in frappe.get_all(
		"Employee Advance",
		filters={
			"employee": employee.name,
			"docstatus": 0,
			"custom_advance_type": ("in", self_advance.TYPES),
			"custom_approval_status": ("!=", "Rejected"),
		},
		fields=["name", "posting_date", "advance_amount", "custom_advance_type as advance_type"],
		order_by="posting_date asc",
	):
		out.append({"kind": "advance", "name": row.name, "date": row.posting_date, "amount": row.advance_amount, "advance_type": row.advance_type})
	for row in frappe.get_all(
		"Expense Claim",
		filters={"employee": employee.name, "docstatus": 0},
		fields=["name", "posting_date", "total_claimed_amount", "total_advance_amount", "custom_reject_reason as reject_reason"],
		order_by="posting_date asc",
	):
		if not row.reject_reason:
			out.append({"kind": "claim", "name": row.name, "date": row.posting_date, "amount": row.total_claimed_amount, "clearing": bool(flt(row.total_advance_amount))})
	return out


def next_week_unbooked(employee):
	"""สัปดาห์ถัดไปยังไม่ได้จองกะ (Weekly Day Off) = วันจันทร์ของสัปดาห์นั้น ไม่ประจำโครงการ = ไม่เตือน"""
	if not employee.custom_project:
		return None
	wdo = self_service.day_off_api()
	week = getdate(add_days(wdo.week_start_of(nowdate()), 7))
	if frappe.db.exists("Weekly Day Off", {"employee": employee.name, "week_start": week}):
		return None
	return week


def expiring_leaves(employee):
	"""สิทธิ์ลาที่เหลือและหมดรอบภายใน 60 วัน (เช่น พักร้อนสิ้นปี)"""
	from hrms.hr.doctype.leave_application.leave_application import get_leave_details

	limit = getdate(add_days(nowdate(), 60))
	allocation = get_leave_details(employee.name, nowdate())["leave_allocation"]
	out = []
	for row in frappe.get_all(
		"Leave Allocation",
		filters={"employee": employee.name, "docstatus": 1, "from_date": ("<=", nowdate()), "to_date": ("between", [nowdate(), limit])},
		fields=["leave_type", "to_date"],
	):
		remaining = flt((allocation.get(row.leave_type) or {}).get("remaining_leaves"))
		if remaining > 0:
			out.append({"leave_type": row.leave_type, "remaining": remaining, "to_date": row.to_date})
	return out


def suggestions(employee, checkin, calendar):
	"""สิ่งที่ควรทำ เรียงตามความสำคัญ (หน้าจอแปลง kind เป็นข้อความ/ปุ่ม)"""
	out = [{"kind": "missing_out", "date": m["date"], "check_in": m["check_in"]} for m in checkin["missing_out"]]
	# วันขาดที่ยังแจ้งมาทำงานได้ (ของเดือนที่แสดง)
	absent = sorted(day for day, cell in calendar["days"].items() if cell.get("can_request"))
	if absent:
		out.append({"kind": "absent", "dates": absent})
	overdue = frappe.get_all(
		"Employee Advance",
		filters={
			"employee": employee.name,
			"docstatus": 1,
			"custom_advance_type": "Expense Advance",
			"custom_clear_due_date": ("<", nowdate()),
			"status": ("in", ["Paid", "Partially Paid"]),
		},
		fields=["name", "custom_clear_due_date as due_date"],
	)
	if overdue:
		out.append({"kind": "overdue_clearing", "count": len(overdue), "due_date": overdue[0].due_date})
	week = next_week_unbooked(employee)
	if week:
		out.append({"kind": "book_shift", "week_start": week})
	for row in expiring_leaves(employee):
		out.append({"kind": "leave_expiring", **row})
	if not checkin["location"]:
		out.append({"kind": "no_location", "text": checkin["location_issue"]})
	return out


@frappe.whitelist()
def get_home(month=None):
	"""หน้าแรกของ Self Service: ลงเวลาวันนี้ + ปฏิทินเดือน + สรุปปี + รายการรออนุมัติ + สิ่งที่ควรทำ"""
	employee = self_service.my_employee()
	month = month_or_now(month)
	checkin = self_service.get_checkin_data()
	calendar = month_payload(employee, month)
	return {
		**checkin,
		"first_name": frappe.db.get_value("Employee", employee.name, "first_name") or employee.employee_name,
		"calendar": calendar,
		"year": year_totals(employee),
		"pending": my_pending(employee),
		"suggestions": suggestions(employee, checkin, calendar),
		"request_days": ATTENDANCE_REQUEST_DAYS,
		"today": nowdate(),
	}


def month_payload(employee, month):
	"""ปฏิทินเดือน + ลงเวลา/คำขอของเดือนนั้น (แผงรายวัน)"""
	calendar = month_calendar(employee, month)
	end = getdate(calendar["end"])
	rows = self_service.checkin_rows(employee.name, calendar["start"])
	calendar["logs"] = [dict(r, has_selfie=bool(r.pop("custom_selfie"))) for r in rows if getdate(r.time) <= end]
	calendar["requests"] = my_requests(employee, calendar["start"], calendar["end"])
	return calendar


@frappe.whitelist()
def get_month(month=None):
	"""ปฏิทินเดือนอื่น (เลื่อนเดือนในหน้าแรก)"""
	return month_payload(self_service.my_employee(), month_or_now(month))


# ---------------------------------------------------------------- แจ้งมาทำงาน (Attendance Request)


def my_requests(employee, start=None, end=None):
	filters = {"employee": employee.name, "docstatus": ("<", 2)}
	if start and end:
		filters.update(from_date=("<=", end), to_date=(">=", start))
	rows = frappe.get_all(
		"Attendance Request", filters=filters, fields=REQUEST_FIELDS, order_by="from_date desc", limit_page_length=self_service.LIST_LIMIT
	)
	for row in rows:
		row.can_delete = row.docstatus == 0
	return rows


@frappe.whitelist()
def get_attendance_requests():
	return my_requests(self_service.my_employee())


def check_request_days(employee, from_date, to_date, own=None):
	"""วันที่แจ้งมาทำงานได้: มีพนักงานอยู่ ยังไม่ออกสลิป ไม่มีใบลาอนุมัติ ไม่มี Attendance อื่นนอกจากขาด"""
	day = from_date
	while day <= to_date:
		label = frappe.format(day, "Date")
		slip = frappe.db.get_value(
			"Salary Slip", {"employee": employee, "docstatus": 1, "start_date": ("<=", day), "end_date": (">=", day)}
		)
		if slip:
			frappe.throw(_("วันที่ {0} ออกสลิปเงินเดือนแล้ว ติดต่อฝ่ายบุคคล").format(label))
		attendance = frappe.db.get_value(
			"Attendance",
			{"employee": employee, "attendance_date": day, "docstatus": 1},
			["status", "leave_type", "attendance_request"],
			as_dict=True,
		)
		if attendance and (attendance.status != "Absent" or attendance.leave_type):
			if not own or attendance.attendance_request != own:
				frappe.throw(_("วันที่ {0} บันทึกการเข้างานแล้ว ไม่ต้องแจ้ง").format(label))
		day = add_days(day, 1)


@frappe.whitelist(methods=["POST"])
def request_attendance(from_date, to_date=None, reason="On Duty", explanation=None, half_day=0, half_day_date=None):
	"""แจ้งมาทำงาน (ไม่ได้ลงเวลา) ส่งให้ผู้อนุมัติใบลาในขอบเขต (Role Leave Approver)"""
	employee = self_service.my_employee()
	from_date = getdate(from_date)
	to_date = getdate(to_date or from_date)
	explanation = (explanation or "").strip()
	if reason not in REQUEST_REASONS:
		frappe.throw(_("ประเภทการแจ้งไม่ถูกต้อง"))
	if not explanation:
		frappe.throw(_("ระบุรายละเอียด เช่น ทำงานที่ไหน ทำไมจึงไม่ได้ลงเวลา"))
	if to_date < from_date:
		frappe.throw(_("วันที่สิ้นสุดต้องไม่ก่อนวันเริ่ม"))
	today = getdate()
	if to_date > today:
		frappe.throw(_("แจ้งได้ถึงวันนี้ (วันข้างหน้าให้ลงเวลาตามปกติ)"))
	if date_diff(today, from_date) > ATTENDANCE_REQUEST_DAYS:
		frappe.throw(_("แจ้งย้อนหลังได้ไม่เกิน {0} วัน ติดต่อฝ่ายบุคคล").format(ATTENDANCE_REQUEST_DAYS))
	half_day = cint(half_day)
	half_day_date = getdate(half_day_date or from_date) if half_day else None
	if half_day and not from_date <= half_day_date <= to_date:
		frappe.throw(_("วันที่ครึ่งวันต้องอยู่ในช่วงที่แจ้ง"))
	check_request_days(employee.name, from_date, to_date)
	# ใบที่ไม่อนุมัติของตัวเองที่ทับช่วงนี้: ลบก่อน (HRMS ห้ามคำขอทับกัน) ผลไม่อนุมัติอยู่ในการแจ้งเตือนแล้ว
	for name in frappe.get_all(
		"Attendance Request",
		filters={
			"employee": employee.name,
			"docstatus": 0,
			"custom_approval_status": "Rejected",
			"from_date": ("<=", to_date),
			"to_date": (">=", from_date),
		},
		pluck="name",
	):
		frappe.delete_doc("Attendance Request", name, ignore_permissions=True)
	doc = frappe.get_doc(
		{
			"doctype": "Attendance Request",
			"employee": employee.name,
			"company": employee.company,
			"from_date": from_date,
			"to_date": to_date,
			"half_day": half_day,
			"half_day_date": half_day_date,
			"reason": reason,
			"explanation": explanation,
			"custom_approval_status": "Pending",
		}
	)
	doc.insert(ignore_permissions=True)
	self_advance.notify_users(
		self_service.approvers_of(employee.name), doc, _("{0} แจ้งมาทำงาน ขอให้อนุมัติ").format(employee.employee_name)
	)
	return {"name": doc.name}


def own_request(name):
	employee = self_service.my_employee()
	doc = frappe.get_doc("Attendance Request", name)
	if doc.employee != employee.name:
		frappe.throw(_("ไม่พบคำขอนี้"), frappe.PermissionError)
	return doc


@frappe.whitelist(methods=["POST"])
def delete_attendance_request(name):
	"""ถอนคำขอที่ยังไม่อนุมัติ (รวมใบที่ไม่อนุมัติ)"""
	doc = own_request(name)
	if doc.docstatus != 0:
		frappe.throw(_("คำขอนี้อนุมัติแล้ว ถอนไม่ได้ ติดต่อฝ่ายบุคคล"))
	frappe.delete_doc("Attendance Request", doc.name, ignore_permissions=True)


def request_filters(pending=True):
	"""รออนุมัติ = ร่างของพนักงานในขอบเขตที่ยังไม่ถูกปฏิเสธ / พิจารณาแล้ว = HISTORY_DAYS วัน (ของผู้ใช้ / HR ทุกคน)"""
	if pending:
		return self_service.scope_filters({"docstatus": 0, "custom_approval_status": ("!=", "Rejected")})
	filters = {
		"custom_approval_status": ("in", ["Approved", "Rejected"]),
		"modified": (">=", add_days(nowdate(), -self_service.HISTORY_DAYS)),
	}
	if not self_service.is_hr():
		filters["custom_reviewed_by"] = frappe.session.user
	return filters


def approval_rows(pending=True):
	if not self_service.is_approver():
		return []
	return frappe.get_all(
		"Attendance Request",
		filters=request_filters(pending),
		fields=[*REQUEST_FIELDS, "employee", "employee_name", "custom_reviewed_by as reviewed_by", "modified"],
		order_by="from_date asc" if pending else "modified desc",
		limit_page_length=200,
	)


@frappe.whitelist(methods=["POST"])
def review_attendance_request(name, approve, reason=None):
	"""อนุมัติ = Submit (HRMS สร้าง/แก้ Attendance ของแต่ละวัน) ไม่อนุมัติ = คงร่าง + เหตุผล อนุมัติของตัวเองไม่ได้"""
	doc = frappe.get_doc("Attendance Request", name)
	if not self_service.can_approve_employee(doc.employee):
		frappe.throw(_("ไม่มีสิทธิ์อนุมัติคำขอนี้"), frappe.PermissionError)
	user = frappe.db.get_value("Employee", doc.employee, "user_id")
	if user == frappe.session.user:
		frappe.throw(_("อนุมัติคำขอของตัวเองไม่ได้"), frappe.PermissionError)
	if doc.docstatus != 0 or doc.custom_approval_status == "Rejected":
		frappe.throw(_("คำขอนี้พิจารณาแล้ว"))
	approve = cint(approve)
	reason = (reason or "").strip()
	if not approve and not reason:
		frappe.throw(_("ระบุเหตุผลที่ไม่อนุมัติ"))
	doc.custom_approval_status = "Approved" if approve else "Rejected"
	doc.custom_reviewed_by = frappe.session.user
	doc.custom_review_note = reason or None
	doc.flags.ignore_permissions = True
	if approve:
		check_request_days(doc.employee, getdate(doc.from_date), getdate(doc.to_date), own=doc.name)
		doc.submit()
	else:
		doc.save()
	self_advance.notify_users(
		[user],
		doc,
		(_("แจ้งมาทำงาน {0} อนุมัติแล้ว") if approve else _("แจ้งมาทำงาน {0} ไม่ได้รับอนุมัติ: {1}")).format(
			frappe.format(doc.from_date, "Date"), reason
		),
	)
	return doc.custom_approval_status


# ---------------------------------------------------------------- เงินเดือน


def salary_rows(employee):
	return frappe.get_all(
		"Salary Structure Assignment",
		filters={"employee": employee, "docstatus": 1},
		fields=["name", "from_date", "base", "salary_structure"],
		order_by="from_date desc",
		limit_page_length=20,
	)


def year_to_date(employee, year):
	"""เงินได้สะสม (gross) และประกันสังคมสะสม (รายการหักตัวย่อ SSO_ABBR) ของสลิปที่ Submit ในปี (ตามวันเริ่มงวด)"""
	slips = frappe.get_all(
		"Salary Slip",
		filters={"employee": employee, "docstatus": 1, "start_date": ("between", [f"{year}-01-01", f"{year}-12-31"])},
		fields=["name", "gross_pay", "net_pay"],
		limit_page_length=0,
	)
	names = [s.name for s in slips] or [""]
	sso = frappe.get_all(
		"Salary Detail",
		filters={"parenttype": "Salary Slip", "parent": ("in", names), "parentfield": "deductions", "abbr": SSO_ABBR},
		fields=["amount"],
		limit_page_length=0,
	)
	return {
		"slips": len(slips),
		"gross": sum(flt(s.gross_pay) for s in slips),
		"net": sum(flt(s.net_pay) for s in slips),
		"sso": sum(flt(r.amount) for r in sso),
	}


def sso_total(employee):
	"""ประกันสังคมที่หักทั้งหมดในระบบ (ทุกปี)"""
	slips = frappe.get_all("Salary Slip", filters={"employee": employee, "docstatus": 1}, pluck="name", limit_page_length=0)
	if not slips:
		return 0
	return sum(
		flt(r.amount)
		for r in frappe.get_all(
			"Salary Detail",
			filters={"parenttype": "Salary Slip", "parent": ("in", slips), "parentfield": "deductions", "abbr": SSO_ABBR},
			fields=["amount"],
			limit_page_length=0,
		)
	)


@frappe.whitelist()
def get_pay():
	"""หน้าเงินเดือน: ค่าจ้างปัจจุบัน + ที่จะปรับ + สะสมของปี + สลิป"""
	employee = self_service.my_employee()
	today = getdate()
	rows = salary_rows(employee.name)
	current = next((r for r in rows if getdate(r.from_date) <= today), None)
	upcoming = sorted((r for r in rows if getdate(r.from_date) > today), key=lambda r: r.from_date)
	previous = next((r for r in rows if current and getdate(r.from_date) < getdate(current.from_date)), None)
	return {
		"current": current and {"base": current.base, "from_date": current.from_date},
		"previous": previous and {"base": previous.base, "from_date": previous.from_date},
		"upcoming": [{"base": r.base, "from_date": r.from_date, "change": flt(r.base) - flt(current.base if current else 0)} for r in upcoming],
		"year": today.year,
		"ytd": year_to_date(employee.name, today.year),
		"last_year": year_to_date(employee.name, today.year - 1),
		"sso_total": sso_total(employee.name),
		"slips": self_service.get_slips(),
	}
