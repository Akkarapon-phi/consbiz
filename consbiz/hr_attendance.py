# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

"""สรุปวันทำงาน (หมวด hr ของแอปออฟฟิศ /conserp/hr, หน้า hr-attendance) ตกลง 2026-11-11

Payroll คิดตาม Attendance ของ HRMS (Payroll Settings payroll_based_on = Attendance) หน้านี้สรุปการลงเวลา
(Employee Checkin) วันหยุด ใบลา วันหยุดประจำสัปดาห์ (Weekly Day Off) ของแต่ละคนรายวัน แล้วสร้าง Attendance ให้

สถานะของวัน (day_state):
- marked   มี Attendance (Submit) แล้ว ใช้ค่านั้นเสมอ (รวม On Leave ที่ HRMS สร้างตอนอนุมัติใบลา)
- holiday  วันหยุดใน Holiday List ของพนักงาน (หรือของบริษัท) ไม่สร้าง Attendance
- day_off  วันหยุดประจำสัปดาห์ ไม่สร้าง Attendance
           สัปดาห์ที่ไม่ได้ลง Weekly Day Off: เสาร์/อาทิตย์ที่ไม่ได้ลงเวลา = วันหยุด (อาทิตย์ก่อน) อีกวันคิดตามปกติ
ชั่วโมงทำงาน (work_hours) = ช่วงเข้าครั้งแรก-ออกครั้งสุดท้าย ที่อยู่ในเวลางาน WORK_START-WORK_END หักพักเที่ยง LUNCH
ตกลง 2026-11-11 (พ.ร.บ.คุ้มครองแรงงาน ม.76 ห้ามตัดครึ่งวันเพราะสาย: ไม่จ่ายได้เฉพาะเวลาที่ไม่ได้ทำงานจริง):
- สาย (late) = นาทีทำงานตั้งแต่ 08:00 ถึงเวลาเข้า เข้าไม่เกิน LATE_GRACE (08:05) = ไม่สาย เกินแล้วนับจาก 08:00 (08:10 = 10 นาที)
- กลับก่อน (early) = นาทีทำงานจากเวลาออกถึง 17:00 ไม่มีผ่อนผัน อยู่เกิน 17:00 ไม่นับ OT (ยังไม่มีนโยบาย)
- ค่าจ้างเต็มเสมอ นาทีสาย/กลับก่อนบันทึกไว้ทางวินัย (Attendance late_entry / early_exit)
  สายเกินเหตุหรือบ่อย HR สั่ง "ไม่จ่ายเวลาที่ไม่ได้ทำงาน" รายเดือน (set_unpaid_time) = Additional Salary
  ค่าจ้างต่อนาที = เงินเดือน (base ของ Salary Structure Assignment) ÷ 30 ÷ 8 ÷ 60
- present  ลงเวลาเข้าและออก ทำงาน ≥ HALF_DAY_HOURS ชม. = มาทำงาน (ไม่ตัดครึ่งวัน)
- absent   วันทำงานที่ไม่มีการลงเวลาเลย = ขาดงาน
- flag     HR ต้องตัดสิน (decide_days): มีรายการรอยืนยัน / มีใบลารออนุมัติ / ลงเข้าหรือออกอย่างเดียว /
           ทำงานน้อยกว่า HALF_DAY_HOURS / ทั้งช่วงไม่มีการลงเวลาเลย (อาจไม่ได้ใช้แอป แนะนำมาทำงาน)
- future   วันนี้หรือหลังจากนี้ ยังไม่สรุป
- inactive ยังไม่เริ่มงาน / ลาออกแล้ว
รายการลงเวลาที่ไม่ได้รับยืนยัน (Rejected) ไม่นับ ส่วนการลงเวลาในวันหยุดแสดงเป็นข้อมูล (ยังไม่คิด OT)

บันทึก Attendance (close_period) = สร้างของวัน present/absent ทั้งหมดถึงเมื่อวาน ต้องตัดสินวัน flag ให้ครบก่อน
แก้ Attendance ที่สร้างแล้ว: decide_days ยกเลิกของเดิมแล้วสร้างใหม่ (ยกเว้นวันลา และงวดที่ออกสลิปแล้ว)
"""

from datetime import datetime, time, timedelta

import frappe
from frappe import _
from frappe.utils import add_days, cint, get_datetime, get_first_day, get_last_day, getdate, nowdate

from consbiz import self_service

