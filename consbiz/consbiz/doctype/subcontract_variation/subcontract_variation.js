// Copyright (c) 2026, Siricons and contributors
// For license information, please see license.txt

// ใบงานเพิ่ม ผรม.: รายการแนบท้ายสัญญา แยกจากงานหลัก เบิกตามปริมาณจริง
// Submit = อนุมัติ: เพิ่มแถวแนบท้ายในสัญญา + PO เดิม (ระบบทำแทน เก็บ PDF ฉบับเดิม แจ้งฝ่ายจัดซื้อ) consbiz/subcontract_variation.py
frappe.ui.form.on("Subcontract Variation", {
	setup(frm) {
		frm.set_query("subcontract_agreement", () => ({
			filters: {
				docstatus: 1,
				status: ["in", ["Active", "Completed"]],
			},
		}));
	},
});
