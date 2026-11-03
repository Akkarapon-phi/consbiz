// รูปแบบตัวเลข/วันที่ และสีที่ใช้ร่วมกันใน Tab ภาพรวมและเอกสารโครงการ

export const percent = (value) =>
	value === null || value === undefined ? "-" : `${format_number(value, null, 2)}%`;
export const ratio = (value) =>
	value === null || value === undefined ? "-" : format_number(value, null, 2);
export const date = (value) => (value ? frappe.datetime.str_to_user(value) : "-");

export function money(value, currency, narrow = false) {
	if (narrow && Math.abs(value || 0) >= 1e6) {
		return `${format_number((value || 0) / 1e6, null, 2)}M`;
	}
	return format_currency(value || 0, currency, 0);
}

// ค่าสีจริงของตัวแปร CSS (frappe.Chart ต้องการรหัสสี ไม่รับ var())
export function css_color(name) {
	return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || name;
}

// สีสถานะเอกสารตาม indicator มาตรฐานของ Frappe
const STATUS_COLORS = {
	Pending: "orange",
	Approved: "green",
	Rejected: "red",
	Completed: "green",
	Cancelled: "gray",
	Passed: "green",
	"Passed with Comments": "blue",
	Failed: "red",
	Open: "orange",
	Closed: "green",
};

export function document_indicator(row, submittable = true) {
	if (!submittable) return row.status ? { label: __(row.status), color: STATUS_COLORS[row.status] || "gray" } : null;
	if (row.docstatus === 0) return { label: __("Draft"), color: "red" };
	if (row.docstatus === 2) return { label: __("Cancelled"), color: "gray" };
	if (!row.status) return { label: __("Submitted"), color: "blue" };
	return { label: __(row.status), color: STATUS_COLORS[row.status] || "gray" };
}
