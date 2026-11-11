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


THAI_DIGITS = ["ศูนย์", "หนึ่ง", "สอง", "สาม", "สี่", "ห้า", "หก", "เจ็ด", "แปด", "เก้า"]
THAI_UNITS = ["", "สิบ", "ร้อย", "พัน", "หมื่น", "แสน"]


def _thai_number(number):
	text = ""
	digits = str(number)
	for i, char in enumerate(digits):
		n = int(char)
		pos = len(digits) - i - 1
		unit = pos % 6
		if n:
			if unit == 0 and n == 1 and i > 0:
				text += "เอ็ด"
			elif unit == 1 and n == 2:
				text += "ยี่"
			elif not (unit == 1 and n == 1):
				text += THAI_DIGITS[n]
			text += THAI_UNITS[unit]
		if pos and pos % 6 == 0:
			text += "ล้าน"
	return text


def thai_baht_text(amount):
	"""จำนวนเงินเป็นคำอ่านภาษาไทย ให้ผลเหมือน thai_baht_text() ใน public/js/utils.js (ติดลบขึ้นต้นด้วย "ติดลบ")"""
	from frappe.utils import flt

	amount = flt(amount, 2)
	prefix = "ติดลบ" if amount < 0 else ""
	baht, satang = divmod(round(abs(amount) * 100), 100)
	text = (_thai_number(baht) or "ศูนย์") + "บาท"
	text += _thai_number(satang) + "สตางค์" if satang else "ถ้วน"
	return prefix + text


def image_data_uri(file_url):
	"""รูปจากไฟล์ในระบบ (รวม private เช่นโลโก้บริษัท) เป็น data URI ให้ Print Format/PDF แสดงได้โดยไม่ต้องล็อกอิน (ใช้ผ่าน jinja)"""
	import base64
	import mimetypes

	if not file_url:
		return ""
	name = frappe.db.get_value("File", {"file_url": file_url}, "name")
	if not name:
		return ""
	try:
		content = frappe.get_doc("File", name).get_content()
	except Exception:
		return ""
	if isinstance(content, str):
		content = content.encode()
	mime = mimetypes.guess_type(file_url)[0] or "image/png"
	return f"data:{mime};base64,{base64.b64encode(content).decode()}"
