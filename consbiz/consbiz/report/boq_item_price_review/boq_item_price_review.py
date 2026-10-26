# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

"""ทบทวนราคามาตรฐาน BOQ Item จากราคาที่ใช้จริงใน BOQ ช่วงเวลาหนึ่ง (ค่าเริ่มต้น 1 ปี)

หนึ่งแถวต่อรายการต่อประเภทราคา (ค่าวัสดุ/ค่าแรง) เทียบราคามาตรฐานกับค่ามัธยฐานของ BOQ
- ใช้ค่ามัธยฐาน ไม่ใช่ค่าเฉลี่ย เพื่อไม่ให้ BOQ ราคาพิเศษใบเดียวดึงค่าไป
- นับ 1 ค่าต่อ BOQ (รายการซ้ำในใบเดียวกันใช้ค่าเฉลี่ยของใบนั้น) และไม่นับราคา 0 (ไม่มีค่าวัสดุ/ค่าแรงในใบนั้น)
- ค่าเริ่มต้นนับเฉพาะ BOQ ที่ Submit แล้ว
"""

from statistics import mean, median

import frappe
from frappe import _
from frappe.query_builder.functions import Coalesce
from frappe.utils import add_days, add_years, flt, getdate, today

RATE_TYPES = (("material_rate", "ค่าวัสดุ"), ("labour_rate", "ค่าแรง"))
RATE_FIELDS = tuple(field for field, _label in RATE_TYPES)
DEFAULT_THRESHOLD = 10
DEFAULT_MIN_BOQ = 3

# สถานะ -> (ข้อความ, สี indicator, ลำดับในรายงาน)
STATUS = {
	"review": ("ควรทบทวน", "orange", 0),
	"few": ("ข้อมูลน้อย", "gray", 1),
	"ok": ("ปกติ", "green", 2),
}


def execute(filters=None):
	filters = frappe._dict(filters or {})
	return get_columns(), get_data(filters)


def get_columns():
	def rate(fieldname, label, width=110):
		return {
			"fieldname": fieldname,
			"label": _(label),
			"fieldtype": "Float",
			"precision": 2,
			"width": width,
		}

	return [
		{
			"fieldname": "item_code",
			"label": _("รหัสรายการ"),
			"fieldtype": "Link",
			"options": "BOQ Item",
			"width": 100,
		},
		{"fieldname": "item_name", "label": _("รายการ"), "fieldtype": "Data", "width": 240},
		{"fieldname": "item_group", "label": _("กลุ่มงาน"), "fieldtype": "Data", "width": 120},
		{"fieldname": "rate_type", "label": _("ประเภทราคา"), "fieldtype": "Data", "width": 90},
		rate("standard_rate", "ราคามาตรฐาน", 120),
		{"fieldname": "boq_count", "label": _("จำนวน BOQ"), "fieldtype": "Int", "width": 90},
		rate("median_rate", "มัธยฐาน"),
		rate("min_rate", "ต่ำสุด"),
		rate("max_rate", "สูงสุด"),
		rate("last_rate", "ล่าสุด"),
		{"fieldname": "diff_percent", "label": _("ส่วนต่าง %"), "fieldtype": "Percent", "width": 100},
		{"fieldname": "status", "label": _("สถานะ"), "fieldtype": "Data", "width": 110},
		{"fieldname": "rate_field", "label": "rate_field", "fieldtype": "Data", "hidden": 1},
	]


