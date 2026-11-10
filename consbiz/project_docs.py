# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

"""สร้าง/แก้/ดู เอกสารโครงการในแอป ConsERP: งานลด-เพิ่ม, EOT, ขอตรวจงาน, Punch List
ค่าที่คำนวณและกฎทั้งหมดอยู่ใน validate ของเอกสาร แอปส่งเฉพาะช่องที่กรอกได้ตาม KINDS
หลัง Submit แก้ได้เฉพาะช่อง after / items_after (ตรงกับ Allow on Submit ของ DocType)
งานลด-เพิ่มมีราคาอยู่ในแถว จึงให้สร้าง/แก้ในแอปเฉพาะผู้ที่เห็นงบต้นทุน ผู้อื่นดูได้โดยไม่เห็นมูลค่า"""

import frappe
from frappe import _
from frappe.utils import cint

from consbiz import store_app
from consbiz.consbiz.doctype.construction_management.construction_management import get_task_options
from consbiz.consbiz.doctype.inspection_request.inspection_request import make_reinspection
from consbiz.consbiz.doctype.variation_order.variation_order import get_tasks
from consbiz.site_app import can_view_finance, check_project, with_status

KINDS = {
	"vo": {
		"doctype": "Variation Order",
		"status": "employer_status",
		"fields": ("title", "reference_no", "date", "is_provisional", "extension_days", "reason", "remarks"),
		"items": ("variation_type", "wbs", "item_name", "uom", "qty", "rate", "amount", "remarks"),
		"after": ("reference_no", "employer_status", "employer_approved_on", "is_provisional", "extension_days", "remarks"),
		"items_after": ("qty", "rate", "amount", "remarks"),
	},
	"eot": {
		"doctype": "Extension of Time",
		"status": "employer_status",
		"fields": (
			"title",
			"cause",
			"variation_order",
			"date",
			"reference_no",
			"event_start",
			"event_end",
			"requested_days",
			"reason",
			"remarks",
		),
		"after": ("employer_status", "employer_approved_on", "approved_days", "approval_reference"),
	},
	"inspection": {
		"doctype": "Inspection Request",
		"status": "result",
		"fields": ("title", "wbs", "location", "request_date", "inspection_date", "inspector", "remarks"),
		"after": ("result", "inspected_on", "comments"),
	},
	"punch": {
		"doctype": "Punch List",
		"status": "status",
		"fields": ("title", "date", "inspection_request"),
		"items": ("location", "description", "wbs", "responsible", "due_date", "photo"),
		"after": (),
		"items_after": ("status", "photo_after"),
	},
}
VO_MONEY = (
	"addition_amount",
	"omission_amount",
	"net_amount",
	"contract_amount",
	"previous_variation_amount",
	"revised_amount",
)
VO_ROW_MONEY = ("rate", "amount")


def config_of(kind):
	if kind not in KINDS:
		frappe.throw(_("ไม่รองรับเอกสารชนิดนี้"), frappe.PermissionError)
	return KINDS[kind]


def can_edit(kind):
	return kind != "vo" or can_view_finance()


def require_edit(kind):
	if not can_edit(kind):
		frappe.throw(_("งานลด-เพิ่มแก้ในแอปได้เฉพาะผู้ที่เห็นงบต้นทุน"), frappe.PermissionError)


def load_doc(kind, name):
	doc = frappe.get_doc(config_of(kind)["doctype"], name)
	doc.check_permission("read")
	project = doc.project or frappe.db.get_value("Construction Management", doc.construction_management, "project")
	if project:
		check_project(project)
	return doc


def plan_for(project):
	_info, cm = check_project(project)
	if not cm:
		frappe.throw(_("โครงการนี้ยังไม่มีแผนงาน (Construction Management)"))
	return cm


def serialize(kind, doc):
	out = doc.as_dict(no_default_fields=True)
	out.update(name=doc.name, docstatus=doc.docstatus, owner=doc.owner)
	if doc.meta.get_field("items"):
		out["items"] = [{**row.as_dict(no_default_fields=True), "name": row.name} for row in doc.get("items")]
	with_status(doc.doctype, [out], config_of(kind)["status"])
	if kind == "vo" and not can_view_finance():
		for field in VO_MONEY:
			out.pop(field, None)
		for row in out["items"]:
			for field in VO_ROW_MONEY:
				row.pop(field, None)
	return out


def form_setup(kind, cm):
	if kind == "vo":
		return {"tasks": get_tasks(cm)}
	if kind == "eot":
		return {
			"orders": frappe.get_list(
				"Variation Order",
				filters={"construction_management": cm, "docstatus": 1},
				fields=["name", "title", "extension_days"],
				order_by="date desc, creation desc",
				limit=100,
			)
		}
	setup = {"wbs": get_task_options(cm)}
	if kind == "punch":
		setup["inspections"] = frappe.get_list(
			"Inspection Request",
			filters={"construction_management": cm, "docstatus": 1},
			fields=["name", "title"],
			order_by="request_date desc, creation desc",
			limit=100,
		)
	return setup