WORK_START = time(8, 0)
WORK_END = time(17, 0)
LUNCH = (time(12, 0), time(13, 0))
LATE_GRACE = time(8, 5)
FULL_DAY_HOURS = 8
HALF_DAY_HOURS = 4
DAYS_PER_MONTH = 30
AUTO_STATUS = {"present": "Present", "absent": "Absent"}
DECISIONS = ("Present", "Half Day", "Absent")
# ไม่หักเงิน (ตักเตือน) = ช่องติ๊กแยกจากสถานะ (ตกลง 2026-11-11): HRMS หักเงินตามสถานะ จึงบันทึกเป็น Present เพื่อจ่ายค่าจ้าง
# สถานะจริงเก็บใน Attendance.custom_waived_status หน้าสรุปแสดงสถานะจริง + ป้ายไม่หัก ขาดบ่อยเกิน HR สั่งหักจริง (charge_waived)
WAIVABLE = ("Absent", "Half Day")
# ปิดครั้งละไม่เกินนี้ (Attendance ต่อคำขอ) เกินให้แบ่งตามโครงการ
CLOSE_LIMIT = 3000
WEEKEND = {5: "Saturday", 6: "Sunday"}


# ---------------------------------------------------------------- สิทธิ์


def can_manage(user=None):
	"""HR ที่สร้าง/Submit Attendance ได้"""
	return self_service.is_hr(user) and bool(frappe.has_permission("Attendance", "submit", user=user))


def hr_sections():
	return ["hr"] if can_manage() else []


def require_hr():
	if not can_manage():
		frappe.throw(_("เฉพาะฝ่ายบุคคล (HR) เท่านั้น"), frappe.PermissionError)


# ---------------------------------------------------------------- ข้อมูลดิบของช่วง


def period_of(month):
	"""'2026-11' / '2026-11-05' → (วันแรก, วันสุดท้าย) ของเดือน"""
	day = getdate(f"{month}-01" if len(str(month)) == 7 else month)
	return get_first_day(day), get_last_day(day)


def employees_of(company, start, end, project=None):
	filters = {"company": company, "date_of_joining": ("<=", end)}
	if project:
		filters["custom_project"] = project
	rows = frappe.get_all(
		"Employee",
		filters=filters,
		or_filters={"status": "Active", "relieving_date": (">=", start)},
		fields=[
			"name",
			"employee_name",
			"department",
			"designation",
			"custom_project as project",
			"date_of_joining",
			"relieving_date",
			"holiday_list",
			"user_id",
		],
		order_by="employee_name asc",
		limit_page_length=0,
	)
	return [r for r in rows if not r.relieving_date or getdate(r.relieving_date) >= start]


def group_by_employee(rows):
	out = {}
	for row in rows:
		out.setdefault(row.employee, []).append(row)
	return out


def load_period(employees, start, end):
	names = [e.name for e in employees] or [""]
	end_time = f"{end} 23:59:59"
	checkins = frappe.get_all(
		"Employee Checkin",
		filters={"employee": ("in", names), "time": ("between", [f"{start} 00:00:00", end_time])},
		fields=["name", "employee", "log_type", "time", "custom_approval_status as approval"],
		order_by="time asc",
		limit_page_length=0,
	)
	attendance = frappe.get_all(
		"Attendance",
		filters={"employee": ("in", names), "docstatus": 1, "attendance_date": ("between", [start, end])},
		fields=["name", "employee", "attendance_date", "status", "leave_type", "half_day_status", "owner", "custom_waived_status"],
		limit_page_length=0,
	)
	open_leaves = frappe.get_all(
		"Leave Application",
		filters={
			"employee": ("in", names),
			"docstatus": 0,
			"status": "Open",
			"from_date": ("<=", end),
			"to_date": (">=", start),
		},
		fields=["name", "employee", "from_date", "to_date", "leave_type"],
		limit_page_length=0,
	)
	# วันหยุดประจำสัปดาห์: รวมสัปดาห์ที่คร่อมต้น/ท้ายเดือน
	day_offs = frappe.get_all(
		"Weekly Day Off",
		filters={"employee": ("in", names), "week_start": ("between", [add_days(start, -6), end])},
		fields=["employee", "week_start", "off_date"],
		limit_page_length=0,
	)
	return {
		"checkins": group_by_employee(checkins),
		"attendance": {(a.employee, getdate(a.attendance_date)): a for a in attendance},
		"open_leaves": group_by_employee(open_leaves),
		"day_offs": {(d.employee, getdate(d.week_start)): getdate(d.off_date) for d in day_offs},
		"holidays": {},
	}


