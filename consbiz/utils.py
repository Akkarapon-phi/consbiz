import re

import frappe
from frappe.utils import getdate


def parse_naming_series_variable(doc, variable):
	if variable == "ABBR":
		if doc and doc.get("company"):
			return frappe.get_cached_value("Company", doc.company, "abbr")
		return frappe.defaults.get_global_default("company_abbr") or "X"


THAI_MONTHS = (
	"มกราคม",
	"กุมภาพันธ์",
	"มีนาคม",
	"เมษายน",
	"พฤษภาคม",
	"มิถุนายน",
	"กรกฎาคม",
	"สิงหาคม",
	"กันยายน",
	"ตุลาคม",
	"พฤศจิกายน",
	"ธันวาคม",
)


def thai_date(value):
	"""วันที่แบบไทย พ.ศ. เช่น 18 สิงหาคม 2570 (ใช้ใน Print Format ผ่าน jinja)"""
	if not value:
		return ""
	date = getdate(value)
	return f"{date.day} {THAI_MONTHS[date.month - 1]} {date.year + 543}"


def name_with_title(name, user=None):
	"""ชื่อพร้อมคำนำหน้า (salutation ของ Employee) ใช้ใน Print Format ผ่าน jinja
	หาพนักงานจากชื่อก่อน แล้วจาก user ถ้าชื่อตรงกับชื่อเต็มของ user นั้น คำนำหน้าไทยเขียนติดชื่อ (นายสมชาย)"""
	if not name:
		return ""
	salutation = frappe.db.get_value("Employee", {"employee_name": name}, "salutation")
	if not salutation and user and frappe.db.get_value("User", user, "full_name") == name:
		salutation = frappe.db.get_value("Employee", {"user_id": user}, "salutation")
	if not salutation or name.startswith(salutation):
		return name
	return salutation + ("" if re.search("[\u0e00-\u0e7f]", salutation) else " ") + name
