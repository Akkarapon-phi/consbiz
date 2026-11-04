// Copyright (c) 2026, Siricons and contributors
// For license information, please see license.txt

// ยืม-คืนอุปกรณ์: สโตร์บันทึก ผู้ยืมเซ็นในช่องลายเซ็น (มือถือ/แท็บเล็ต) แล้ว Submit = ส่งมอบ
// รับคืนด้วยปุ่ม "รับคืน" (consbiz.equipment_return_dialog ใน utils.js) คืนได้หลายครั้งจนครบ

frappe.ui.form.on("Equipment Borrowing", {
	setup(frm) {
		const by_company = () => ({ filters: { company: frm.doc.company, is_group: 0 } });
		frm.set_query("source_warehouse", by_company);
		frm.set_query("loan_warehouse", by_company);
		frm.set_query("item_code", "items", () => ({ filters: { is_stock_item: 1, disabled: 0 } }));
	},

	project(frm) {
		// อุปกรณ์ของโครงการ: ตั้งต้นคลังต้นทาง = คลังของโครงการ
		consbiz.set_project_warehouse(frm, frm.doc.project, ["source_warehouse"]);
	},

	refresh(frm) {
		if (frm.doc.docstatus === 1 && ["Borrowed", "Partially Returned"].includes(frm.doc.status)) {
			frm.add_custom_button(__("รับคืน"), () => consbiz.equipment_return_dialog(frm.doc.name, () => frm.reload_doc())).addClass(
				"btn-primary"
			);
			if (frm.doc.due_date && frm.doc.due_date < frappe.datetime.get_today()) {
				frm.set_intro(__("เกินกำหนดคืน ({0})", [frappe.datetime.str_to_user(frm.doc.due_date)]), "red");
			}
		}
	},
});
