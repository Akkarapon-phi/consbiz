// Copyright (c) 2026, Siricons and contributors
// For license information, please see license.txt

frappe.query_reports["Construction Earned Value"] = {
	filters: [
		{
			fieldname: "construction_management",
			label: __("Construction Management"),
			fieldtype: "Link",
			options: "Construction Management",
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
			fieldname: "periodicity",
			label: __("ช่วง"),
			fieldtype: "Select",
			options: [
				{ value: "Monthly", label: __("รายเดือน") },
				{ value: "Weekly", label: __("รายสัปดาห์") },
			],
			default: "Monthly",
		},
	],

	// SPI / CPI ต่ำกว่า 1 = ช้ากว่าแผน / ต้นทุนเกิน
	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (["spi", "cpi"].includes(column.fieldname) && data?.[column.fieldname] != null) {
			return `<span class="${data[column.fieldname] < 1 ? "text-danger" : "text-success"}">${value}</span>`;
		}
		return value;
	},
};
