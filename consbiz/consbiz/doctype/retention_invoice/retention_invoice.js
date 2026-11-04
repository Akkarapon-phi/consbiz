// ใบวางบิลเรียกเงินประกันผลงานคืน ปุ่ม/dialog: public/js/retention.js (server: consbiz/retention.py)

frappe.ui.form.on("Retention Invoice", {
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
