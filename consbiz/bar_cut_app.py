# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

"""แผนตัดเหล็กในแอปหน้างาน (หมวดควบคุมงาน /conserp/work/rebar) หน้าจอครอบ Bar Cut Plan
ความยาวตัด/การจัดตัด/ผลรวมคำนวณใน validate ของ Bar Cut Plan (bar_cut_plan.py + optimizer.py) เหมือนบันทึกในระบบเต็ม
แอปส่งเฉพาะช่องใน INPUT / ITEM / STOCK แล้วบันทึก ผลการตัดมาจาก server เสมอ"""

import json

import frappe
from frappe import _
from frappe.query_builder.functions import Sum
from frappe.utils import cint, flt

from consbiz import store_app
from consbiz.consbiz.doctype.bar_cut_plan.bar_cut_plan import SETTINGS, get_unit_weight, preview_cut_length

DOCTYPE = "Bar Cut Plan"
INPUT = ("title", "date", "kerf", "min_reusable", *SETTINGS)
ITEM = ("mark", "shape", "rebar_type", "a", "b", "c", "d", "e", "f", "r", "n", "t", "qty", "remarks")
STOCK = ("rebar_type", "length", "qty", "remarks")
TOTALS = (
	"total_stock_length",
	"total_required_length",
	"reusable_offcut",
	"scrap",
	"total_weight",
	"loss_percent",
)


def boot_permissions():
	return {
		"bar_cut": bool(frappe.has_permission(DOCTYPE, "read")),
		"bar_cut_write": bool(frappe.has_permission(DOCTYPE, "create")),
	}


@frappe.whitelist()
def get_plans(project):
	"""แผนตัดเหล็กของโครงการ (ใหม่สุดก่อน)"""
	store_app.check_project(project)
	frappe.has_permission(DOCTYPE, "read", throw=True)
	rows = frappe.get_list(
		DOCTYPE,
		filters={"project": project},
		fields=["name", "title", "date", "modified", "owner", *TOTALS],
		order_by="date desc, creation desc",
		limit_page_length=300,
	)
	counts = {}
	if rows:
		item = frappe.qb.DocType("Bar Cut Item")
		counts = dict(
			frappe.qb.from_(item)
			.select(item.parent, Sum(item.qty))
			.where(item.parenttype == DOCTYPE)
			.where(item.parent.isin([r.name for r in rows]))
			.groupby(item.parent)
			.run()
		)
	for row in rows:
		row.pieces = cint(counts.get(row.name))
	return rows


@frappe.whitelist()
def get_setup():
	"""รูปทรง (พร้อม SVG) + ประเภทเหล็ก + ค่าตั้งต้นของแผนใหม่"""
	frappe.has_permission(DOCTYPE, "read", throw=True)
	shapes = frappe.get_all(
		"Bar Shape", fields=["name", "shape_name", "dimensions", "svg"], order_by="name asc"
	)
	for shape in shapes:
		shape.dims = [d.strip().lower() for d in (shape.pop("dimensions") or "").split(",") if d.strip()]
	rebar_types = frappe.get_all(
		"Rebar Type",
		fields=["name", "surface", "diameter", "standard_lengths"],
		order_by="surface asc, diameter asc",
	)
	for row in rebar_types:
		row.unit_weight = get_unit_weight(row.name)
	meta = frappe.get_meta(DOCTYPE)
	defaults = {field: meta.get_field(field).default for field in ("kerf", "min_reusable", *SETTINGS)}
	return {"shapes": shapes, "rebar_types": rebar_types, "defaults": defaults}


def serialize(doc):
	from consbiz.site_app import pdf_url

	saved = not doc.is_new()
	out = {field: doc.get(field) for field in ("name", "project", *INPUT, *TOTALS)}
	out["modified"] = str(doc.modified) if saved else None
	out["items"] = [
		{
			**{field: row.get(field) for field in ITEM},
			"cut_length": flt(row.cut_length),
			"total_length": flt(row.total_length),
			"weight": flt(row.weight),
		}
		for row in doc.items
	]
	out["stock"] = [{field: row.get(field) for field in STOCK} for row in doc.stock]
	out["summary"] = [
		{
			field: row.get(field)
			for field in (
				"rebar_type",
				"stock_length",
				"bars",
				"stock_weight",
				"required_length",
				"reusable_offcut",
				"scrap",
				"loss_percent",
			)
		}
		for row in doc.summary
	]
	out["patterns"] = [
		{
			"rebar_type": row.rebar_type,
			"stock_length": flt(row.stock_length),
			"bars": cint(row.bars),
			"offcut": flt(row.offcut),
			"offcut_type": row.offcut_type,
			"pieces": json.loads(row.pieces or "[]"),
		}
		for row in doc.patterns
	]
	return {
		"doc": out,
		"can_write": bool(doc.has_permission("write")) if saved else True,
		"can_delete": saved and store_app.can_delete(doc),
		"pdf_url": pdf_url(DOCTYPE, doc.name) if saved else None,
	}


@frappe.whitelist()
def get_plan(name=None, project=None):
	if name:
		doc = frappe.get_doc(DOCTYPE, name)
		doc.check_permission("read")
		return serialize(doc)
	store_app.check_project(project)
	doc = frappe.new_doc(DOCTYPE)
	doc.check_permission("create")
	doc.project = project
	return serialize(doc)


@frappe.whitelist()
def preview(shape, rebar_type, dimensions, settings=None):
	"""ความยาวตัดของ 1 ชิ้นก่อนเพิ่มรายการ (ฟังก์ชันเดียวกับหน้าต่างเพิ่มรายการของระบบเต็ม)"""
	return preview_cut_length(shape, rebar_type, dimensions, settings)


@frappe.whitelist(methods=["POST"])
def save_plan(data):
	"""บันทึก = คำนวณความยาวตัดและจัดตัดใหม่ทั้งแผน (validate ของ Bar Cut Plan)"""
	data = frappe._dict(json.loads(data) if isinstance(data, str) else data)
	if data.name:
		doc = frappe.get_doc(DOCTYPE, data.name)
		doc.check_permission("write")
		if data.modified and str(doc.modified) != str(data.modified):
			frappe.throw(_("มีผู้อื่นแก้ไขแผนนี้ไปแล้ว กรุณาโหลดใหม่"))
	else:
		store_app.check_project(data.project)
		doc = frappe.new_doc(DOCTYPE)
		doc.check_permission("create")
		doc.project = data.project
	for field in INPUT:
		if field in data:
			doc.set(field, data[field])
	doc.set("items", [{field: row.get(field) for field in ITEM} for row in data.get("items") or []])
	doc.set(
		"stock",
		[
			{field: row.get(field) for field in STOCK}
			for row in data.get("stock") or []
			if row.get("rebar_type") and flt(row.get("length")) > 0
		],
	)
	doc.save()
	return serialize(doc)


@frappe.whitelist(methods=["POST"])
def delete_plan(name):
	doc = frappe.get_doc(DOCTYPE, name)
	store_app.delete_document(doc)
