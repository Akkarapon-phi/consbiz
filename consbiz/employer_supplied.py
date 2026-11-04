# วัสดุผู้ว่าจ้างจัดหา (Customer Provided Item ของ ERPNext)
# - ERPNext ติ๊ก Customer Provided ได้ที่ Item เท่านั้น และ Item นั้นซื้อ (PO) ไม่ได้ มูลค่าสต็อกเป็น 0
#   จึงมี "Item คู่" ที่ระบบสร้างจาก Item หลักเอง (employer_item) ผูกกลับด้วย custom_base_item (unique)
#   ผู้ใช้เลือก Item หลักเสมอ เอกสารของผู้ว่าจ้างจัดหาสลับเป็น Item คู่ให้
#   (Material Request ประเภท Customer Provided และแถวแผนวัสดุที่ติ๊กผู้ว่าจ้างจัดหา)
# - Item คู่ใช้ชื่อ (+ SUFFIX) กลุ่ม หน่วย และคำอธิบายของ Item หลักเสมอ (before_validate)
#   แก้ Item หลักแล้วซิงก์ตาม (on_update) เปลี่ยนรหัส Item หลัก Frappe แก้ custom_base_item ให้เอง
#   Merge Item หลักสองตัว: merge Item คู่ก่อน (before_rename) ไม่งั้น custom_base_item ชน unique

import frappe
from frappe import _

SUFFIX = " (ผู้ว่าจ้างจัดหา)"
# รหัส Item คู่ เมื่อไซต์ตั้งชื่อ Item ด้วยรหัส (Stock Settings: Item Naming By = Item Code)
CODE_SUFFIX = "-OWN"
COPY_FIELDS = ("item_group", "stock_uom", "description", "image", "brand")
CUSTOMER_PROVIDED = "Customer Provided"
# เลขที่ Material Request ของผู้ว่าจ้างจัดหา (ประเภทอื่นใช้ชุดแรกของ naming_series)
EMPLOYER_SERIES_PREFIX = "OPO-"


@frappe.whitelist()
def get_employer_item(item_code):
	"""Item คู่ของ item_code (สร้างถ้ายังไม่มี) ถ้าเป็น Customer Provided อยู่แล้วคืนตัวเดิม"""
	frappe.has_permission("Item", "read", item_code, throw=True)
	return employer_item(item_code)


def employer_item(item_code):
	base = frappe.db.get_value("Item", item_code, ["name", "is_customer_provided_item"], as_dict=True)
	if not base:
		frappe.throw(_("ไม่พบ Item {0}").format(item_code))
	if base.is_customer_provided_item:
		return base.name
	return frappe.db.get_value("Item", {"custom_base_item": base.name}, "name") or create_employer_item(base.name)


def base_item(item_code):
	"""Item หลักของ Item คู่ (Item อื่นคืนตัวเอง)"""
	return frappe.db.get_value("Item", item_code, "custom_base_item") or item_code


def create_employer_item(base_name):
	base = frappe.get_doc("Item", base_name)
	item = frappe.new_doc("Item")
	item.custom_base_item = base.name
	item.is_stock_item = base.is_stock_item
	if frappe.db.get_default("item_naming_by") != "Naming Series":
		item.item_code = base.name + CODE_SUFFIX
	copy_from_base(item, base)
	# Item คู่เป็นข้อมูลที่ได้จาก Item หลัก ผู้ทำเอกสารไม่ต้องมีสิทธิ์สร้าง Item
	item.flags.ignore_permissions = True
	item.insert()
	return item.name


def copy_from_base(item, base):
	"""ตั้งค่า Item คู่ตาม Item หลัก คืน True ถ้ามีค่าเปลี่ยน"""
	values = {
		"item_name": (base.item_name or base.name)[: 140 - len(SUFFIX)] + SUFFIX,
		"is_customer_provided_item": 1,
		"is_purchase_item": 0,
		"is_sales_item": 0,
		"include_item_in_manufacturing": 0,
		**{field: base.get(field) for field in COPY_FIELDS},
	}
	changed = any(item.get(field) != value for field, value in values.items())
	item.update(values)
	uoms = [(row.uom, row.conversion_factor) for row in base.uoms]
	if [(row.uom, row.conversion_factor) for row in item.uoms] != uoms:
		item.set("uoms", [{"uom": uom, "conversion_factor": factor} for uom, factor in uoms])
		changed = True
	return changed


# ---------- doc_events ของ Item ----------


def enforce_base_values(doc, method=None):
	"""Item.before_validate: Item คู่ใช้ค่าจาก Item หลักเสมอ (แก้ที่ Item คู่ตรงๆ ก็ถูกทับ)"""
	if not doc.get("custom_base_item"):
		return
	base = frappe.get_doc("Item", doc.custom_base_item)
	if base.name == doc.name or base.is_customer_provided_item or base.get("custom_base_item"):
		frappe.throw(_("Item หลักของวัสดุผู้ว่าจ้างจัดหาต้องเป็น Item ที่ไม่ใช่วัสดุผู้ว่าจ้างจัดหา"))
	copy_from_base(doc, base)


def sync_employer_item(doc, method=None):
	"""Item.on_update: แก้ Item หลักแล้วซิงก์ Item คู่ตาม"""
	if doc.get("custom_base_item") or doc.is_customer_provided_item:
		return
	name = frappe.db.get_value("Item", {"custom_base_item": doc.name}, "name")
	if not name:
		return
	twin = frappe.get_doc("Item", name)
	if copy_from_base(twin, doc):
		twin.flags.ignore_permissions = True
		twin.save()


def merge_employer_items(doc, method, old, new, merge=False):
	"""Item.before_rename: merge Item หลัก old เข้า new ที่ต่างมี Item คู่ ให้ merge Item คู่ตามก่อน"""
	if not merge or doc.get("custom_base_item"):
		return
	old_twin = frappe.db.get_value("Item", {"custom_base_item": old}, "name")
	new_twin = frappe.db.get_value("Item", {"custom_base_item": new}, "name")
	if old_twin and new_twin and old_twin != new_twin:
		frappe.rename_doc("Item", old_twin, new_twin, merge=True, show_alert=False)


def sync_after_rename(doc, method, old, new, merge=False):
	"""Item.after_rename: merge แล้วชื่อของ Item หลักอาจเปลี่ยน ซิงก์ Item คู่"""
	if merge:
		sync_employer_item(doc)


# ---------- doc_events ของ Material Request ----------


def employer_series(doctype="Material Request"):
	options = (frappe.get_meta(doctype).get_field("naming_series").options or "").split("\n")
	return next((s for s in options if s.startswith(EMPLOYER_SERIES_PREFIX)), None), options[0]


def set_request_series(doc, method=None):
	"""Material Request.before_insert: ผู้ว่าจ้างจัดหาใช้เลขชุด OPO- ประเภทอื่นห้ามใช้ชุดนี้"""
	employer, default = employer_series()
	if not employer:
		return
	if doc.material_request_type == CUSTOMER_PROVIDED:
		doc.naming_series = employer
	elif doc.naming_series == employer:
		doc.naming_series = default


def swap_request_items(doc, method=None):
	"""Material Request.before_validate: ประเภท Customer Provided สลับรายการเป็น Item คู่"""
	if doc.material_request_type != CUSTOMER_PROVIDED:
		return
	for row in doc.items:
		if not row.item_code:
			continue
		code = employer_item(row.item_code)
		if code != row.item_code:
			row.item_code = code
			row.item_name = frappe.db.get_value("Item", code, "item_name")
