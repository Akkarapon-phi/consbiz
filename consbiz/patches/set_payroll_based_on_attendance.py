# Payroll คิดตาม Attendance (ตกลง 2026-11-11): HR สร้าง Attendance จากหน้าสรุปวันทำงาน (consbiz/hr_attendance.py)
# วันที่ยังไม่ได้บันทึก Attendance คงนับเป็นมาทำงาน (consider_unmarked_attendance_as = Present) ไม่ให้เงินเดือนหายถ้า HR ยังไม่ปิดเดือน

import frappe


def execute():
	if not frappe.db.exists("DocType", "Payroll Settings"):
		return
	frappe.db.set_single_value("Payroll Settings", "payroll_based_on", "Attendance")
	if not frappe.db.get_single_value("Payroll Settings", "consider_unmarked_attendance_as"):
		frappe.db.set_single_value("Payroll Settings", "consider_unmarked_attendance_as", "Present")
