<script setup>
// หน้า Gantt ของ Construction Management: ตาราง WBS ซ้าย, timeline + S-Curve ขวา, ตารางสรุปด้านล่าง
// ฝั่ง server: consbiz/consbiz/doctype/construction_management/construction_management.py
// ความคืบหน้าจริงเก็บเป็นรายการรายวัน (Construction Progress Entry) กรอกในหน้านี้ได้ ณ "วันที่เลือกดู"
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";
import Toolbar from "./components/Toolbar.vue";
import TaskGrid from "./components/TaskGrid.vue";
import Timeline from "./components/Timeline.vue";
import { COLUMNS, DEFAULT_COLUMNS } from "./columns";
import { open_plan_dialog } from "./plan_dialog";
import { open_print_dialog } from "./print";
import {
	actual_curve,
	count_days,
	curve_of,
	distribution_fits,
	end_of,
	floor_to,
	from_day,
	next_of,
	parse_distribution,
	plan_percent,
	roll_up,
	to_day,
	today,
	value_at,
} from "./schedule";

const props = defineProps({ page: Object, schedule: String });

const API = "consbiz.consbiz.doctype.construction_management.construction_management";
const DOCTYPE = "Construction Management";
const ROW_HEIGHT = 32;
const HEADER_HEIGHT = 48;
const SUMMARY_ROW_HEIGHT = 22;

// px_per_day: ความกว้างต่อวันที่ซูม 100%, top/bottom: หน่วยของหัว timeline 2 แถว, pad: วันเผื่อหน้า-หลัง
const SCALES = {
	day: { label: __("วัน"), px_per_day: 32, top: "month", bottom: "day", pad: 3 },
	week: { label: __("สัปดาห์"), px_per_day: 12, top: "month", bottom: "week", pad: 7 },
	month: { label: __("เดือน"), px_per_day: 4, top: "year", bottom: "month", pad: 15 },
	year: { label: __("ปี"), px_per_day: 0.8, top: "year", bottom: "quarter", pad: 60 },
};

// print_color ใช้ในงานพิมพ์ (ไม่ตามธีมมืด) ค่าเดียวกับสีของ Frappe ที่ตัวแปรอ้างถึง
const CURVES = [
	{
		key: "baseline",
		label: __("Baseline"),
		color: "var(--consbiz-gantt-baseline)",
		print_color: "#999999",
	},
	{ key: "plan", label: __("แผน"), color: "var(--consbiz-gantt-plan)", print_color: "#0d8ef8" },
	{
		key: "actual",
		label: __("จริง"),
		color: "var(--consbiz-gantt-actual)",
		print_color: "#43ac79",
	},
];

// curve = เส้นที่ใช้สี, money = แสดงเป็นจำนวนเงิน (Cash = มูลค่างานตามแผน/ที่ทำจริง)
const SUMMARY_ROWS = [
	{ key: "baseline", curve: "baseline", label: __("% Baseline สะสม") },
	{ key: "plan", curve: "plan", label: __("% แผนสะสม") },
	{ key: "actual", curve: "actual", label: __("% จริงสะสม") },
	{ key: "cash_plan", curve: "plan", label: __("Cash Plan (บาท)"), money: true },
	{ key: "cash_plan_cum", curve: "plan", label: __("Cash Plan สะสม"), money: true },
	{ key: "cash_actual", curve: "actual", label: __("Cash Actual (บาท)"), money: true },
	{ key: "cash_actual_cum", curve: "actual", label: __("Cash Actual สะสม"), money: true },
].map((row) => {
	const { color, print_color } = CURVES.find((c) => c.key === row.curve);
	return { ...row, color, print_color };
});

const data = ref(null);
const tasks = ref([]);
const entries = ref([]);
// ความคืบหน้าที่แก้แล้วยังไม่บันทึก key = "<task>|<date>"
const pending_progress = reactive(new Map());
const dirty = ref(false);
const saving = ref(false);
const hovered = ref(null);
const collapsed = reactive(new Set());
const status_date = ref(frappe.datetime.get_today());
const body_height = ref(0);
const settings = reactive({
	columns: [...DEFAULT_COLUMNS],
	widths: {},
	scale: "week",
	zoom: 1,
	curves: { baseline: true, plan: true, actual: true },
	show_baseline_bars: true,
	show_summary: true,
	show_split: true,
	show_labels: false,
	show_progress: false,
	show_status: true,
	grid_width: 560,
	print: {},
});

