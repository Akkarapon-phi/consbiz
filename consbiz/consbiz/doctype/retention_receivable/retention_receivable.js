// เงินประกันผลงานรับ (ระบบสร้างเองตอน Submit Sales Invoice) ปุ่ม/ยอดรวม: public/js/retention.js

frappe.ui.form.on("Retention Receivable", {
	refresh(frm) {
		consbiz.retention.source_refresh(frm);
	},
	validate(frm) {
		consbiz.retention.set_totals(frm);
	},
});
