<script setup>
// หน้า Gantt ของ Construction Management: ตาราง WBS ซ้าย, timeline + S-Curve ขวา, ตารางสรุปด้านล่าง
// ฝั่ง server: consbiz/consbiz/doctype/construction_management/construction_management.py
// ความคืบหน้าจริงเก็บเป็นรายการรายวัน (Construction Progress Entry) กรอกในหน้านี้ได้ ณ "วันที่เลือกดู"
// การแก้ไข: Undo/Redo (Ctrl+Z / Ctrl+Y) ย้อนได้ทั้งวันที่ % แผนที่กำหนดเอง งานก่อนหน้า และ % จริงที่กรอก
// งานก่อนหน้า (FS/SS/FF/SF + lag): งานที่ตามมาเลื่อนตามทันทีที่แก้ (ASAP, apply_dependencies ใน schedule.js)
// ลาก/แก้วันที่ของงานที่มีงานก่อนหน้า = ปรับ lag ให้งานอยู่ตรงที่วาง (hold_start)
// บันทึกอัตโนมัติหลังหยุดแก้ AUTO_SAVE_DELAY และโหลดใหม่เองเมื่อมีการแก้จากที่อื่น (ตรวจทุก REFRESH_INTERVAL)
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";
import Toolbar from "./components/Toolbar.vue";
import TaskGrid from "./components/TaskGrid.vue";
import Timeline from "./components/Timeline.vue";
import { COLUMNS, DEFAULT_COLUMNS } from "./columns";
import { open_import_dialog } from "./import_dialog";
import { open_plan_dialog } from "./plan_dialog";
import { open_print_dialog } from "./print";
import {
	actual_curve,
	apply_dependencies,
	count_days,
	curve_of,
	dependency_order,
	distribution_fits,
	end_of,
	floor_to,
	format_predecessors,
	from_day,
	hold_start,
	next_of,
	parse_distribution,
	parse_predecessors,
	plan_percent,
	roll_up,
	to_day,
	today,
	value_at,
} from "./schedule";

const props = defineProps({ page: Object, schedule: String });

const API = "consbiz.consbiz.doctype.construction_management.construction_management";
const EXCEL_API = "consbiz.consbiz.doctype.construction_management.schedule_excel";
const DOCTYPE = "Construction Management";
const AUTO_SAVE_DELAY = 1500;
const REFRESH_INTERVAL = 30000;
const HISTORY_LIMIT = 100;
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

// แถวตารางสรุป เรียงเป็นกลุ่มตามเส้น (Baseline / แผน / จริง) แต่ละกลุ่มมีรายช่วงและสะสม
// curve = เส้นที่ใช้สีและเป็นกลุ่ม, money = แสดงเป็นจำนวนเงิน (Cash = มูลค่างานตามแผน/ที่ทำจริง)
// key ต้องตรงกับค่าที่ summary_values ใน schedule.js คืนมา ผู้ใช้เลือกแถวที่แสดงได้ (settings.summary_keys)
const SUMMARY_ROWS = [
	{ key: "baseline_period", curve: "baseline", label: __("% Baseline รายช่วง") },
	{ key: "baseline", curve: "baseline", label: __("% Baseline สะสม") },
	{ key: "plan_period", curve: "plan", label: __("% แผนรายช่วง") },
	{ key: "plan", curve: "plan", label: __("% แผนสะสม") },
	{ key: "cash_plan", curve: "plan", label: __("Cash Plan รายช่วง"), money: true },
	{ key: "cash_plan_cum", curve: "plan", label: __("Cash Plan สะสม"), money: true },
	{ key: "actual_period", curve: "actual", label: __("% จริงรายช่วง") },
	{ key: "actual", curve: "actual", label: __("% จริงสะสม") },
	{ key: "cash_actual", curve: "actual", label: __("Cash Actual รายช่วง"), money: true },
	{ key: "cash_actual_cum", curve: "actual", label: __("Cash Actual สะสม"), money: true },
].map((row) => {
	const { color, print_color } = CURVES.find((c) => c.key === row.curve);
	return { ...row, color, print_color };
});
const DEFAULT_SUMMARY_KEYS = SUMMARY_ROWS.map((row) => row.key);

const data = ref(null);
const tasks = ref([]);
const entries = ref([]);
const saving = ref(false);
// บันทึกไม่สำเร็จ (เช่น มีคนแก้แผนจากที่อื่น) หยุดบันทึกอัตโนมัติจนกว่าจะกดบันทึกเองหรือโหลดใหม่
const save_error = ref(false);
// มีการแก้จากที่อื่นระหว่างที่หน้านี้ยังมีงานค้างบันทึก
const remote_changed = ref(false);
// สถานะที่บันทึกแล้ว (ตรงกับฐานข้อมูล) และประวัติสำหรับ Undo/Redo เก็บเป็น snapshot()
const saved_state = ref(null);
const history = reactive({ past: [], future: [] });
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
	summary_keys: [...DEFAULT_SUMMARY_KEYS],
	show_split: true,
	show_links: true,
	show_labels: false,
	show_progress: false,
	show_status: true,
	auto_save: true,
	grid_width: 560,
	print: {},
	// แบบไฟล์ Excel ที่ส่งออก (schedule_excel.EDITABLE): duration = กำหนดจำนวนวัน, dates = กำหนดวันเริ่ม-จบ
	excel_mode: "duration",
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
const task_by_name = computed(() => new Map(tasks.value.map((t) => [t.name, t])));
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