def holidays_of(data, employee, start, end):
	from hrms.utils.holiday_list import get_holiday_list_for_employee

	# HRMS v16: Holiday List Assignment (ของพนักงาน > ของบริษัท) ไม่มีจึงใช้ช่องเดิมของพนักงาน
	holiday_list = (
		get_holiday_list_for_employee(employee.name, raise_exception=False, as_on=start) or employee.holiday_list
	)
	if not holiday_list:
		return set()
	key = (holiday_list, start, end)
	if key not in data["holidays"]:
		data["holidays"][key] = {
			getdate(d)
			for d in frappe.get_all(
				"Holiday",
				filters={"parent": holiday_list, "holiday_date": ("between", [start, end])},
				pluck="holiday_date",
			)
		}
	return data["holidays"][key]


# ---------------------------------------------------------------- สถานะรายวัน


def week_start_of(day):
	return day - timedelta(days=day.weekday())


def work_hours(first_in, last_out):
	"""ชั่วโมงทำงานที่นับ: เฉพาะช่วงในเวลางาน หักพักเที่ยงที่ทับช่วงนั้น (มาก่อน 8 โมง/อยู่เกิน 5 โมงเย็นไม่นับเพิ่ม)"""
	day = first_in.date()
	at = lambda t: datetime.combine(day, t)  # noqa: E731
	start, end = max(first_in, at(WORK_START)), min(last_out, at(WORK_END))
	if end <= start:
		return 0
	lunch = max(timedelta(0), min(end, at(LUNCH[1])) - max(start, at(LUNCH[0])))
	return round((end - start - lunch).total_seconds() / 3600, 2)


def work_minutes(start, end):
	"""นาทีทำงานตามเวลางานระหว่างสองเวลา (หักพักเที่ยง) ปัดวินาทีทิ้ง"""
	start, end = start.replace(second=0, microsecond=0), end.replace(second=0, microsecond=0)
	return round(work_hours(start, end) * 60) if end > start else 0


def late_minutes(first_in):
	if not first_in or first_in.replace(second=0, microsecond=0).time() <= LATE_GRACE:
		return 0
	return work_minutes(datetime.combine(first_in.date(), WORK_START), first_in)


def early_minutes(last_out):
	if not last_out:
		return 0
	return work_minutes(last_out, datetime.combine(last_out.date(), WORK_END))


def summarize_logs(logs):
	"""รายการลงเวลาของวัน → (เข้าครั้งแรก, ออกครั้งสุดท้าย, ชั่วโมง, มีรอยืนยัน) ไม่นับที่ไม่ได้รับยืนยัน"""
	counted = [l for l in logs if l.approval != "Rejected"]
	pending = any(l.approval == "Pending" for l in counted)
	ins = [get_datetime(l.time) for l in counted if l.log_type == "IN"]
	outs = [get_datetime(l.time) for l in counted if l.log_type == "OUT"]
	first_in = min(ins) if ins else None
	last_out = max(outs) if outs else None
	hours = None
	if first_in and last_out and last_out > first_in:
		hours = work_hours(first_in, last_out)
	return first_in, last_out, hours, pending, bool(counted)


def day_offs_of(data, employee, days_logged, start, end):
	"""วันหยุดประจำสัปดาห์ของช่วง: ที่ลงไว้ + สัปดาห์ที่ไม่ได้ลง = เสาร์/อาทิตย์ที่ไม่ได้ลงเวลา (อาทิตย์ก่อน)"""
	out = {}
	week = week_start_of(start)
	while week <= end:
		booked = data["day_offs"].get((employee, week))
		if booked:
			out[booked] = "booked"
		else:
			for day in (week + timedelta(days=6), week + timedelta(days=5)):
				if day not in days_logged:
					out[day] = "default"
					break
		week += timedelta(days=7)
	return out


