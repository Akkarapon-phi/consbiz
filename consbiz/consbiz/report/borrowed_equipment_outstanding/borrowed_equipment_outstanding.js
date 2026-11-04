// Copyright (c) 2026, Siricons and contributors
// For license information, please see license.txt

frappe.query_reports["Borrowed Equipment Outstanding"] = {
	filters: [
		{
			fieldname: "company",
			label: __("บริษัท"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
		},
		{
			fieldname: "project",
			label: __("โครงการ"),
			fieldtype: "Link",
			options: "Project",
		},
		{
			fieldname: "supplier",
			label: __("ผรม."),
			fieldtype: "Link",
			options: "Supplier",
		},
		{
			fieldname: "borrower_type",
			label: __("ประเภทผู้ยืม"),
			fieldtype: "Select",
			options: [
				{ value: "", label: __("ทั้งหมด") },
				{ value: "Employee", label: __("พนักงาน") },
				{ value: "Subcontractor", label: __("ผรม.") },
				{ value: "Worker", label: __("คนงาน") },
			],
		},
		{
			fieldname: "overdue_only",
			label: __("เฉพาะที่เกินกำหนด"),
			fieldtype: "Check",
		},
	],
	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname === "days_overdue" && data?.days_overdue > 0) value = `<span class="text-danger">${value}</span>`;
		return value;
	},
};
