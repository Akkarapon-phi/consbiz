"""ตั้งค่าแบบฟอร์มพิมพ์ของเอกสารในแอป (ตกลง 2026-11-18): หมวดจัดซื้อ เมนู ⋯ > ตั้งค่า > แบบฟอร์มพิมพ์

ค่าที่เลือกเก็บเป็น global default `consbiz_print_format::<DocType>` (frappe.db.set_default) ใช้กับปุ่มพิมพ์ของแอปเท่านั้น
(site_app.print_options) ไม่เปลี่ยนแบบเริ่มต้นของระบบเต็ม ยังไม่เลือก = แบบชื่อเดียวกับ DocType ตามเดิม"""

import frappe
from frappe import _

# เอกสารของแต่ละหมวดที่ตั้งได้ (kind ตรงกับ DOC_KINDS)
SECTIONS = {
	"buy": [
		("mr", "Material Request", "ใบขอซื้อ"),
		("po", "Purchase Order", "ใบสั่งซื้อ"),
		("pi", "Purchase Invoice", "ใบแจ้งหนี้ซื้อ"),
	],
}
EDIT_ROLES = {"buy": ("Purchase Manager", "System Manager")}
# ชื่อที่ผู้ใช้เห็น (แบบที่ไม่อยู่ในนี้แสดงชื่อ Print Format)
LABELS = {
	"Purchase Order": "ใบสั่งซื้อ (รูปแบบที่ 1 · Print Designer)",
	"Purchase Order TH": "ใบสั่งซื้อ (รูปแบบที่ 2 · HTML)",
	"Purchase Order TH 3": "ใบสั่งซื้อ (รูปแบบที่ 3 · HTML)",
	"Purchase Order TH 4": "ใบสั่งซื้อ (รูปแบบที่ 4 · HTML)",
}
# ค่าเริ่มต้นของแอปเมื่อยังไม่ได้เลือกในหน้าตั้งค่า (ตกลง 2026-11-19: ใบสั่งซื้อใช้รูปแบบที่ 4) ไม่อยู่ในนี้ = แบบชื่อเดียวกับ DocType
DEFAULTS = {"Purchase Order": "Purchase Order TH 4"}
# แบบที่รองรับพิมพ์หลายฉบับ (ต้นฉบับ/สำเนา ผ่าน ?copies=)
COPIES_FORMATS = {"Purchase Order TH", "Purchase Order TH 3", "Purchase Order TH 4"}


def key_of(doctype):
	return f"consbiz_print_format::{doctype}"


def chosen_format(doctype):
	"""แบบที่ตั้งไว้ในแอป > ค่าเริ่มต้นของแอป (DEFAULTS) ที่ยังใช้ได้อยู่ หรือ None"""
	usable = lambda name: name and frappe.db.get_value("Print Format", {"name": name, "doc_type": doctype, "disabled": 0})
	value = frappe.db.get_default(key_of(doctype))
	if usable(value):
		return value
	return DEFAULTS.get(doctype) if usable(DEFAULTS.get(doctype)) else None


def can_edit(section):
	return bool(set(frappe.get_roles()) & set(EDIT_ROLES.get(section, ())))


def formats_of(doctype):
	"""แบบที่เลือกได้: แบบที่ตั้งชื่อไว้ (LABELS) ก่อน แล้วแบบอื่นเรียงตามชื่อ"""
	rows = frappe.get_all(
		"Print Format",
		filters={"doc_type": doctype, "disabled": 0},
		fields=["name", "print_designer", "standard", "module"],
		order_by="name asc",
	)

	def kind(r):
		if r.print_designer:
			return "Print Designer"
		return "HTML (ConsERP)" if r.standard == "Yes" and r.module == "ConsBiz" else "HTML (ระบบเต็ม)"

	rows.sort(key=lambda r: (r.name not in LABELS, LABELS.get(r.name, r.name)))
	return [
		{
			"value": r.name,
			"label": LABELS.get(r.name, r.name),
			"kind": kind(r),
			"copies": r.name in COPIES_FORMATS,
		}
		for r in rows
	]


@frappe.whitelist()
def get_settings(section="buy"):
	if section not in SECTIONS:
		frappe.throw(_("ไม่รองรับหมวดนี้"))
	from consbiz.site_app import print_options

	out = []
	for kind, doctype, label in SECTIONS[section]:
		if not frappe.has_permission(doctype, "read"):
			continue
		current, _generator = print_options(doctype)
		out.append(
			{
				"default": LABELS.get(DEFAULTS.get(doctype), DEFAULTS.get(doctype)) if DEFAULTS.get(doctype) else None,
				"kind": kind,
				"doctype": doctype,
				"label": label,
				"current": current,
				"chosen": chosen_format(doctype),
				"formats": formats_of(doctype),
			}
		)
	return {"docs": out, "can_edit": can_edit(section)}


@frappe.whitelist(methods=["POST"])
def set_format(section, doctype, print_format=None):
	if section not in SECTIONS or doctype not in [d for _k, d, _l in SECTIONS[section]]:
		frappe.throw(_("ไม่รองรับเอกสารนี้"))
	if not can_edit(section):
		frappe.throw(_("ไม่มีสิทธิ์ตั้งค่าแบบฟอร์มพิมพ์"), frappe.PermissionError)
	if print_format and not frappe.db.get_value(
		"Print Format", {"name": print_format, "doc_type": doctype, "disabled": 0}
	):
		frappe.throw(_("ไม่พบแบบฟอร์ม {0}").format(print_format))
	frappe.db.set_default(key_of(doctype), print_format or "")
	return get_settings(section)
