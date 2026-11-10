// สถานะและการแก้แผนงานของหน้าแก้แผนในแอป (PlanEdit.vue) ไม่พึ่ง desk
// คำนวณด้วย construction_management/schedule.js ชุดเดียวกับหน้า Gantt ของระบบเต็ม (App.vue) ผลจึงตรงกัน
// โหลด/บันทึกผ่าน API เดิม get_schedule_data / save_tasks / get_schedule_version (construction_management.py)
// แก้ได้: วันเริ่ม-จบ/จำนวนวัน (ลากแถบหรือกรอก), งานก่อนหน้า, % แผนรายช่วง (plan_distribution), % จริง ณ วัน Cut-off (รายการ Manual),
// คน/เครื่องจักร + วัสดุของงาน (แถวของแผนทรัพยากร/แผนวัสดุ บันทึกพร้อมแผนงานเหมือน App.vue)
// Undo/Redo เก็บเป็น snapshot ทั้งชุด บันทึกอัตโนมัติหลังหยุดแก้ AUTO_SAVE_DELAY
import { computed, reactive, ref, watch } from "vue";
import { call, post, show_error, toast } from "../../../../shared/api.js";
import {
	actual_curve,
	allocate_materials,
	apply_dependencies,
	count_days,
	curve_of,
	dependency_order,
	distribution_fits,
	end_of,
	format_predecessors,
	from_day,
	hold_start,
	parse_distribution,
	parse_predecessors,
	plan_percent,
	roll_up,
	to_day,
	today,
	total_float,
	value_at,
} from "../../../../construction_management/schedule.js";

const API = "consbiz.consbiz.doctype.construction_management.construction_management";
const STRUCTURE_API = "consbiz.consbiz.doctype.construction_management.structure";
const AUTO_SAVE_DELAY = 1500;
const HISTORY_LIMIT = 100;
// ช้ากว่าแผนไม่เกินนี้ (จุด %) = เฝ้าระวัง เกิน = ล่าช้า (ตรงกับ progress_status ใน columns.js)
const LATE_LIMIT = 10;

export const LINK_TYPES = [
	{ value: "FS", label: "FS", description: "จบแล้วเริ่ม" },
	{ value: "SS", label: "SS", description: "เริ่มพร้อมกัน" },
	{ value: "FF", label: "FF", description: "จบพร้อมกัน" },
	{ value: "SF", label: "SF", description: "เริ่มแล้วจบ" },
];

// คอลัมน์ของตาราง (PlanSheet.vue) edit = แก้ในช่องได้: date / int / text / pct
export const COLUMNS = {
	wbs: { label: "WBS", w: 58 },
	item_name: { label: "ชื่องาน", w: 240 },
	boq_wbs: { label: "เลข BOQ", w: 72 },
	start_date: { label: "เริ่ม", w: 104, edit: "date" },
	end_date: { label: "จบ", w: 104, edit: "date" },
	duration: { label: "วัน", w: 54, edit: "int", align: "end" },
	predecessors: { label: "งานก่อนหน้า", w: 108, edit: "text" },
	plan_pct: { label: "% แผน", w: 76, align: "end" },
	actual_pct: { label: "% จริง", w: 76, edit: "pct", align: "end" },
	diff: { label: "±%", w: 76, align: "end" },
	status: { label: "สถานะ", w: 92 },
	total_float: { label: "Float", w: 58, align: "end" },
};

