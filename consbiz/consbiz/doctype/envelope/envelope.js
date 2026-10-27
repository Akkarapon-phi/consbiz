// Copyright (c) 2026, Siricons and contributors
// For license information, please see license.txt

// ---- ย้ายจาก Client Script "Envelope Receiver Filter" ----

frappe.ui.form.on("Envelope", {
	refresh: function (frm) {
		// 1. Filter ฟิลด์ 'from' (Address) ตาม Company และต้องไม่ถูก Disabled (disabled = 0)
		frm.set_query("from", function () {
			return {
				query: "frappe.contacts.doctype.address.address.address_query",
				filters: {
					link_doctype: "Company",
					link_name: frm.doc.company,
					disabled: 0,
				},
			};
		});

		// 2. Filter ฟิลด์ 'receiver' ตามค่าในฟิลด์ 'to'
		frm.set_query("receiver", function () {
			return {
				filters: {
					address: frm.doc.to,
				},
			};
		});
	},

	// เมื่อเปลี่ยนบริษัท ให้เคลียร์ค่า 'from' เดิมออกอัตโนมัติ
	company: function (frm) {
		frm.set_value("from", "");
	},

	// เมื่อเปลี่ยน 'to' ให้เคลียร์ค่า 'receiver' เดิมออกอัตโนมัติ
	to: function (frm) {
		frm.set_value("receiver", "");
	},
});
