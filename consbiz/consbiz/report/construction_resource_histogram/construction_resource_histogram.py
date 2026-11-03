# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

"""แผนทรัพยากรเทียบกับที่ใช้จริง (แรงงาน คน-วัน / เครื่องจักร คัน-วัน) รายช่วง
แผนจาก Construction Resource Plan × วันทำงานของงาน, จริงจาก Daily Report ที่ Submit แล้ว"""

import frappe
from frappe import _
from frappe.utils import add_days, flt, getdate

from consbiz.consbiz.doctype.construction_management.construction_management import (
	floor_period,
	next_period,
)
from consbiz.consbiz.doctype.construction_resource_plan.construction_resource_plan import (
	actual_resources,
	planned_resources,
)

PERIOD_UNITS = {"Daily": "day", "Weekly": "week", "Monthly": "month"}
RESOURCE_TYPES = {"Labour": "แรงงาน", "Equipment": "เครื่องจักร"}


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.construction_management:
		return get_columns(), []
	frappe.get_doc("Construction Management", filters.construction_management).check_permission("read")
	start, end = getdate(filters.from_date), getdate(filters.to_date)
	unit = PERIOD_UNITS.get(filters.periodicity, "week")
	planned = planned_resources(filters.construction_management, start, end)
	actual = actual_resources(filters.construction_management, start, end)

	rows, totals = {}, {}
	for source, values in (("planned", planned), ("actual", actual)):
		for (resource_type, resource, day), qty in values.items():
			if filters.resource_type and resource_type != filters.resource_type:
				continue
			period = floor_period(day, unit)
			row = rows.setdefault(
				(period, resource_type, resource),
				frappe._dict(
					period=period,
					period_end=min(getdate(add_days(next_period(period, unit), -1)), end),
					resource_type=_(RESOURCE_TYPES[resource_type]),
					resource=resource,
					planned=0,
					actual=0,
				),
			)
			row[source] += qty
			total = totals.setdefault(period, {"planned": 0, "actual": 0})
			total[source] += qty

	data = sorted(rows.values(), key=lambda row: (row.period, row.resource_type, row.resource))
	for row in data:
		row.variance = row.actual - row.planned
	return get_columns(), data, None, get_chart(totals)


def get_columns():
	def number(fieldname, label):
		return {"fieldname": fieldname, "label": label, "fieldtype": "Float", "precision": 1, "width": 110}

	return [
		{"fieldname": "period", "label": _("ตั้งแต่"), "fieldtype": "Date", "width": 100},
		{"fieldname": "period_end", "label": _("ถึง"), "fieldtype": "Date", "width": 100},
		{"fieldname": "resource_type", "label": _("ชนิด"), "fieldtype": "Data", "width": 90},
		{"fieldname": "resource", "label": _("ทรัพยากร"), "fieldtype": "Data", "width": 180},
		number("planned", _("แผน (วัน)")),
		number("actual", _("ใช้จริง (วัน)")),
		number("variance", _("ต่าง")),
	]


def get_chart(totals):
	periods = sorted(totals)
	return {
		"data": {
			"labels": [frappe.format(period, "Date") for period in periods],
			"datasets": [
				{"name": _("แผน"), "values": [flt(totals[p]["planned"], 1) for p in periods]},
				{"name": _("ใช้จริง"), "values": [flt(totals[p]["actual"], 1) for p in periods]},
			],
		},
		"type": "bar",
	}
