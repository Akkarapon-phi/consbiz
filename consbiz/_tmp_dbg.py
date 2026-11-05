import frappe

from consbiz.consbiz.doctype.construction_management.construction_management import create_from_boq


def run():
	try:
		boq = frappe.new_doc("BOQ")
		boq.naming_series = frappe.get_meta("BOQ").get_field("naming_series").options.split("\n")[0]
		boq.date = "2026-11-02"
		for row in (
			{"wbs": "1", "item_name": "หมวด", "quantity": 0},
			{"wbs": "1.1", "item_name": "งานมีปริมาณ", "quantity": 10, "total_amount": 3000},
			{"wbs": "1.2", "item_name": "งานเหมา", "quantity": 0, "total_amount": 1000},
		):
			boq.append("boq_details", row)
		boq.insert()
		print("boq", [(r.wbs, r.quantity, r.get("total_amount"), r.get("amount")) for r in boq.boq_details])
		cm = frappe.get_doc("Construction Management", create_from_boq(boq.name))
		print(
			"cm",
			cm.total_amount,
			cm.revised_amount,
			[(t.wbs, t.is_group, t.amount, t.contract_amount, t.rate, t.weight) for t in cm.tasks],
		)
	finally:
		frappe.db.rollback()
