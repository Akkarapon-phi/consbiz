# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

"""วิเคราะห์ความล่าช้าของแผนงาน ณ วันที่เลือก: งานที่ช้ากว่าแผน งานวิกฤต วันเสร็จที่คาดการณ์ และค่าปรับ
การคำนวณอยู่ใน construction_management/delay.py"""

import frappe
from frappe import _

from consbiz.consbiz.doctype.construction_management.delay import STATUS, analyse, penalty_warning


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.construction_management:
		return get_columns(), []
	doc = frappe.get_doc("Construction Management", filters.construction_management)
	doc.check_permission("read")
	result = analyse(doc, filters.date or frappe.utils.today())
	rows = [row for row in result["tasks"] if not filters.only_issues or is_issue(row)]
	for row in rows:
		row.status_label, row.status_color = STATUS[row.status]
		row.status_label = _(row.status_label)
	rows.sort(key=lambda row: (not row.critical, -row.delay_days, row.variance))
	summary = result["summary"]
	baseline = any(row.baseline_start_date for row in doc.tasks)
	return get_columns(baseline), rows, penalty_warning(summary), None, get_summary(summary, doc)


def is_issue(row):
	return row.status in ("behind", "not_started", "overdue") or row.delay_days > 0


def get_columns(baseline=False):
	# เทียบกับ Baseline ถ้าตั้งไว้แล้ว ไม่งั้นแผนปัจจุบัน (delay.target_dates)
	basis = _("แผนสัญญา") if baseline else _("แผน")

	def column(fieldname, label, fieldtype, width, **extra):
		return {"fieldname": fieldname, "label": label, "fieldtype": fieldtype, "width": width, **extra}

	return [
		column("wbs", _("WBS"), "Data", 70),
		column("item_name", _("รายการ"), "Data", 240),
		column("status_label", _("สถานะ"), "Data", 170),
		column("critical", _("งานวิกฤต"), "Check", 80),
		column("total_float", _("Float (วัน)"), "Int", 80),
		column("start_date", _("วันเริ่ม ({0})").format(basis), "Date", 105),
		column("end_date", _("วันจบ ({0})").format(basis), "Date", 105),
		column("plan_pct", _("% {0}").format(basis), "Percent", 80),
		column("actual_pct", _("% จริง"), "Percent", 80),
		column("variance", _("ต่าง (%)"), "Float", 80, precision=2),
		column("forecast_end", _("คาดว่าเสร็จ"), "Date", 105),
		column("delay_days", _("ล่าช้า (วัน)"), "Int", 90),
	]


def get_summary(summary, doc):
	currency = frappe.get_cached_value("Company", doc.company, "default_currency") if doc.company else None
	late = summary.overrun_days > 0
	return [
		{"label": _("สิ้นสุดสัญญาปรับปรุง"), "value": summary.contract_finish, "datatype": "Date"},
		{
			"label": _("ส่งมอบงานจริง") if summary.handover_date else _("คาดว่าเสร็จ"),
			"value": summary.handover_date or summary.forecast_finish,
			"datatype": "Date",
			"indicator": "Red" if late else "Green",
		},
		{
			"label": _("เกินกำหนด (วัน)"),
			"value": summary.overrun_days,
			"datatype": "Int",
			"indicator": "Red" if late else "Green",
		},
		{
			"label": _("ค่าปรับคาดการณ์"),
			"value": summary.penalty,
			"datatype": "Currency",
			"currency": currency,
			"indicator": "Red" if summary.penalty else "Green",
		},
	]
