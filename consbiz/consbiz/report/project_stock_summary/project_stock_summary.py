# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

"""คลังวัสดุของโครงการ 1 แถวต่อ Item หลัก (ข้อมูลเดียวกับ Tab "คลังวัสดุ" ของ Construction Management)

ส่วนซื้อเอง / ผู้ว่าจ้างจัดหา: ยังไม่ส่ง (สั่งแล้ว - รับแล้ว) รับเข้า เบิกออก คงเหลือ ของคลังที่ผูกโครงการ
ตามแผน = แผนวัสดุของแผนงานของโครงการ ยังไม่ได้ขอ = ตามแผน - ขอแล้ว หน่วยสต็อก ดู construction_management/stock.py
"""

import frappe
from frappe import _

from consbiz.consbiz.doctype.construction_management.stock import SOURCES, stock_items

SOURCE_LABELS = {"company": "ซื้อเอง", "employer": "ผู้ว่าจ้างจัดหา"}
SOURCE_FIELDS = (("pending", "ยังไม่ส่ง"), ("qty_in", "รับเข้า"), ("qty_out", "เบิกออก"), ("balance", "คงเหลือ"))


def execute(filters=None):
	filters = frappe._dict(filters or {})
	return get_columns(), get_data(filters)


def get_columns():
	def number(fieldname, label, width=100):
		return {"fieldname": fieldname, "label": _(label), "fieldtype": "Float", "width": width}

	columns = [
		{"fieldname": "item_code", "label": _("Item"), "fieldtype": "Link", "options": "Item", "width": 120},
		{"fieldname": "item_name", "label": _("วัสดุ"), "fieldtype": "Data", "width": 220},
		{"fieldname": "stock_uom", "label": _("หน่วย"), "fieldtype": "Link", "options": "UOM", "width": 70},
		number("need", "ตามแผน"),
	]
	for source in SOURCES:
		for field, label in SOURCE_FIELDS:
			columns.append(number(f"{source}_{field}", f"{label} ({SOURCE_LABELS[source]})", 130))
	columns += [number("balance", "คงเหลือรวม"), number("short", "ยังไม่ได้ขอ")]
	return columns


def get_data(filters):
	if not filters.project:
		return []
	rows = []
	for item in stock_items(filters.project)["items"]:
		row = {key: item[key] for key in ("item_code", "item_name", "stock_uom", "need", "balance", "short")}
		for source in SOURCES:
			for field, _label in SOURCE_FIELDS:
				row[f"{source}_{field}"] = item[source][field]
		rows.append(row)
	return rows