def get_data(filters) -> list[dict]:
	threshold = flt(filters.threshold) if filters.threshold is not None else DEFAULT_THRESHOLD
	min_boq = int(filters.min_boq) if filters.min_boq else DEFAULT_MIN_BOQ

	item_filters = {"item_group": filters.item_group} if filters.item_group else {}
	items = frappe.get_all(
		"BOQ Item", filters=item_filters, fields=["name", "item_name", "item_group", *RATE_FIELDS]
	)
	samples = get_boq_rates(filters, [item.name for item in items])

	data = []
	for item in items:
		for rate_field, rate_label in RATE_TYPES:
			# ค่าต่อ BOQ เรียงตามวันที่: [(date, rate)]
			per_boq = []
			for date, rates in samples.get((item.name, rate_field), {}).values():
				rates = [rate for rate in rates if rate]
				if rates:
					per_boq.append((date, mean(rates)))
			per_boq.sort()
			if not per_boq:
				continue
			values = [rate for _date, rate in per_boq]
			standard = flt(item.get(rate_field))
			median_rate = median(values)
			diff = (median_rate - standard) / standard * 100 if standard else None

			if len(values) < min_boq:
				status = "few"
			elif diff is None or abs(diff) >= threshold:
				status = "review"
			else:
				status = "ok"
			if filters.only_review and status != "review":
				continue

			label, color, order = STATUS[status]
			data.append(
				{
					"item_code": item.name,
					"item_name": item.item_name,
					"item_group": item.item_group,
					"rate_type": _(rate_label),
					"rate_field": rate_field,
					"standard_rate": standard,
					"boq_count": len(values),
					"median_rate": median_rate,
					"min_rate": min(values),
					"max_rate": max(values),
					"last_rate": values[-1],
					"diff_percent": diff,
					"status": _(label),
					"status_color": color,
					"_order": order,
				}
			)

	data.sort(key=lambda row: (row.pop("_order"), -abs(row["diff_percent"] or 0)))
	return data


def get_boq_rates(filters, item_codes: list[str]) -> dict:
	"""{(item_code, rate_field): {boq: (date, [rates])}} จาก BOQ ในช่วงวันที่"""
	if not item_codes:
		return {}
	from_date = getdate(filters.from_date or add_years(today(), -1))
	to_date = getdate(filters.to_date or today())

	detail = frappe.qb.DocType("BOQ Item Detail")
	boq = frappe.qb.DocType("BOQ")
	boq_date = Coalesce(boq.date, boq.creation)
	docstatus = boq.docstatus < 2 if filters.include_draft else boq.docstatus == 1
	rows = (
		frappe.qb.from_(detail)
		.join(boq)
		.on(detail.parent == boq.name)
		.select(
			detail.item_code, boq.name.as_("boq"), boq_date.as_("date"), *(detail[f] for f in RATE_FIELDS)
		)
		.where(
			(detail.parenttype == "BOQ")
			& detail.item_code.isin(item_codes)
			& docstatus
			& (boq_date >= from_date)
			& (boq_date < add_days(to_date, 1))
		)
		.run(as_dict=True)
	)

	samples = {}
	for row in rows:
		for rate_field in RATE_FIELDS:
			per_boq = samples.setdefault((row.item_code, rate_field), {})
			per_boq.setdefault(row.boq, (getdate(row.date), []))[1].append(flt(row.get(rate_field)))
	return samples


@frappe.whitelist()
def update_standard_rates(updates: list[dict] | str) -> int:
	"""ตั้งราคามาตรฐานจากรายงาน: [{"item_code", "rate_field", "rate"}] (ประวัติการเปลี่ยนอยู่ใน timeline ของ BOQ Item)"""
	by_item = {}
	for update in frappe.parse_json(updates):
		if update.get("rate_field") not in RATE_FIELDS:
			frappe.throw(_("ประเภทราคาไม่ถูกต้อง"))
		if flt(update.get("rate")) < 0:
			frappe.throw(_("ราคาของ {0} ต้องไม่ติดลบ").format(update.get("item_code")))
		by_item.setdefault(update["item_code"], {})[update["rate_field"]] = flt(update["rate"])

	for item_code, values in by_item.items():
		item = frappe.get_doc("BOQ Item", item_code)
		item.update(values)
		item.save()  # ตรวจสิทธิ์เขียน BOQ Item ของผู้ใช้
	return sum(len(values) for values in by_item.values())
