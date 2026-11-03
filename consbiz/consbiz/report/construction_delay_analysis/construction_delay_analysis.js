// Copyright (c) 2026, Siricons and contributors
// For license information, please see license.txt

frappe.query_reports["Construction Delay Analysis"] = {
	filters: [
		{
			fieldname: "construction_management",
			label: __("Construction Management"),
			fieldtype: "Link",
			options: "Construction Management",
			reqd: 1,
		},
		{
			fieldname: "date",
			label: __("ณ วันที่"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
		},
		{
			fieldname: "only_issues",
			label: __("เฉพาะงานที่มีปัญหา"),
			fieldtype: "Check",
			default: 1,
		},
	],

	// สถานะเป็น indicator มาตรฐานของ Frappe
	formatter(value, row, column, data, default_formatter) {
		if (column.fieldname === "status_label" && data?.status_color) {
			return `<span class="indicator-pill ${data.status_color}">${frappe.utils.escape_html(
				value || ""
			)}</span>`;
		}
		value = default_formatter(value, row, column, data);
		if (column.fieldname === "delay_days" && data?.delay_days > 0) {
			return `<span class="text-danger">${value}</span>`;
		}
		return value;
	},
};
