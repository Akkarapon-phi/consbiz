// Copyright (c) 2026, Siricons and contributors
// For license information, please see license.txt

frappe.ui.form.on("Construction Management", {
	refresh(frm) {
		if (!frm.is_new()) {
			frm.add_custom_button(__("เปิด Gantt"), () =>
				frappe.set_route("construction-gantt", frm.doc.name)
			);
			frm.add_custom_button(__("สร้าง Daily Request"), () =>
				frappe.new_doc("Daily Request", { construction_management: frm.doc.name })
			);
			frm.add_custom_button(__("สร้าง Daily Report"), () =>
				frappe.new_doc("Daily Report", { construction_management: frm.doc.name })
			);
			frm.add_custom_button(__("สร้างงานลด-งานเพิ่ม"), () =>
				frappe.new_doc("Variation Order", { construction_management: frm.doc.name })
			);
		}
		frm.set_df_property("tasks", "cannot_add_rows", true);
	},

	boq(frm) {
		// boq แก้ได้เฉพาะตอนสร้าง (set_only_once) เลือกแล้วดึงงานทั้งหมดมาแทนตารางเดิม
		if (!frm.is_new()) return;
		if (!frm.doc.boq) {
			frm.clear_table("tasks");
			frm.refresh_field("tasks");
			return;
		}
		frappe
			.call({
				method: "consbiz.consbiz.doctype.construction_management.construction_management.get_boq_plan",
				args: { boq: frm.doc.boq },
				freeze: true,
			})
			.then(({ message: plan }) => {
				const start_date = frm.doc.start_date || plan.start_date;
				for (const key of ["project", "start_date", "holiday_list"]) {
					if (!frm.doc[key] && plan[key]) frm.set_value(key, plan[key]);
				}
				frm.clear_table("tasks");
				plan.tasks.forEach((task) => frm.add_child("tasks", { ...task, start_date }));
				frm.refresh_field("tasks");
			});
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