def employee_days(employee, data, start, end, today):
	logs_by_day = {}
	for log in data["checkins"].get(employee.name, []):
		logs_by_day.setdefault(getdate(log.time), []).append(log)
	logged = {day for day, logs in logs_by_day.items() if any(l.approval != "Rejected" for l in logs)}
	holidays = holidays_of(data, employee, start, end)
	day_offs = day_offs_of(data, employee.name, logged, start, end)
	open_leaves = data["open_leaves"].get(employee.name, [])
	# ทั้งช่วง (ถึงเมื่อวาน) ไม่มีการลงเวลาเลย: อาจไม่ได้ใช้แอป ให้ HR ตัดสินแทนการตัดขาดทั้งเดือน
	never = not any(day < today for day in logged)
	joined = getdate(employee.date_of_joining)
	relieved = employee.relieving_date and getdate(employee.relieving_date)

	days = {}
	day = start
	while day <= end:
		logs = logs_by_day.get(day, [])
		first_in, last_out, hours, pending, has_logs = summarize_logs(logs)
		cell = {"in": first_in and first_in.strftime("%H:%M"), "out": last_out and last_out.strftime("%H:%M")}
		if hours is not None:
			cell["hours"] = hours
		if late_minutes(first_in):
			cell["late"] = late_minutes(first_in)
		if early_minutes(last_out) and first_in and last_out > first_in:
			cell["early"] = early_minutes(last_out)
		attendance = data["attendance"].get((employee.name, day))
		leave = next(
			(l for l in open_leaves if getdate(l.from_date) <= day <= getdate(l.to_date)), None
		)
		if day < joined or (relieved and day > relieved):
			cell["s"] = "inactive"
		elif attendance:
			cell.update(
				s="marked",
				status=attendance.status,
				attendance=attendance.name,
				leave_type=attendance.leave_type,
			)
			if attendance.custom_waived_status:
				cell.update(status=attendance.custom_waived_status, waived=1)
		elif day in holidays:
			cell["s"] = "holiday"
		elif day in day_offs:
			cell["s"] = "day_off"
			if day_offs[day] == "default":
				cell["note"] = _("ไม่ได้ลงวันหยุด ถือเป็นวันหยุดประจำสัปดาห์")
		elif day >= today:
			cell["s"] = "future"
		elif leave:
			cell.update(s="flag", suggest=None, note=_("มีใบลารออนุมัติ ({0})").format(leave.leave_type))
		elif pending:
			cell.update(s="flag", suggest=None, note=_("มีการลงเวลารอยืนยัน"))
		elif not has_logs:
			if never:
				cell.update(s="flag", suggest="Present", note=_("ไม่มีการลงเวลาทั้งช่วง (อาจไม่ได้ใช้แอป)"))
			else:
				cell["s"] = "absent"
		elif not last_out:
			cell.update(s="flag", suggest=None, note=_("ลงเวลาเข้าอย่างเดียว ไม่มีเวลาออก"))
		elif not first_in:
			cell.update(s="flag", suggest=None, note=_("ลงเวลาออกอย่างเดียว ไม่มีเวลาเข้า"))
		elif (hours or 0) >= HALF_DAY_HOURS:
			cell["s"] = "present"
		else:
			cell.update(
				s="flag",
				suggest=None,
				note=_("ทำงาน {0} ชม. น้อยกว่าครึ่งวัน ({1} ชม.)").format(hours or 0, HALF_DAY_HOURS),
			)
		if has_logs and cell["s"] in ("holiday", "day_off"):
			cell["worked"] = 1
			cell.pop("late", None)
			cell.pop("early", None)
		days[str(day)] = cell
		day += timedelta(days=1)
	return days


def totals_of(days):
	totals = {
		"present": 0,
		"half": 0,
		"absent": 0,
		"waived": 0,
		"leave": 0,
		"flag": 0,
		"off": 0,
		"late_count": 0,
		"late_min": 0,
		"early_count": 0,
		"early_min": 0,
	}
	for cell in days.values():
		# นาทีสาย/กลับก่อนนับเฉพาะวันที่นับว่ามาทำงาน (วันลา/ขาด/วันหยุดไม่นับ)
		if cell["s"] == "present" or cell.get("status") in ("Present", "Work From Home"):
			for key in ("late", "early"):
				if cell.get(key):
					totals[f"{key}_count"] += 1
					totals[f"{key}_min"] += cell[key]
		state = cell["s"]
		status = cell.get("status")
		if cell.get("waived"):
			totals["waived"] += 1
		elif state == "present" or status in ("Present", "Work From Home"):
			totals["present"] += 1
		elif status == "Half Day":
			totals["leave" if cell.get("leave_type") else "half"] += 1
		elif state == "absent" or status == "Absent":
			totals["absent"] += 1
		elif status == "On Leave":
			totals["leave"] += 1
		elif state == "flag":
			totals["flag"] += 1
		elif state in ("holiday", "day_off"):
			totals["off"] += 1
	return totals


