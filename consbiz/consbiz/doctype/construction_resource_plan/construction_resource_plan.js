// Copyright (c) 2026, Siricons and contributors
// For license information, please see license.txt

// แผนทรัพยากร: เลือก WBS ของงานย่อย ชนิด (แรงงาน / เครื่องจักร) ชื่อทรัพยากร และจำนวนต่อวัน
// ชื่อทรัพยากรเลือกจากที่หน้างานเคยลงใน Daily Report เพื่อให้เทียบกับที่ใช้จริงได้

const RESOURCE_PLAN_API =
	"consbiz.consbiz.doctype.construction_resource_plan.construction_resource_plan";

frappe.ui.form.on("Construction Resource Plan", {
	setup(frm) {
		frm.set_query("construction_management", () => ({ filters: { status: "Active" } }));
	},

	refresh(frm) {
		load_options(frm);
		if (!frm.is_new()) {
			frm.add_custom_button(__("เทียบแผนกับที่ใช้จริง"), () =>
				frappe.set_route("query-report", "Construction Resource Histogram", {
					construction_management: frm.doc.construction_management,
				})
			);
		}
	},

	construction_management: load_options,
});

frappe.ui.form.on("Construction Resource Plan Item", {
	wbs(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		const task = (frm._options?.tasks || []).find((t) => t.value === row.wbs);
		frappe.model.set_value(cdt, cdn, "item_name", task ? task.label.slice(row.wbs.length + 1) : "");
	},
});

function load_options(frm) {
	if (!frm.doc.construction_management) return;
	frappe
		.call(`${RESOURCE_PLAN_API}.get_options`, {
			construction_management: frm.doc.construction_management,
		})
		.then(({ message }) => {
			frm._options = message;
			frm.fields_dict.items.grid.update_docfield_property("wbs", "options", message.tasks);
			set_resource_options(frm);
		});
}

// ตัวเลือกชื่อทรัพยากรรวมทั้งแรงงานและเครื่องจักร (Autocomplete ในตารางตั้งได้ชุดเดียวทั้งคอลัมน์)
function set_resource_options(frm) {
	const options = frm._options;
	if (!options) return;
	frm.fields_dict.items.grid.update_docfield_property("resource", "options", [
		...options.labour,
		...options.equipment,
	]);
}
