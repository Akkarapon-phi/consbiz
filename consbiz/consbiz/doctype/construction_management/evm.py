# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

# Earned Value Management ของแผนงาน (รายงาน Construction Earned Value และ Dashboard)
# - BAC = งบต้นทุน (budget_cost) ถ้ากรอกไว้ ไม่งั้นมูลค่าสัญญาปรับปรุง (CPI จะสะท้อนกำไรแทนประสิทธิภาพต้นทุน)
# - PV = % แผน (Baseline ถ้าตั้งไว้แล้ว: target_progress) × BAC
# - EV = % จริง (actual_progress_at ตัวหาร ณ วันนั้น) × BAC
# - AC = ต้นทุนจริงจาก GL Entry บัญชีค่าใช้จ่าย (root_type Expense) ที่ผูก Project ของแผนงาน
#   ครอบคลุม Purchase Invoice, Journal Entry, Expense Claim, Stock Entry เบิกวัสดุ ฯลฯ ที่ใส่ Project

import frappe
from frappe.utils import add_days, flt, getdate

from consbiz.consbiz.doctype.construction_management.construction_management import (
	actual_progress_at,
	floor_period,
	next_period,
	target_progress,
)

PERIOD_UNITS = {"Weekly": "week", "Monthly": "month"}


def budget_at_completion(doc):
	return flt(doc.budget_cost) or flt(doc.revised_amount) or flt(doc.total_amount)


def actual_cost(doc, date):
	"""ต้นทุนจริงสะสมถึงสิ้นวัน date"""
	if not doc.project:
		return 0
	gl = frappe.qb.DocType("GL Entry")
	account = frappe.qb.DocType("Account")
	query = (
		frappe.qb.from_(gl)
		.join(account)
		.on(gl.account == account.name)
		.select(frappe.query_builder.functions.Sum(gl.debit - gl.credit))
		.where(
			(gl.project == doc.project)
			& (gl.is_cancelled == 0)
			& (account.root_type == "Expense")
			& (gl.posting_date <= getdate(date))
		)
	)
	if doc.company:
		query = query.where(gl.company == doc.company)
	return flt(query.run()[0][0])


def evm_at(doc, date):
	"""ค่า EVM ณ สิ้นวัน date"""
	bac = budget_at_completion(doc)
	plan = target_progress(doc, date)[0]
	actual = actual_progress_at(doc, date)[1]
	pv, ev, ac = bac * plan / 100, bac * actual / 100, actual_cost(doc, date)
	return frappe._dict(indices(date=getdate(date), bac=bac, pv=pv, ev=ev, ac=ac, plan=plan, actual=actual))


def indices(**values):
	"""SV, CV, SPI, CPI, EAC (= BAC / CPI), ETC, VAC, TCPI (ประสิทธิภาพต้นทุนที่ต้องทำได้กับงานที่เหลือ)"""
	bac, pv, ev, ac = values["bac"], values["pv"], values["ev"], values["ac"]
	spi = ev / pv if pv else None
	cpi = ev / ac if ac else None
	eac = bac / cpi if cpi else None
	return {
		**values,
		"sv": ev - pv,
		"cv": ev - ac,
		"spi": spi,
		"cpi": cpi,
		"eac": eac,
		"etc": eac - ac if eac is not None else None,
		"vac": bac - eac if eac is not None else None,
		"tcpi": (bac - ev) / (bac - ac) if bac - ac > 0 else None,
	}


def evm_series(doc, to_date, periodicity="Monthly"):
	"""ค่า EVM ณ สิ้นแต่ละช่วงตั้งแต่วันเริ่มสัญญา (หรืองานแรก) ถึง to_date"""
	unit = PERIOD_UNITS.get(periodicity, "month")
	end = getdate(to_date)
	starts = [getdate(row.start_date) for row in doc.tasks if not row.is_group and row.start_date]
	start = getdate(doc.start_date) if doc.start_date else min(starts, default=end)
	result = []
	period = floor_period(start, unit)
	while period <= end:
		period_end = min(getdate(add_days(next_period(period, unit), -1)), end)
		result.append(evm_at(doc, period_end))
		period = next_period(period, unit)
	return result
