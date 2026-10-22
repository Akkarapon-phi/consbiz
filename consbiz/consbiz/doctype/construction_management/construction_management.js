// Copyright (c) 2026, Siricons and contributors
// For license information, please see license.txt

frappe.ui.form.on("Construction Management", {
	refresh(frm) {
		if (!frm.is_new()) {
			frm.add_custom_button(__("เปิด Gantt"), () =>
				frappe.set_route("construction-gantt", frm.doc.name)
			);
			frm.add_custom_button(__("สร้าง Daily Report"), () =>
				frappe.new_doc("Daily Report", { construction_management: frm.doc.name })
			);
		}
		frm.set_df_property("tasks", "cannot_add_rows", true);
	},
});

frappe.ui.form.on("Construction Management Task", {
	duration(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.start_date || row.is_group) return;
		// นับแบบปฏิทินคำนวณวันจบได้เลย ถ้านับวันทำงานให้ server คำนวณตอนบันทึก (ต้องใช้วันหยุด)
		const end_date = frm.doc.use_working_days
			? null
			: frappe.datetime.add_days(row.start_date, Math.max(row.duration || 1, 1) - 1);
		frappe.model.set_value(cdt, cdn, "end_date", end_date);
	},
});
