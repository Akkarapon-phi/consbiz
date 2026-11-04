# Copyright (c) 2026, Siricons and contributors
# For license information, please see license.txt

# ข้อมูล Tab "การเงิน" ของ Construction Management (Vue: public/js/project_dashboard/Finance.vue)
# - Cash Flow รายเดือน: Cash Plan = % แผนปัจจุบัน x มูลค่าสัญญาปรับปรุง (ตรงกับแถว Cash Plan ของตารางสรุปในหน้า Gantt)
#   Cash Actual = มูลค่างานที่ทำได้จริง (Progress Entry x มูลค่างาน) งานเพิ่มนับตั้งแต่วันที่อนุมัติ (ตรงกับ actual_curve)
#   เดือนหลังวันที่ดูไม่มีค่าจริง
# - EVM (PV/EV/AC) และต้นทุนตามหมวด (cost.py) เฉพาะผู้ที่เห็นงบต้นทุน (budget_cost permlevel 1)

import frappe
from frappe.utils import add_days, flt, getdate, nowdate

from consbiz.consbiz.doctype.construction_management.construction_management import (
	PROGRESS_ENTRY,
	floor_period,
	is_counted,
	next_period,
	plan_progress,
)
from consbiz.consbiz.doctype.construction_management.cost import cost_control
from consbiz.consbiz.doctype.construction_management.evm import evm_series


@frappe.whitelist()
def get_finance(name, date=None):
	doc = frappe.get_doc("Construction Management", name)
	doc.check_permission("read")
	day = getdate(date or nowdate())
	show_cost = doc.has_permlevel_access_to("budget_cost")
	series = evm_series(doc, day) if show_cost else []
	months = cash_flow(doc, day)
	current = next((row for row in reversed(months) if row["actual_cum"] is not None), None)
	return {
		"date": day,
		"currency": frappe.db.get_value("Company", doc.company, "default_currency") if doc.company else None,
		"contract": {
			"total_amount": doc.total_amount,
			"revised_amount": doc.revised_amount,
			"variation_amount": doc.variation_amount,
		},
		"summary": {
			"plan": current["plan_at_date"] if current else 0,
			"actual": current["actual_cum"] if current else 0,
		},
		"months": months,
		"evm": evm_values(series) if series else None,
		"cost": cost_control(doc, day) if show_cost else None,
	}


def cash_flow(doc, day):
	"""รายเดือนตั้งแต่เดือนที่เริ่มถึงเดือนที่จบของแผน (หรือเดือนของวันที่ดู ถ้าเลยแผนแล้ว)
	[{month, plan, plan_cum, actual, actual_cum, variance, plan_at_date}] ค่า actual เป็น None หลังวันที่ดู"""
	tasks = [row for row in doc.tasks if not row.is_group]
	starts = [getdate(row.start_date) for row in tasks if row.start_date]
	ends = [getdate(row.end_date) for row in tasks if row.end_date]
	start = getdate(doc.start_date) if doc.start_date else min(starts, default=None)
	if not start:
		return []
	end = max([*ends, *(getdate(d) for d in (doc.finish_date, doc.revised_finish_date) if d), start, day])
	amount = flt(doc.revised_amount) or flt(doc.total_amount)
	earned = earned_by_day(doc, day)

	rows = []
	plan_before = actual_before = 0
	period = floor_period(start, "month")
	while period <= end:
		month_end = getdate(add_days(next_period(period, "month"), -1))
		plan_cum = plan_progress(doc, month_end) / 100 * amount
		row = {
			"month": period,
			"month_end": month_end,
			"plan": plan_cum - plan_before,
			"plan_cum": plan_cum,
			"actual": None,
			"actual_cum": None,
			"variance": None,
			"plan_at_date": None,
		}
		if period <= day:
			cutoff = min(month_end, day)
			actual_cum = sum(value for d, value in earned.items() if d <= cutoff)
			# เดือนของวันที่ดู: เทียบกับแผน ณ วันที่ดู ไม่ใช่สิ้นเดือน
			plan_at_date = plan_progress(doc, cutoff) / 100 * amount if cutoff < month_end else plan_cum
			row.update(
				actual=actual_cum - actual_before,
				actual_cum=actual_cum,
				variance=actual_cum - plan_at_date,
				plan_at_date=plan_at_date,
			)
			actual_before = actual_cum
		rows.append(row)
		plan_before = plan_cum
		period = next_period(period, "month")
	return rows


def earned_by_day(doc, day):
	"""{วันที่: มูลค่างานที่ทำได้} ถึงวัน day งานเพิ่มที่ลงก่อนวันอนุมัติ นับที่วันอนุมัติ (counted_from)"""
	leaves = {row.name: row for row in doc.tasks if not row.is_group and is_counted(row)}
	result = {}
	for entry in frappe.get_all(
		PROGRESS_ENTRY,
		filters={"construction_management": doc.name, "date": ("<=", day)},
		fields=["task", "date", "percent"],
	):
		task = leaves.get(entry.task)
		if not task:
			continue
		date = getdate(entry.date)
		if task.counted_from and date < getdate(task.counted_from):
			date = getdate(task.counted_from)
		if date > day:
			continue
		result[date] = result.get(date, 0) + flt(task.amount) * flt(entry.percent) / 100
	return result


def evm_values(series):
	last = series[-1]
	return {
		**{k: last[k] for k in ("bac", "pv", "ev", "ac", "spi", "cpi", "eac", "vac")},
		"series": [{"date": row.date, "pv": row.pv, "ev": row.ev, "ac": row.ac} for row in series],
	}
