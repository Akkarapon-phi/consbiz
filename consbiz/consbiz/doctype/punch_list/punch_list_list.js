// Copyright (c) 2026, Siricons and contributors
// For license information, please see license.txt

frappe.listview_settings["Punch List"] = {
	add_fields: ["status", "open_items"],
	get_indicator(doc) {
		if (doc.docstatus === 0) return [__("Draft"), "red", "docstatus,=,0"];
		if (doc.docstatus === 2) return [__("Cancelled"), "gray", "docstatus,=,2"];
		if (doc.status === "Closed") return [__("Closed"), "green", "status,=,Closed"];
		return [__("ค้าง {0} รายการ", [doc.open_items]), "orange", "status,=,Open"];
	},
};