def build(company, month, project=None, employee=None):
	start, end = period_of(month)
	employees = employees_of(company, start, end, project)
	if employee:
		employees = [e for e in employees if e.name == employee]
	data = load_period(employees, start, end)
	today = getdate()
	rows = []
	for emp in employees:
		days = employee_days(emp, data, start, end, today)
		rows.append(
			{
				"employee": emp.name,
				"employee_name": emp.employee_name,
				"department": emp.department,
				"designation": emp.designation,
				"project": emp.project,
				"days": days,
				"totals": totals_of(days),
			}
		)
	return start, end, rows


# ---------------------------------------------------------------- API


def default_company(company=None):
	company = company or frappe.defaults.get_user_default("Company")
	if not company:
		frappe.throw(_("เลือกบริษัทก่อน"))
	return company


@frappe.whitelist()
def get_summary_month(month=None, company=None, project=None):
	"""ตารางสรุปวันทำงานของเดือน: แถว = พนักงาน, ช่อง = วัน"""
	require_hr()
	company = default_company(company)
	start, end, rows = build(company, month or nowdate()[:7], project)
	return {
		"company": company,
		"start": start,
		"end": end,
		"today": nowdate(),
		"rows": rows,
		"payroll_based_on": frappe.db.get_single_value("Payroll Settings", "payroll_based_on"),
		"half_day_hours": HALF_DAY_HOURS,
		"late_grace": LATE_GRACE.strftime("%H:%M"),
		"projects": dict(
			frappe.get_all(
				"Project",
				filters={"name": ("in", list({r["project"] for r in rows if r["project"]}) or [""])},
				fields=["name", "project_name"],
				as_list=True,
			)
		),
	}


@frappe.whitelist()
def get_summary(project=None, company=None):
	"""ตัวเลขบนเมนู: วันที่รอ HR ตัดสินของเดือนนี้"""
	if not can_manage():
		return {}
	company = company or frappe.defaults.get_user_default("Company")
	if not company:
		return {}
	_start, _end, rows = build(company, nowdate()[:7], project)
	return {"flag": sum(r["totals"]["flag"] for r in rows)}


@frappe.whitelist()
def get_day(employee, date):
	"""รายละเอียดของวัน: รายการลงเวลา ใบลา Attendance สถานะที่คำนวณ"""
	require_hr()
	day = getdate(date)
	company = frappe.db.get_value("Employee", employee, "company")
	_start, _end, rows = build(company, str(day), employee=employee)
	if not rows:
		frappe.throw(_("ไม่พบพนักงาน"), frappe.DoesNotExistError)
	cell = rows[0]["days"][str(day)]
	logs = frappe.get_all(
		"Employee Checkin",
		filters={"employee": employee, "time": ("between", [f"{day} 00:00:00", f"{day} 23:59:59"])},
		fields=[
			"name",
			"log_type",
			"time",
			"device_id",
			"custom_distance as distance",
			"custom_reason as reason",
			"custom_manual as manual",
			"custom_selfie",
			"custom_approval_status as approval",
			"custom_review_note as review_note",
		],
		order_by="time asc",
	)
	for log in logs:
		log.has_selfie = bool(log.pop("custom_selfie"))
	leaves = frappe.get_all(
		"Leave Application",
		filters={"employee": employee, "docstatus": ("<", 2), "from_date": ("<=", day), "to_date": (">=", day)},
		fields=["name", "leave_type", "status", "docstatus", "half_day", "half_day_date"],
	)
	attendance = cell.get("attendance") and frappe.db.get_value(
		"Attendance",
		cell["attendance"],
		["name", "status", "leave_type", "half_day_status", "owner", "modified"],
		as_dict=True,
	)
	return {
		"employee": employee,
		"employee_name": rows[0]["employee_name"],
		"date": day,
		"cell": cell,
		"logs": logs,
		"leaves": leaves,
		"attendance": attendance,
		"locked": locked_reason(employee, day),
	}


