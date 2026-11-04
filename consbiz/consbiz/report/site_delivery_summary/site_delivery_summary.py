# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

"""สรุปใบส่งของหน้างาน: ของที่รับเข้าคลัง 1 แถวต่อรายการ พร้อมเลขที่ใบส่งของ ผู้ส่ง และทะเบียนรถ

- ซื้อเอง = Purchase Receipt (supplier_delivery_note, lr_no)
- รับเข้าอื่น/ผู้ว่าจ้างจัดหา = Stock Entry ประเภท Material Receipt (custom_supplier_delivery_note, custom_delivered_by, custom_vehicle_no)
- แหล่ง (ซื้อเอง / ผู้ว่าจ้างจัดหา) ดูจาก Item: Customer Provided = ผู้ว่าจ้างจัดหา (Item คู่ ดู consbiz/employer_supplied.py)
- โครงการ = project ของรายการ หรือของหัวเอกสาร นับเฉพาะเอกสารที่ Submit แล้ว จำนวนเป็นหน่วยสต็อก
"""

import frappe
from frappe import _
from frappe.query_builder.functions import Coalesce
from frappe.utils import getdate

SUPPLY_COMPANY = "Company"
SUPPLY_EMPLOYER = "Employer"


def execute(filters=None):
	filters = frappe._dict(filters or {})
	return get_columns(), get_data(filters)


def get_columns():
	return [
		{"fieldname": "posting_date", "label": _("วันที่รับ"), "fieldtype": "Date", "width": 95},
		{"fieldname": "delivery_note", "label": _("เลขที่ใบส่งของ"), "fieldtype": "Data", "width": 120},
		{"fieldname": "delivered_by", "label": _("ผู้ส่ง"), "fieldtype": "Data", "width": 160},
		{"fieldname": "vehicle_no", "label": _("ทะเบียนรถ"), "fieldtype": "Data", "width": 95},
		{"fieldname": "supply", "label": _("แหล่ง"), "fieldtype": "Data", "width": 110},
		{"fieldname": "item_code", "label": _("Item"), "fieldtype": "Link", "options": "Item", "width": 120},
		{"fieldname": "item_name", "label": _("รายการ"), "fieldtype": "Data", "width": 220},
		{"fieldname": "qty", "label": _("จำนวน"), "fieldtype": "Float", "width": 90},
		{"fieldname": "uom", "label": _("หน่วย"), "fieldtype": "Link", "options": "UOM", "width": 70},
		{"fieldname": "warehouse", "label": _("คลัง"), "fieldtype": "Link", "options": "Warehouse", "width": 150},
		{"fieldname": "project", "label": _("โครงการ"), "fieldtype": "Link", "options": "Project", "width": 120},
		{"fieldname": "voucher_type", "label": _("ประเภทเอกสาร"), "fieldtype": "Data", "hidden": 1},
		{
			"fieldname": "voucher_no",
			"label": _("เอกสาร"),
			"fieldtype": "Dynamic Link",
			"options": "voucher_type",
			"width": 150,
		},
	]


def get_data(filters):
	rows = purchase_receipt_rows(filters) + stock_entry_rows(filters)
	provided = set(
		frappe.get_all(
			"Item",
			filters={"name": ("in", list({row.item_code for row in rows}) or [""]), "is_customer_provided_item": 1},
			pluck="name",
		)
	)
	result = []
	for row in rows:
		supply = SUPPLY_EMPLOYER if row.item_code in provided else SUPPLY_COMPANY
		if filters.supply and filters.supply != supply:
			continue
		row.supply = _("ผู้ว่าจ้างจัดหา") if supply == SUPPLY_EMPLOYER else _("ซื้อเอง")
		result.append(row)
	result.sort(key=lambda row: (getdate(row.posting_date), row.voucher_no, row.idx))
	return result


def apply_filters(query, parent, child, warehouse, delivery_note, filters):
	query = query.where(
		(parent.docstatus == 1)
		& (parent.company == filters.company)
		& (parent.posting_date >= filters.from_date)
		& (parent.posting_date <= filters.to_date)
	)
	if filters.project:
		query = query.where(Coalesce(child.project, parent.project) == filters.project)
	if filters.warehouse:
		query = query.where(warehouse == filters.warehouse)
	if filters.item_code:
		query = query.where(child.item_code == filters.item_code)
	if filters.delivery_note:
		query = query.where(delivery_note.like(f"%{filters.delivery_note}%"))
	return query


def purchase_receipt_rows(filters):
	parent = frappe.qb.DocType("Purchase Receipt")
	child = frappe.qb.DocType("Purchase Receipt Item")
	query = (
		frappe.qb.from_(child)
		.join(parent)
		.on(child.parent == parent.name)
		.select(
			parent.posting_date,
			parent.supplier_delivery_note.as_("delivery_note"),
			parent.supplier_name.as_("delivered_by"),
			parent.lr_no.as_("vehicle_no"),
			child.item_code,
			child.item_name,
			child.stock_qty.as_("qty"),
			child.stock_uom.as_("uom"),
			child.warehouse,
			Coalesce(child.project, parent.project).as_("project"),
			parent.name.as_("voucher_no"),
			child.idx,
		)
	)
	query = apply_filters(query, parent, child, child.warehouse, parent.supplier_delivery_note, filters)
	return [frappe._dict(row, voucher_type="Purchase Receipt") for row in query.run(as_dict=True)]


def stock_entry_rows(filters):
	parent = frappe.qb.DocType("Stock Entry")
	child = frappe.qb.DocType("Stock Entry Detail")
	query = (
		frappe.qb.from_(child)
		.join(parent)
		.on(child.parent == parent.name)
		.select(
			parent.posting_date,
			parent.custom_supplier_delivery_note.as_("delivery_note"),
			parent.custom_delivered_by.as_("delivered_by"),
			parent.custom_vehicle_no.as_("vehicle_no"),
			child.item_code,
			child.item_name,
			child.transfer_qty.as_("qty"),
			child.stock_uom.as_("uom"),
			child.t_warehouse.as_("warehouse"),
			Coalesce(child.project, parent.project).as_("project"),
			parent.name.as_("voucher_no"),
			child.idx,
		)
		.where(parent.purpose == "Material Receipt")
	)
	query = apply_filters(query, parent, child, child.t_warehouse, parent.custom_supplier_delivery_note, filters)
	return [frappe._dict(row, voucher_type="Stock Entry") for row in query.run(as_dict=True)]