const panes = ref(null);
const grid = ref(null);
const timeline = ref(null);

// วันหยุดทั้งหมดใช้แรเงา ส่วนการนับวันใช้เฉพาะเมื่อติ๊ก "นับเฉพาะวันทำงาน"
const holidays = computed(() => new Set((data.value?.holidays || []).map(to_day)));
const counting_holidays = computed(() =>
	data.value?.use_working_days ? holidays.value : new Set()
);
const can_write = computed(() => Boolean(data.value?.can_write));
const status_day = computed(() => to_day(status_date.value) ?? today());

const columns = computed(() =>
	settings.columns
		.map((key) => COLUMNS.find((c) => c.key === key))
		.filter(Boolean)
		.map((c) => ({ ...c, width: settings.widths[c.key] || c.width }))
);

const visible_tasks = computed(() => {
	const rows = [];
	let hide_below = null;
	for (const task of tasks.value) {
		if (hide_below !== null && task.indent > hide_below) continue;
		hide_below = task.is_group && collapsed.has(task.name) ? task.indent : null;
		rows.push(task);
	}
	return rows;
});

// หน่วยสัปดาห์ตามตั้งค่าของแผน: เริ่มวันจันทร์ หรือแบ่งในเดือน 7-7-7-ที่เหลือ
const week_unit = computed(() => (data.value?.week_by_month ? "mweek" : "week"));
const scale = computed(() => {
	const config = SCALES[settings.scale];
	return config.bottom === "week" ? { ...config, bottom: week_unit.value } : config;
});
const ppd = computed(() => scale.value.px_per_day * settings.zoom);

// วันแรก-วันสุดท้ายของงานทั้งหมด (รวม baseline)
const extent = computed(() => {
	const days = tasks.value
		.flatMap((t) => [
			to_day(t.start_date),
			to_day(t.end_date),
			to_day(t.baseline_start_date),
			to_day(t.baseline_end_date),
		])
		.filter((d) => d !== null);
	const first = days.length ? Math.min(...days) : to_day(data.value?.start_date) ?? today();
	const last = days.length ? Math.max(...days) : first + 30;
	return { first, last };
});

const range = computed(() => {
	const { first, last } = extent.value;
	const { top, pad } = scale.value;
	return {
		start: floor_to(first - pad, top),
		end: next_of(floor_to(last + pad, top), top),
	};
});

const finish_date = computed(() => {
	const ends = tasks.value
		.filter((t) => !t.is_group && t.end_date)
		.map((t) => to_day(t.end_date));
	return ends.length ? from_day(Math.max(...ends)) : null;
});

// ---------- S-Curve และค่า % ----------

const has_baseline = computed(() => tasks.value.some((t) => t.baseline_start_date));

const curves = computed(() => ({
	baseline: has_baseline.value
		? curve_of(
				tasks.value,
				counting_holidays.value,
				"baseline_start_date",
				"baseline_end_date",
				"baseline_distribution"
		  )
		: null,
	plan: curve_of(tasks.value, counting_holidays.value),
	actual: actual_curve(tasks.value, entries.value, today()),
}));

const visible_curves = computed(() =>
	CURVES.filter((c) => settings.curves[c.key] && curves.value[c.key]).map((c) => ({
		...c,
		curve: curves.value[c.key],
	}))
);

const summary_rows = computed(() => (settings.show_summary ? SUMMARY_ROWS : []));

const readout = computed(() => ({
	baseline: value_at(curves.value.baseline, status_day.value),
	plan: value_at(curves.value.plan, status_day.value),
	actual: curves.value.actual ? value_at(curves.value.actual, status_day.value) : 0,
}));

