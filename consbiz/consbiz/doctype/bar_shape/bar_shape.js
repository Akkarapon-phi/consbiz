// Copyright (c) 2026, Siricons and contributors
// For license information, please see license.txt

frappe.ui.form.on("Bar Shape", {
	refresh(frm) {
		render_preview(frm);
	},
	svg(frm) {
		render_preview(frm);
	},
});

function render_preview(frm) {
	frm.fields_dict.preview.$wrapper.html(
		`<div class="consbiz-bar-shape" style="max-width: 320px">${frm.doc.svg || ""}</div>`
	);
}
