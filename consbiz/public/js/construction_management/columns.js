// คอลัมน์ของตาราง WBS ใช้ร่วมกันระหว่างหน้าจอ (TaskGrid) และงานพิมพ์ (print.js)
// editor = fieldtype ของ Frappe control ที่ใช้แก้ค่าในช่อง (ไม่มี = แก้ไม่ได้)
// plan_pct / actual_pct / actual_qty เป็นค่า ณ วันที่ที่เลือกดู, predecessors เป็นข้อความ WBS (metrics จาก App)

export const COLUMNS = [
	{ key: "wbs", label: __("WBS"), width: 64 },
	{ key: "item_name", label: __("รายการ"), width: 260 },
	{ key: "quantity", label: __("ปริมาณ"), width: 80, align: "right" },
	{ key: "uom", label: __("หน่วย"), width: 64 },
	{ key: "amount", label: __("มูลค่า"), width: 110, align: "right" },
	{ key: "weight", label: __("น้ำหนัก %"), width: 80, align: "right" },
	{ key: "start_date", label: __("วันเริ่ม"), width: 100, editor: "Date" },
	{ key: "end_date", label: __("วันจบ"), width: 100, editor: "Date" },
	{ key: "duration", label: __("จำนวนวัน"), width: 72, align: "right", editor: "Int" },
	{ key: "predecessors", label: __("งานก่อนหน้า"), width: 110, editor: "Data" },
	{ key: "baseline_start_date", label: __("เริ่ม (Baseline)"), width: 100 },
	{ key: "baseline_end_date", label: __("จบ (Baseline)"), width: 100 },
	{ key: "plan_pct", label: __("% แผน"), width: 72, align: "right" },
	{ key: "actual_qty", label: __("ปริมาณจริง"), width: 90, align: "right", editor: "Float" },
	{ key: "actual_pct", label: __("% จริง"), width: 72, align: "right", editor: "Float" },
];

export const DEFAULT_COLUMNS = [
	"wbs",
	"item_name",
	"weight",
	"start_date",
	"end_date",
	"duration",
	"plan_pct",
	"actual_pct",
];

const METRIC_KEYS = ["plan_pct", "actual_pct", "actual_qty", "predecessors"];

export function cell_value(task, key, metrics) {
	if (METRIC_KEYS.includes(key)) return metrics.get(task.name)?.[key] ?? null;
	return task[key];
}

export function can_edit(task, column) {
	if (!column.editor || task.is_group) return false;
	if (column.key === "duration") return Boolean(task.start_date);
	// ปริมาณจริงกรอกได้เฉพาะงานที่มีปริมาณใน BOQ งานเหมาให้กรอก % แทน
	if (column.key === "actual_qty") return task.quantity > 0;
	return true;
}

export function cell_text(task, key, metrics) {
	const value = cell_value(task, key, metrics);
	switch (key) {
		case "start_date":
		case "end_date":
		case "baseline_start_date":
		case "baseline_end_date":
			return value ? frappe.datetime.str_to_user(value) : "";
		case "quantity":
			return task.is_group || !value ? "" : format_number(value, null, 2);
		case "actual_qty":
			return task.is_group || !(task.quantity > 0) ? "" : format_number(value || 0, null, 2);
		case "amount":
		case "weight":
		case "plan_pct":
		case "actual_pct":
			return format_number(value || 0, null, 2);
		case "duration":
			return value || "";
		default:
			return value ?? "";
	}
}

const locale = frappe.boot.lang === "th" ? "th-TH" : frappe.boot.lang || "en";
const compact = new Intl.NumberFormat(locale, { notation: "compact", maximumFractionDigits: 1 });

// % ในตารางสรุป (หน้าจอและงานพิมพ์) แสดง 3 ตำแหน่ง
export function format_percent(value, decimals = 3) {
	return value === null || value === undefined ? "" : format_number(value, null, decimals);
}

// ช่องแคบใช้รูปย่อ (1.2M) ช่องกว้างแสดงเต็ม
export function format_money(value, narrow) {
	if (value === null || value === undefined || Math.abs(value) < 0.005) return "";
	return narrow ? compact.format(value) : format_number(value, null, 0);
}

const date_formats = {
	month: new Intl.DateTimeFormat(locale, { month: "short", year: "numeric", timeZone: "UTC" }),
	month_short: new Intl.DateTimeFormat(locale, { month: "short", timeZone: "UTC" }),
	year: new Intl.DateTimeFormat(locale, { year: "numeric", timeZone: "UTC" }),
};

// ป้ายของช่องเวลาในหัว timeline (top_level = แถวบน แสดงเดือนพร้อมปี)
export function period_label(period, unit, top_level) {
	const date = period.date;
	switch (unit) {
		case "day":
			return date.getUTCDate();
		case "week":
			return `${date.getUTCDate()}/${date.getUTCMonth() + 1}`;
		case "mweek":
			return `W${Math.floor((date.getUTCDate() - 1) / 7) + 1}`;
		case "month":
			return (top_level ? date_formats.month : date_formats.month_short).format(date);
		case "quarter":
			return `Q${Math.floor(date.getUTCMonth() / 3) + 1}`;
		case "year":
			return date_formats.year.format(date);
	}
}

// % ที่แบ่งบนแถบ: ค่าลงตัวไม่แสดงทศนิยม (20%) ค่าที่มีเศษแสดง 1 ตำแหน่ง (2.9%)
export function format_share(value) {
	const decimals = Math.abs(value - Math.round(value)) < 0.05 ? 0 : 1;
	return `${format_number(value, null, decimals)}%`;
}

// สถานะของงาน ณ วันที่เลือกดู ใช้สี indicator มาตรฐานของ Frappe
// ช้ากว่าแผนไม่เกิน LATE_LIMIT จุด = ส้ม เกินกว่านั้น = แดง
const LATE_LIMIT = 10;

export function progress_status(plan, actual) {
	if (actual >= 99.995) return { color: "green", label: __("เสร็จแล้ว") };
	if (plan <= 0.005 && actual <= 0.005) return { color: "gray", label: __("ยังไม่ถึงกำหนด") };
	const diff = actual - plan;
	if (diff >= -0.005) return { color: "blue", label: __("ตามแผนหรือเร็วกว่าแผน") };
	if (diff >= -LATE_LIMIT)
		return { color: "orange", label: __("ช้ากว่าแผนไม่เกิน {0}%", [LATE_LIMIT]) };
	return { color: "red", label: __("ช้ากว่าแผนเกิน {0}%", [LATE_LIMIT]) };
}

// ความกว้างข้อความ (px) ใช้วางกรอบสถานะต่อจากชื่องานใน SVG
let canvas;
export function text_width(text, font) {
	canvas = canvas || document.createElement("canvas");
	const context = canvas.getContext("2d");
	context.font = font;
	return context.measureText(text).width;
}
