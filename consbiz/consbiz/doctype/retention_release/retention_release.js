// ใบตั้งเบิกจ่ายเงินประกันผลงานคืน ปุ่ม/dialog: public/js/retention.js (server: consbiz/retention.py)

frappe.ui.form.on("Retention Release", {
	setup(frm) {
		consbiz.retention.claim_setup(frm);
	},
	refresh(frm) {
		consbiz.retention.claim_refresh(frm);
	},
	validate(frm) {
		consbiz.retention.set_totals(frm);
	},
});
