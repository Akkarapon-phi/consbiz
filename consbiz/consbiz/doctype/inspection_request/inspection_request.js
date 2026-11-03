// Copyright (c) 2026, Siricons and contributors
// For license information, please see license.txt

// ขอตรวจงาน: เลือกแผนงานและ WBS ของงาน Submit = ส่งขอตรวจ แล้วบันทึกผลตรวจหลัง Submit
// ตรวจไม่ผ่าน (Failed) มีปุ่ม "ขอตรวจซ้ำ"

const TASK_OPTIONS_METHOD =
	"consbiz.consbiz.doctype.construction_management.construction_management.get_task_options";

frappe.ui.form.on("Inspection Request", {
	setup(frm) {
		frm.set_query("construction_management", () => ({ filters: { status: "Active" } }));
	},

	refresh(frm) {
		load_task_options(frm);
		if (frm.doc.docstatus === 1 && frm.doc.result === "Failed") {
			frm.add_custom_button(__("ขอตรวจซ้ำ"), () =>
				frappe.model.open_mapped_doc({
					method: "consbiz.consbiz.doctype.inspection_request.inspection_request.make_reinspection",
					frm,
				})
			);
		}
	},

	construction_management: load_task_options,
});

function load_task_options(frm) {
	if (!frm.doc.construction_management) return;
	frappe
		.call(TASK_OPTIONS_METHOD, { construction_management: frm.doc.construction_management })
		.then(({ message }) => {
			frm._tasks = message;
			frm.set_df_property("wbs", "options", message);
		});
}
