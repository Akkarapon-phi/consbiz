// Copyright (c) 2026, Siricons and contributors
// For license information, please see license.txt

frappe.ui.form.on("BOQ Item", {
	refresh(frm) {
		if (frm.is_new()) return;
		const body = frm.dashboard.add_section("", __("แนวโน้มราคา"));
		frm.dashboard.show();
		consbiz.render_price_history(body, frm.doc.name);
	},
});
