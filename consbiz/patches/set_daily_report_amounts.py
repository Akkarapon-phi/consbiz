# รายงานประจำวันที่บันทึกก่อนแก้ ราคาต่อหน่วยและมูลค่าเป็น 0 เพราะตอนนั้นไม่ได้ดึงจากงานในแผน
# เติมจากงานในแผน (มูลค่า = มูลค่างาน x % ของแถว) ไม่แตะปริมาณ/% และรายการความคืบหน้า

import frappe
from frappe.utils import flt


def execute():
	rows = frappe.get_all(
		"Daily Report Item",
		filters={"parenttype": "Daily Report", "rate": 0, "task": ("is", "set")},
		fields=["name", "parent", "task", "percent"],
	)
	tasks = (
		{
			task.name: task
			for task in frappe.get_all(
				"Construction Management Task",
				filters={"name": ("in", list({row.task for row in rows}))},
				fields=["name", "rate", "amount"],
			)
		}
		if rows
		else {}
	)

	reports = set()
	for row in rows:
		task = tasks.get(row.task)
		if not task:
			continue
		frappe.db.set_value(
			"Daily Report Item",
			row.name,
			{"rate": flt(task.rate), "amount": flt(task.amount) * flt(row.percent) / 100},
			update_modified=False,
		)
		reports.add(row.parent)

	for report in reports:
		total = sum(
			flt(amount)
			for amount in frappe.get_all(
				"Daily Report Item", filters={"parent": report, "parenttype": "Daily Report"}, pluck="amount"
			)
		)
		frappe.db.set_value("Daily Report", report, "total_amount", total, update_modified=False)
