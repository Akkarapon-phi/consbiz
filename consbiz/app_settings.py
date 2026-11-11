# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

"""หน้าตั้งค่าของ ConsERP (popup จาก avatar, public/js/shared/components/SettingsDialog.vue)

สิทธิ์ของ Role ต่อหมวดในแอป: ครอบ Role Permission ของ Frappe (Custom DocPerm) ค่าเดียวกับ Role Permission Manager ในระบบเต็ม
แก้ได้เฉพาะ System Manager และเฉพาะเอกสารที่อยู่ใน MODULES
"""

import frappe
from frappe import _
from frappe.core.doctype.custom_docperm.custom_docperm import update_custom_docperm
from frappe.core.doctype.doctype.doctype import validate_permissions_for_doctype
from frappe.core.page.permission_manager import permission_manager
from frappe.permissions import add_permission, get_all_perms, setup_custom_perms
from frappe.utils import cint

COLUMNS = ("read", "create", "write", "delete", "submit", "cancel", "amend", "export")
SUBMIT_COLUMNS = ("submit", "cancel", "amend")
# permlevel สูงกว่า 0 กำหนดได้แค่ดู/แก้ช่องของระดับนั้น
LEVEL_COLUMNS = ("read", "write")

# เงื่อนไขของ Frappe (validate_permissions) เปิดสิทธิ์นี้ต้องมีสิทธิ์ใดบ้าง / ปิดสิทธิ์นี้แล้วสิทธิ์ใดต้องปิดตาม
REQUIRES = {"submit": ("write",), "cancel": ("submit", "write"), "amend": ("write",)}
DEPENDENTS = {"read": COLUMNS, "write": SUBMIT_COLUMNS, "submit": ("cancel",)}

# (แอป, หมวด ตาม MODULE_META, ((DocType, ชื่อที่แสดง, permlevel), ...)) เอกสารซ้ำหลายหมวดได้ (ค่าเดียวกัน)
MODULES = (
	(
		"site",
		"store",
		(
			("Purchase Receipt", "รับของตามใบสั่งซื้อ", 0),
			("Stock Entry", "เบิก / รับของผู้ว่าจ้าง / คลัง", 0),
			("Equipment Borrowing", "ยืม-คืนอุปกรณ์", 0),
		),
	),
	(
		"site",
		"work",
		(
			("Daily Report", "รายงานประจำวัน", 0),
			("Daily Request", "ขออนุมัติปฏิบัติงาน", 0),
			("Inspection Request", "ขอตรวจงาน", 0),
			("Punch List", "Punch List", 0),
			("Concrete Usage", "คอนกรีต", 0),
		),
	),
	(
		"site",
		"pm",
		(
			("Construction Management", "แผนงาน", 0),
			("Construction Management", "งบต้นทุน มูลค่า และการเงิน", 1),
			("Variation Order", "งานลด-เพิ่ม", 0),
			("Extension of Time", "ขยายเวลา (EOT)", 0),
			("Construction Baseline", "Baseline", 0),
		),
	),
	(
		"site",
		"resources",
		(
			("Construction Resource Plan", "แผนคนและเครื่องจักร", 0),
			("Construction Material Plan", "แผนวัสดุ", 0),
		),
	),
	("site", "buy", (("Material Request", "ใบขอซื้อ", 0),)),
	(
		"office",
		"purchase",
		(
			("Material Request", "ใบขอซื้อ", 0),
			("Purchase Order", "ใบสั่งซื้อ", 0),
			("Purchase Invoice", "ใบแจ้งหนี้ซื้อ", 0),
		),
	),
	(
		"office",
		"sales",
		(
			("Quotation", "ใบเสนอราคา", 0),
			("Sales Order", "ใบสั่งขาย", 0),
			("Sales Invoice", "ใบแจ้งหนี้ขาย", 0),
		),
	),
	("office", "boq", (("BOQ", "BOQ", 0),)),
	("office", "hr", (("Attendance", "การเข้างาน (Attendance)", 0),)),
)
TARGETS = {(row[0], row[2]) for _app, _section, rows in MODULES for row in rows}


def can_manage():
	return "System Manager" in frappe.get_roles()


def require_manager():
	if not can_manage():
		frappe.throw(_("เฉพาะ System Manager เท่านั้น"), frappe.PermissionError)


def columns_of(doctype, permlevel):
	if permlevel:
		return LEVEL_COLUMNS
	if frappe.get_meta(doctype).is_submittable:
		return COLUMNS
	return tuple(ptype for ptype in COLUMNS if ptype not in SUBMIT_COLUMNS)


def rule_key(doctype, permlevel):
	return f"{doctype}:{cint(permlevel)}"


def editable_roles():
	return [row["value"] for row in permission_manager.get_roles_and_doctypes()["roles"]]


@frappe.whitelist()
def get_permission_setup():
	"""Role ที่ตั้งได้ + แถวของแต่ละหมวด"""
	require_manager()
	return {
		"roles": [{"value": role, "label": _(role)} for role in editable_roles()],
		"columns": COLUMNS,
		"modules": [
			{
				"app": app,
				"section": section,
				"rows": [
					{
						"key": rule_key(doctype, permlevel),
						"doctype": doctype,
						"label": label,
						"permlevel": permlevel,
						"columns": columns_of(doctype, permlevel),
					}
					for doctype, label, permlevel in rows
				],
			}
			for app, section, rows in MODULES
		],
	}


