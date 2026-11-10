// ข้อมูลงานพิมพ์ของแผนงานในแอป (รูปแบบเดียวกับ print_model ใน construction_management/App.vue)
// คอลัมน์ แถวที่ย่อ/กรอง และการแสดงผล ตามที่ตั้งไว้ในหน้าแผนงาน
import { cell_text, text_width } from "../../../../construction_management/columns.js";
import { from_day, to_day, today } from "../../../../construction_management/schedule.js";
import { thai_date } from "../../../../shared/api.js";
import { COLUMNS, SUMMARY_ROWS } from "./planner.js";

// สีเดียวกับ CURVES ใน App.vue (งานพิมพ์ไม่ตามธีมมืด)
const CURVES = [
	{ key: "baseline", label: "แผนสัญญา", color: "#999999" },
	{ key: "plan", label: "แผน", color: "#0d8ef8" },
	{ key: "actual", label: "จริง", color: "#43ac79" },
];
const color_of = (key) => CURVES.find((curve) => curve.key === key).color;

export const PRINT_SCALES = [
	{ value: "day", label: "รายวัน" },
	{ value: "week", label: "รายสัปดาห์" },
	{ value: "month", label: "รายเดือน" },
	{ value: "year", label: "รายปี" },
];

const percent = (value) => (Number(value) || 0).toFixed(2);
const date_text = (value) => thai_date(value, { year: true });
const FULL_MONTHS = ["มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน", "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"];
function full_date(value) {
	const [year, month, day] = String(value).slice(0, 10).split("-").map(Number);
	return `${day} ${FULL_MONTHS[month - 1]} ${year + 543}`;
}

function contract_text(data) {
	const { start_date, finish_date, duration, extension_days, revised_finish_date } = data;
	if (!start_date || !finish_date) return "";
	const text = `${full_date(start_date)} - ${full_date(finish_date)} (${duration} วัน)`;
	return extension_days ? `${text} ขยายเวลา ${extension_days} วัน ถึง ${full_date(revised_finish_date)}` : text;
}

function status_text(p) {
	const { plan, actual, baseline } = p.summary;
	const pct = (value) => (Number(value) || 0).toFixed(3);
	const head = `ณ วันที่ ${date_text(p.cutoff)}:`;
	const base = baseline === null ? "" : ` แผนสัญญา ${pct(baseline)}% ·`;
	return `${head}${base} แผน ${pct(plan)}% · จริง ${pct(actual)}%`;
}

