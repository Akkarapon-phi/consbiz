// Copyright (c) 2026, Siricons and contributors
// For license information, please see license.txt

frappe.ui.form.on("BOQ", {
	refresh(frm) {
		if (frm.is_new() || frm.doc.docstatus === 2) return;

		frappe.db
			.get_value("Construction Management", { boq: frm.doc.name, status: "Active" }, "name")
			.then(({ message }) => {
				const schedule = message && message.name;
				if (schedule) {
					frm.add_custom_button(__("แผนงานก่อสร้าง"), () =>
						frappe.set_route("construction-gantt", schedule)
					);
				} else if (frappe.model.can_create("Construction Management")) {
					frm.add_custom_button(__("สร้างแผนงาน"), () =>
						frappe
							.call({
								method: "consbiz.consbiz.doctype.construction_management.construction_management.create_from_boq",
								args: { boq: frm.doc.name },
								freeze: true,
							})
							.then((r) => frappe.set_route("construction-gantt", r.message))
					);
				}
			});
	},
});