def add_to_rules(rules, perm):
	"""รวมกฎ 1 แถวเข้า {"DocType:level": {read: 0/1, ..., if_owner}} if_owner = มีกฎ "เฉพาะเอกสารที่ตนสร้าง" (แก้ในระบบเต็ม)"""
	if (perm.parent, cint(perm.permlevel)) not in TARGETS:
		return
	rule = rules.setdefault(rule_key(perm.parent, perm.permlevel), dict.fromkeys(COLUMNS, 0))
	if perm.if_owner:
		rule["if_owner"] = 1
	else:
		rule.update({ptype: cint(perm.get(ptype)) for ptype in COLUMNS})


@frappe.whitelist()
def get_role_rules(role):
	require_manager()
	rules = {}
	for perm in get_all_perms(role):
		add_to_rules(rules, perm)
	return rules


@frappe.whitelist()
def get_all_rules():
	"""{Role: กฎ} ของเอกสารใน MODULES เฉพาะ Role ที่ตั้งได้ (DocType ที่มี Custom DocPerm ใช้ชุดนั้นแทนของมาตรฐาน)"""
	require_manager()
	doctypes = sorted({doctype for doctype, _level in TARGETS})
	custom = frappe.get_all("Custom DocPerm", fields="*", filters={"parent": ("in", doctypes)})
	customized = {perm.parent for perm in custom}
	standard = frappe.get_all(
		"DocPerm", fields="*", filters={"parent": ("in", [d for d in doctypes if d not in customized])}
	)
	roles = set(editable_roles())
	rules = {}
	for perm in custom + standard:
		if perm.role in roles:
			add_to_rules(rules.setdefault(perm.role, {}), perm)
	return rules


def docperm_of(doctype, role, permlevel):
	return frappe.db.get_value(
		"Custom DocPerm", {"parent": doctype, "role": role, "permlevel": permlevel, "if_owner": 0}
	)


def ensure_rule(doctype, role, permlevel):
	"""กฎของ Role (ไม่มี = เพิ่มพร้อมสิทธิ์อ่าน) Custom DocPerm ตั้งค่าเริ่มต้นส่งออก = 1 ปิดไว้ก่อนให้เปิดเองในตาราง"""
	name = docperm_of(doctype, role, permlevel)
	if not name:
		add_permission(doctype, role, permlevel)
		name = docperm_of(doctype, role, permlevel)
		update_custom_docperm(name, {"export": 0})
	return name


def remove_higher_levels(doctype, role):
	"""กฎระดับสูงต้องมีกฎระดับ 0 ก่อน: ปิดระดับ 0 จึงต้องลบระดับสูงด้วย"""
	levels = frappe.get_all(
		"Custom DocPerm",
		filters={"parent": doctype, "role": role, "permlevel": (">", 0)},
		pluck="permlevel",
		distinct=True,
	)
	for level in levels:
		permission_manager.remove(doctype, role, level)


def check_role(role):
	if role not in editable_roles():
		frappe.throw(_("ตั้งสิทธิ์ของ Role {0} ไม่ได้").format(role))


def finish_change(doctype):
	validate_permissions_for_doctype(doctype)
	frappe.db.after_commit.add(lambda: frappe.clear_cache(doctype=doctype))


def turn_on(doctype, role, permlevel, ptype):
	if permlevel:
		ensure_rule(doctype, role, 0)
	changes = {"read": 1, ptype: 1, **dict.fromkeys(REQUIRES.get(ptype, ()), 1)}
	update_custom_docperm(ensure_rule(doctype, role, permlevel), changes)


def turn_off(doctype, role, permlevel, ptype):
	name = docperm_of(doctype, role, permlevel)
	if not name:
		return
	# ไม่เหลือสิทธิ์พื้นฐาน Frappe ไม่ยอมให้คงกฎไว้ จึงลบทั้งแถว (สิทธิ์ select อย่างเดียวยังคงแถวได้)
	if ptype == "read" and not frappe.db.get_value("Custom DocPerm", name, "select"):
		if not permlevel:
			remove_higher_levels(doctype, role)
		permission_manager.remove(doctype, role, permlevel)
		return
	update_custom_docperm(name, {ptype: 0, **dict.fromkeys(DEPENDENTS.get(ptype, ()), 0)})


@frappe.whitelist(methods=["POST"])
def set_role_permission(role, doctype, permlevel, ptype, value):
	"""เปิด/ปิดสิทธิ์ 1 ช่อง พร้อมสิทธิ์ที่ต้องไปด้วยกันตามเงื่อนไขของ Frappe คืนกฎทั้งหมดของ Role"""
	require_manager()
	permlevel = cint(permlevel)
	if (doctype, permlevel) not in TARGETS or ptype not in columns_of(doctype, permlevel):
		frappe.throw(_("ตั้งสิทธิ์นี้ในแอปไม่ได้"))
	check_role(role)
	setup_custom_perms(doctype)
	(turn_on if cint(value) else turn_off)(doctype, role, permlevel, ptype)
	finish_change(doctype)
	return get_role_rules(role)


@frappe.whitelist(methods=["POST"])
def remove_role_from_module(role, app, section):
	"""เอา Role ออกจากเอกสารทุกใบของหมวด (เอกสารที่อยู่หลายหมวด เช่น ใบขอซื้อ มีผลกับทุกหมวดนั้น) คืนกฎทั้งหมดของ Role"""
	require_manager()
	check_role(role)
	rows = next((rows for a, s, rows in MODULES if (a, s) == (app, section)), None)
	if rows is None:
		frappe.throw(_("ไม่พบหมวด {0}").format(section))
	for doctype in {row[0] for row in rows}:
		setup_custom_perms(doctype)
		turn_off(doctype, role, 0, "read")
		finish_change(doctype)
	return get_role_rules(role)
