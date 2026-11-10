# Copyright (c) 2026, Siricons and Contributors
# See license.txt

# หมวด BOQ ของแอปออฟฟิศ (/conserp/boq): รายการ / สร้าง-แก้ร่าง / Submit / สร้างแผนงาน
# สิทธิ์ = สิทธิ์ของ DocType BOQ (Projects Manager, System Manager) ราคาในเอกสารนี้ห้ามออกไปแอปหน้างาน
# หลัง Submit แก้ไม่ได้: งานเพิ่ม-ลดจากจุดนี้เป็นหน้าที่ของ Variation Order

import frappe
from frappe import _

HEADER_FIELDS = ("customer", "project", "location", "date", "company", "combined_rate", "round_down_total")
ROW_FIELDS = (
	"wbs",
	"item_code",
	"item_name",
	"quantity",
	"uom",
	"item_group",
	"combined_rate",
	"material_rate",
	"labour_rate",
	"description",
)
LIST_LIMIT = 500
# ค้นหาในฟอร์ม: {DocType: ช่องชื่อที่แสดง}
SEARCH = {"Customer": "customer_name", "Project": "project_name", "BOQ Item": "item_name"}


def active_plan(boq):
	return frappe.db.get_value("Construction Management", {"boq": boq}, "name", order_by="creation desc")


@frappe.whitelist()
def get_boqs(company=None):
	frappe.has_permission("BOQ", "read", throw=True)
	return frappe.get_list(
		"BOQ",
		filters={"company": company} if company else None,
		fields=["name", "customer", "project", "location", "date", "company", "grand_total", "docstatus", "modified"],
		order_by="modified desc",
		limit_page_length=LIST_LIMIT,
	)


@frappe.whitelist()
def get_setup():
	frappe.has_permission("BOQ", "read", throw=True)
	return {"uoms": frappe.get_all("UOM", filters={"enabled": 1}, pluck="name", order_by="name asc", limit_page_length=0)}


@frappe.whitelist()
def search(doctype, txt=""):
	frappe.has_permission("BOQ", "read", throw=True)
	label = SEARCH.get(doctype)
	if not label:
		frappe.throw(_("ค้นหา {0} ไม่ได้").format(doctype))
	txt = (txt or "").strip()
	or_filters = [["name", "like", f"%{txt}%"], [label, "like", f"%{txt}%"]] if txt else None
	fields = ["name", f"{label} as label"]
	if doctype == "BOQ Item":
		fields += ["uom", "item_group", "description"]
	rows = frappe.get_list(doctype, or_filters=or_filters, fields=fields, order_by="modified desc", limit_page_length=30)
	return [{**row, "value": row.name, "label": row.label or row.name} for row in rows]


def as_form(doc):
	out = {field: doc.get(field) for field in HEADER_FIELDS}
	out.update(
		{
			"name": doc.name,
			"docstatus": doc.docstatus,
			"amended_from": doc.amended_from,
			"modified": str(doc.modified),
			"total_material_cost": doc.total_material_cost,
			"total_labour_cost": doc.total_labour_cost,
			"grand_total": doc.grand_total,
			"plan": active_plan(doc.name),
			"can_create_plan": bool(frappe.has_permission("Construction Management", "create")),
			"can": {
				**{ptype: bool(doc.has_permission(ptype)) for ptype in ("write", "submit", "cancel", "delete", "export")},
				"amend": bool(doc.has_permission("amend") and frappe.has_permission("BOQ", "create")),
				"open_plan": bool(frappe.has_permission("Construction Management", "read")),
				"sync_plan": bool(frappe.has_permission("Construction Management", "write")),
			},
			"rows": [
				{
					**{field: row.get(field) for field in ROW_FIELDS},
					"name": row.name,
					"material_amount": row.material_amount,
					"labour_amount": row.labour_amount,
					"total_amount": row.total_amount,
				}
				for row in doc.boq_details
			],
		}
	)
	return out


@frappe.whitelist()
def get_boq(name):
	doc = frappe.get_doc("BOQ", name)
	doc.check_permission("read")
	return as_form(doc)


def fill(doc, data):
	for field in HEADER_FIELDS:
		if field in data:
			doc.set(field, data[field])
	# คงรหัสแถวเดิม แผนงานอ้าง BOQ ด้วยรหัสนี้ (boq_detail) รับเฉพาะรหัสที่เป็นของใบนี้
	existing = {row.name for row in doc.boq_details}
	doc.set("boq_details", [])
	for row in data.get("rows") or []:
		values = {field: row.get(field) for field in ROW_FIELDS}
		if row.get("name") in existing:
			existing.discard(row["name"])
			values["name"] = row["name"]
		doc.append("boq_details", values)


@frappe.whitelist(methods=["POST"])
def save_boq(data):
	data = frappe.parse_json(data)
	if data.get("name"):
		doc = frappe.get_doc("BOQ", data["name"])
		if str(doc.modified) != data.get("modified"):
			frappe.throw(_("BOQ นี้ถูกแก้ไขจากที่อื่น โหลดใหม่ก่อนบันทึก"))
	else:
		doc = frappe.new_doc("BOQ")
		doc.naming_series = frappe.get_meta("BOQ").get_field("naming_series").options.split("\n")[0]
	fill(doc, data)
	doc.save()
	return as_form(doc)


@frappe.whitelist(methods=["POST"])
def submit_boq(name):
	doc = frappe.get_doc("BOQ", name)
	if not doc.boq_details:
		frappe.throw(_("BOQ ต้องมีรายการอย่างน้อย 1 แถว"))
	doc.submit()
	return as_form(doc)


@frappe.whitelist(methods=["POST"])
def cancel_boq(name):
	doc = frappe.get_doc("BOQ", name)
	doc.cancel()
	return as_form(doc)


@frappe.whitelist(methods=["POST"])
def amend_boq(name):
	source = frappe.get_doc("BOQ", name)
	source.check_permission("amend")
	if source.docstatus != 2:
		frappe.throw(_("แก้ไขฉบับใหม่ได้เฉพาะใบที่ยกเลิกแล้ว"))
	doc = frappe.copy_doc(source)
	doc.docstatus = 0
	doc.amended_from = source.name
	doc.insert()
	return as_form(doc)


@frappe.whitelist(methods=["POST"])
def delete_boq(name):
	doc = frappe.get_doc("BOQ", name)
	if doc.docstatus == 1:
		frappe.throw(_("ลบได้เฉพาะร่างหรือฉบับที่ยกเลิกแล้ว"))
	doc.delete()


@frappe.whitelist(methods=["POST"])
def create_plan(name):
	"""สร้างแผนงานได้ตั้งแต่ BOQ เป็นร่าง (แก้ BOQ แล้วกดอัปเดตแผนงาน boq_sync.py) 1 BOQ มีแผนได้ 1 ชุด"""
	from consbiz.consbiz.doctype.construction_management.construction_management import create_from_boq

	frappe.has_permission("Construction Management", "create", throw=True)
	if active_plan(name):
		frappe.throw(_("BOQ นี้มีแผนงานแล้ว"))
	return create_from_boq(name)