def locked_reason(employee, day):
	"""แก้ Attendance ของวันนี้ไม่ได้เพราะ: ออกสลิป (Submit) งวดนั้นแล้ว / ยังไม่ถึงวัน"""
	if getdate(day) >= getdate():
		return _("ยังไม่ถึงวัน")
	slip = frappe.db.get_value(
		"Salary Slip",
		{"employee": employee, "docstatus": 1, "start_date": ("<=", day), "end_date": (">=", day)},
		"name",
	)
	if slip:
		return _("ออกสลิปเงินเดือน {0} แล้ว ต้องยกเลิกสลิปก่อน").format(slip)
	return None


def drop_no_leave_alerts(start):
	"""HRMS แจ้ง "No leave record found" ทุกครั้งที่ครึ่งวันไม่มีใบลา (ตอน insert และ submit) ซึ่งเป็นกรณีปกติของการตัดสิน
	ครึ่งวันจากเวลาทำงาน จึงตัดเฉพาะข้อความนี้ที่เกิดหลังตำแหน่ง start ข้อความอื่นคงไว้"""
	log = frappe.local.message_log
	frappe.local.message_log = log[:start] + [m for m in log[start:] if "No leave record found" not in str(m)]


def make_attendance(employee, day, status, cell, note=None, company=None, waive=False):
	waive = bool(waive) and status in WAIVABLE
	doc = frappe.get_doc(
		{
			"doctype": "Attendance",
			"employee": employee,
			"attendance_date": day,
			"status": "Present" if waive else status,
			"custom_waived_status": status if waive else None,
			"company": company or frappe.db.get_value("Employee", employee, "company"),
			"half_day_status": "Absent" if status == "Half Day" and not waive else None,
		}
	)
	if cell.get("in"):
		doc.in_time = get_datetime(f"{day} {cell['in']}")
	if cell.get("out"):
		doc.out_time = get_datetime(f"{day} {cell['out']}")
	if cell.get("hours") is not None:
		doc.working_hours = cell["hours"]
	doc.late_entry = 1 if cell.get("late") else 0
	doc.early_exit = 1 if cell.get("early") else 0
	doc.flags.ignore_permissions = True
	before = len(frappe.local.message_log)
	doc.insert()
	doc.submit()
	drop_no_leave_alerts(before)
	if note:
		doc.add_comment("Comment", note)
	# ผูกรายการลงเวลาของวันกับ Attendance (แบบที่ HRMS ทำตอนสร้างจากกะ)
	checkin = frappe.qb.DocType("Employee Checkin")
	(
		frappe.qb.update(checkin)
		.set(checkin.attendance, doc.name)
		.where(
			(checkin.employee == employee)
			& (checkin.time >= f"{day} 00:00:00")
			& (checkin.time <= f"{day} 23:59:59")
			& ((checkin.custom_approval_status.isnull()) | (checkin.custom_approval_status != "Rejected"))
		)
	).run()
	return doc


def cancel_attendance(name):
	doc = frappe.get_doc("Attendance", name)
	doc.flags.ignore_permissions = True
	doc.cancel()
	checkin = frappe.qb.DocType("Employee Checkin")
	frappe.qb.update(checkin).set(checkin.attendance, None).where(checkin.attendance == name).run()


@frappe.whitelist(methods=["POST"])
def decide_days(employee, dates, status, note=None, waive=0):
	"""HR ตัดสินวัน (หลายวันของพนักงานคนเดียวได้): สร้าง Attendance ตามที่เลือก waive = ไม่หักเงิน (ขาด/ครึ่งวัน)
	วันที่มี Attendance อยู่แล้ว = ยกเลิกของเดิมแล้วสร้างใหม่ (วันลาและงวดที่ออกสลิปแล้วแก้ไม่ได้)"""
	require_hr()
	if status not in DECISIONS:
		frappe.throw(_("สถานะไม่ถูกต้อง"))
	dates = frappe.parse_json(dates) if isinstance(dates, str) else dates
	days = sorted({getdate(d) for d in (dates or [])})
	if not days:
		frappe.throw(_("เลือกวันก่อน"))
	note = (note or "").strip()
	waive = bool(cint(waive)) and status in WAIVABLE
	company = frappe.db.get_value("Employee", employee, "company")
	if not company:
		frappe.throw(_("ไม่พบพนักงาน"), frappe.DoesNotExistError)
	done = []
	for month in sorted({str(d)[:7] for d in days}):
		_start, _end, rows = build(company, month, employee=employee)
		cells = rows[0]["days"] if rows else {}
		for day in (d for d in days if str(d)[:7] == month):
			cell = cells.get(str(day))
			if not cell or cell["s"] in ("inactive", "future", "holiday", "day_off"):
				frappe.throw(_("วันที่ {0} ไม่ใช่วันทำงานที่บันทึกได้").format(frappe.format(day, "Date")))
			reason = locked_reason(employee, day)
			if reason:
				frappe.throw(_("วันที่ {0}: {1}").format(frappe.format(day, "Date"), reason))
			if cell["s"] == "marked":
				if cell.get("leave_type") or cell.get("status") == "On Leave":
					frappe.throw(
						_("วันที่ {0} เป็นวันลา แก้ที่ใบลา").format(frappe.format(day, "Date"))
					)
				if cell.get("status") == status and bool(cell.get("waived")) == waive:
					continue
				cancel_attendance(cell["attendance"])
			make_attendance(employee, day, status, cell, note, company, waive)
			done.append(str(day))
	return {"done": done}


