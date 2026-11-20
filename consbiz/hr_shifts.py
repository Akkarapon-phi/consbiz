# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

"""กะ (หมวด hr ของแอปออฟฟิศ หน้า hr-shifts, office_app/views/hr/HrShifts.vue) ตกลง 2026-11-17

ครอบ DocType ของ HRMS:
- ตารางกะรายสัปดาห์: พนักงาน x วัน สถานะจาก hr_attendance.employee_days (กะของวัน วันหยุด/จองกะ ลา) ชุดเดียวกับหน้าเวลาทำงาน
- ประเภทกะ = Shift Type (เวลาเข้า-ออก, พัก custom_break_start/end, ผ่อนผันสาย late_entry_grace_period, สี color)
  กะข้ามเที่ยงคืนยังไม่รองรับ (ห้ามบันทึก)
- กำหนดกะ = Shift Assignment (Submit) ช่วงวันที่ (ไม่มีวันสิ้นสุดได้) ของเดิมที่ทับช่วง: เริ่มก่อน = ตัดวันสิ้นสุด,
  เริ่มในช่วง = Inactive (ส่วนที่เลยช่วงใหม่สร้างต่อให้) ไม่ใช้ = กะเริ่มต้นของพนักงาน (Employee.default_shift) > ของบริษัท
- จุดลงเวลา = Shift Location (ตั้ง/แก้ใช้ master_data.save_checkin_location ชุดเดียวกับฟอร์มโครงการ)
สิทธิ์ = HR ที่เข้าหมวดบุคคลได้ (hr_attendance.require_hr)
"""

import json

import frappe
from frappe import _
from frappe.utils import add_days, cint, getdate, nowdate

from consbiz import hr_attendance

TYPE_FIELDS = ["name", "start_time", "end_time", "custom_break_start", "custom_break_end", "late_entry_grace_period", "color"]


def time_text(value):
	t = hr_attendance.to_time(value)
	return t.strftime("%H:%M") if t else None


def type_rows():
	rows = frappe.get_all("Shift Type", fields=TYPE_FIELDS, order_by="start_time asc, name asc", limit_page_length=200)
	from collections import Counter

	defaults = Counter(
		frappe.get_all("Employee", filters={"status": "Active", "default_shift": ("is", "set")}, pluck="default_shift")
	)
	active = Counter(
		shift
		for _employee, shift in {
			(r.employee, r.shift_type)
			for r in frappe.get_all(
				"Shift Assignment",
				filters={"docstatus": 1, "status": "Active", "start_date": ("<=", nowdate())},
				or_filters=[["end_date", "is", "not set"], ["end_date", ">=", nowdate()]],
				fields=["employee", "shift_type"],
				limit_page_length=0,
			)
		}
	)
	out = []
	for row in rows:
		shift = hr_attendance.shift_type(row.name)
		out.append(
			{
				"name": row.name,
				"start": time_text(row.start_time),
				"end": time_text(row.end_time),
				"break_start": time_text(row.custom_break_start),
				"break_end": time_text(row.custom_break_end),
				"grace": cint(row.late_entry_grace_period),
				"color": row.color,
				"hours": shift.hours if shift else None,
				"usable": bool(shift),
				"default_people": defaults.get(row.name, 0),
				"assigned_people": active.get(row.name, 0),
			}
		)
	return out


@frappe.whitelist()
def get_shifts(week_start=None, company=None, project=None):
	"""ตารางกะ 7 วันของสัปดาห์ + ประเภทกะ + กะเริ่มต้นของบริษัท"""
	hr_attendance.require_hr()
	company = hr_attendance.default_company(company)
	start = hr_attendance.week_start_of(getdate(week_start or nowdate()))
	end = add_days(start, 6)
	employees = hr_attendance.employees_of(company, start, end, project or None)
	data = hr_attendance.load_period(employees, start, end)
	data["company_shift"] = hr_attendance.company_shift(company)
	today = getdate()
	rows = []
	for emp in employees:
		days = hr_attendance.employee_days(emp, data, start, end, today)
		for key, cell in days.items():
			# กะที่ใช้จริงของวัน (รวมกะเริ่มต้น) ให้หน้าจอแสดงทุกวันทำงาน
			cell["shift"] = hr_attendance.shift_of(data, emp, getdate(key)).name or ""
		rows.append(
			{
				"employee": emp.name,
				"employee_name": emp.employee_name,
				"designation": emp.designation,
				"project": emp.project,
				"default_shift": emp.default_shift,
				"days": days,
			}
		)
	projects = {r["project"] for r in rows if r["project"]}
	return {
		"company": company,
		"week_start": start,
		"today": nowdate(),
		"rows": rows,
		"types": type_rows(),
		"company_shift": data["company_shift"],
		"default_hours": f"{hr_attendance.WORK_START:%H:%M}-{hr_attendance.WORK_END:%H:%M}",
		"projects": dict(frappe.get_all("Project", filters={"name": ("in", list(projects) or [""])}, fields=["name", "project_name"], as_list=True)),
	}


