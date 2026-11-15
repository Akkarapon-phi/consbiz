// Copyright (c) 2026, Siricons and contributors
// For license information, please see license.txt

// สัญญาจ้างเหมาช่วง: ปุ่มสร้าง PO / จ่ายเงินล่วงหน้า / ใบเบิกงวด (API consbiz/subcontract.py)
frappe.ui.form.on("Subcontract Agreement", {
	refresh(frm) {
		if (frm.doc.docstatus !== 1) return;
		const run = (method, doctype) =>
			frappe
				.call({
					method: `consbiz.subcontract.${method}`,
					args: { name: frm.doc.name },
					freeze: true,
				})
				.then((r) => {
					if (r.message) frappe.set_route("Form", doctype, r.message);
				});
		if (!frm.doc.purchase_order) {
			frm.add_custom_button(
				__("สร้างใบสั่งซื้อ (PO)"),
				() => run("make_purchase_order", "Purchase Order"),
				__("สร้าง")
			);
		}
		if (frm.doc.advance_amount && frm.doc.purchase_order) {
			frm.add_custom_button(
				__("จ่ายเงินล่วงหน้า"),
				() => run("make_advance_payment", "Payment Entry"),
				__("สร้าง")
			);
		}
		if (frm.doc.status === "Active") {
			frm.add_custom_button(
				__("ใบเบิกงวด"),
				() => frappe.new_doc("Subcontract Claim", { subcontract_agreement: frm.doc.name }),
				__("สร้าง")
			);
		}
		const open = ["Active", "Completed"].includes(frm.doc.status);
		if (open) {
			frm.add_custom_button(
				__("ใบงานเพิ่ม"),
				() =>
					frappe.new_doc("Subcontract Variation", {
						subcontract_agreement: frm.doc.name,
					}),
				__("สร้าง")
			);
		}
		if (open && frm.perm[0]?.submit) {
			// ปิดสัญญา = งานจบต่ำกว่าสัญญาหรือ ผรม. ไม่ทำต่อ (ไม่มีงานลด) ระบบปิด PO ให้ด้วย
			frm.add_custom_button(__("ปิดสัญญา"), () =>
				frappe.prompt(
					{ fieldname: "reason", fieldtype: "Small Text", label: __("เหตุผล"), reqd: 1 },
					({ reason }) =>
						frappe
							.call({
								method: "consbiz.subcontract.close_agreement",
								args: { name: frm.doc.name, reason },
								freeze: true,
							})
							.then(() => frm.reload_doc()),
					__("ปิดสัญญา {0}", [frm.doc.name]),
					__("ปิดสัญญา")
				)
			);
		}
		if (frm.doc.status === "Closed" && frm.perm[0]?.submit) {
			frm.add_custom_button(__("เปิดสัญญาอีกครั้ง"), () =>
				frappe.confirm(__("เปิดสัญญานี้อีกครั้งและเปิดใบสั่งซื้อ?"), () =>
					frappe
						.call({
							method: "consbiz.subcontract.reopen_agreement",
							args: { name: frm.doc.name },
							freeze: true,
						})
						.then(() => frm.reload_doc())
				)
			);
		}
	},
});