@frappe.whitelist(methods=["POST"])
def close_period(month, company=None, project=None):
	"""บันทึก Attendance ของวันมาทำงาน/ครึ่งวัน/ขาดงานทั้งหมดถึงเมื่อวาน (วันที่ HR ตัดสินแล้วสร้างไว้ก่อนหน้า)
	ยังมีวันรอตัดสิน = บันทึกไม่ได้ ข้ามวันของงวดที่ออกสลิปแล้ว"""
	require_hr()
	company = default_company(company)
	_start, _end, rows = build(company, month, project)
	flagged = sum(r["totals"]["flag"] for r in rows)
	if flagged:
		frappe.throw(_("ยังมี {0} วันที่รอตัดสิน ตัดสินให้ครบก่อนบันทึก").format(flagged))
	todo = [
		(row["employee"], day, cell)
		for row in rows
		for day, cell in row["days"].items()
		if cell["s"] in AUTO_STATUS
	]
	if len(todo) > CLOSE_LIMIT:
		frappe.throw(_("รายการมากเกินไป ({0}) เลือกทีละโครงการ").format(len(todo)))
	created = skipped = 0
	slips = {}
	for employee, day, cell in todo:
		if employee not in slips:
			slips[employee] = frappe.get_all(
				"Salary Slip",
				filters={"employee": employee, "docstatus": 1, "end_date": (">=", _start), "start_date": ("<=", _end)},
				fields=["start_date", "end_date"],
			)
		if any(getdate(s.start_date) <= getdate(day) <= getdate(s.end_date) for s in slips[employee]):
			skipped += 1
			continue
		try:
			make_attendance(employee, day, AUTO_STATUS[cell["s"]], cell, company=company)
		except frappe.ValidationError as error:
			frappe.clear_messages()
			name = frappe.db.get_value("Employee", employee, "employee_name")
			frappe.throw(_("บันทึกของ {0} วันที่ {1} ไม่สำเร็จ: {2}").format(name, frappe.format(day, "Date"), error))
		created += 1
	return {"created": created, "skipped": skipped}


# ---------------------------------------------------------------- ไม่จ่ายเวลาที่ไม่ได้ทำงาน (No Work, No Pay)


def unpaid_component(company):
	return frappe.db.get_value("Company", company, "custom_unpaid_time_component")


def existing_unpaid(employee, component, start, end):
	if not component:
		return None
	return frappe.db.get_value(
		"Additional Salary",
		{
			"employee": employee,
			"salary_component": component,
			"docstatus": 1,
			"payroll_date": ("between", [start, end]),
		},
		["name", "amount", "payroll_date", "owner"],
		as_dict=True,
	)


def unpaid_info(employee, month):
	"""นาทีสาย/กลับก่อนของเดือน + ค่าจ้างต่อนาที + ยอดที่หักได้ + ใบหักที่มีอยู่"""
	from consbiz import self_advance

	company = frappe.db.get_value("Employee", employee, "company")
	if not company:
		frappe.throw(_("ไม่พบพนักงาน"), frappe.DoesNotExistError)
	start, end, rows = build(company, month, employee=employee)
	if not rows:
		frappe.throw(_("ไม่พบพนักงานในเดือนนี้"), frappe.DoesNotExistError)
	totals = rows[0]["totals"]
	minutes = totals["late_min"] + totals["early_min"]
	base = self_advance.base_salary(employee)
	per_minute = base / DAYS_PER_MONTH / FULL_DAY_HOURS / 60 if base else 0
	component = unpaid_component(company)
	slip = frappe.db.get_value(
		"Salary Slip",
		{"employee": employee, "docstatus": 1, "start_date": ("<=", end), "end_date": (">=", start)},
		"name",
	)
	return frappe._dict(
		company=company,
		start=start,
		end=end,
		row=rows[0],
		minutes=minutes,
		base=base,
		per_minute=round(per_minute, 4),
		amount=round(minutes * per_minute, 2),
		component=component,
		existing=existing_unpaid(employee, component, start, end),
		slip=slip,
	)