// ---------- Baseline หลายชุด ----------
// ชุดที่เปิดดู (viewed_baseline) แยกจากชุดที่ใช้เทียบกับความคืบหน้าจริงในรายงาน (data.active_baseline)
// เปิดดูชุดไหน คัดลอกวันที่/% แผน/น้ำหนักของชุดนั้นลงช่อง baseline_* ของงานในหน้านี้ (ไม่บันทึก)
// แถบ Baseline, เส้น S-Curve, ตารางสรุป และงานพิมพ์จึงเป็นของชุดที่เปิดดู
const viewed_baseline = ref(null);
const baselines = computed(() => data.value?.baselines || []);
const viewed_baseline_doc = computed(
	() => baselines.value.find((b) => b.name === viewed_baseline.value) || null
);
const can_delete_baseline = frappe.model.can_delete("Construction Baseline");
const active_baseline_doc = computed(
	() => baselines.value.find((b) => b.name === data.value?.active_baseline) || null
);

function show_baseline(name) {
	const baseline = baselines.value.find((b) => b.name === name);
	viewed_baseline.value = baseline?.name || null;
	if (!baseline) return;
	const rows = (typeof baseline.tasks === "string" ? JSON.parse(baseline.tasks) : baseline.tasks) || {};
	for (const task of tasks.value) {
		const [start, end, distribution, weight] = rows[task.name] || [null, null, null, 0];
		Object.assign(task, {
			baseline_start_date: start,
			baseline_end_date: end,
			baseline_distribution: distribution,
			baseline_weight: weight,
		});
	}
}

// มูลค่าสัญญาปรับปรุง (สัญญาเดิม + งานเพิ่ม-ลดที่ผู้ว่าจ้างอนุมัติแล้ว) ใช้กับ Cash Plan และหัวเครื่องมือ
const revised_amount = computed(() => data.value?.revised_amount || data.value?.total_amount || 0);

const curves = computed(() => ({
	baseline: has_baseline.value
		? curve_of(
				tasks.value,
				counting_holidays.value,
				"baseline_start_date",
				"baseline_end_date",
				"baseline_distribution",
				// baseline ที่ตั้งก่อนมีการเก็บน้ำหนักใช้น้ำหนักปัจจุบัน
				tasks.value.some((t) => t.baseline_weight) ? "baseline_weight" : "weight"
		  )
		: null,
	plan: curve_of(tasks.value, counting_holidays.value),
	actual: actual_curve(
		tasks.value,
		entries.value,
		today(),
		data.value?.total_amount,
		data.value?.variation_steps
	),
}));

const visible_curves = computed(() =>
	CURVES.filter((c) => settings.curves[c.key] && curves.value[c.key]).map((c) => ({
		...c,
		curve: curves.value[c.key],
	}))
);

// แถวที่เลือกแสดง group_start = แถวแรกของกลุ่ม (ขีดเส้นแบ่งกลุ่ม)
const summary_rows = computed(() => {
	if (!settings.show_summary) return [];
	const rows = SUMMARY_ROWS.filter((row) => settings.summary_keys.includes(row.key));
	return rows.map((row, i) => ({ ...row, group_start: i > 0 && rows[i - 1].curve !== row.curve }));
});

const readout = computed(() => ({
	baseline: value_at(curves.value.baseline, status_day.value),
	plan: value_at(curves.value.plan, status_day.value),
	actual: curves.value.actual ? value_at(curves.value.actual, status_day.value) : 0,
}));

