// Copyright (c) 2026, Siricons and contributors
// For license information, please see license.txt

// Punch List: กรอกรายการที่ต้องแก้ (ตำแหน่ง รายละเอียด ผู้รับผิดชอบ กำหนดเสร็จ รูปก่อนแก้)
// หลัง Submit เปลี่ยนสถานะรายการเป็น Closed พร้อมรูปหลังแก้ แล้วกด Update

const PUNCH_TASK_OPTIONS =
	"consbiz.consbiz.doctype.construction_management.construction_management.get_task_options";

frappe.ui.form.on("Punch List", {
	setup(frm) {
		frm.set_query("construction_management", () => ({ filters: { status: "Active" } }));
		frm.set_query("inspection_request", () => ({
			filters: { construction_management: frm.doc.construction_management, docstatus: 1 },
		}));
	},

	refresh(frm) {
		if (!frm.doc.construction_management) return;
		frappe
			.call(PUNCH_TASK_OPTIONS, { construction_management: frm.doc.construction_management })
			.then(({ message }) =>
				frm.fields_dict.items.grid.update_docfield_property("wbs", "options", message)
			);
	},

	construction_management(frm) {
		frm.trigger("refresh");
	},
});
