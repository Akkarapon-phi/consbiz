# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

"""อุปกรณ์ที่ยังค้างคืน 1 แถวต่อรายการของใบยืม (Equipment Borrowing ที่ Submit แล้วและยังคืนไม่ครบ)

ผู้รับผิดชอบ = ผรม. (supplier) ถ้ามี ไม่งั้นผู้ยืม เรียงตามผู้รับผิดชอบ ใช้ตอนตามคืนหรือหักงวด ผรม.
"""

import frappe
from frappe import _
from frappe.utils import date_diff, getdate, nowdate

BORROWER_TYPES = {"Employee": "พนักงาน", "Subcontractor": "ผรม.", "Worker": "คนงาน"}


def execute(filters=None):
	filters = frappe._dict(filters or {})
	return get_columns(), get_data(filters)


def get_columns():
	return [
		{"fieldname": "responsible", "label": _("ผู้รับผิดชอบ"), "fieldtype": "Data", "width": 180},
		{"fieldname": "borrower_type", "label": _("ประเภทผู้ยืม"), "fieldtype": "Data", "width": 90},
		{"fieldname": "borrower_name", "label": _("ผู้ยืม"), "fieldtype": "Data", "width": 160},
		{"fieldname": "equipment_borrowing", "label": _("ใบยืม"), "fieldtype": "Link", "options": "Equipment Borrowing", "width": 140},
		{"fieldname": "project", "label": _("โครงการ"), "fieldtype": "Link", "options": "Project", "width": 110},
		{"fieldname": "item_code", "label": _("อุปกรณ์"), "fieldtype": "Link", "options": "Item", "width": 120},
		{"fieldname": "item_name", "label": _("ชื่ออุปกรณ์"), "fieldtype": "Data", "width": 180},
		{"fieldname": "outstanding_qty", "label": _("ค้างคืน"), "fieldtype": "Float", "width": 80},
		{"fieldname": "uom", "label": _("หน่วย"), "fieldtype": "Link", "options": "UOM", "width": 70},
		{"fieldname": "date", "label": _("วันที่ยืม"), "fieldtype": "Date", "width": 95},
		{"fieldname": "due_date", "label": _("กำหนดคืน"), "fieldtype": "Date", "width": 95},
		{"fieldname": "days_overdue", "label": _("เกินกำหนด (วัน)"), "fieldtype": "Int", "width": 110},
	]


def get_data(filters):
	parent = frappe.qb.DocType("Equipment Borrowing")
	child = frappe.qb.DocType("Equipment Borrowing Item")
	query = (
		frappe.qb.from_(child)
		.join(parent)
		.on(child.parent == parent.name)
		.select(
			parent.name.as_("equipment_borrowing"),
			parent.borrower_type,
			parent.borrower_name,
			parent.supplier,
			parent.project,
			parent.date,
			parent.due_date,
			child.item_code,
			child.item_name,
			child.outstanding_qty,
			child.uom,
		)
		.where((parent.docstatus == 1) & (child.outstanding_qty > 0))
	)
	for field in ("company", "project", "supplier", "borrower_type"):
		if filters.get(field):
			query = query.where(parent[field] == filters.get(field))
	today = getdate(nowdate())
	if filters.overdue_only:
		query = query.where(parent.due_date < today)
	rows = query.run(as_dict=True)
	suppliers = {row.supplier for row in rows if row.supplier}
	supplier_names = (
		dict(frappe.get_all("Supplier", filters={"name": ("in", list(suppliers))}, fields=["name", "supplier_name"], as_list=True))
		if suppliers
		else {}
	)
	for row in rows:
		row.responsible = supplier_names.get(row.supplier, row.supplier) if row.supplier else row.borrower_name
		row.days_overdue = max(date_diff(today, row.due_date), 0) if row.due_date else 0
		row.borrower_type = _(BORROWER_TYPES.get(row.borrower_type, row.borrower_type))
	rows.sort(key=lambda row: (row.responsible or "", str(row.due_date or "9999"), row.equipment_borrowing))
	return rows