// % แผน / % จริง / ปริมาณจริงสะสมของแต่ละงาน ณ วันที่เลือกดู (กลุ่มถ่วงน้ำหนักจากงานย่อย)
const metrics = computed(() => {
	const day = status_day.value;
	const sums = new Map();
	for (const entry of entries.value) {
		if (to_day(entry.date) > day) continue;
		const sum = sums.get(entry.task) || { percent: 0, qty: 0 };
		sum.percent += entry.percent || 0;
		sum.qty += entry.qty || 0;
		sums.set(entry.task, sum);
	}

	const map = new Map();
	for (const task of tasks.value) {
		if (task.is_group) continue;
		const sum = sums.get(task.name) || { percent: 0, qty: 0 };
		map.set(task.name, {
			plan_pct: plan_percent(
				task.start_date,
				task.end_date,
				day,
				counting_holidays.value,
				task.plan_distribution
			),
			actual_pct: Math.min(Math.max(sum.percent, 0), 100),
			actual_qty: sum.qty,
		});
	}
	tasks.value.forEach((task, i) => {
		if (!task.is_group) return;
		let weight = 0;
		let plan = 0;
		let actual = 0;
		for (const child of tasks.value.slice(i + 1)) {
			if (child.indent <= task.indent) break;
			if (child.is_group) continue;
			const m = map.get(child.name);
			weight += child.weight || 0;
			plan += (child.weight || 0) * m.plan_pct;
			actual += (child.weight || 0) * m.actual_pct;
		}
		map.set(task.name, {
			plan_pct: weight ? plan / weight : 0,
			actual_pct: weight ? actual / weight : 0,
			actual_qty: null,
		});
	});
	return map;
});

// ---------- โหลดและบันทึก ----------

function set_data(message) {
	data.value = message;
	tasks.value = message.tasks.map((t) => ({ ...t }));
	entries.value = message.progress_entries.map((e) => ({ ...e }));
	pending_progress.clear();
	dirty.value = false;
}

async function load() {
	const { message } = await frappe.call(`${API}.get_schedule_data`, { name: props.schedule });
	set_data(message);
	setup_page();
}

async function save() {
	if (!dirty.value || saving.value) return;
	saving.value = true;
	try {
		const { message } = await frappe.call({
			method: `${API}.save_tasks`,
			args: {
				name: props.schedule,
				modified: data.value.modified,
				tasks: tasks.value
					.filter((t) => !t.is_group)
					.map(({ name, start_date, end_date, plan_distribution }) => ({
						name,
						start_date,
						end_date,
						plan_distribution,
					})),
				progress: [...pending_progress.values()],
			},
			freeze: true,
		});
		set_data(message);
		frappe.show_alert({ message: __("บันทึกแล้ว"), indicator: "green" });
	} finally {
		saving.value = false;
	}
}

function set_baseline() {
	if (dirty.value) {
		frappe.msgprint(__("กรุณาบันทึกการแก้ไขก่อนตั้ง Baseline"));
		return;
	}
	const message = data.value.baseline_date
		? __("แทนที่ Baseline เดิม (ตั้งเมื่อ {0}) ด้วยวันที่ของแผนปัจจุบัน?", [
				frappe.datetime.str_to_user(data.value.baseline_date),
		  ])
		: __("เก็บวันเริ่ม/วันจบของแผนปัจจุบันเป็น Baseline?");
	frappe.confirm(message, async () => {
		const { message } = await frappe.call({
			method: `${API}.set_baseline`,
			args: { name: props.schedule, modified: data.value.modified },
			freeze: true,
		});
		set_data(message);
		setup_page();
		frappe.show_alert({ message: __("บันทึก Baseline แล้ว"), indicator: "green" });
	});
}

function reload() {
	if (dirty.value) {
		frappe.confirm(__("ทิ้งการแก้ไขที่ยังไม่บันทึก?"), load);
	} else {
		load();
	}
}