// เส้น S-Curve และแถวตารางสรุปที่เลือกแสดงได้ (หน้าแผนงานและงานพิมพ์ใช้ชุดเดียวกัน)
// Baseline = แผนตามสัญญา (ตัวเทียบหลัก), แผน = แผนปัจจุบันที่ปรับได้ตลอด, จริง = ผลงานจริง
export const CURVE_ITEMS = [
	{ key: "baseline", label: "แผนสัญญา" },
	{ key: "actual", label: "จริง" },
	{ key: "plan", label: "แผนปัจจุบัน" },
];
export const SUMMARY_ROWS = [
	{ key: "baseline_period", curve: "baseline", label: "% แผนสัญญารายช่วง" },
	{ key: "baseline", curve: "baseline", label: "% แผนสัญญาสะสม" },
	{ key: "plan_period", curve: "plan", label: "% แผนรายช่วง" },
	{ key: "plan", curve: "plan", label: "% แผนสะสม" },
	{ key: "actual_period", curve: "actual", label: "% จริงรายช่วง" },
	{ key: "actual", curve: "actual", label: "% จริงสะสม" },
];
// ค่าเริ่มต้น = Baseline กับจริง แผนที่ยังไม่มี Baseline ใช้แผนปัจจุบันแทน
export const default_curves = (has_baseline) => ({ baseline: has_baseline, actual: true, plan: !has_baseline });
export const default_summary = (has_baseline) =>
	Object.fromEntries(
		SUMMARY_ROWS.map((row) => [row.key, row.curve === "actual" || row.curve === (has_baseline ? "baseline" : "plan")])
	);
// ค่าบนหน้าแผนงาน: settings เก็บเฉพาะที่ผู้ใช้เปลี่ยน ที่เหลือตามว่าแผนมี Baseline หรือไม่
export const view_curves = (settings, p) => ({ ...default_curves(Boolean(p.curves.baseline)), ...settings.curve_lines });
export const view_summary = (settings, p) => ({ ...default_summary(Boolean(p.curves.baseline)), ...settings.summary_rows });

export const DEFAULT_COLUMNS = ["wbs", "item_name", "boq_wbs", "start_date", "end_date", "duration", "actual_pct", "status"];

const RESOURCE_KEYS = ["name", "key", "task", "resource_type", "resource", "qty_per_day", "lead_time_days", "remarks"];
const MATERIAL_KEYS = [
	"name",
	"key",
	"task",
	"item_code",
	"item_label",
	"qty",
	"uom",
	"lead_time_days",
	"material_request",
	"request_docstatus",
	"request_status",
	"remarks",
	// ตัวคูณเป็นหน่วยสต็อก และ Item เป็นของผู้ว่าจ้างจัดหา (ข้อมูลประกอบ ไม่ส่งกลับ)
	"factor",
	"stock_uom",
	"customer_provided",
];
const pick = (keys) => (row) => Object.fromEntries(keys.map((k) => [k, row[k] ?? null]));
const pick_resource = pick(RESOURCE_KEYS);
const pick_material = pick(MATERIAL_KEYS);

// ตัวกรองงาน (metric = ค่าจาก planner.metrics)
export const TASK_FILTERS = [
	{ value: "all", label: "งานทั้งหมด" },
	{ value: "late", label: "ล่าช้า" },
	{ value: "critical", label: "วิกฤต" },
	{ value: "active", label: "กำลังทำ" },
];
export function task_matches(metric, filter) {
	switch (filter) {
		case "late":
			return ["late", "watch"].includes(metric.status?.key);
		case "critical":
			return Boolean(metric.critical);
		case "active":
			return !["done", "wait"].includes(metric.status?.key);
		default:
			return true;
	}
}

// สถานะของงาน ณ วัน Cut-off (tone = สีของแอป)
export function task_status(plan, actual) {
	if (actual >= 99.995) return { key: "done", tone: "green", label: "เสร็จแล้ว" };
	if (plan <= 0.005 && actual <= 0.005) return { key: "wait", tone: "gray", label: "ยังไม่เริ่ม" };
	const diff = actual - plan;
	if (diff > 0.005) return { key: "ahead", tone: "blue", label: "เร็วกว่าแผน" };
	if (diff >= -0.005) return { key: "ontrack", tone: "teal", label: "ตามแผน" };
	if (diff >= -LATE_LIMIT) return { key: "watch", tone: "amber", label: "เฝ้าระวัง" };
	return { key: "late", tone: "rose", label: "ล่าช้า" };
}

