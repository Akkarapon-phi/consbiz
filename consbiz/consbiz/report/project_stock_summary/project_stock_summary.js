// Copyright (c) 2026, Siricons and contributors
// For license information, please see license.txt

frappe.query_reports["Project Stock Summary"] = {
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
			reqd: 1,
			get_query: () => {
				const company = frappe.query_report.get_filter_value("company");
				return { filters: company ? { company } : {} };
			},
		},
	],
};
