# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

"""Earned Value ของแผนงานรายช่วง (PV / EV / AC สะสม, SPI, CPI) และ EAC ณ วันที่เลือก
เห็นต้นทุนจริงและงบต้นทุน จึงให้สิทธิ์เฉพาะ Projects Manager การคำนวณอยู่ใน construction_management/evm.py"""

import frappe
from frappe import _
from frappe.utils import flt

from consbiz.consbiz.doctype.construction_management.evm import evm_series


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.construction_management:
		return get_columns(), []
	doc = frappe.get_doc("Construction Management", filters.construction_management)
	doc.check_permission("read")
	series = evm_series(doc, filters.to_date or frappe.utils.today(), filters.periodicity or "Monthly")
	currency = frappe.get_cached_value("Company", doc.company, "default_currency") if doc.company else None
	for row in series:
		row.currency = currency
	message = None
	if not flt(doc.budget_cost):
		message = _("ยังไม่ได้กรอกงบประมาณต้นทุนในแผนงาน BAC ใช้มูลค่าสัญญา CPI จึงสะท้อนกำไรแทนประสิทธิภาพต้นทุน")
	if not doc.project:
		message = _("แผนงานยังไม่ได้ผูก Project จึงไม่มีต้นทุนจริง (AC)")
	return (
		get_columns(),
		series,
		message,
		get_chart(series),
		get_summary(series[-1], currency) if series else [],
	)


def get_columns():
	def money(fieldname, label):
		return {
			"fieldname": fieldname,
			"label": label,
			"fieldtype": "Currency",
			"options": "currency",
			"width": 130,
		}

	def ratio(fieldname, label):
		return {"fieldname": fieldname, "label": label, "fieldtype": "Float", "precision": 2, "width": 80}

	return [
		{"fieldname": "date", "label": _("ณ วันที่"), "fieldtype": "Date", "width": 100},
		{"fieldname": "plan", "label": _("% แผน"), "fieldtype": "Percent", "width": 80},
		{"fieldname": "actual", "label": _("% จริง"), "fieldtype": "Percent", "width": 80},
		money("pv", _("PV (มูลค่าตามแผน)")),
		money("ev", _("EV (มูลค่างานที่ทำได้)")),
		money("ac", _("AC (ต้นทุนจริง)")),
		money("sv", _("SV")),
		money("cv", _("CV")),
		ratio("spi", _("SPI")),
		ratio("cpi", _("CPI")),
		money("eac", _("EAC")),
		{"fieldname": "currency", "label": _("Currency"), "fieldtype": "Link", "options": "Currency", "hidden": 1},
	]


def get_chart(series):
	return {
		"data": {
			"labels": [frappe.format(row.date, "Date") for row in series],
			"datasets": [
				{"name": _("PV"), "values": [flt(row.pv, 2) for row in series]},
				{"name": _("EV"), "values": [flt(row.ev, 2) for row in series]},
				{"name": _("AC"), "values": [flt(row.ac, 2) for row in series]},
			],
		},
		"type": "line",
		"fieldtype": "Currency",
	}


def get_summary(last, currency):
	"""ค่าที่ยังคิดไม่ได้ (เช่น ยังไม่มีต้นทุนจริง) แสดง "-" """

	def item(label, value, datatype, good=None):
		if value is None:
			return {"label": label, "value": "-", "datatype": "Data", "indicator": "Gray"}
		result = {"label": label, "value": value, "datatype": datatype}
		if datatype == "Currency":
			result["currency"] = currency
		if good is not None:
			result["indicator"] = "Green" if good else "Red"
		return result

	def ratio(label, value):
		return item(label, None if value is None else flt(value, 2), "Float", value is not None and value >= 1)

	return [
		ratio(_("SPI"), last.spi),
		ratio(_("CPI"), last.cpi),
		item(_("BAC"), last.bac, "Currency"),
		item(_("EAC (คาดว่าต้นทุนรวม)"), last.eac, "Currency", last.eac is not None and last.eac <= last.bac),
		item(_("VAC"), last.vac, "Currency", last.vac is not None and last.vac >= 0),
	]
