// Copyright (c) 2026, Siricons and contributors
// For license information, please see license.txt

frappe.query_reports["Concrete Usage Summary"] = {
	filters: [
		{
			fieldname: "company",
			label: __("บริษัท"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
		},
		{
			fieldname: "from_date",
			label: __("ตั้งแต่วันที่"),
			fieldtype: "Date",
			default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
		},
		{
			fieldname: "to_date",
			label: __("ถึงวันที่"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
		},
		{
			fieldname: "project",
			label: __("โครงการ"),
			fieldtype: "Link",
			options: "Project",
		},
		{
			fieldname: "construction_management",
			label: __("แผนงาน"),
			fieldtype: "Link",
			options: "Construction Management",
		},
		{
			fieldname: "supplier",
			label: __("ผู้ขาย"),
			fieldtype: "Link",
			options: "Supplier",
		},
		{
			fieldname: "supply",
			label: __("แหล่ง"),
			fieldtype: "Select",
			options: [
				{ value: "", label: __("ทั้งหมด") },
				{ value: "Company", label: __("ซื้อเอง") },
				{ value: "Employer", label: __("ผู้ว่าจ้างจัดหา") },
			],
		},
		{
			fieldname: "show_tickets",
			label: __("แสดงรายตั๋ว"),
			fieldtype: "Check",
		},
	],
};
