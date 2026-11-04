// Copyright (c) 2026, Siricons and contributors
// For license information, please see license.txt

frappe.listview_settings["Equipment Borrowing"] = {
	add_fields: ["status", "due_date"],
	get_indicator(doc) {
		const open = ["Borrowed", "Partially Returned"].includes(doc.status);
		if (open && doc.due_date && doc.due_date < frappe.datetime.get_today()) {
			return [__("Overdue"), "red", `due_date,<,${frappe.datetime.get_today()}`];
		}
		const colors = { Draft: "red", Borrowed: "orange", "Partially Returned": "yellow", Returned: "green", Cancelled: "gray" };
		return [__(doc.status), colors[doc.status] || "gray", `status,=,${doc.status}`];
	},
};