@frappe.whitelist()
def get_person(employee, month):
	require_hr()
	return unpaid_info(employee, month)


@frappe.whitelist(methods=["POST"])
def set_unpaid_time(employee, month, note=None):
	"""ไม่จ่ายค่าจ้างของนาทีสาย/กลับก่อนทั้งเดือน (HR ตัดสินเมื่อสายเกินเหตุหรือบ่อย) = Additional Salary (Submit)"""
	require_hr()
	info = unpaid_info(employee, month)
	if info.slip:
		frappe.throw(_("ออกสลิปเงินเดือน {0} ของงวดนี้แล้ว ต้องยกเลิกสลิปก่อน").format(info.slip))
	if not info.component:
		frappe.throw(_("ตั้งรายการหัก \"ไม่จ่ายเวลาที่ไม่ได้ทำงาน\" ที่บริษัท {0} ก่อน").format(info.company))
	if info.existing:
		frappe.throw(_("เดือนนี้หักไปแล้ว ({0})").format(info.existing.name))
	if not info.base:
		frappe.throw(_("พนักงานยังไม่มีโครงสร้างเงินเดือน (Salary Structure Assignment)"))
	if info.amount <= 0:
		frappe.throw(_("เดือนนี้ไม่มีเวลาที่ไม่ได้ทำงาน"))
	doc = frappe.get_doc(
		{
			"doctype": "Additional Salary",
			"employee": employee,
			"company": info.company,
			"salary_component": info.component,
			"amount": info.amount,
			"payroll_date": info.end,
			"currency": frappe.get_cached_value("Company", info.company, "default_currency"),
			"overwrite_salary_structure_amount": 0,
			"ref_doctype": "Employee",
			"ref_docname": employee,
		}
	)
	doc.flags.ignore_permissions = True
	doc.insert()
	doc.submit()
	t = info.row["totals"]
	doc.add_comment(
		"Comment",
		_("ไม่จ่ายเวลาที่ไม่ได้ทำงาน {0}: สาย {1} ครั้ง {2} นาที กลับก่อน {3} ครั้ง {4} นาที x {5} บาท/นาที{6}").format(
			month, t["late_count"], t["late_min"], t["early_count"], t["early_min"], info.per_minute,
			f" ({note.strip()})" if (note or "").strip() else "",
		),
	)
	return {"name": doc.name, "amount": doc.amount}


@frappe.whitelist(methods=["POST"])
def cancel_unpaid_time(employee, month):
	require_hr()
	info = unpaid_info(employee, month)
	if not info.existing:
		frappe.throw(_("เดือนนี้ยังไม่ได้หัก"))
	if info.slip:
		frappe.throw(_("ออกสลิปเงินเดือน {0} ของงวดนี้แล้ว ต้องยกเลิกสลิปก่อน").format(info.slip))
	doc = frappe.get_doc("Additional Salary", info.existing.name)
	doc.flags.ignore_permissions = True
	doc.cancel()
	return {"name": doc.name}


@frappe.whitelist(methods=["POST"])
def charge_waived(employee, month, note=None):
	"""หักเงินวันที่ยกเว้นไว้ทั้งเดือน (ขาดบ่อย/เกินเหตุ) = บันทึกเป็นสถานะจริง (ขาด/ครึ่งวัน) ระบบเงินเดือนจึงหัก"""
	require_hr()
	company = frappe.db.get_value("Employee", employee, "company")
	_start, _end, rows = build(company, month, employee=employee)
	waived = {d: c["status"] for d, c in (rows[0]["days"].items() if rows else []) if c.get("waived")}
	if not waived:
		frappe.throw(_("เดือนนี้ไม่มีวันที่ยกเว้นไม่หักเงิน"))
	done = []
	for status in sorted(set(waived.values())):
		days = [d for d, s in waived.items() if s == status]
		done += decide_days(employee, days, status, note or _("หักเงินวันที่เคยยกเว้น"))["done"]
	return {"done": done}