function setup_page() {
	const page = props.page;
	page.set_title(data.value.project_name || data.value.name);
	page.clear_actions();
	page.clear_menu();
	page.clear_icons();
	if (can_write.value) {
		page.set_primary_action(__("บันทึก"), save, "save");
		page.set_secondary_action(
			data.value.baseline_date ? __("ตั้ง Baseline ใหม่") : __("ตั้ง Baseline"),
			set_baseline
		);
	}
	page.add_action_icon("printer", print, "", __("พิมพ์"));
	page.add_menu_item(__("เปิดเอกสารแผนงาน"), () =>
		frappe.set_route("Form", DOCTYPE, data.value.name)
	);
	page.add_menu_item(__("เปิด BOQ"), () => frappe.set_route("Form", "BOQ", data.value.boq));
	page.add_menu_item(__("สร้าง Daily Report"), () =>
		frappe.new_doc("Daily Report", {
			construction_management: data.value.name,
			date: status_date.value,
		})
	);
	page.add_menu_item(__("รายการความคืบหน้า"), () =>
		frappe.set_route("List", "Construction Progress Entry", {
			construction_management: data.value.name,
		})
	);
	page.add_menu_item(__("โหลดใหม่"), reload);
	update_indicator();
}

function update_indicator() {
	if (dirty.value) props.page.set_indicator(__("ยังไม่บันทึก"), "orange");
	else if (data.value?.baseline_date)
		props.page.set_indicator(
			__("Baseline {0}", [frappe.datetime.str_to_user(data.value.baseline_date)]),
			"gray"
		);
	else props.page.clear_indicator();
}
watch(dirty, update_indicator);

// ---------- แก้ค่าจากตารางและการลากแถบ ----------

function update_task(task, field, value) {
	if (field === "actual_pct") return update_actual(task, value || 0);
	if (field === "actual_qty") return update_actual(task, ((value || 0) / task.quantity) * 100);

	const hol = counting_holidays.value;
	let start = to_day(task.start_date);
	let end = to_day(task.end_date);

	if (field === "start_date") {
		start = to_day(value);
		// เลื่อนวันเริ่มแล้วคงจำนวนวันเดิม
		end = start === null ? null : end_of(start, task.duration || 1, hol);
	} else if (field === "end_date") {
		end = to_day(value);
		if (end !== null && start === null) start = end;
		if (end !== null && end < start) {
			frappe.show_alert({ message: __("วันจบต้องไม่ก่อนวันเริ่ม"), indicator: "red" });
			return;
		}
		if (end === null && start !== null) end = start;
	} else if (field === "duration") {
		if (start === null) return;
		end = end_of(start, Math.max(cint(value), 1), hol);
	}
	set_dates(task, start, end);
}

function set_dates(task, start, end) {
	const hol = counting_holidays.value;
	// % แผนที่กำหนดเองใช้ต่อได้ถ้าจำนวนช่วงเท่าเดิม ไม่งั้นกลับไปคิดตามจำนวนวัน
	const distribution = parse_distribution(task.plan_distribution);
	if (distribution && (start === null || !distribution_fits(start, end, distribution))) {
		task.plan_distribution = null;
		frappe.show_alert({
			message: __("งาน {0}: จำนวนช่วงเปลี่ยน % แผนที่กำหนดเองถูกล้าง กลับไปคิดตามจำนวนวัน", [
				task.wbs,
			]),
			indicator: "orange",
		});
	}
	task.start_date = start === null ? null : from_day(start);
	task.end_date = end === null ? null : from_day(end);
	task.duration = start === null ? 0 : count_days(start, end, hol);
	roll_up(tasks.value, hol);
	dirty.value = true;
}

// คลิกแถบงาน: กำหนด % แผนรายวัน/สัปดาห์/เดือนของงานนั้น
function edit_plan(task) {
	const bottom = scale.value.bottom;
	open_plan_dialog(
		{
			task,
			holidays: counting_holidays.value,
			week_unit: week_unit.value,
			default_unit: ["day", "month"].includes(bottom) ? bottom : week_unit.value,
		},
		(distribution) => {
			if ((distribution || null) === (task.plan_distribution || null)) return;
			task.plan_distribution = distribution;
			dirty.value = true;
		}
	);
}

