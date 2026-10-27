# เดิมแผนงานมี Baseline ได้ชุดเดียว เก็บในช่อง baseline_* ของแถวงาน
# ย้ายเป็น Construction Baseline ชุดแรก แล้วตั้งเป็นชุดที่ใช้เทียบ (active_baseline) ค่าในแถวงานไม่เปลี่ยน

import frappe
from frappe.utils import flt


def execute():
	for name in frappe.get_all(
		"Construction Management", filters={"active_baseline": ("is", "not set")}, pluck="name"
	):
		doc = frappe.get_doc("Construction Management", name)
		if not any(row.baseline_start_date for row in doc.tasks):
			continue
		# baseline ที่ตั้งก่อนมีการเก็บน้ำหนักใช้น้ำหนักปัจจุบัน (เหมือน plan_progress)
		weight_key = "baseline_weight" if any(flt(row.baseline_weight) for row in doc.tasks) else "weight"
		tasks = {
			row.name: [
				str(row.baseline_start_date) if row.baseline_start_date else None,
				str(row.baseline_end_date) if row.baseline_end_date else None,
				row.baseline_distribution or None,
				flt(row.get(weight_key)),
			]
			for row in doc.tasks
		}
		baseline = frappe.get_doc(
			{
				"doctype": "Construction Baseline",
				"construction_management": name,
				"title": "Baseline",
				"baseline_date": doc.baseline_date or doc.creation,
				"tasks": frappe.as_json(tasks, indent=None),
			}
		).insert(ignore_permissions=True)
		doc.db_set("active_baseline", baseline.name, update_modified=False)
