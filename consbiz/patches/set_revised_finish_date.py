# แผนงานที่สร้างก่อนมี Extension of Time: วันสิ้นสุดสัญญาปรับปรุง = วันสิ้นสุดเดิม
# (บันทึกแผนงานครั้งถัดไป apply_extensions คำนวณค่าเดียวกันนี้เอง)

import frappe

PLAN = frappe.qb.DocType("Construction Management")


def execute():
	(
		frappe.qb.update(PLAN)
		.set(PLAN.revised_finish_date, PLAN.finish_date)
		.set(PLAN.revised_duration, PLAN.duration)
		.where(PLAN.revised_finish_date.isnull() & PLAN.finish_date.isnotnull())
	).run()
