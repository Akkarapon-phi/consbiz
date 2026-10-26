// Copyright (c) 2026, Siricons and contributors
// For license information, please see license.txt

frappe.listview_settings["Daily Request"] = {
	add_fields: ["status"],
	get_indicator(doc) {
		const colors = {
			Pending: "orange",
			Approved: "blue",
			Completed: "green",
			Rejected: "red",
			Cancelled: "gray",
		};
		return [__(doc.status), colors[doc.status] || "gray", `status,=,${doc.status}`];
	},
};
