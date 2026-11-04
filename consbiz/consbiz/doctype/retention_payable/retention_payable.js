// เงินประกันผลงานจ่าย (ระบบสร้างเองตอน Submit Purchase Invoice) ปุ่ม/ยอดรวม: public/js/retention.js

frappe.ui.form.on("Retention Payable", {
	refresh(frm) {
		consbiz.retention.source_refresh(frm);
	},
	posting_date(frm) {
		frm.trigger("period");
	},
	// ระยะเวลาประกัน (วัน) นับจากวันที่เอกสาร = วันครบกำหนดคืน
	period(frm) {
		if (frm.doc.posting_date && cint(frm.doc.period) > 0) {
			frm.set_value("due_date", frappe.datetime.add_days(frm.doc.posting_date, cint(frm.doc.period)));
		}
	},
	validate(frm) {
		consbiz.retention.set_totals(frm);
	},
});