// กรอก % จริงสะสม ณ วันที่เลือกดู: เก็บเป็นรายการ Manual ของวันนั้น = ยอดสะสมที่ต้องการ - ยอดของวันอื่นก่อนหน้า
function update_actual(task, cumulative) {
	const day = status_day.value;
	const date = from_day(day);
	let before = 0;
	let after = 0;
	let manual = null;
	for (const entry of entries.value) {
		if (entry.task !== task.name) continue;
		const d = to_day(entry.date);
		if (d > day) after += entry.percent || 0;
		else if (d === day && entry.source === "Manual") manual = entry;
		else before += entry.percent || 0;
	}

	if (cumulative < 0 || cumulative > 100 + 1e-6) {
		frappe.show_alert({ message: __("% จริงต้องอยู่ระหว่าง 0-100"), indicator: "red" });
		return;
	}
	if (cumulative + after > 100 + 1e-6) {
		frappe.show_alert({
			message: __("รวมกับความคืบหน้าหลังวันที่ {0} แล้วจะเกิน 100%", [
				frappe.datetime.str_to_user(date),
			]),
			indicator: "red",
		});
		return;
	}

	const percent = cumulative - before;
	const qty = task.quantity > 0 ? (percent * task.quantity) / 100 : 0;
	if (Math.abs(percent) < 1e-9) {
		if (manual) entries.value.splice(entries.value.indexOf(manual), 1);
	} else if (manual) {
		Object.assign(manual, { percent, qty });
	} else {
		entries.value.push({ task: task.name, date, percent, qty, source: "Manual" });
	}
	pending_progress.set(`${task.name}|${date}`, { task: task.name, date, percent, qty });
	dirty.value = true;
}

// ---------- ย่อ/ขยาย ----------

function toggle(task) {
	if (collapsed.has(task.name)) collapsed.delete(task.name);
	else collapsed.add(task.name);
}

// แสดง WBS ถึงระดับ level (1 = หัวข้อหลัก) โดยย่อกลุ่มที่ลึกกว่านั้น null = ขยายทั้งหมด
function set_wbs_level(level) {
	collapsed.clear();
	if (!level) return;
	tasks.value
		.filter((t) => t.is_group && t.indent >= level - 1)
		.forEach((t) => collapsed.add(t.name));
}

const wbs_depth = computed(() => Math.max(0, ...tasks.value.map((t) => t.indent || 0)));

// ---------- คอลัมน์ ซูม และการตั้งค่า (จำต่อผู้ใช้ใน User Settings ของ Construction Management) ----------

function choose_columns() {
	const dialog = new frappe.ui.Dialog({
		title: __("เลือกคอลัมน์"),
		fields: [
			{
				fieldname: "columns",
				fieldtype: "MultiCheck",
				columns: 2,
				options: COLUMNS.filter((c) => c.key !== "item_name").map((c) => ({
					label: c.label,
					value: c.key,
					checked: settings.columns.includes(c.key),
				})),
			},
			{
				fieldtype: "HTML",
				options: `<p class="text-muted small">${__(
					"สลับตำแหน่งคอลัมน์ได้โดยลากหัวคอลัมน์ในตาราง"
				)}</p>`,
			},
		],
		primary_action_label: __("ตกลง"),
		primary_action({ columns: selected }) {
			// คอลัมน์เดิมคงลำดับไว้ ที่เพิ่มใหม่ต่อท้าย
			const kept = settings.columns.filter(
				(key) => key === "item_name" || selected.includes(key)
			);
			const added = selected.filter((key) => !kept.includes(key));
			settings.columns = [...kept, ...added];
			dialog.hide();
		},
	});
	dialog.show();
}

function resize_column(key, width) {
	settings.widths[key] = Math.max(40, Math.round(width));
}

function move_column(from, to) {
	const keys = settings.columns.filter((key) => key !== from);
	keys.splice(
		keys.indexOf(to) + (settings.columns.indexOf(from) < settings.columns.indexOf(to) ? 1 : 0),
		0,
		from
	);
	settings.columns = keys;
}

function zoom(action) {
	if (action === "in") settings.zoom = Math.min(settings.zoom * 1.25, 8);
	else if (action === "out") settings.zoom = Math.max(settings.zoom / 1.25, 0.05);
	else {
		const width = timeline.value.viewport_width() - 48;
		const days = range.value.end - range.value.start;
		settings.zoom = Math.min(Math.max(width / (days * scale.value.px_per_day), 0.05), 8);
	}
}

