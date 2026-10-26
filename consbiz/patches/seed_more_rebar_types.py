# เพิ่มขนาดเหล็กให้ครบตาม มอก. 20 (เหล็กเส้นกลม SR24) และ มอก. 24 (เหล็กข้ออ้อย) ข้ามชื่อที่มีอยู่แล้ว
# และแก้น้ำหนักต่อเมตรของรายการเดิมที่ระบบคำนวณจากสูตรเก่า 0.00617 x d² ให้เป็นมวลระบุตาม มอก.
# (รายการที่ผู้ใช้กรอกน้ำหนักเองไม่แตะ)

import frappe
from frappe.utils import flt

from consbiz.consbiz.doctype.rebar_type.rebar_type import nominal_mass

# (ชื่อ, ผิว, ขนาด มม., ชั้นคุณภาพ, ความยาวมาตรฐาน ม.)
REBAR_TYPES = [
	("RB8", "RB", 8, "SR24", "10"),
	("RB10", "RB", 10, "SR24", "10"),
	("RB12", "RB", 12, "SR24", "10"),
	("RB15", "RB", 15, "SR24", "10"),
	("RB19", "RB", 19, "SR24", "10"),
	("RB22", "RB", 22, "SR24", "10"),
	("RB25", "RB", 25, "SR24", "10"),
	("RB28", "RB", 28, "SR24", "10"),
	("RB34", "RB", 34, "SR24", "10"),
	("DB6", "DB", 6, "SD40", "10"),
	("DB8", "DB", 8, "SD40", "10"),
	("DB22", "DB", 22, "SD40", "10, 12"),
	("DB36", "DB", 36, "SD40", "10, 12"),
	("DB40", "DB", 40, "SD40", "10, 12"),
]


def execute():
	frappe.reload_doc("consbiz", "doctype", "rebar_type")

	for name, diameter, unit_weight in frappe.get_all(
		"Rebar Type", fields=["name", "diameter", "unit_weight"], as_list=True
	):
		if flt(unit_weight) == round(0.00617 * flt(diameter) ** 2, 3):
			frappe.db.set_value("Rebar Type", name, "unit_weight", nominal_mass(diameter))

	for name, surface, diameter, grade, lengths in REBAR_TYPES:
		if not frappe.db.exists("Rebar Type", name):
			frappe.get_doc(
				{
					"doctype": "Rebar Type",
					"rebar_name": name,
					"surface": surface,
					"diameter": diameter,
					"grade": grade,
					"standard_lengths": lengths,
				}
			).insert(ignore_permissions=True)