# ---------------------------------------------------------------- ประเภทกะ


def parse_time(value, label, required=True):
	if value in (None, ""):
		if required:
			frappe.throw(_("ระบุ{0}").format(label))
		return None
	try:
		t = hr_attendance.to_time(value)
	except (ValueError, IndexError):
		t = None
	if not t:
		frappe.throw(_("{0} ไม่ถูกต้อง").format(label))
	return t.strftime("%H:%M:%S")


@frappe.whitelist(methods=["POST"])
def save_shift_type(data):
	"""สร้าง/แก้ประเภทกะ (Shift Type) ชื่อ = ชื่อกะ (สร้างแล้วเปลี่ยนชื่อไม่ได้)"""
	hr_attendance.require_hr()
	data = frappe._dict(json.loads(data) if isinstance(data, str) else data)
	start = parse_time(data.start, _("เวลาเข้า"))
	end = parse_time(data.end, _("เวลาออก"))
	if end <= start:
		frappe.throw(_("เวลาออกต้องหลังเวลาเข้า (กะข้ามเที่ยงคืนยังไม่รองรับ)"))
	break_start = parse_time(data.break_start, _("เวลาเริ่มพัก"), required=False)
	break_end = parse_time(data.break_end, _("เวลาสิ้นสุดพัก"), required=False)
	if bool(break_start) != bool(break_end):
		frappe.throw(_("ระบุเวลาพักให้ครบทั้งเริ่มและสิ้นสุด"))
	if break_start and not (start <= break_start < break_end <= end):
		frappe.throw(_("เวลาพักต้องอยู่ในเวลากะ"))
	grace = cint(data.grace)
	if not 0 <= grace <= 120:
		frappe.throw(_("ผ่อนผันสายได้ 0-120 นาที"))
	if data.original:
		doc = frappe.get_doc("Shift Type", data.original)
	else:
		name = (data.name or "").strip()
		if not name:
			frappe.throw(_("ระบุชื่อกะ"))
		if frappe.db.exists("Shift Type", name):
			frappe.throw(_("มีกะชื่อ {0} แล้ว").format(name))
		doc = frappe.new_doc("Shift Type")
		doc.name = doc.__newname = name
	doc.update(
		{
			"start_time": start,
			"end_time": end,
			"custom_break_start": break_start,
			"custom_break_end": break_end,
			"late_entry_grace_period": grace,
			"enable_late_entry_marking": 1,
			"color": data.color or doc.color or "Blue",
		}
	)
	# HR ที่เข้าหมวดได้ตั้งกะได้ (HR User ของ HRMS ไม่มีสิทธิ์สร้าง Shift Type)
	doc.save(ignore_permissions=True)
	return type_rows()


@frappe.whitelist(methods=["POST"])
def set_company_shift(company, shift_type=None):
	"""กะเริ่มต้นของบริษัท (ว่าง = 08:00-17:00)"""
	hr_attendance.require_hr()
	if shift_type and not frappe.db.exists("Shift Type", shift_type):
		frappe.throw(_("ไม่พบกะ {0}").format(shift_type))
	frappe.db.set_value("Company", company, "custom_default_shift", shift_type or None)
	return shift_type


# ---------------------------------------------------------------- กำหนดกะ


def new_assignment(employee, company, shift_type, start, end):
	doc = frappe.get_doc(
		{
			"doctype": "Shift Assignment",
			"employee": employee,
			"company": company,
			"shift_type": shift_type,
			"start_date": start,
			"end_date": end,
			"status": "Active",
		}
	)
	doc.insert()
	doc.submit()
	return doc