const save_settings = frappe.utils.debounce(() => {
	frappe.model.user_settings.save(DOCTYPE, "gantt", JSON.parse(JSON.stringify(settings)));
}, 1000);
watch(settings, save_settings, { deep: true });

// ---------- พิมพ์ ----------

function print() {
	open_print_dialog(print_model, settings.print, (options) => (settings.print = options));
}

// ระยะเวลาสัญญา เช่น "01-11-2026 - 30-04-2027 (181 วัน)"
function contract_text() {
	const { start_date, finish_date, duration } = data.value;
	if (!start_date || !finish_date) return "";
	return `${frappe.datetime.str_to_user(start_date)} - ${frappe.datetime.str_to_user(
		finish_date
	)} (${duration} ${__("วัน")})`;
}

function print_model() {
	const percent = (value) => format_number(value || 0, null, 2);
	return {
		title: data.value.project_name || data.value.name,
		project_name: data.value.project_name || "",
		employer: data.value.employer,
		contractor: data.value.contractor,
		supervisor: data.value.supervisor,
		contract_text: contract_text(),
		status_text: __("ณ วันที่ {0}: แผน {1}% · จริง {2}%", [
			frappe.datetime.str_to_user(status_date.value),
			percent(readout.value.plan),
			percent(readout.value.actual),
		]),
		columns: columns.value,
		rows: visible_tasks.value,
		metrics: metrics.value,
		extent: extent.value,
		ppd: ppd.value,
		units: { top: scale.value.top, bottom: scale.value.bottom },
		week_unit: week_unit.value,
		holidays: holidays.value,
		today: today(),
		status_day: status_day.value,
		curves: visible_curves.value.map((c) => ({ ...c, color: c.print_color })),
		all_curves: curves.value,
		total_amount: data.value.total_amount,
		show_baseline_bars: settings.show_baseline_bars,
		show_split: settings.show_split,
		show_labels: settings.show_labels,
		show_progress: settings.show_progress,
		show_status: settings.show_status,
		counting_holidays: counting_holidays.value,
		scale: settings.scale,
		scales: Object.fromEntries(
			Object.entries(SCALES).map(([key, config]) => [
				key,
				{
					label: config.label,
					top: config.top,
					bottom: config.bottom === "week" ? week_unit.value : config.bottom,
				},
			])
		),
		summary_rows: summary_rows.value.map((r) => ({ ...r, color: r.print_color })),
		colors: { baseline: CURVES[0].print_color },
		format_day: (day) => frappe.datetime.str_to_user(from_day(day)),
	};
}

// ---------- เลื่อนและปรับขนาด ----------

function on_timeline_scroll(scroll_top) {
	if (grid.value) grid.value.body.scrollTop = scroll_top;
}

function on_grid_wheel(delta) {
	timeline.value.body.scrollTop += delta;
}

function start_split(event) {
	const start_x = event.clientX;
	const start_width = settings.grid_width;
	const move = (e) => {
		const max = panes.value.clientWidth - 120;
		settings.grid_width = Math.min(Math.max(start_width + e.clientX - start_x, 180), max);
	};
	const up = () => {
		document.removeEventListener("mousemove", move);
		document.removeEventListener("mouseup", up);
		document.body.classList.remove("cs-resizing");
	};
	document.addEventListener("mousemove", move);
	document.addEventListener("mouseup", up);
	document.body.classList.add("cs-resizing");
}

// ความสูงของพื้นที่ Gantt ให้เต็มจอที่เหลือ
const pane_height = ref(400);
function fit_height() {
	if (!panes.value) return;
	const top = panes.value.getBoundingClientRect().top + window.scrollY;
	pane_height.value = Math.max(window.innerHeight - top - 24, 300);
}

function scroll_to_start() {
	const first = tasks.value.map((t) => to_day(t.start_date)).filter((d) => d !== null);
	timeline.value?.scroll_to_day(first.length ? Math.min(...first) : today());
}

watch(
	() => settings.scale,
	() => {
		settings.zoom = 1;
		setTimeout(scroll_to_start);
	}
);

