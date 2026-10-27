# Daily Report / Daily Request ที่บันทึกก่อนมีช่องเทียบความคืบหน้ากับแผน (Baseline)
# เติม % วันนี้ / % สะสม / % แผน / เร็ว-ช้ากว่าแผน จากแผนงานปัจจุบัน ไม่แตะรายการและรายการความคืบหน้า

import frappe

FIELDS = {
	"Daily Report": ("today_progress", "cumulative_progress", "baseline_progress", "plan_basis", "progress_variance"),
	"Daily Request": ("baseline_progress", "plan_basis", "progress_variance"),
}


def execute():
	for doctype, fields in FIELDS.items():
		for name in frappe.get_all(doctype, filters={"docstatus": ("<", 2)}, pluck="name"):
			doc = frappe.get_doc(doctype, name)
			if not doc.construction_management or not doc.date:
				continue
			if doctype == "Daily Report":
				doc.set_progress()
			else:
				doc.set_plan_comparison()
			doc.db_set({field: doc.get(field) for field in fields}, update_modified=False)
