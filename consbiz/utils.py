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