onMounted(async () => {
	await frappe.model.with_doctype(DOCTYPE);
	const saved = frappe.get_user_settings(DOCTYPE).gantt || {};
	Object.assign(settings, saved, { curves: { ...settings.curves, ...saved.curves } });
	if (!SCALES[settings.scale]) settings.scale = "week";
	settings.columns = settings.columns.filter((key) => COLUMNS.some((c) => c.key === key));
	if (!settings.columns.includes("item_name")) settings.columns.unshift("item_name");
	await load();
	await nextTick();
	fit_height();
	window.addEventListener("resize", fit_height);
	setTimeout(scroll_to_start);
});

onBeforeUnmount(() => {
	window.removeEventListener("resize", fit_height);
	props.page.clear_indicator();
});
</script>

<template>
	<div class="cs-gantt">
		<div v-if="!data" class="text-muted p-4">{{ __("กำลังโหลด...") }}</div>
		<template v-else>
			<Toolbar
				v-model:status-date="status_date"
				:scales="SCALES"
				:settings="settings"
				:curves="CURVES"
				:wbs-depth="wbs_depth"
				:readout="readout"
				:total-amount="data.total_amount"
				:finish-date="finish_date"
				:contract-finish="data.finish_date"
				@choose-columns="choose_columns"
				@wbs-level="set_wbs_level"
				@today="timeline.scroll_to_day(today())"
				@zoom="zoom"
			/>
			<div ref="panes" class="cs-panes" :style="{ height: pane_height + 'px' }">
				<TaskGrid
					ref="grid"
					:style="{ width: settings.grid_width + 'px' }"
					:tasks="visible_tasks"
					:columns="columns"
					:metrics="metrics"
					:collapsed="collapsed"
					:can-write="can_write"
					:row-height="ROW_HEIGHT"
					:header-height="HEADER_HEIGHT"
					:body-height="body_height"
					:summary-rows="summary_rows"
					:summary-row-height="SUMMARY_ROW_HEIGHT"
					:hovered="hovered"
					@update="update_task"
					@toggle="toggle"
					@resize-column="resize_column"
					@move-column="move_column"
					@hover="hovered = $event"
					@scroll-y="on_grid_wheel"
				/>
				<div class="cs-splitter" @mousedown.prevent="start_split" />
				<Timeline
					ref="timeline"
					:tasks="visible_tasks"
					:range="range"
					:ppd="ppd"
					:units="{ top: scale.top, bottom: scale.bottom }"
					:holidays="holidays"
					:curves="visible_curves"
					:all-curves="curves"
					:show-baseline-bars="settings.show_baseline_bars"
					:show-split="settings.show_split"
					:show-labels="settings.show_labels"
					:show-progress="settings.show_progress"
					:counting-holidays="counting_holidays"
					:show-status="settings.show_status"
					:summary-rows="summary_rows"
					:summary-row-height="SUMMARY_ROW_HEIGHT"
					:total-amount="data.total_amount"
					:status-day="status_day"
					:metrics="metrics"
					:can-write="can_write"
					:row-height="ROW_HEIGHT"
					:header-height="HEADER_HEIGHT"
					:hovered="hovered"
					@scroll="on_timeline_scroll"
					@hover="hovered = $event"
					@set-dates="set_dates"
					@edit-plan="edit_plan"
					@body-height="body_height = $event"
				/>
			</div>
		</template>
	</div>
</template>

<style scoped>
/* ระยะขอบซ้าย-ขวาเท่าหัวเพจของ Frappe ไม่ให้ชิดเส้น sidebar */
.cs-gantt {
	padding: 0 var(--padding-md);
}
.cs-panes {
	display: flex;
	border: 1px solid var(--border-color);
	border-radius: var(--border-radius-md);
	overflow: hidden;
	background: var(--card-bg);
}
.cs-splitter {
	flex: 0 0 5px;
	cursor: col-resize;
	background: var(--border-color);
}
.cs-splitter:hover {
	background: var(--gray-400);
}
</style>

<style>
body.cs-resizing {
	cursor: col-resize;
	user-select: none;
}
</style>