// % แผน / % จริง / ปริมาณจริงสะสมของแต่ละงาน ณ วันที่เลือกดู (กลุ่มถ่วงน้ำหนักจากงานย่อย)
// และข้อความงานก่อนหน้า (WBS) ของงานย่อย
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
			predecessors: format_predecessors(task.predecessors, task_by_name.value),
		});
	}
	tasks.value.forEach((task, i) => {
		if (!task.is_group) return;
		const children = [];
		for (const child of tasks.value.slice(i + 1)) {
			if (child.indent <= task.indent) break;
			if (!child.is_group) children.push(child);
		}
		// กลุ่มงานเพิ่ม (VO) น้ำหนัก 0 ถ่วงด้วยมูลค่าแทน (ตรงกับ weighted_progress ฝั่ง Python)
		const key = children.some((child) => child.weight) ? "weight" : "amount";
		let weight = 0;
		let plan = 0;
		let actual = 0;
		for (const child of children) {
			const m = map.get(child.name);
			weight += child[key] || 0;
			plan += (child[key] || 0) * m.plan_pct;
			actual += (child[key] || 0) * m.actual_pct;
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

// ---------- สถานะที่แก้ได้ (Undo/Redo, เทียบกับที่บันทึกแล้ว) ----------

// ค่าที่ผู้ใช้แก้ได้ในหน้านี้: วันที่ % แผนที่กำหนดเอง และงานก่อนหน้าของงานย่อย และรายการ % จริงที่กรอกเอง (Manual)
function snapshot() {
	return JSON.stringify({
		tasks: tasks.value
			.filter((t) => !t.is_group)
			.map((t) => [
				t.name,
				t.start_date || null,
				t.end_date || null,
				t.duration || 0,
				t.plan_distribution || null,
				t.predecessors || null,
			]),
		entries: entries.value
			.filter((e) => e.source === "Manual")
			.map(({ task, date, percent, qty }) => ({ task, date, percent, qty }))
			.sort((a, b) => (a.task + a.date).localeCompare(b.task + b.date)),
	});
}

const current_state = computed(snapshot);
const dirty = computed(() => saved_state.value !== null && current_state.value !== saved_state.value);

function restore(state) {
	const { tasks: rows, entries: manual } = JSON.parse(state);
	const by_name = new Map(tasks.value.map((t) => [t.name, t]));
	for (const [name, start_date, end_date, duration, plan_distribution, predecessors] of rows) {
		const task = by_name.get(name);
		if (task)
			Object.assign(task, {
				start_date,
				end_date,
				duration,
				plan_distribution,
				predecessors,
			});
	}
	roll_up(tasks.value, counting_holidays.value);
	entries.value = [
		...entries.value.filter((e) => e.source !== "Manual"),
		...manual.map((e) => ({ ...e, source: "Manual" })),
	];
}

// ทำการแก้ไข 1 ครั้ง (change) แล้วเก็บสถานะก่อนแก้ไว้ Undo ถ้าค่าไม่เปลี่ยนไม่เก็บ
function record(change) {
	const before = current_state.value;
	change();
	if (snapshot() === before) return;
	history.past.push(before);
	if (history.past.length > HISTORY_LIMIT) history.past.shift();
	history.future = [];
}

function undo() {
	if (!history.past.length || !can_write.value) return;
	history.future.push(current_state.value);
	restore(history.past.pop());
}

function redo() {
	if (!history.future.length || !can_write.value) return;
	history.past.push(current_state.value);
	restore(history.future.pop());
}

// Ctrl+Z / Ctrl+Y / Ctrl+Shift+Z ทำงานเหมือนปุ่ม Undo/Redo ทั้งหน้า รวมถึงตอนพิมพ์ในช่องของตาราง
// (ค่าที่พิมพ์ค้างในช่องถูกยกเลิกแล้วย้อนการแก้ไขล่าสุด) ยกเว้นช่องนอกหน้า Gantt เช่นช่องค้นหาด้านบน และใน dialog
function on_keydown(event) {
	if (!(event.ctrlKey || event.metaKey) || event.altKey) return;
	const key = event.key.toLowerCase();
	const is_undo = key === "z" && !event.shiftKey;
	const is_redo = key === "y" || (key === "z" && event.shiftKey);
	if (!is_undo && !is_redo) return;
	if (document.querySelector(".modal.show")) return;
	const typing = event.target.closest("input, textarea, select, [contenteditable='true']");
	if (typing && !typing.closest(".cs-gantt")) return;
	event.preventDefault();
	event.stopPropagation();
	grid.value?.cancel_edit();
	if (is_undo) undo();
	else redo();
}

// % จริงที่เปลี่ยนจากที่บันทึกไว้ 1 รายการต่องานต่อวัน (ค่า 0 = ลบรายการนั้น)
function progress_changes(saved) {
	const key = (e) => `${e.task}|${e.date}`;
	const before = new Map(JSON.parse(saved).entries.map((e) => [key(e), e]));
	const now = new Map(JSON.parse(current_state.value).entries.map((e) => [key(e), e]));
	const changes = [];
	for (const [k, e] of now) {
		const old = before.get(k);
		if (!old || old.percent !== e.percent || old.qty !== e.qty) changes.push(e);
	}
	for (const [k, e] of before) {
		if (!now.has(k)) changes.push({ task: e.task, date: e.date, percent: 0, qty: 0 });
	}
	return changes;
}

// ---------- โหลดและบันทึก ----------

// keep_history: ข้อมูลจากการบันทึกของหน้านี้เอง (Undo ต่อได้) ไม่งั้นเป็นข้อมูลใหม่จากฐานข้อมูล ล้างประวัติ
function set_data(message, { keep_history = false } = {}) {
	data.value = message;
	// งานก่อนหน้าเขียนเป็น JSON รูปแบบเดียวกับที่หน้านี้สร้าง ไม่ให้ Undo กลับมาแล้วดูเหมือนยังไม่บันทึก
	tasks.value = message.tasks.map((t) => ({
		...t,
		predecessors: t.predecessors ? JSON.stringify(parse_predecessors(t.predecessors)) : null,
	}));
	entries.value = message.progress_entries.map((e) => ({ ...e }));
	// เปิดดูชุดเดิมต่อถ้ายังอยู่ ไม่งั้นดูชุดที่ใช้เทียบ
	show_baseline(
		message.baselines.some((b) => b.name === viewed_baseline.value)
			? viewed_baseline.value
			: message.active_baseline
	);
	saved_state.value = snapshot();
	save_error.value = false;
	remote_changed.value = false;
	if (!keep_history) {
		history.past = [];
		history.future = [];
	}
}

async function load() {
	const { message } = await frappe.call(`${API}.get_schedule_data`, { name: props.schedule });
	set_data(message);
	setup_page();
}

async function save({ auto = false } = {}) {
	if (!dirty.value || saving.value || !can_write.value) return;
	const state = current_state.value;
	saving.value = true;
	try {
		const { message } = await frappe.call({
			method: `${API}.save_tasks`,
			args: {
				name: props.schedule,
				modified: data.value.modified,
				tasks: tasks.value
					.filter((t) => !t.is_group)
					.map(({ name, start_date, end_date, plan_distribution, predecessors }) => ({
						name,
						start_date,
						end_date,
						plan_distribution,
						predecessors,
					})),
				progress: progress_changes(saved_state.value),
			},
			freeze: !auto,
		});
		if (current_state.value === state) {
			set_data(message, { keep_history: true });
		} else {
			// แก้ต่อระหว่างรอบันทึก: เก็บสิ่งที่แก้ใหม่ไว้ บันทึกรอบถัดไป
			Object.assign(data.value, { modified: message.modified, version: message.version });
			saved_state.value = state;
		}
		save_error.value = false;
		if (!auto) frappe.show_alert({ message: __("บันทึกแล้ว"), indicator: "green" });
	} catch (error) {
		save_error.value = true;
	} finally {
		saving.value = false;
	}
	if (dirty.value && !save_error.value) schedule_auto_save();
}

const schedule_auto_save = frappe.utils.debounce(() => {
	if (settings.auto_save && dirty.value && !save_error.value) save({ auto: true });
}, AUTO_SAVE_DELAY);
watch(current_state, () => dirty.value && schedule_auto_save());
watch(
	() => settings.auto_save,
	(on) => on && schedule_auto_save()
);

// โหลดใหม่เองเมื่อแผนงานหรือความคืบหน้าถูกแก้จากที่อื่น (เช่น Submit Daily Report หรือ Variation Order)
// ถ้าหน้านี้ยังมีงานค้างบันทึก ไม่โหลดทับ แค่แจ้งเตือน
async function check_remote() {
	if (document.hidden || saving.value || !data.value) return;
	let version;
	try {
		({ message: version } = await frappe.call({
			method: `${API}.get_schedule_version`,
			args: { name: props.schedule },
		}));
	} catch {
		return;
	}
	if (version === data.value.version || saving.value) return;
	if (dirty.value) {
		remote_changed.value = true;
		return;
	}
	await load();
	frappe.show_alert({ message: __("โหลดข้อมูลล่าสุดแล้ว"), indicator: "blue" });
}

let refresh_timer = null;
function on_visibility_change() {
	if (!document.hidden) check_remote();
}

// เปลี่ยน Baseline ต้องบันทึกแผนงานด้วย จึงให้บันทึกการแก้ไขที่ค้างอยู่ก่อน
function check_saved() {
	if (!dirty.value) return true;
	frappe.msgprint(__("กรุณาบันทึกการแก้ไขก่อนเปลี่ยน Baseline"));
	return false;
}

function save_baseline() {
	if (!check_saved()) return;
	const dialog = new frappe.ui.Dialog({
		title: __("บันทึก Baseline ใหม่"),
		fields: [
			{
				fieldname: "title",
				fieldtype: "Data",
				label: __("ชื่อ"),
				reqd: 1,
				default: __("Baseline {0}", [baselines.value.length + 1]),
			},
			{
				fieldname: "reason",
				fieldtype: "Small Text",
				label: __("เหตุผลที่ปรับแผน"),
				description: __("เช่น แผนตามสัญญา, ได้รับอนุมัติขยายเวลา (EOT), งานเพิ่ม-ลด"),
			},
			{
				fieldname: "activate",
				fieldtype: "Check",
				label: __("ใช้ชุดนี้เทียบกับความคืบหน้าจริง (Daily Report / Daily Request)"),
				default: 1,
			},
		],
		primary_action_label: __("บันทึก"),
		primary_action: async (values) => {
			const { message } = await frappe.call({
				method: `${API}.save_baseline`,
				args: { name: props.schedule, modified: data.value.modified, ...values },
				freeze: true,
			});
			dialog.hide();
			viewed_baseline.value = message.baselines.at(-1).name;
			set_data(message);
			setup_page();
			frappe.show_alert({ message: __("บันทึก Baseline แล้ว"), indicator: "green" });
		},
	});
	dialog.show();
}

function activate_baseline() {
	const baseline = viewed_baseline_doc.value;
	if (!baseline || !check_saved()) return;
	frappe.confirm(
		__(
			"ใช้ {0} เทียบกับความคืบหน้าจริง? Daily Report / Daily Request ที่บันทึกต่อจากนี้จะเทียบกับชุดนี้ (ฉบับที่บันทึกแล้วไม่เปลี่ยน)",
			[frappe.utils.escape_html(baseline.title)]
		),
		async () => {
			const { message } = await frappe.call({
				method: `${API}.activate_baseline`,
				args: { name: props.schedule, modified: data.value.modified, baseline: baseline.name },
				freeze: true,
			});
			set_data(message);
			setup_page();
			frappe.show_alert({ message: __("เปลี่ยน Baseline ที่ใช้เทียบแล้ว"), indicator: "green" });
		}
	);
}

function delete_baseline() {
	const baseline = viewed_baseline_doc.value;
	if (!baseline || baseline.name === data.value.active_baseline) return;
	frappe.confirm(
		__("ลบ Baseline {0}? ลบแล้วเรียกคืนไม่ได้", [frappe.utils.escape_html(baseline.title)]),
		async () => {
			const { message } = await frappe.call({
				method: `${API}.delete_baseline`,
				args: { name: props.schedule, baseline: baseline.name },
				freeze: true,
			});
			// ลบไม่เปลี่ยนแผนงาน: อัปเดตแค่รายการแล้วกลับไปดูชุดที่ใช้เทียบ (การแก้ที่ค้างอยู่ยังอยู่)
			data.value.baselines = message;
			show_baseline(data.value.active_baseline);
			update_indicator();
			frappe.show_alert({ message: __("ลบ Baseline แล้ว"), indicator: "green" });
		}
	);
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
	}
	page.add_action_icon("refresh-cw", reload, "", __("โหลดใหม่"));
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
	page.add_menu_item(__("ส่งออก Excel"), export_excel);
	if (can_write.value) page.add_menu_item(__("นำเข้าจาก Excel"), import_excel);
	page.add_menu_item(__("รายการความคืบหน้า"), () =>
		frappe.set_route("List", "Construction Progress Entry", {
			construction_management: data.value.name,
		})
	);
	page.add_menu_item(__("โหลดใหม่"), reload);
	update_indicator();
}

function update_indicator() {
	if (saving.value) props.page.set_indicator(__("กำลังบันทึก..."), "blue");
	else if (save_error.value) props.page.set_indicator(__("บันทึกไม่สำเร็จ"), "red");
	else if (remote_changed.value)
		props.page.set_indicator(__("มีการแก้จากที่อื่น บันทึกหรือโหลดใหม่"), "red");
	else if (dirty.value) props.page.set_indicator(__("ยังไม่บันทึก"), "orange");
	else if (viewed_baseline_doc.value && viewed_baseline_doc.value !== active_baseline_doc.value)
		props.page.set_indicator(
			__("กำลังดู Baseline: {0}", [frappe.utils.escape_html(viewed_baseline_doc.value.title)]),
			"blue"
		);
	else if (active_baseline_doc.value)
		props.page.set_indicator(__("Baseline: {0}", [frappe.utils.escape_html(active_baseline_doc.value.title)]), "gray");
	else props.page.clear_indicator();
}
watch([dirty, saving, save_error, remote_changed, viewed_baseline], update_indicator);

// ---------- แก้ค่าจากตารางและการลากแถบ ----------

function update_task(task, field, value) {
	if (field === "actual_pct") return update_actual(task, value || 0);
	if (field === "actual_qty") return update_actual(task, ((value || 0) / task.quantity) * 100);
	if (field === "predecessors") return update_predecessors(task, value);

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

// ตั้งวันที่ของงาน ถ้างานมีงานก่อนหน้าปรับ lag ให้งานอยู่ตรงนั้น แล้วเลื่อนงานที่ตามมา
function set_dates(task, start, end) {
	const hol = counting_holidays.value;
	task.start_date = start === null ? null : from_day(start);
	task.end_date = end === null ? null : from_day(end);
	task.duration = start === null ? 0 : count_days(start, end, hol);
	if (hold_start(task, task_by_name.value, hol)) {
		frappe.show_alert({
			message: __("งาน {0}: งานก่อนหน้าเปลี่ยนเป็น {1}", [
				task.wbs,
				format_predecessors(task.predecessors, task_by_name.value),
			]),
			indicator: "blue",
		});
	}
	reschedule([task]);
}

// เลื่อนงานตามงานก่อนหน้า แล้วคิดวันที่ของกลุ่มใหม่ (edited = งานที่ผู้ใช้เพิ่งแก้)
function reschedule(edited) {
	const hol = counting_holidays.value;
	const moved = apply_dependencies(tasks.value, hol) || [];

	// % แผนที่กำหนดเองใช้ต่อได้ถ้าจำนวนช่วงเท่าเดิม ไม่งั้นกลับไปคิดตามจำนวนวัน
	const cleared = [...new Set([...edited, ...moved])].filter((t) => {
		const distribution = parse_distribution(t.plan_distribution);
		const s = to_day(t.start_date);
		if (
			!distribution ||
			(s !== null && distribution_fits(s, to_day(t.end_date), distribution))
		)
			return false;
		t.plan_distribution = null;
		return true;
	});
	if (cleared.length) {
		frappe.show_alert({
			message: __("งาน {0}: จำนวนช่วงเปลี่ยน % แผนที่กำหนดเองถูกล้าง กลับไปคิดตามจำนวนวัน", [
				wbs_list(cleared),
			]),
			indicator: "orange",
		});
	}
	const [task] = edited;
	if (edited.length === 1 && moved.includes(task)) {
		frappe.show_alert({
			message: __("งาน {0} เลื่อนไปเริ่ม {1} ตามงานก่อนหน้า", [
				task.wbs,
				frappe.datetime.str_to_user(task.start_date),
			]),
			indicator: "blue",
		});
	}
	const followers = moved.filter((t) => !edited.includes(t));
	if (followers.length) {
		frappe.show_alert({
			message: __("เลื่อนงานที่ตามมา {0} งาน: {1}", [followers.length, wbs_list(followers)]),
			indicator: "blue",
		});
	}
	roll_up(tasks.value, hol);
}

// WBS ของงานสำหรับข้อความแจ้งเตือน (ยาวเกินตัดท้าย)
function wbs_list(rows, limit = 10) {
	const text = rows
		.slice(0, limit)
		.map((t) => t.wbs)
		.join(", ");
	return rows.length > limit ? `${text} ...` : text;
}

// กรอกงานก่อนหน้าเป็น WBS คั่นด้วยจุลภาค เช่น "1.2, 1.3SS+2, 2.1FF-1" (ไม่ระบุชนิด = FS, lag เป็นวัน)
const LINK_PATTERN = /^(.+?)\s*(FS|SS|FF|SF)?\s*(?:([+-])\s*(\d+))?$/i;

// แปลงข้อความงานก่อนหน้าของ task เป็น JSON ที่เก็บใน predecessors คืน { value } หรือ { error }
function parse_link_text(task, text) {
	const by_wbs = new Map(tasks.value.map((t) => [String(t.wbs || "").trim(), t]));
	const links = new Map();
	for (const token of String(text || "")
		.split(/[,;]/)
		.map((s) => s.trim())
		.filter(Boolean)) {
		const match = token.match(LINK_PATTERN);
		const predecessor = match && by_wbs.get(match[1].trim());
		if (!predecessor) return { error: __("ไม่พบงาน WBS {0}", [match ? match[1] : token]) };
		if (predecessor.is_group)
			return { error: __("{0} เป็นหัวข้อกลุ่ม ให้ผูกกับงานย่อยแทน", [predecessor.wbs]) };
		if (predecessor === task) return { error: __("งานผูกกับตัวเองไม่ได้") };
		const lag = match[4] ? Number(match[4]) * (match[3] === "-" ? -1 : 1) : 0;
		links.set(predecessor.name, {
			task: predecessor.name,
			type: (match[2] || "FS").toUpperCase(),
			lag,
		});
	}
	return { value: links.size ? JSON.stringify([...links.values()]) : null };
}

function update_predecessors(task, text) {
	const { value, error } = parse_link_text(task, text);
	if (error) {
		frappe.show_alert({ message: error, indicator: "red" });
		return;
	}
	const before = task.predecessors;
	task.predecessors = value;
	if (!dependency_order(tasks.value)) {
		task.predecessors = before;
		frappe.show_alert({ message: __("งานก่อนหน้าผูกกันเป็นวง"), indicator: "red" });
		return;
	}
	reschedule([task]);
}

// ---------- Excel (schedule_excel.py) ----------

function export_excel() {
	if (dirty.value) {
		frappe.msgprint(__("กรุณาบันทึกการแก้ไขก่อนส่งออก"));
		return;
	}
	const dialog = new frappe.ui.Dialog({
		title: __("ส่งออก Excel"),
		fields: [
			{
				fieldname: "mode",
				fieldtype: "Select",
				label: __("แก้ในไฟล์โดย"),
				options: [
					{ value: "duration", label: __("กำหนดวันเริ่ม + จำนวนวัน (วันจบคำนวณให้)") },
					{ value: "dates", label: __("กำหนดวันเริ่ม-วันจบ (จำนวนวันนับให้)") },
				],
				default: settings.excel_mode,
			},
			{
				fieldtype: "HTML",
				options: `<p class="text-muted small">${__(
					"นำเข้ากลับได้ทั้งสองแบบ ระบบใช้วันเริ่ม-วันจบในไฟล์เสมอ (จำนวนวันใช้เมื่อวันจบว่าง)"
				)}</p>`,
			},
		],
		primary_action_label: __("ส่งออก"),
		primary_action({ mode }) {
			settings.excel_mode = mode;
			dialog.hide();
			open_url_post(`/api/method/${EXCEL_API}.export_schedule`, {
				name: props.schedule,
				mode,
			});
		},
	});
	dialog.show();
}

function import_excel() {
	open_import_dialog(`${EXCEL_API}.import_schedule`, props.schedule, (result) =>
		record(() => apply_import(result))
	);
}

// ใส่ค่าจากไฟล์ทีละงาน (แก้ในหน้านี้ ยังไม่บันทึก Undo ได้ทั้งชุด) ช่องที่ไม่มีในแถว = ไม่เปลี่ยน
// วันที่: ใช้วันเริ่ม-วันจบเสมอ จำนวนวันใช้เฉพาะแถวที่วันจบว่าง (ไม่ตรงกับวันที่ = แจ้งเตือน)
// งานที่วันเริ่มเปลี่ยนแต่งานก่อนหน้าไม่เปลี่ยน ปรับ lag ให้อยู่ตามวันในไฟล์เหมือนลากในหน้า
// ถ้างานก่อนหน้าเปลี่ยนด้วย หรือแก้แค่วันจบ/จำนวนวัน วันเริ่มเป็นไปตามงานก่อนหน้า
// (วันที่ในไฟล์ไม่เลื่อนตามงานก่อนหน้าที่แก้ในไฟล์เดียวกัน จึงตรึงไม่ได้)
function apply_import({ rows, warnings }) {
	const hol = counting_holidays.value;
	const before = current_state.value;
	const by_wbs = new Map(tasks.value.map((t) => [String(t.wbs || "").trim(), t]));
	const messages = [...warnings];
	const edited = [];
	const held = [];
	for (const row of rows) {
		const task = by_wbs.get(row.wbs);
		if (!task) {
			messages.push(__("แถว {0}: ไม่พบงาน WBS {1} ในแผนนี้", [row.row_no, row.wbs]));
			continue;
		}
		if (task.is_group) continue;

		let links_changed = false;
		if ("predecessors" in row) {
			const { value, error } = parse_link_text(task, row.predecessors);
			if (error) messages.push(__("แถว {0}: {1}", [row.row_no, error]));
			else if (value !== (task.predecessors || null)) {
				task.predecessors = value;
				links_changed = true;
			}
		}

		const start = row.start_date ? to_day(row.start_date) : to_day(task.start_date);
		let end = to_day(task.end_date);
		if (row.end_date) {
			end = to_day(row.end_date);
			const days = start === null || end < start ? null : count_days(start, end, hol);
			if (row.duration && days !== null && row.duration !== days)
				messages.push(
					__(
						"แถว {0}: จำนวนวันในไฟล์ ({1}) ไม่ตรงกับวันเริ่ม-วันจบ ใช้วันที่ ({2} วัน)",
						[row.row_no, row.duration, days]
					)
				);
		} else if (row.duration && start !== null) end = end_of(start, row.duration, hol);
		else if (row.start_date) end = end_of(start, task.duration || 1, hol);
		let dates_changed = false;
		if (start === null && end !== null) {
			messages.push(
				__("แถว {0}: ใส่วันจบแล้วต้องใส่วันเริ่มด้วย ข้ามวันที่ของงานนี้", [row.row_no])
			);
		} else if (start !== null && end < start) {
			messages.push(
				__("แถว {0}: วันจบต้องไม่ก่อนวันเริ่ม ข้ามวันที่ของงานนี้", [row.row_no])
			);
		} else if (start !== to_day(task.start_date) || end !== to_day(task.end_date)) {
			if (!links_changed && start !== to_day(task.start_date)) held.push(task);
			task.start_date = from_day(start);
			task.end_date = from_day(end);
			task.duration = count_days(start, end, hol);
			dates_changed = true;
		}
		if (links_changed || dates_changed) edited.push(task);
	}

	if (!dependency_order(tasks.value)) {
		restore(before);
		frappe.msgprint(__("งานก่อนหน้าในไฟล์ผูกกันเป็นวง ยกเลิกการนำเข้า"));
		return;
	}
	for (const task of held) hold_start(task, task_by_name.value, hol);
	reschedule(edited);

	const summary = edited.length
		? __("แก้แผน {0} งานแล้ว ตรวจดูแล้วกดบันทึก (ย้อนกลับได้ด้วย Undo)", [edited.length])
		: __("ไม่มีงานที่เปลี่ยน");
	if (messages.length) {
		frappe.msgprint({
			title: __("นำเข้าจาก Excel"),
			message: `<p>${summary}</p><ul>${messages
				.map((m) => `<li>${frappe.utils.escape_html(m)}</li>`)
				.join("")}</ul>`,
			indicator: "orange",
		});
	} else {
		frappe.show_alert({ message: summary, indicator: "green" });
	}
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
			record(() => (task.plan_distribution = distribution));
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
		status_text:
			readout.value.baseline !== null
				? __("ณ วันที่ {0}: {1} {2}% · แผน {3}% · จริง {4}%", [
						frappe.datetime.str_to_user(status_date.value),
						viewed_baseline_doc.value
							? `Baseline (${viewed_baseline_doc.value.title})`
							: "Baseline",
						percent(readout.value.baseline),
						percent(readout.value.plan),
						percent(readout.value.actual),
				  ])
				: __("ณ วันที่ {0}: แผน {1}% · จริง {2}%", [
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
		total_amount: revised_amount.value,
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

// ปุ่มวันนี้: ดูค่า ณ วันนี้ และเลื่อน timeline ไปที่วันนี้
function go_today() {
	status_date.value = frappe.datetime.get_today();
	timeline.value?.scroll_to_day(today());
}

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
	settings.summary_keys = (saved.summary_keys || DEFAULT_SUMMARY_KEYS).filter((key) =>
		SUMMARY_ROWS.some((row) => row.key === key)
	);
	if (!SCALES[settings.scale]) settings.scale = "week";
	settings.columns = settings.columns.filter((key) => COLUMNS.some((c) => c.key === key));
	if (!settings.columns.includes("item_name")) settings.columns.unshift("item_name");
	await load();
	await nextTick();
	fit_height();
	window.addEventListener("resize", fit_height);
	// capture: ให้ทำงานก่อน undo ของช่องกรอกและ handler อื่นของ Frappe
	document.addEventListener("keydown", on_keydown, true);
	document.addEventListener("visibilitychange", on_visibility_change);
	refresh_timer = setInterval(check_remote, REFRESH_INTERVAL);
	setTimeout(scroll_to_start);
});

onBeforeUnmount(() => {
	window.removeEventListener("resize", fit_height);
	document.removeEventListener("keydown", on_keydown, true);
	document.removeEventListener("visibilitychange", on_visibility_change);
	clearInterval(refresh_timer);
	// ออกจากหน้าโดยยังมีงานค้าง บันทึกให้ทันที (ถ้าเปิดบันทึกอัตโนมัติ)
	if (settings.auto_save && dirty.value && !save_error.value) save({ auto: true });
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
				:summary-options="SUMMARY_ROWS"
				:can-write="can_write"
				:can-undo="history.past.length > 0"
				:can-redo="history.future.length > 0"
				:contract-amount="data.total_amount"
				:total-amount="revised_amount"
				:finish-date="finish_date"
				:contract-finish="data.finish_date"
				:contract-start="data.start_date"
				:contract-duration="data.duration"
				:baselines="baselines"
				:viewed-baseline="viewed_baseline"
				:active-baseline="data.active_baseline"
				:can-delete-baseline="can_delete_baseline"
				@view-baseline="show_baseline"
				@save-baseline="save_baseline"
				@activate-baseline="activate_baseline"
				@delete-baseline="delete_baseline"
				@choose-columns="choose_columns"
				@wbs-level="set_wbs_level"
				@today="go_today"
				@zoom="zoom"
				@undo="undo"
				@redo="redo"
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
					@update="(...args) => record(() => update_task(...args))"
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
					:show-links="settings.show_links"
					:show-labels="settings.show_labels"
					:show-progress="settings.show_progress"
					:counting-holidays="counting_holidays"
					:show-status="settings.show_status"
					:summary-rows="summary_rows"
					:summary-row-height="SUMMARY_ROW_HEIGHT"
					:total-amount="revised_amount"
					:status-day="status_day"
					:metrics="metrics"
					:can-write="can_write"
					:row-height="ROW_HEIGHT"
					:header-height="HEADER_HEIGHT"
					:hovered="hovered"
					@scroll="on_timeline_scroll"
					@hover="hovered = $event"
					@set-dates="(...args) => record(() => set_dates(...args))"
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
	border-radius: var(--radius-lg);
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
