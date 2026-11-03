// Copyright (c) 2026, Siricons and contributors
// For license information, please see license.txt

frappe.query_reports["Construction Resource Histogram"] = {
	filters: [
		{
			fieldname: "construction_management",
			label: __("Construction Management"),
			fieldtype: "Link",
			options: "Construction Management",
			reqd: 1,
		},
		{
			fieldname: "from_date",
			label: __("ตั้งแต่วันที่"),
			fieldtype: "Date",
			default: frappe.datetime.month_start(),
			reqd: 1,
		},
		{
			fieldname: "to_date",
			label: __("ถึงวันที่"),
			fieldtype: "Date",
			default: frappe.datetime.add_months(frappe.datetime.month_start(), 3),
			reqd: 1,
		},
		{
			fieldname: "periodicity",
			label: __("ช่วง"),
			fieldtype: "Select",
			options: [
				{ value: "Daily", label: __("รายวัน") },
				{ value: "Weekly", label: __("รายสัปดาห์") },
				{ value: "Monthly", label: __("รายเดือน") },
			],
			default: "Weekly",
		},
		{
			// กราฟรวมจำนวนของทุกทรัพยากรที่กรองไว้ จึงตั้งต้นที่แรงงานอย่างเดียว
			fieldname: "resource_type",
			label: __("ชนิด"),
			fieldtype: "Select",
			options: [
				{ value: "", label: __("ทั้งหมด") },
				{ value: "Labour", label: __("แรงงาน") },
				{ value: "Equipment", label: __("เครื่องจักร") },
			],
			default: "Labour",
		},
	],

	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname === "variance" && data?.variance) {
			return `<span class="${data.variance < 0 ? "text-danger" : "text-success"}">${value}</span>`;
		}
		return value;
	},
};
