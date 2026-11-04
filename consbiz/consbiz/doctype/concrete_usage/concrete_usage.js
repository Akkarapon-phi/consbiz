// Copyright (c) 2026, Siricons and contributors
// For license information, please see license.txt

// บันทึกการใช้คอนกรีต: เลือกแผนงานและงาน (WBS) ที่เท แล้วกรอกตั๋วรถทีละคัน
// ช่อง "ผู้ว่าจ้างจัดหา" ที่หัวเอกสารเป็นค่าตั้งต้นของตั๋วที่เพิ่มใหม่ ติ๊ก/เอาออกรายใบได้

const TASK_OPTIONS_API =
	"consbiz.consbiz.doctype.construction_management.construction_management.get_task_options";

frappe.ui.form.on("Concrete Usage", {
	setup(frm) {
		frm.set_query("construction_management", () => ({ filters: { status: "Active" } }));
		frm.set_query("concrete_item", () => ({ filters: { custom_base_item: ["is", "not set"] } }));
	},

	refresh(frm) {
		load_tasks(frm);
	},

	construction_management(frm) {
		frm.set_value("wbs", "");
		load_tasks(frm);
	},

	wbs(frm) {
		const task = (frm._tasks || []).find((t) => t.value === frm.doc.wbs);
		frm.set_value("task_name", task ? task.label.slice(task.value.length + 1) : "");
	},

	employer_supplied(frm) {
		// เปลี่ยนค่าตั้งต้นตอนยังไม่มีตั๋ว ให้แถวแรกตามด้วย
		if ((frm.doc.tickets || []).length === 1 && !frm.doc.tickets[0].ticket_no) {
			frappe.model.set_value(frm.doc.tickets[0].doctype, frm.doc.tickets[0].name, "employer_supplied", frm.doc.employer_supplied);
		}
	},
});

frappe.ui.form.on("Concrete Usage Ticket", {
	tickets_add(frm, cdt, cdn) {
		frappe.model.set_value(cdt, cdn, "employer_supplied", frm.doc.employer_supplied || 0);
	},
});

function load_tasks(frm) {
	if (!frm.doc.construction_management) return;
	frappe.call(TASK_OPTIONS_API, { construction_management: frm.doc.construction_management }).then(({ message }) => {
		frm._tasks = message;
		frm.set_df_property("wbs", "options", message);
	});
}