// ชื่อไฟล์ PDF: แผนงาน_ปี พ.ศ.-เดือน-วัน ของ Cut-off_ชื่อโครงการ (เรียงตามชื่อไฟล์แล้วได้ตามวันที่) (ชื่อยาวตัดคำ)
const MAX_NAME = 40;
export function print_file_name(p) {
	const [year, month, day] = String(p.cutoff).slice(0, 10).split("-");
	const clean = String(p.data.project_name || p.data.name || "")
		.replace(/[\\/:*?"<>|\u0000-\u001f]/g, " ")
		.replace(/\s+/g, " ")
		.trim();
	const letters = [...new Intl.Segmenter("th", { granularity: "grapheme" }).segment(clean)].map((s) => s.segment);
	const project = letters.slice(0, MAX_NAME).join("").trim();
	return `แผนงาน_${Number(year) + 543}-${month}-${day}_${project}`;
}

function extent_of(p) {
	const days = p.tasks
		.flatMap((t) => [t.start_date, t.end_date, t.baseline_start_date, t.baseline_end_date])
		.map(to_day)
		.filter((day) => day !== null && day !== undefined);
	const first = days.length ? Math.min(...days) : to_day(p.data.start_date) ?? today();
	return { first, last: days.length ? Math.max(...days) : first + 30 };
}

// คอลัมน์ ±% และสถานะ คำนวณในหน้าแผนงาน ใส่เป็นค่าข้อความในแถวที่ใช้พิมพ์
function print_row(task, metrics) {
	const metric = metrics.get(task.name);
	if (!metric) return task;
	const diff = metric.actual_pct - metric.plan_pct;
	return { ...task, diff: `${diff > 0 ? "+" : ""}${percent(diff)}`, status: metric.status?.label || "" };
}

// ความกว้างที่พอดีข้อความของแต่ละคอลัมน์ (px ของงานพิมพ์ ตัวอักษรหัว 7px เนื้อหา 8px ตรงกับ cell ใน print.js)
const PRINT_FONT = `"Noto Sans Thai", system-ui, -apple-system, sans-serif`;
const CELL_PADDING = 10;
const MAX_FIT = { item_name: 320 };
export const MIN_COLUMN_WIDTH = 20;

export function fit_column_widths(p, rows, keys) {
	const printable = rows.map((task) => print_row(task, p.metrics));
	return Object.fromEntries(
		keys.map((key) => {
			let width = text_width(COLUMNS[key].label, `600 7px ${PRINT_FONT}`);
			for (const task of printable) {
				const value = String(cell_text(task, key, p.metrics) ?? "");
				if (!value) continue;
				const indent = key === "item_name" ? task.indent * 10 : 0;
				width = Math.max(width, text_width(value, `${task.is_group ? 600 : 400} 8px ${PRINT_FONT}`) + indent);
			}
			return [key, Math.min(Math.ceil(width) + CELL_PADDING, MAX_FIT[key] || Infinity)];
		})
	);
}

// options = ค่าของแท็บพิมพ์ (columns: [{ key, visible, width }] เรียงตามลำดับพิมพ์), fit = ผลจาก fit_column_widths
export function build_print_model(p, settings, rows, options, fit) {
	const data = p.data;
	const show = settings.show;
	const week = data.week_by_month ? "mweek" : "week";
	const curves = CURVES.filter((c) => options.curves[c.key] && p.curves[c.key]).map((c) => ({
		...c,
		curve: p.curves[c.key],
	}));
	return {
		title: print_file_name(p),
		project_name: data.project_name || "",
		employer: data.employer,
		contractor: data.contractor,
		supervisor: data.supervisor,
		contract_text: contract_text(data),
		status_text: status_text(p),
		exact_widths: true,
		show_critical: show.critical,
		// ตัวเลขหัวกระดาษของแบบเอกสาร
		kpi: {
			baseline: p.summary.baseline,
			plan: p.summary.plan,
			actual: p.summary.actual,
			cutoff: date_text(p.cutoff),
		},
		columns: options.columns
			.filter((column) => column.visible && COLUMNS[column.key])
			.map(({ key, width }) => ({
				key,
				label: COLUMNS[key].label,
				width: width ? Math.max(Number(width), MIN_COLUMN_WIDTH) : fit[key],
				align: COLUMNS[key].align === "end" ? "right" : undefined,
			})),
		rows: rows.map((task) => print_row(task, p.metrics)),
		metrics: p.metrics,
		extent: extent_of(p),
		ppd: 12,
		week_unit: week,
		holidays: p.holidays,
		today: today(),
		status_day: p.cutoff_day,
		curves,
		all_curves: p.curves,
		total_amount: data.revised_amount || data.total_amount || 0,
		show_baseline_bars: show.baseline,
		show_split: show.split,
		show_labels: options.end_name,
		show_plan: options.end_plan,
		show_actual: options.end_actual,
		show_status_text: options.end_status,
		show_status: true,
		counting_holidays: p.counting,
		scale: settings.scale,
		scales: {
			day: { label: "รายวัน", top: "month", bottom: "day" },
			week: { label: "รายสัปดาห์", top: "month", bottom: week },
			month: { label: "รายเดือน", top: "year", bottom: "month" },
			year: { label: "รายปี", top: "year", bottom: "quarter" },
		},
		summary_rows: SUMMARY_ROWS.filter(
			(row) => options.summary[row.key] && (row.curve !== "baseline" || p.curves.baseline)
		).map((row) => ({ ...row, color: color_of(row.curve) })),
		colors: { baseline: color_of("baseline") },
		format_day: (day) => date_text(from_day(day)),
	};
}
