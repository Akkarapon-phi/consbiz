# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

"""สรุปการใช้คอนกรีตจาก Concrete Usage ที่ Submit แล้ว

- ค่าเริ่มต้น 1 แถวต่อการเท (เอกสาร): ปริมาณรวม แยกซื้อเอง / ผู้ว่าจ้างจัดหา เทียบปริมาณตามแบบ
- ติ๊ก "แสดงรายตั๋ว": 1 แถวต่อตั๋วรถ ใช้ตรวจกับใบแจ้งหนี้ผู้ขาย (ซื้อเอง) หรือยอดหักงวดงาน (ผู้ว่าจ้างจัดหา)
- กรองแหล่ง: นับเฉพาะตั๋วของแหล่งนั้น
"""

import frappe
from frappe import _
from frappe.utils import flt

SUPPLY_COMPANY = "Company"
SUPPLY_EMPLOYER = "Employer"


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if filters.show_tickets:
		return ticket_columns(), ticket_rows(filters)
	return usage_columns(), usage_rows(filters)


def base_columns():
	return [
		{"fieldname": "date", "label": _("วันที่"), "fieldtype": "Date", "width": 95},
		{"fieldname": "concrete_usage", "label": _("เอกสาร"), "fieldtype": "Link", "options": "Concrete Usage", "width": 140},
		{"fieldname": "project", "label": _("โครงการ"), "fieldtype": "Link", "options": "Project", "width": 110},
		{"fieldname": "wbs", "label": _("WBS"), "fieldtype": "Data", "width": 70},
		{"fieldname": "task_name", "label": _("งาน"), "fieldtype": "Data", "width": 200},
		{"fieldname": "location", "label": _("ตำแหน่ง"), "fieldtype": "Data", "width": 140},
	]


def usage_columns():
	return base_columns() + [
		{"fieldname": "concrete_item", "label": _("คอนกรีต"), "fieldtype": "Link", "options": "Item", "width": 120},
		{"fieldname": "concrete_item_name", "label": _("ชื่อคอนกรีต"), "fieldtype": "Data", "width": 220},
		{"fieldname": "supplier", "label": _("ผู้ขาย"), "fieldtype": "Link", "options": "Supplier", "width": 140},
		{"fieldname": "trucks", "label": _("จำนวนรถ"), "fieldtype": "Int", "width": 80},
		{"fieldname": "qty", "label": _("ใช้จริง (คิว)"), "fieldtype": "Float", "width": 100},
		{"fieldname": "company_qty", "label": _("ซื้อเอง (คิว)"), "fieldtype": "Float", "width": 100},
		{"fieldname": "employer_qty", "label": _("ผู้ว่าจ้างจัดหา (คิว)"), "fieldtype": "Float", "width": 130},
		{"fieldname": "planned_qty", "label": _("ตามแบบ (คิว)"), "fieldtype": "Float", "width": 100},
		{"fieldname": "variance", "label": _("ส่วนต่าง (คิว)"), "fieldtype": "Float", "width": 100},
	]


def ticket_columns():
	return base_columns() + [
		{"fieldname": "supplier", "label": _("ผู้ขาย"), "fieldtype": "Link", "options": "Supplier", "width": 140},
		{"fieldname": "ticket_no", "label": _("เลขตั๋ว"), "fieldtype": "Data", "width": 100},
		{"fieldname": "vehicle_no", "label": _("ทะเบียนรถ"), "fieldtype": "Data", "width": 95},
		{"fieldname": "arrive_time", "label": _("เวลาถึง"), "fieldtype": "Time", "width": 80},
		{"fieldname": "qty", "label": _("ปริมาณ (คิว)"), "fieldtype": "Float", "width": 100},
		{"fieldname": "supply", "label": _("แหล่ง"), "fieldtype": "Data", "width": 110},
		{"fieldname": "slump", "label": _("Slump (ซม.)"), "fieldtype": "Float", "width": 90},
		{"fieldname": "samples", "label": _("ก้อนตัวอย่าง"), "fieldtype": "Int", "width": 90},
		{"fieldname": "remarks", "label": _("หมายเหตุ"), "fieldtype": "Data", "width": 180},
	]


def fetch_tickets(filters):
	parent = frappe.qb.DocType("Concrete Usage")
	child = frappe.qb.DocType("Concrete Usage Ticket")
	item = frappe.qb.DocType("Item")
	query = (
		frappe.qb.from_(child)
		.join(parent)
		.on(child.parent == parent.name)
		.left_join(item)
		.on(item.name == parent.concrete_item)
		.select(
			parent.name.as_("concrete_usage"),
			parent.date,
			parent.project,
			parent.wbs,
			parent.task_name,
			parent.location,
			parent.concrete_item,
			item.item_name.as_("concrete_item_name"),
			parent.supplier,
			parent.planned_qty,
			child.ticket_no,
			child.vehicle_no,
			child.arrive_time,
			child.qty,
			child.employer_supplied,
			child.slump,
			child.samples,
			child.remarks,
		)
		.where(parent.docstatus == 1)
		.orderby(parent.date)
		.orderby(parent.name)
		.orderby(child.idx)
	)
	for field in ("company", "project", "construction_management", "supplier", "concrete_item"):
		if filters.get(field):
			query = query.where(parent[field] == filters.get(field))
	if filters.from_date:
		query = query.where(parent.date >= filters.from_date)
	if filters.to_date:
		query = query.where(parent.date <= filters.to_date)
	if filters.supply:
		query = query.where(child.employer_supplied == (1 if filters.supply == SUPPLY_EMPLOYER else 0))
	return query.run(as_dict=True)


def supply_label(employer_supplied):
	return _("ผู้ว่าจ้างจัดหา") if employer_supplied else _("ซื้อเอง")


def ticket_rows(filters):
	rows = fetch_tickets(filters)
	for row in rows:
		row.supply = supply_label(row.employer_supplied)
	return rows


def usage_rows(filters):
	result = {}
	for ticket in fetch_tickets(filters):
		row = result.get(ticket.concrete_usage)
		if not row:
			row = result[ticket.concrete_usage] = frappe._dict(
				{key: ticket[key] for key in ("concrete_usage", "date", "project", "wbs", "task_name", "location", "concrete_item", "concrete_item_name", "supplier", "planned_qty")},
				trucks=0,
				qty=0.0,
				company_qty=0.0,
				employer_qty=0.0,
			)
		row.trucks += 1
		row.qty += flt(ticket.qty)
		row["employer_qty" if ticket.employer_supplied else "company_qty"] += flt(ticket.qty)
	for row in result.values():
		row.variance = row.qty - flt(row.planned_qty) if flt(row.planned_qty) else None
	return list(result.values())
