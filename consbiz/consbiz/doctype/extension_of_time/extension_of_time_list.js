// Copyright (c) 2026, Siricons and contributors
// For license information, please see license.txt

frappe.listview_settings["Extension of Time"] = {
	add_fields: ["employer_status", "approved_days"],
	get_indicator(doc) {
		if (doc.docstatus === 0) return [__("Draft"), "red", "docstatus,=,0"];
		if (doc.docstatus === 2) return [__("Cancelled"), "gray", "docstatus,=,2"];
		const colors = { Pending: "orange", Approved: "green", Rejected: "red" };
		const label =
			doc.employer_status === "Approved"
				? `${__("Approved")} ${__("{0} วัน", [doc.approved_days])}`
				: __(doc.employer_status);
		return [label, colors[doc.employer_status] || "gray", `employer_status,=,${doc.employer_status}`];
	},
};
