// Copyright (c) 2026, Siricons and contributors
// For license information, please see license.txt

const PRICE_REVIEW_METHOD =
	"consbiz.consbiz.report.boq_item_price_review.boq_item_price_review.update_standard_rates";

frappe.query_reports["BOQ Item Price Review"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("ตั้งแต่วันที่"),
			fieldtype: "Date",
			default: frappe.datetime.add_months(frappe.datetime.get_today(), -12),
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
			fieldname: "item_group",
			label: __("กลุ่มงาน"),
			fieldtype: "Link",
			options: "BOQ Item Group",
		},
		{
			fieldname: "threshold",
			label: __("ส่วนต่างที่ควรทบทวน (%)"),
			fieldtype: "Float",
			default: 10,
		},
		{
			fieldname: "min_boq",
			label: __("จำนวน BOQ ขั้นต่ำ"),
			fieldtype: "Int",
			default: 3,
		},
		{
			fieldname: "only_review",
			label: __("เฉพาะที่ควรทบทวน"),
			fieldtype: "Check",
		},
		{
			fieldname: "include_draft",
			label: __("รวม BOQ ที่ยังไม่ Submit"),
			fieldtype: "Check",
		},
	],

	formatter(value, row, column, data, default_formatter) {
		if (column.fieldname === "status" && data) {
			return `<span class="indicator-pill ${data.status_color}">${frappe.utils.escape_html(value)}</span>`;
		}
		return default_formatter(value, row, column, data);
	},

	get_datatable_options(options) {
		return Object.assign(options, { checkboxColumn: true });
	},

	onload(report) {
		if (!frappe.model.can_write("BOQ Item")) return;
		report.page.add_inner_button(__("ตั้งราคามาตรฐานตามค่ามัธยฐาน"), () =>
			update_standard_rates(report)
		);
	},
};

// ยืนยันก่อนบันทึก: แสดงราคาเดิม → ใหม่ (ค่าเริ่มต้นคือมัธยฐาน แก้ตัวเลขได้)
function update_standard_rates(report) {
	const rows = report.get_checked_items();
	if (!rows.length) {
		frappe.msgprint(__("กรุณาติ๊กเลือกรายการในรายงานก่อน"));
		return;
	}
	const dialog = new frappe.ui.Dialog({
		title: __("ตั้งราคามาตรฐานใหม่ {0} รายการ", [rows.length]),
		size: "extra-large",
		fields: [
			{
				fieldtype: "HTML",
				options: `<p class="text-muted small">${__(
					"ราคาใหม่ตั้งต้นเป็นค่ามัธยฐานของ BOQ แก้ตัวเลขได้ก่อนบันทึก การเปลี่ยนแปลงทุกครั้งเก็บไว้ใน timeline ของ BOQ Item"
				)}</p>`,
			},
			{
				fieldname: "rates",
				fieldtype: "Table",
				cannot_add_rows: true,
				cannot_delete_rows: false,
				in_place_edit: true,
				data: rows.map((row) => ({
					item_code: row.item_code,
					item_name: row.item_name,
					rate_type: row.rate_type,
					rate_field: row.rate_field,
					standard_rate: row.standard_rate,
					new_rate: flt(row.median_rate, 2),
				})),
				fields: [
					{ fieldname: "item_code", label: __("รหัสรายการ"), fieldtype: "Data", read_only: 1, in_list_view: 1, columns: 1 },
					{ fieldname: "item_name", label: __("รายการ"), fieldtype: "Data", read_only: 1, in_list_view: 1, columns: 4 },
					{ fieldname: "rate_type", label: __("ประเภทราคา"), fieldtype: "Data", read_only: 1, in_list_view: 1, columns: 1 },
					{ fieldname: "rate_field", fieldtype: "Data", hidden: 1 },
					{ fieldname: "standard_rate", label: __("ราคาเดิม"), fieldtype: "Float", precision: 2, read_only: 1, in_list_view: 1, columns: 2 },
					{ fieldname: "new_rate", label: __("ราคาใหม่"), fieldtype: "Float", precision: 2, in_list_view: 1, columns: 2 },
				],
			},
		],
		primary_action_label: __("บันทึกราคามาตรฐาน"),
		primary_action({ rates }) {
			const updates = (rates || [])
				.filter((row) => flt(row.new_rate, 2) !== flt(row.standard_rate, 2))
				.map(({ item_code, rate_field, new_rate }) => ({ item_code, rate_field, rate: new_rate }));
			if (!updates.length) {
				dialog.hide();
				return;
			}
			frappe
				.call({ method: PRICE_REVIEW_METHOD, args: { updates }, freeze: true })
				.then(({ message: count }) => {
					dialog.hide();
					frappe.show_alert({
						message: __("ตั้งราคามาตรฐานใหม่ {0} รายการ", [count]),
						indicator: "green",
					});
					report.refresh();
				});
		},
	});
	dialog.show();
}