def clear_range(employee, start, end):
	"""ปิดกะเดิมที่ทับช่วง start..end (end ว่าง = ไม่มีกำหนด) ส่วนที่เลยช่วงสร้างต่อให้ (กะเดิม)"""
	rows = frappe.get_all(
		"Shift Assignment",
		filters={"employee": employee, "docstatus": 1, "status": "Active"},
		or_filters=[["end_date", "is", "not set"], ["end_date", ">=", start]],
		fields=["name", "shift_type", "company", "start_date", "end_date"],
	)
	for row in rows:
		r_start, r_end = getdate(row.start_date), row.end_date and getdate(row.end_date)
		if end and r_start > end:
			continue
		tail = end and (not r_end or r_end > end)
		if r_start < start:
			frappe.db.set_value("Shift Assignment", row.name, "end_date", add_days(start, -1))
		else:
			frappe.db.set_value("Shift Assignment", row.name, "status", "Inactive")
		if tail:
			new_assignment(employee, row.company, row.shift_type, add_days(end, 1), r_end)


@frappe.whitelist(methods=["POST"])
def assign_shift(employees, from_date, to_date=None, shift_type=None):
	"""กำหนดกะให้พนักงานหลายคนในช่วงวันที่ shift_type ว่าง = กลับไปใช้กะเริ่มต้น (ปิดกะที่กำหนดไว้ในช่วงนั้น)"""
	hr_attendance.require_hr()
	employees = json.loads(employees) if isinstance(employees, str) else employees
	start = getdate(from_date)
	end = getdate(to_date) if to_date else None
	if end and end < start:
		frappe.throw(_("วันสิ้นสุดต้องไม่ก่อนวันเริ่ม"))
	if shift_type and not hr_attendance.shift_type(shift_type):
		frappe.throw(_("กะ {0} ไม่มีเวลาเข้า-ออกที่ใช้ได้").format(shift_type))
	if not employees:
		frappe.throw(_("เลือกพนักงาน"))
	for employee in employees:
		company = frappe.db.get_value("Employee", employee, "company")
		if not company:
			frappe.throw(_("ไม่พบพนักงาน {0}").format(employee))
		clear_range(employee, start, end)
		if shift_type:
			new_assignment(employee, company, shift_type, start, end)
	return len(employees)


@frappe.whitelist(methods=["POST"])
def set_default_shift(employees, shift_type=None):
	"""กะประจำของพนักงาน (Employee.default_shift) ใช้ทุกวันที่ไม่ได้กำหนดกะเป็นช่วง"""
	hr_attendance.require_hr()
	employees = json.loads(employees) if isinstance(employees, str) else employees
	if shift_type and not frappe.db.exists("Shift Type", shift_type):
		frappe.throw(_("ไม่พบกะ {0}").format(shift_type))
	for employee in employees:
		frappe.db.set_value("Employee", employee, "default_shift", shift_type or None)
	return len(employees)


# ---------------------------------------------------------------- จุดลงเวลา


@frappe.whitelist()
def get_locations():
	"""จุดลงเวลาทั้งหมด + ใครใช้ (โครงการ/พนักงานเฉพาะคน)"""
	hr_attendance.require_hr()
	rows = frappe.get_all(
		"Shift Location",
		fields=["name", "location_name", "latitude", "longitude", "checkin_radius as radius"],
		order_by="location_name asc",
		limit_page_length=500,
	)
	projects = {}
	for name, project_name, location in frappe.get_all(
		"Project", filters={"custom_checkin_location": ("is", "set")}, fields=["name", "project_name", "custom_checkin_location"], as_list=True
	):
		projects.setdefault(location, []).append({"name": name, "label": project_name or name})
	people = {}
	for name, employee_name, location in frappe.get_all(
		"Employee", filters={"status": "Active", "custom_checkin_location": ("is", "set")}, fields=["name", "employee_name", "custom_checkin_location"], as_list=True
	):
		people.setdefault(location, []).append({"name": name, "label": employee_name})
	for row in rows:
		row.projects = projects.get(row.name, [])
		row.people = people.get(row.name, [])
	return rows
