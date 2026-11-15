// Copyright (c) 2026, Siricons and contributors
// For license information, please see license.txt

// ใบเบิกงวด ผรม.: Submit = อนุมัติ แล้วสร้างใบแจ้งหนี้ซื้อ (API consbiz/subcontract.py)
frappe.ui.form.on("Subcontract Claim", {
	refresh(frm) {
		if (frm.doc.docstatus === 1 && !frm.doc.purchase_invoice) {
			frm.add_custom_button(__("สร้างใบแจ้งหนี้ซื้อ (PI)"), () =>
				frappe
					.call({
						method: "consbiz.subcontract.make_purchase_invoice",
						args: { name: frm.doc.name },
						freeze: true,
					})
					.then(
						(r) => r.message && frappe.set_route("Form", "Purchase Invoice", r.message)
					)
			);
		}
	},
	subcontract_agreement(frm) {
		frm.clear_table("items");
		frm.refresh_field("items");
	},
});
