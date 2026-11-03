// Copyright (c) 2026, Siricons and contributors
// For license information, please see license.txt

frappe.listview_settings["Inspection Request"] = {
	add_fields: ["result"],
	get_indicator(doc) {
		if (doc.docstatus === 0) return [__("Draft"), "red", "docstatus,=,0"];
		if (doc.docstatus === 2) return [__("Cancelled"), "gray", "docstatus,=,2"];
		const colors = { Pending: "orange", Passed: "green", "Passed with Comments": "blue", Failed: "red" };
		return [__(doc.result), colors[doc.result] || "gray", `result,=,${doc.result}`];
	},
};
