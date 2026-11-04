// Copyright (c) 2026, Siricons and contributors
// For license information, please see license.txt

frappe.listview_settings["Transmittal"] = {
	add_fields: ["status", "docstatus"],
	get_indicator(doc) {
		const colors = {
			Draft: "gray",
			"To Send": "orange",
			Sent: "blue",
			Received: "green",
			Cancelled: "red",
		};
		return [__(doc.status), colors[doc.status] || "gray", `status,=,${doc.status}`];
	},
};
