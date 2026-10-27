# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.query_builder.functions import Coalesce
from frappe.utils import getdate

HISTORY_LIMIT = 30


class BOQItem(Document):
	pass


@frappe.whitelist()
def get_price_history(item_code: str) -> dict:
	"""ราคาของรายการนี้ใน BOQ ที่ยังไม่ยกเลิก เรียงจากเก่าไปใหม่ (ล่าสุด HISTORY_LIMIT ใบ) พร้อมราคามาตรฐาน"""
	item = frappe.get_doc("BOQ Item", item_code)
	item.check_permission("read")
	frappe.has_permission("BOQ", "read", throw=True)

	detail = frappe.qb.DocType("BOQ Item Detail")
	boq = frappe.qb.DocType("BOQ")
	boq_date = Coalesce(boq.date, boq.creation)
	history = (
		frappe.qb.from_(detail)
		.join(boq)
		.on(detail.parent == boq.name)
		.select(
			boq.name.as_("boq"),
			boq_date.as_("date"),
			boq.project,
			boq.customer,
			boq.docstatus,
			detail.material_rate,
			detail.labour_rate,
		)
		.where(
			(detail.parenttype == "BOQ")
			& (detail.item_code == item_code)
			& (detail.combined_rate == 0)  # ราคารวม แยกค่าวัสดุ/ค่าแรงไม่ได้ ไม่นำมาเทียบ
			& (boq.docstatus < 2)
		)
		.orderby(boq_date, order=frappe.qb.desc)
		.orderby(boq.name, order=frappe.qb.desc)
		.limit(HISTORY_LIMIT)
		.run(as_dict=True)
	)
	for row in history:
		row.date = getdate(row.date)
	history.reverse()

	return {
		"item_name": item.item_name,
		"material_rate": item.material_rate,
		"labour_rate": item.labour_rate,
		"history": history,
	}