export function create_planner({ readonly = false, loader = null } = {}) {
	const name = ref("");
	const data = ref(null);
	const tasks = ref([]);
	const entries = ref([]);
	const resources = ref([]);
	const materials = ref([]);
	let new_row_id = 0;
	const loading = ref(false);
	const saving = ref(false);
	const save_error = ref(false);
	const remote_changed = ref(false);
	const saved_state = ref(null);
	const history = reactive({ past: [], future: [] });
	const auto_save = ref(true);
	const cutoff = ref(from_day(today()));
	const viewed_baseline = ref(null);

	const holidays = computed(() => new Set((data.value?.holidays || []).map(to_day)));
	const counting = computed(() => (data.value?.use_working_days ? holidays.value : new Set()));
	const can_write = computed(() => !readonly && Boolean(data.value?.can_write));
	const by_name = computed(() => new Map(tasks.value.map((t) => [t.name, t])));
	const cutoff_day = computed(() => to_day(cutoff.value) ?? today());
	const baselines = computed(() => data.value?.baselines || []);
	const has_baseline = computed(() => tasks.value.some((t) => t.baseline_start_date));
	// แก้แผนทรัพยากรได้เมื่อแก้แผนงานได้และมีสิทธิ์แก้แผนนั้น (ยังไม่มีแผน = สิทธิ์สร้าง)
	const can_edit_resources = computed(() => can_write.value && Boolean(data.value?.resource_plan?.can_write));
	const can_edit_materials = computed(() => can_write.value && Boolean(data.value?.material_plan?.can_write));
	// ยอดวัสดุที่ขอ/สั่ง/รับแล้วของแต่ละแถว เปลี่ยนตามวันเริ่มงาน
	const material_coverage = computed(() =>
		allocate_materials(tasks.value, materials.value, data.value?.material_plan?.buffer_days, data.value?.material_plan?.supply)
	);

	// ทรัพยากรที่กำหนดแล้วของแต่ละงาน (เครื่องหมายท้ายชื่องาน + จำนวนบนแท็บของแผงงาน)
	const plan_marks = computed(() => {
		const marks = new Map();
		const mark_of = (task) => {
			if (!marks.has(task)) marks.set(task, { resources: [], materials: [] });
			return marks.get(task);
		};
		for (const row of resources.value) mark_of(row.task).resources.push(row.resource);
		for (const row of materials.value) mark_of(row.task).materials.push(row.item_label || row.item_code);
		return marks;
	});

	// ---------- % แผน / % จริง / Float ----------
	const floats = computed(() => total_float(tasks.value, counting.value) || new Map());

	const metrics = computed(() => {
		const day = cutoff_day.value;
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
			const plan = plan_percent(task.start_date, task.end_date, day, counting.value, task.plan_distribution);
			const actual = Math.min(Math.max(sum.percent, 0), 100);
			const float = floats.value.get(task.name);
			map.set(task.name, {
				plan_pct: plan,
				actual_pct: actual,
				actual_qty: sum.qty,
				total_float: float ?? null,
				critical: float !== undefined && float <= 0,
				predecessors: format_predecessors(task.predecessors, by_name.value),
				status: task_status(plan, actual),
			});
		}
		// กลุ่ม: ถ่วงน้ำหนักจากงานย่อย (กลุ่มงานเพิ่มน้ำหนัก 0 ถ่วงด้วยมูลค่า ตรงกับ App.vue)
		tasks.value.forEach((task, i) => {
			if (!task.is_group) return;
			const children = [];
			for (const child of tasks.value.slice(i + 1)) {
				if (child.indent <= task.indent) break;
				if (!child.is_group) children.push(child);
			}
			const key = children.some((c) => c.weight) ? "weight" : "amount";
			let weight = 0;
			let plan = 0;
			let actual = 0;
			const child_floats = [];
			for (const child of children) {
				const m = map.get(child.name);
				weight += child[key] || 0;
				plan += (child[key] || 0) * m.plan_pct;
				actual += (child[key] || 0) * m.actual_pct;
				if (m.total_float !== null) child_floats.push(m.total_float);
			}
			const plan_pct = weight ? plan / weight : 0;
			const actual_pct = weight ? actual / weight : 0;
			map.set(task.name, {
				plan_pct,
				actual_pct,
				actual_qty: null,
				total_float: child_floats.length ? Math.min(...child_floats) : null,
				critical: false,
				predecessors: "",
				status: task_status(plan_pct, actual_pct),
			});
		});
		return map;
	});

	const curves = computed(() => ({
		baseline: has_baseline.value
			? curve_of(
					tasks.value,
					counting.value,
					"baseline_start_date",
					"baseline_end_date",
					"baseline_distribution",
					tasks.value.some((t) => t.baseline_weight) ? "baseline_weight" : "weight"
			  )
			: null,
		plan: curve_of(tasks.value, counting.value),
		actual: actual_curve(
			tasks.value,
			entries.value,
			today(),
			data.value?.total_amount,
			data.value?.variation_steps
		),
	}));

	// ตัวเลขของแถบสถานะล่าง ณ วัน Cut-off
	const summary = computed(() => {
		const leaves = tasks.value.filter((t) => !t.is_group);
		const dated = leaves.filter((t) => t.end_date);
		const finish = dated.length ? Math.max(...dated.map((t) => to_day(t.end_date))) : null;
		const plan = value_at(curves.value.plan, cutoff_day.value);
		const actual = curves.value.actual ? value_at(curves.value.actual, cutoff_day.value) : 0;
		const late = leaves.filter((t) => ["late", "watch"].includes(metrics.value.get(t.name)?.status.key)).length;
		return {
			tasks: leaves.length,
			critical: leaves.filter((t) => metrics.value.get(t.name)?.critical).length,
			finish: finish === null ? null : from_day(finish),
			plan,
			actual,
			baseline: curves.value.baseline ? value_at(curves.value.baseline, cutoff_day.value) : null,
			late,
			amount: data.value?.revised_amount || data.value?.total_amount || 0,
		};
	});

	// ---------- Baseline ที่เปิดดู (ไม่บันทึก) ----------
	function show_baseline(baseline_name) {
		const baseline = baselines.value.find((b) => b.name === baseline_name);
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

	// ---------- snapshot / Undo / Redo ----------
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
			resources: resources.value.map(pick_resource),
			materials: materials.value.map(pick_material),
		});
	}
	const current_state = computed(snapshot);
	const dirty = computed(() => saved_state.value !== null && current_state.value !== saved_state.value);

	function restore(state) {
		const { tasks: rows, entries: manual, resources: resource_rows, materials: material_rows } = JSON.parse(state);
		resources.value = resource_rows;
		materials.value = material_rows;
		for (const [task_name, start_date, end_date, duration, plan_distribution, predecessors] of rows) {
			const task = by_name.value.get(task_name);
			if (task) Object.assign(task, { start_date, end_date, duration, plan_distribution, predecessors });
		}
		roll_up(tasks.value, counting.value);
		entries.value = [
			...entries.value.filter((e) => e.source !== "Manual"),
			...manual.map((e) => ({ ...e, source: "Manual" })),
		];
	}

	// ทำการแก้ไข 1 ครั้งแล้วเก็บสถานะก่อนแก้ไว้ Undo (ค่าไม่เปลี่ยน = ไม่เก็บ)
	function record(change) {
		if (!can_write.value) return;
		const before = current_state.value;
		change();
		if (snapshot() === before) return;
		history.past.push(before);
		if (history.past.length > HISTORY_LIMIT) history.past.shift();
		history.future = [];
	}
	function undo() {
		if (!history.past.length) return;
		history.future.push(current_state.value);
		restore(history.past.pop());
	}
	function redo() {
		if (!history.future.length) return;
		history.past.push(current_state.value);
		restore(history.future.pop());
	}

	// ---------- แก้วันที่ ----------
	const wbs_list = (rows, limit = 6) =>
		rows.slice(0, limit).map((t) => t.wbs).join(", ") + (rows.length > limit ? " ..." : "");

	function reschedule(edited) {
		const hol = counting.value;
		const moved = apply_dependencies(tasks.value, hol) || [];
		const cleared = [...new Set([...edited, ...moved])].filter((t) => {
			const distribution = parse_distribution(t.plan_distribution);
			const s = to_day(t.start_date);
			if (!distribution || (s !== null && distribution_fits(s, to_day(t.end_date), distribution))) return false;
			t.plan_distribution = null;
			return true;
		});
		if (cleared.length) toast(`งาน ${wbs_list(cleared)}: จำนวนช่วงเปลี่ยน % แผนที่กำหนดเองถูกล้าง`, "warning");
		const followers = moved.filter((t) => !edited.includes(t));
		if (edited.length === 1 && moved.includes(edited[0]))
			toast(`งาน ${edited[0].wbs} เลื่อนตามงานก่อนหน้า`, "info");
		if (followers.length) toast(`เลื่อนงานที่ตามมา ${followers.length} งาน: ${wbs_list(followers)}`, "info");
		roll_up(tasks.value, hol);
	}

	// ตั้งวันที่ของงาน ถ้ามีงานก่อนหน้าปรับ lag ให้อยู่ตรงนั้น (hold_start) แล้วเลื่อนงานที่ตามมา
	function set_dates(task, start, end) {
		const hol = counting.value;
		task.start_date = start === null ? null : from_day(start);
		task.end_date = end === null ? null : from_day(end);
		task.duration = start === null ? 0 : count_days(start, end, hol);
		if (hold_start(task, by_name.value, hol))
			toast(`งาน ${task.wbs}: งานก่อนหน้าเป็น ${format_predecessors(task.predecessors, by_name.value)}`, "info");
		reschedule([task]);
	}

	function update_task(task, field, value) {
		if (task.is_group) return;
		record(() => {
			if (field === "actual_pct") return update_actual(task, Number(value) || 0);
			if (field === "actual_qty") return update_actual(task, ((Number(value) || 0) / task.quantity) * 100);
			if (field === "predecessors") return set_predecessors(task, value);
			const hol = counting.value;
			let start = to_day(task.start_date);
			let end = to_day(task.end_date);
			if (field === "start_date") {
				start = to_day(value);
				end = start === null ? null : end_of(start, task.duration || 1, hol);
			} else if (field === "end_date") {
				end = to_day(value);
				if (end !== null && start === null) start = end;
				if (end !== null && end < start) return toast("วันจบต้องไม่ก่อนวันเริ่ม", "error");
			} else if (field === "duration") {
				if (start === null) return;
				end = end_of(start, Math.max(Math.round(Number(value)) || 1, 1), hol);
			}
			set_dates(task, start, end);
		});
	}

	// ลากแถบ: เลื่อนทั้งแถบ (move) หรือยืด/หดด้านใดด้านหนึ่ง คืนค่าวันใหม่โดยไม่แก้ (ใช้แสดงระหว่างลาก)
	function drag_dates(task, mode, delta) {
		let start = to_day(task.start_date);
		let end = to_day(task.end_date);
		if (start === null) return null;
		if (mode === "move") {
			start += delta;
			end += delta;
		} else if (mode === "start") start = Math.min(start + delta, end);
		else end = Math.max(end + delta, start);
		return { start, end };
	}
	function apply_drag(task, mode, delta) {
		const next = drag_dates(task, mode, delta);
		if (!next || !delta) return;
		record(() => {
			// เลื่อนทั้งแถบในโหมดนับวันทำงาน: คงจำนวนวันทำงานเดิม
			const end = mode === "move" ? end_of(next.start, task.duration || 1, counting.value) : next.end;
			set_dates(task, next.start, end);
		});
	}

	// ---------- งานก่อนหน้า ----------
	// ข้อความ WBS คั่นด้วยจุลภาค เช่น "1.2, 1.3SS+2, 2.1FF-1" (ไม่ระบุชนิด = FS, lag เป็นวัน)
	const LINK_PATTERN = /^(.+?)\s*(FS|SS|FF|SF)?\s*(?:([+-])\s*(\d+))?$/i;
	function parse_link_text(task, text) {
		const by_wbs = new Map(tasks.value.map((t) => [String(t.wbs || "").trim(), t]));
		const links = [];
		for (const token of String(text || "").split(/[,;]/).map((s) => s.trim()).filter(Boolean)) {
			const match = token.match(LINK_PATTERN);
			const predecessor = match && by_wbs.get(match[1].trim());
			if (!predecessor) return { error: `ไม่พบงาน WBS ${match ? match[1] : token}` };
			if (predecessor.is_group) return { error: `${predecessor.wbs} เป็นหัวข้อกลุ่ม ให้ผูกกับงานย่อยแทน` };
			if (predecessor === task) return { error: "งานผูกกับตัวเองไม่ได้" };
			const lag = match[4] ? Number(match[4]) * (match[3] === "-" ? -1 : 1) : 0;
			links.push({ task: predecessor.name, type: (match[2] || "FS").toUpperCase(), lag });
		}
		return { links };
	}
	function set_links(task, links) {
		const unique = new Map(links.map((link) => [link.task, link]));
		const before = task.predecessors;
		task.predecessors = unique.size ? JSON.stringify([...unique.values()]) : null;
		if (!dependency_order(tasks.value)) {
			task.predecessors = before;
			toast("งานก่อนหน้าผูกกันเป็นวง", "error");
			return false;
		}
		reschedule([task]);
		return true;
	}
	function set_predecessors(task, text) {
		const { links, error } = parse_link_text(task, text);
		if (error) return toast(error, "error");
		set_links(task, links);
	}
	function update_links(task, links) {
		record(() => set_links(task, links));
	}
	// ---------- คน/เครื่องจักร และวัสดุของงาน ----------
	function add_resource(task, values) {
		const duplicate = resources.value.some(
			(row) => row.task === task.name && row.resource_type === values.resource_type && row.resource === values.resource
		);
		if (duplicate) {
			toast(`${values.resource} มีในงานนี้แล้ว`, "error");
			return false;
		}
		record(() => resources.value.push(pick_resource({ ...values, task: task.name, key: `new-${++new_row_id}` })));
		return true;
	}
	function add_material(task, values) {
		record(() => materials.value.push(pick_material({ ...values, task: task.name, key: `new-${++new_row_id}` })));
	}
	function update_plan_row(row, field, value) {
		record(() => (row[field] = field === "lead_time_days" ? Math.trunc(value) : value));
	}
	function remove_resource(row) {
		record(() => resources.value.splice(resources.value.indexOf(row), 1));
	}
	function remove_material(row) {
		record(() => materials.value.splice(materials.value.indexOf(row), 1));
	}

	// % แผนรายช่วงของงาน: JSON { unit, weights } หรือ null = คิดตามจำนวนวัน
	function update_distribution(task, distribution) {
		record(() => (task.plan_distribution = distribution));
	}

	// ---------- % จริง ณ วัน Cut-off ----------
	// เก็บเป็นรายการ Manual ของวันนั้น = ยอดสะสมที่ต้องการ - ยอดของวันอื่นก่อนหน้า
	function update_actual(task, cumulative) {
		const day = cutoff_day.value;
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
		if (cumulative < 0 || cumulative > 100 + 1e-6) return toast("% จริงต้องอยู่ระหว่าง 0-100", "error");
		if (cumulative + after > 100 + 1e-6)
			return toast("รวมกับความคืบหน้าหลังวัน Cut-off แล้วจะเกิน 100%", "error");
		const percent = cumulative - before;
		const qty = task.quantity > 0 ? (percent * task.quantity) / 100 : 0;
		if (Math.abs(percent) < 1e-9) {
			if (manual) entries.value.splice(entries.value.indexOf(manual), 1);
		} else if (manual) Object.assign(manual, { percent, qty });
		else entries.value.push({ task: task.name, date, percent, qty, source: "Manual" });
	}

	// ---------- โหลด / บันทึก ----------
	function set_data(message, { keep_history = false } = {}) {
		data.value = message;
		tasks.value = message.tasks.map((t) => ({
			...t,
			predecessors: t.predecessors ? JSON.stringify(parse_predecessors(t.predecessors)) : null,
		}));
		entries.value = message.progress_entries.map((e) => ({ ...e }));
		resources.value = (message.resource_plan?.items || []).map(pick_resource);
		materials.value = (message.material_plan?.items || []).map(pick_material);
		show_baseline(
			message.baselines.some((b) => b.name === viewed_baseline.value) ? viewed_baseline.value : message.active_baseline
		);
		saved_state.value = snapshot();
		save_error.value = false;
		remote_changed.value = false;
		if (!keep_history) {
			history.past = [];
			history.future = [];
		}
	}

	async function load(cm = name.value) {
		name.value = cm;
		loading.value = true;
		try {
			// loader: แหล่งข้อมูลอื่น (หมวดทรัพยากร) คืน null = ยังไม่มีแผนงาน
			const message = await (loader ? loader(cm) : call(`${API}.get_schedule_data`, { name: cm }));
			if (message) set_data(message);
		} finally {
			loading.value = false;
		}
	}

	// ค่าที่ส่งไป save_tasks: % จริงที่เปลี่ยนจากที่บันทึก 1 รายการต่องานต่อวัน (ค่า 0 = ลบ)
	function progress_changes(saved) {
		const key = (e) => `${e.task}|${e.date}`;
		const before = new Map(JSON.parse(saved).entries.map((e) => [key(e), e]));
		const now = new Map(JSON.parse(current_state.value).entries.map((e) => [key(e), e]));
		const changes = [];
		for (const [k, e] of now) {
			const old = before.get(k);
			if (!old || old.percent !== e.percent || old.qty !== e.qty) changes.push(e);
		}
		for (const [k, e] of before) if (!now.has(k)) changes.push({ task: e.task, date: e.date, percent: 0, qty: 0 });
		return changes;
	}

	// รายการทั้งชุดของแผนที่เปลี่ยน (ตรงกับ plan_changes ใน App.vue)
	function plan_changes(saved) {
		const before = JSON.parse(saved);
		const now = JSON.parse(current_state.value);
		const wbs = (task) => by_name.value.get(task)?.wbs;
		const changes = {};
		if (JSON.stringify(before.resources) !== JSON.stringify(now.resources)) {
			changes.resources = {
				modified: data.value.resource_plan?.modified,
				items: now.resources.map(({ key, ...row }) => ({ ...row, wbs: wbs(row.task) })),
			};
		}
		if (JSON.stringify(before.materials) !== JSON.stringify(now.materials)) {
			changes.materials = {
				modified: data.value.material_plan?.modified,
				items: now.materials.map(
					({ key, item_label, request_docstatus, request_status, factor, stock_uom, customer_provided, ...row }) => ({
						...row,
						wbs: wbs(row.task),
					})
				),
			};
		}
		return changes;
	}

	async function save({ auto = false } = {}) {
		if (!dirty.value || saving.value || !can_write.value) return;
		const state = current_state.value;
		saving.value = true;
		try {
			const message = await post(`${API}.save_tasks`, {
				name: name.value,
				modified: data.value.modified,
				tasks: tasks.value
					.filter((t) => !t.is_group)
					.map(({ name: row, start_date, end_date, plan_distribution, predecessors }) => ({
						name: row,
						start_date,
						end_date,
						plan_distribution,
						predecessors,
					})),
				progress: progress_changes(saved_state.value),
				...plan_changes(saved_state.value),
			});
			if (current_state.value === state) set_data(message, { keep_history: true });
			else {
				// แก้ต่อระหว่างรอบันทึก: เก็บสิ่งที่แก้ใหม่ไว้บันทึกรอบถัดไป
				Object.assign(data.value, { modified: message.modified, version: message.version });
				for (const plan of ["resource_plan", "material_plan"]) {
					if (data.value[plan] && message[plan]) {
						Object.assign(data.value[plan], { modified: message[plan].modified, exists: message[plan].exists });
					}
				}
				saved_state.value = state;
			}
			save_error.value = false;
			if (!auto) toast("บันทึกแล้ว", "success");
		} catch (error) {
			save_error.value = true;
			show_error(error);
		} finally {
			saving.value = false;
		}
		if (dirty.value && !save_error.value) queue_save();
	}

	let save_timer = null;
	function queue_save() {
		clearTimeout(save_timer);
		save_timer = setTimeout(() => {
			if (auto_save.value && dirty.value && !save_error.value) save({ auto: true });
		}, AUTO_SAVE_DELAY);
	}
	watch(current_state, () => dirty.value && queue_save());
	watch(auto_save, (on) => on && queue_save());

	// เพิ่ม/ลบ/เลื่อนระดับงาน: บันทึกงานค้างก่อนแล้วทำที่ server ทันที (เลข WBS และลำดับแถวเปลี่ยน จึง Undo ไม่ได้)
	function change_structure(action, names = [], item_name = null) {
		return call_structure("change_structure", { action, tasks: names, item_name });
	}

	// ยกเลิกการยืนยันแผน: ลบ Baseline ทุกชุด แล้วกลับไปแก้โครงสร้างงานได้
	function unconfirm_plan() {
		return call_structure("unconfirm_plan");
	}

	async function call_structure(method, args = {}) {
		if (!(await flush())) {
			toast("บันทึกงานค้างไม่สำเร็จ ลองบันทึกก่อน", "error");
			return false;
		}
		saving.value = true;
		try {
			const message = await post(`${STRUCTURE_API}.${method}`, {
				name: name.value,
				modified: data.value.modified,
				...args,
			});
			set_data(message);
			return true;
		} catch (error) {
			show_error(error);
			return false;
		} finally {
			saving.value = false;
		}
	}

	// ก่อนออกจากหน้า: บันทึกงานค้าง คืน true ถ้าไม่มีอะไรค้าง
	async function flush() {
		clearTimeout(save_timer);
		while (saving.value) await new Promise((r) => setTimeout(r, 100));
		if (dirty.value && !save_error.value && !remote_changed.value) await save({ auto: true });
		while (saving.value) await new Promise((r) => setTimeout(r, 100));
		return !dirty.value;
	}

	// แผนถูกแก้จากที่อื่น (Daily Report, VO, ระบบเต็ม): ไม่มีงานค้าง = โหลดใหม่ มีงานค้าง = แจ้ง
	async function check_remote() {
		if (document.hidden || saving.value || !data.value) return;
		let version;
		try {
			version = await call(`${API}.get_schedule_version`, { name: name.value });
		} catch {
			return;
		}
		if (version === data.value.version || saving.value) return;
		if (dirty.value) {
			remote_changed.value = true;
			return;
		}
		await load();
		toast("โหลดข้อมูลล่าสุดแล้ว", "info");
	}

	// สถานะการบันทึกของแถบบน
	const save_status = computed(() => {
		if (saving.value) return { tone: "blue", label: "กำลังบันทึก..." };
		if (save_error.value) return { tone: "rose", label: "บันทึกไม่สำเร็จ" };
		if (remote_changed.value) return { tone: "rose", label: "มีการแก้จากที่อื่น" };
		if (dirty.value) return { tone: "amber", label: auto_save.value ? "รอบันทึก..." : "ยังไม่บันทึก" };
		return { tone: "green", label: "บันทึกแล้ว" };
	});

	return reactive({
		change_structure,
		unconfirm_plan,
		name,
		data,
		tasks,
		entries,
		resources,
		materials,
		can_edit_resources,
		can_edit_materials,
		material_coverage,
		plan_marks,
		loading,
		saving,
		save_error,
		remote_changed,
		history,
		auto_save,
		cutoff,
		cutoff_day,
		viewed_baseline,
		baselines,
		holidays,
		counting,
		can_write,
		by_name,
		metrics,
		curves,
		summary,
		dirty,
		save_status,
		show_baseline,
		record,
		undo,
		redo,
		update_task,
		update_links,
		update_distribution,
		add_resource,
		add_material,
		update_plan_row,
		remove_resource,
		remove_material,
		parse_link_text,
		drag_dates,
		apply_drag,
		load,
		save,
		flush,
		check_remote,
	});
}