@frappe.whitelist()
def get_form(kind, project=None, name=None, source=None):
	"""ค่าตั้งต้นของฟอร์ม name = เอกสารร่างที่แก้ source = ฉบับที่ตรวจไม่ผ่าน (ขอตรวจซ้ำ)"""
	config = config_of(kind)
	require_edit(kind)
	if name:
		doc = load_doc(kind, name)
		doc.check_permission("write")
		if doc.docstatus != 0:
			frappe.throw(_("เอกสารนี้ Submit แล้ว แก้ในฟอร์มไม่ได้"))
	else:
		cm = plan_for(project)
		if source and kind == "inspection":
			doc = make_reinspection(source)
		else:
			doc = frappe.new_doc(config["doctype"])
			doc.construction_management = cm
		doc.check_permission("create")
	return {
		"doc": serialize(kind, doc),
		"setup": form_setup(kind, doc.construction_management),
		"can_submit": bool(frappe.has_permission(config["doctype"], "submit")),
	}


@frappe.whitelist()
def get_view(kind, name):
	config = config_of(kind)
	doc = load_doc(kind, name)
	can_write = bool(doc.has_permission("write")) and can_edit(kind)
	can_submit = bool(doc.has_permission("submit"))
	result = {
		"doc": serialize(kind, doc),
		"can_delete": store_app.can_delete(doc) and can_edit(kind),
		"can_edit": doc.docstatus == 0 and can_write,
		"can_submit": doc.docstatus == 0 and can_submit and can_edit(kind),
		"can_update": doc.docstatus == 1 and can_write,
	}
	if kind == "inspection" and doc.docstatus == 1 and doc.result == "Failed":
		result["reinspection"] = frappe.db.get_value(
			config["doctype"], {"reinspection_of": doc.name, "docstatus": ("<", 2)}
		)
		result["can_reinspect"] = bool(frappe.has_permission(config["doctype"], "create"))
	return result


def attach_new_files(files, doc):
	"""รูปในแถว (อัปโหลดก่อนบันทึก) ผูกกับเอกสาร ไม่งั้นไฟล์ private คนอื่นเปิดไม่ได้ รับเฉพาะไฟล์ของผู้ใช้ที่ยังไม่ผูกเอกสาร"""
	if not files:
		return
	mine = frappe.get_all(
		"File",
		filters={"name": ("in", files), "owner": frappe.session.user, "attached_to_name": ("is", "not set")},
		pluck="name",
	)
	store_app.attach_files(mine, doc.doctype, doc.name)


@frappe.whitelist(methods=["POST"])
def save_doc(kind, data, project=None, submit=0):
	"""บันทึก/แก้ร่าง แล้ว Submit ถ้า submit=1"""
	config = config_of(kind)
	require_edit(kind)
	data = store_app.parse(data)
	if data.get("name"):
		doc = load_doc(kind, data["name"])
		if doc.docstatus != 0:
			frappe.throw(_("เอกสารนี้ Submit แล้ว แก้ในฟอร์มไม่ได้"))
	else:
		cm = plan_for(project)
		if kind == "inspection" and data.get("reinspection_of"):
			doc = make_reinspection(data["reinspection_of"])
		else:
			doc = frappe.new_doc(config["doctype"])
			doc.construction_management = cm
	for field in config["fields"]:
		if field in data:
			doc.set(field, data[field])
	if config.get("items"):
		doc.set("items", [])
		for row in data.get("items") or []:
			doc.append("items", {field: row.get(field) for field in config["items"] if field in row})
	doc.save()
	if cint(submit):
		doc.submit()
	attach_new_files(data.get("files"), doc)
	return {"name": doc.name, "docstatus": doc.docstatus}


@frappe.whitelist(methods=["POST"])
def submit_doc(kind, name):
	require_edit(kind)
	doc = load_doc(kind, name)
	doc.submit()
	return {"name": doc.name, "docstatus": doc.docstatus}


@frappe.whitelist(methods=["POST"])
def delete_doc(kind, name):
	require_edit(kind)
	store_app.delete_document(load_doc(kind, name))


@frappe.whitelist(methods=["POST"])
def update_submitted(kind, name, data):
	"""แก้หลัง Submit: ผลอนุมัติ/ผลตรวจ, ปิดรายการ Punch List, ปริมาณจริงของงานลด-เพิ่ม"""
	config = config_of(kind)
	require_edit(kind)
	data = store_app.parse(data)
	doc = load_doc(kind, name)
	if doc.docstatus != 1:
		frappe.throw(_("ใช้ได้กับเอกสารที่ Submit แล้วเท่านั้น"))
	for field in config["after"]:
		if field in data:
			doc.set(field, data[field])
	rows = {row.name: row for row in doc.get("items") or []} if config.get("items_after") else {}
	for values in data.get("items") or []:
		row = rows.get(values.get("name"))
		if row:
			row.update({field: values[field] for field in config["items_after"] if field in values})
	doc.save()
	attach_new_files(data.get("files"), doc)
	return get_view(kind, name)
