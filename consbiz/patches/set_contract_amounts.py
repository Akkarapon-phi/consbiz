# แผนงานที่สร้างก่อนมี Variation Order: ค่าปัจจุบันคือค่าตามสัญญา
# เติม contract_quantity / contract_amount / counted_amount ของงานเดิม และ revised_amount ของแผนงาน
# (บันทึกแผนงานครั้งถัดไป apply_variations คำนวณค่าเดียวกันนี้เอง) ไม่แตะน้ำหนักและความคืบหน้า

import frappe

TASK = frappe.qb.DocType("Construction Management Task")
PLAN = frappe.qb.DocType("Construction Management")


def execute():
	(
		frappe.qb.update(TASK)
		.set(TASK.contract_quantity, TASK.quantity)
		.set(TASK.contract_amount, TASK.amount)
		.set(TASK.counted_amount, TASK.amount)
		.where(
			(TASK.parenttype == "Construction Management")
			& (TASK.is_group == 0)
			& (TASK.is_variation == 0)
			& (TASK.contract_quantity == 0)
			& (TASK.contract_amount == 0)
		)
	).run()
	(frappe.qb.update(PLAN).set(PLAN.revised_amount, PLAN.total_amount).where(PLAN.revised_amount == 0)).run()
