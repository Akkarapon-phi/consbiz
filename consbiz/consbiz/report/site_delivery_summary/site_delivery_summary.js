// Copyright (c) 2026, Siricons and contributors
// For license information, please see license.txt

frappe.query_reports["Site Delivery Summary"] = {
	filters: [
		{
			fieldname: "company",
			label: __("บริษัท"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			reqd: 1,
		},
		{
			fieldname: "from_date",
			label: __("ตั้งแต่วันที่"),
			fieldtype: "Date",
			default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
			reqd: 1,
		},
		{
			fieldname: "to_date",
			label: __("ถึงวันที่"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
		},
		{
			fieldname: "project",
			label: __("โครงการ"),
			fieldtype: "Link",
			options: "Project",
		},
		{
			fieldname: "warehouse",
			label: __("คลัง"),
			fieldtype: "Link",
			options: "Warehouse",
			get_query: () => ({ filters: { company: frappe.query_report.get_filter_value("company") } }),
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
			fieldname: "item_code",
			label: __("Item"),
			fieldtype: "Link",
			options: "Item",
		},
		{
			fieldname: "delivery_note",
			label: __("เลขที่ใบส่งของ"),
			fieldtype: "Data",
		},
	],
};
