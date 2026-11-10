<!-- tab "พิมพ์" ของหน้าแผนงาน: ซ้าย = Preview, ขวา = Properties
     Preview คือ iframe เอกสารเดียวกับที่สั่งพิมพ์ (build_print ใน construction_management/print.js) งานพิมพ์จึงตรงกับที่เห็น
     ย่อ/ขยายเพื่อดูทำที่ตัว iframe จากภายนอก ไม่กระทบเอกสาร ขอบกระดาษและเงาในเอกสารเป็น @media screen ไม่ออกตอนพิมพ์
     tab คอลัมน์: เลือก/เรียง/กำหนดความกว้าง (ว่าง = พอดีข้อความ) ไม่กระทบตาราง
     การย่อ-หุบ WBS เป็นของงานพิมพ์ แยกจากตาราง (ครั้งแรกตั้งต้นจากตาราง) ค่าทั้งหมดจำในเครื่องแยกตามแผนงาน -->
<template>
	<div class="pl-print">
		<div ref="stage" class="pl-print-stage">
			<div v-if="result.error" class="pl-print-error">
				<Empty icon="alert" title="พิมพ์แบบนี้ไม่ได้" :text="result.error" />
			</div>
			<div v-show="!result.error" class="pl-print-sheet" :style="sheet_style">
				<iframe ref="frame" title="ตัวอย่างงานพิมพ์" class="pl-print-frame" :style="frame_style" tabindex="-1" scrolling="no"></iframe>
			</div>
			<div class="pl-print-zoom">
				<button type="button" class="ss-icon-btn" aria-label="ย่อตัวอย่าง" title="ย่อตัวอย่าง" @click="step_zoom(-1)"><Icon name="minus" :size="16" /></button>
				<span>{{ Math.round(zoom * 100) }}%</span>
				<button type="button" class="ss-icon-btn" aria-label="ขยายตัวอย่าง" title="ขยายตัวอย่าง" @click="step_zoom(1)"><Icon name="plus" :size="16" /></button>
				<button type="button" class="ss-btn ss-btn--soft" :disabled="!manual_zoom" @click="manual_zoom = null">พอดีจอ</button>
			</div>
		</div>

		<aside class="pl-print-props" aria-label="ตั้งค่าการพิมพ์">
			<StatusTabs v-model="prop_tab" :options="PROP_TABS" />
			<div v-if="prop_tab === 'page'" class="pl-print-fields">
				<div class="ss-field">
					<span class="ss-field-label">แบบเอกสาร</span>
					<Segmented v-model="options.template" :options="TEMPLATES" />
				</div>
				<div class="ss-field">
					<span class="ss-field-label">ขนาดกระดาษ</span>
					<SelectBox v-model="options.paper" label="ขนาดกระดาษ" :options="PAPERS" />
				</div>
				<div class="ss-field">
					<span class="ss-field-label">แนวกระดาษ</span>
					<Segmented v-model="options.orientation" :options="ORIENTATIONS" />
				</div>
				<div class="ss-field">
					<span class="ss-field-label">การแบ่งหน้า</span>
					<Segmented v-model="options.mode" :options="MODES" />
				</div>
				<label class="ss-field">
					<span class="ss-field-label pl-print-label">Scale<b>{{ options.content_scale }}%</b></span>
					<input v-model.number="options.content_scale" class="pl-print-range" type="range" min="30" max="200" step="5" />
				</label>
				<div class="ss-field">
					<span class="ss-field-label">ระยะขอบ</span>
					<SelectBox v-model="options.margin" label="ระยะขอบ" :options="MARGINS" />
				</div>
				<button type="button" class="ss-btn ss-btn--ghost" :disabled="page_is_default" @click="reset_page">คืนค่าเริ่มต้น</button>
				<p class="pl-print-note">ในหน้าต่างพิมพ์ของเบราว์เซอร์ให้คง Scale เป็น 100% (ค่าเริ่มต้น)</p>
			</div>
			<div v-else-if="prop_tab === 'curve'" class="pl-print-fields">
				<div class="ss-field">
					<span class="ss-field-label">เส้น S-Curve</span>
					<label v-for="item in curve_items" :key="item.key" class="ss-toggle" :class="{ 'is-on': options.curves[item.key] }">
						<input v-model="options.curves[item.key]" type="checkbox" />
						<span class="ss-toggle-track"><span></span></span>
						<span>{{ item.label }}</span>
					</label>
				</div>
				<div class="ss-field">
					<span class="ss-field-label">ตารางสรุป</span>
					<label v-for="row in summary_items" :key="row.key" class="ss-toggle" :class="{ 'is-on': options.summary[row.key] }">
						<input v-model="options.summary[row.key]" type="checkbox" />
						<span class="ss-toggle-track"><span></span></span>
						<span>{{ row.label }}</span>
					</label>
				</div>
				<button type="button" class="ss-btn ss-btn--ghost" :disabled="curve_is_default" @click="reset_curve">คืนค่าเริ่มต้น</button>
				<p class="pl-print-note">แผนสัญญา = แผนที่ยืนยันตามสัญญา (เปลี่ยนเมื่อบันทึกชุดใหม่) · แผนปัจจุบัน = แผนที่ปรับได้ตลอด · จริง = ผลงานจริง<template v-if="!has_baseline"> แผนนี้ยังไม่มีแผนสัญญา</template></p>
			</div>
			<div v-else-if="prop_tab === 'columns'" ref="columns_box" class="pl-print-fields">
				<ul ref="column_list" class="pl-print-cols">
					<li v-for="(col, i) in options.columns" :key="col.key" :data-key="col.key" :class="{ 'is-dragging': drag_key === col.key }">
						<span class="ss-grip" title="ลากเพื่อย้ายลำดับ" aria-label="ลากเพื่อย้ายลำดับ" @pointerdown="start_drag($event, col.key)"><Icon name="grip" :size="14" /></span>
						<span class="pl-print-col-no">{{ i + 1 }}</span>
						<label class="ss-toggle" :class="{ 'is-on': col.visible }">
							<input v-model="col.visible" type="checkbox" />
							<span class="ss-toggle-track"><span></span></span>
							<span>{{ COLUMNS[col.key].label }}</span>
						</label>
						<input
							v-model.number="col.width"
							class="ss-input pl-print-col-width"
							type="number"
							inputmode="numeric"
							:min="MIN_COLUMN_WIDTH"
							:disabled="!col.visible"
							:placeholder="col.visible && fit_widths[col.key] ? String(fit_widths[col.key]) : 'พอดี'"
							:aria-label="`ความกว้าง ${COLUMNS[col.key].label}`"
						/>
					</li>
				</ul>
				<button type="button" class="ss-btn ss-btn--ghost" :disabled="columns_is_default" @click="reset_columns">คืนค่าเริ่มต้น</button>
				<p class="pl-print-note">ลากที่จับเพื่อเรียงลำดับ ช่องความกว้างเว้นว่าง = พอดีกับข้อความ</p>
			</div>
			<div v-else class="pl-print-fields">
				<div class="ss-field">
					<span class="ss-field-label">ช่องเวลา</span>
					<SelectBox v-model="options.scale" label="ช่องเวลา" :options="PRINT_SCALES" />
				</div>
				<label v-if="options.mode === 'pages'" class="ss-field">
					<span class="ss-field-label pl-print-label">ความกว้างช่องเวลา<b>{{ options.period_scale }}%</b></span>
					<input v-model.number="options.period_scale" class="pl-print-range" type="range" min="30" max="300" step="10" />
				</label>
				<div class="ss-field">
					<span class="ss-field-label">ท้ายแถบ Gantt</span>
					<label v-for="item in END_ITEMS" :key="item.key" class="ss-toggle" :class="{ 'is-on': options[item.key] }">
						<input v-model="options[item.key]" type="checkbox" />
						<span class="ss-toggle-track"><span></span></span>
						<span>{{ item.label }}</span>
					</label>
				</div>
				<div class="ss-field">
					<span class="ss-field-label">ระดับ WBS</span>
					<SelectBox :model-value="level_value" label="ระดับ WBS" :options="level_options" @update:model-value="set_level" />
				</div>
				<button type="button" class="ss-btn ss-btn--soft" :disabled="!done_groups.length" @click="collapse_done">หุบงานที่เสร็จแล้ว</button>
				<div v-if="level_value === CUSTOM_LEVEL && tree.length" class="ss-field">
					<span class="ss-field-label">เปิด-ปิดรายกลุ่ม</span>
					<div class="pl-print-tree">
						<button
							v-for="task in tree"
							:key="task.name"
							type="button"
							class="pl-print-node"
							:style="{ paddingLeft: `${6 + task.indent * 12}px` }"
							:aria-expanded="!collapsed.has(task.name)"
							:title="`${task.wbs} ${task.item_name}`"
							@click="toggle(task)"
						>
							<Icon :name="collapsed.has(task.name) ? 'chevron-right' : 'chevron-down'" :size="14" />
							<b>{{ task.wbs }}</b>
							<span>{{ task.item_name }}</span>
						</button>
					</div>
				</div>
				<button type="button" class="ss-btn ss-btn--ghost" :disabled="gantt_is_default" @click="reset_gantt">คืนค่าเริ่มต้น</button>
				<p class="pl-print-note">คอลัมน์ เส้น S-Curve แถบแผนสัญญาตารางสรุป และตัวกรองงาน ตั้งที่แท็บแผนงานและมุมมอง S-Curve กับตารางสรุปคิดจากทั้งแผนเสมอ</p>
			</div>
			<div class="pl-print-foot">
				<span>{{ result.error ? "–" : `${rows.length} แถว · ${result.pages} หน้า · ${options.paper}` }}</span>
				<button type="button" class="ss-btn ss-btn--primary" :disabled="!!result.error || printing" @click="print">
					<Icon name="printer" :size="16" /> <span>พิมพ์</span>
				</button>
			</div>
		</aside>
	</div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";
import Empty from "../../../../shared/components/Empty.vue";
import Icon from "../../../../shared/components/Icon.vue";
import Segmented from "../../../../shared/components/Segmented.vue";
import SelectBox from "../../../../shared/components/SelectBox.vue";
import StatusTabs from "../../../../shared/components/StatusTabs.vue";
import { build_print } from "../../../../construction_management/print.js";
import { COLUMNS, CURVE_ITEMS, SUMMARY_ROWS, default_curves, default_summary } from "./planner.js";
import { MIN_COLUMN_WIDTH, PRINT_SCALES, build_print_model, fit_column_widths } from "./print_model.js";

const props = defineProps({
	p: { type: Object, required: true },
	settings: { type: Object, required: true },
	// ชื่องานที่ผ่านตัวกรองของตาราง (null = ไม่กรอง)
	kept: { type: Object, default: null },
	// การย่อ-หุบของตาราง ใช้ตั้งต้นครั้งแรกของแผนนี้เท่านั้น
	is_table_collapsed: { type: Function, default: null },
});

const PROP_TABS = [
	{ value: "page", label: "หน้ากระดาษ" },
	{ value: "gantt", label: "Gantt" },
	{ value: "columns", label: "คอลัมน์" },
	{ value: "curve", label: "S-Curve" },
];

const END_ITEMS = [
	{ key: "end_name", label: "ชื่องาน" },
	{ key: "end_status", label: "สถานะ" },
	{ key: "end_plan", label: "% แผน" },
	{ key: "end_actual", label: "% จริง" },
];
const SLIDE_MS = 180; // เท่ากับ BoqForm.vue (Design.md)
const TEMPLATES = [
	{ value: "app", label: "ตามหน้าจอ" },
	{ value: "formal", label: "ทางการ" },
	{ value: "sidebar", label: "แถบข้าง" },
];
const PAPERS = ["A4", "A3", "A2", "A1"].map((value) => ({ value, label: value }));
const ORIENTATIONS = [
	{ value: "landscape", label: "แนวนอน" },
	{ value: "portrait", label: "แนวตั้ง" },
];
const MODES = [
	{ value: "fit", label: "1 หน้า" },
	{ value: "pages", label: "ต่อเนื่อง" },
];
const MARGINS = [5, 8, 10, 15, 20].map((value) => ({ value, label: `${value} มม.` }));
const ZOOM_STEPS = [0.25, 0.33, 0.5, 0.67, 0.75, 1, 1.25, 1.5, 2];
const MM = 96 / 25.4;
const GUTTER = 16; // ช่องว่างรอบกระดาษใน @media screen ของเอกสาร (print.js)
const PAGE_DEFAULTS = { template: "app", paper: "A3", orientation: "landscape", mode: "fit", content_scale: 100, margin: 8 };

const CUSTOM_LEVEL = "custom";
const ALL_LEVELS = "all";
const groups = computed(() => props.p.tasks.filter((t) => t.is_group));

// ค่าที่จำแยกตามแผนงาน แผนที่ยังไม่เคยพิมพ์ใช้กระดาษ/รูปแบบที่ใช้ล่าสุด
const storage_key = `consbiz.planner.print.${props.p.name}`;
function read_saved() {
	try {
		return JSON.parse(localStorage.getItem(storage_key) || "null");
	} catch {
		return null;
	}
}
const saved = read_saved();
const prop_tab = ref("page");
const end_defaults = () => ({
	end_name: props.settings.show.labels,
	end_status: false,
	end_plan: props.settings.show.progress,
	end_actual: props.settings.show.progress,
});
// ค่าเริ่มต้นตามคอลัมน์ที่ตารางแสดงอยู่ ตามด้วยคอลัมน์ที่เหลือ (ซ่อน) width ว่าง = พอดีข้อความ
function default_columns() {
	const shown = props.settings.columns.filter((key) => COLUMNS[key]);
	const rest = Object.keys(COLUMNS).filter((key) => !shown.includes(key));
	return [...shown, ...rest].map((key) => ({ key, visible: shown.includes(key), width: null }));
}
// คงลำดับที่จำไว้ ตัดคอลัมน์ที่เลิกใช้ เพิ่มคอลัมน์ใหม่ต่อท้ายแบบซ่อน
function merged_columns(remembered) {
	if (!remembered?.length) return default_columns();
	const known = remembered.filter((column) => COLUMNS[column.key]);
	const missing = Object.keys(COLUMNS).filter((key) => !known.some((column) => column.key === key));
	return [...known, ...missing.map((key) => ({ key, visible: false, width: null }))];
}
// เส้นและแถวหลัก = Baseline กับจริง ยังไม่มี Baseline ใช้แผนปัจจุบันแทน
const has_baseline = computed(() => Boolean(props.p.curves.baseline));
const curve_defaults = () => default_curves(has_baseline.value);
const summary_defaults = () => default_summary(has_baseline.value);
const curve_items = computed(() => CURVE_ITEMS.filter((item) => item.key !== "baseline" || has_baseline.value));
const summary_items = computed(() => SUMMARY_ROWS.filter((row) => row.curve !== "baseline" || has_baseline.value));
const remembered = { ...props.settings.print, ...saved?.options };
const options = reactive({
	...PAGE_DEFAULTS,
	...end_defaults(),
	period_scale: 100,
	scale: props.settings.scale,
	...remembered,
	columns: merged_columns(remembered.columns),
	curves: { ...curve_defaults(), ...remembered.curves },
	summary: { ...summary_defaults(), ...remembered.summary },
});
if (!TEMPLATES.some((t) => t.value === options.template)) options.template = PAGE_DEFAULTS.template;
const same = (a, b) => Object.keys(b).every((key) => a[key] === b[key]);
const curve_is_default = computed(() => same(options.curves, curve_defaults()) && same(options.summary, summary_defaults()));
function reset_curve() {
	options.curves = curve_defaults();
	options.summary = summary_defaults();
}
const collapsed = reactive(
	new Set(saved?.collapsed ?? groups.value.filter((t) => props.is_table_collapsed?.(t)).map((t) => t.name))
);
// กำหนดเอง = แสดงรายกลุ่ม แผนเดิมที่ยังไม่เคยจำค่านี้: ถือว่ากำหนดเองเมื่อที่หุบไว้ไม่ตรงระดับใด
const custom_wbs = ref(saved?.custom_wbs ?? false);
watch(
	[options, () => [...collapsed], custom_wbs],
	() => {
		props.settings.print = { ...options };
		try {
			localStorage.setItem(storage_key, JSON.stringify({ options, collapsed: [...collapsed], custom_wbs: custom_wbs.value }));
		} catch {
			// โหมดส่วนตัว: ไม่จำ
		}
	},
	{ deep: true }
);
const page_is_default = computed(() =>
	Object.entries(PAGE_DEFAULTS).every(([key, value]) => options[key] === value)
);
function reset_page() {
	Object.assign(options, PAGE_DEFAULTS);
}
const gantt_is_default = computed(
	() =>
		!collapsed.size &&
		!custom_wbs.value &&
		options.period_scale === 100 &&
		options.scale === props.settings.scale &&
		Object.entries(end_defaults()).every(([key, value]) => options[key] === value)
);
function reset_gantt() {
	Object.assign(options, end_defaults());
	options.period_scale = 100;
	options.scale = props.settings.scale;
	custom_wbs.value = false;
	collapsed.clear();
}

// ---------- ย่อ-หุบ WBS ---------- ลำดับเดียวกับ rows ใน PlanSheet.vue
function walk(tasks) {
	const result = [];
	let hide_below = null;
	for (const task of tasks) {
		if (props.kept && !props.kept.has(task.name)) continue;
		if (hide_below !== null && task.indent > hide_below) continue;
		hide_below = task.is_group && collapsed.has(task.name) ? task.indent : null;
		result.push(task);
	}
	return result;
}
const rows = computed(() => walk(props.p.tasks));
const tree = computed(() => rows.value.filter((t) => t.is_group));

function toggle(task) {
	if (collapsed.has(task.name)) collapsed.delete(task.name);
	else collapsed.add(task.name);
}
// ระดับ n = เห็นถึงความลึก n เหมือน set_level ของตาราง
const names_at = (level) => groups.value.filter((t) => t.indent >= level - 1).map((t) => t.name);
const depth = computed(() => Math.max(0, ...props.p.tasks.map((t) => t.indent || 0)));
const same_as = (names) => names.length === collapsed.size && names.every((name) => collapsed.has(name));
const level_value = computed(() => {
	if (custom_wbs.value) return CUSTOM_LEVEL;
	if (!collapsed.size) return ALL_LEVELS;
	for (let level = 1; level <= depth.value; level++) if (same_as(names_at(level))) return level;
	return CUSTOM_LEVEL;
});
const level_options = computed(() => [
	{ value: ALL_LEVELS, label: "ทุกระดับ" },
	...Array.from({ length: depth.value }, (_, i) => ({ value: i + 1, label: `ระดับ ${i + 1}` })),
	{ value: CUSTOM_LEVEL, label: "ตั้งค่าเอง" },
]);
function set_level(value) {
	custom_wbs.value = value === CUSTOM_LEVEL;
	if (custom_wbs.value) return;
	collapsed.clear();
	if (value !== ALL_LEVELS) names_at(value).forEach((name) => collapsed.add(name));
}
const done_groups = computed(() =>
	groups.value.filter((t) => props.p.metrics.get(t.name)?.actual_pct >= 99.995).map((t) => t.name)
);
function collapse_done() {
	custom_wbs.value = true;
	done_groups.value.forEach((name) => collapsed.add(name));
}

const visible_keys = computed(() => options.columns.filter((c) => c.visible).map((c) => c.key));
const fit_widths = computed(() => fit_column_widths(props.p, rows.value, visible_keys.value));
const columns_is_default = computed(
	() => JSON.stringify(options.columns) === JSON.stringify(default_columns())
);
function reset_columns() {
	slide_columns(() => (options.columns = default_columns()));
}

const result = computed(() =>
	build_print(build_print_model(props.p, props.settings, rows.value, options, fit_widths.value), options)
);

// ---------- ลากเรียงคอลัมน์ ---------- แถวย้ายจริงระหว่างลาก แถวอื่นเลื่อนหลบด้วย animation (กฎเดียวกับ BOQ ใน Design.md)
const column_list = ref(null);
const columns_box = ref(null);
const drag_key = ref(null);
const SCROLL_EDGE = 28;
let drag_y = 0;
let drag_frame = 0;

function slide_columns(change) {
	const list = column_list.value;
	if (!list || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return change();
	const before = new Map([...list.children].map((el) => [el.dataset.key, el.offsetTop]));
	change();
	nextTick(() => {
		for (const el of list.children) {
			const delta = before.get(el.dataset.key) - el.offsetTop;
			if (!delta) continue;
			el.animate([{ transform: `translateY(${delta}px)` }, { transform: "none" }], {
				duration: SLIDE_MS,
				easing: "cubic-bezier(0.22, 1, 0.36, 1)",
			});
		}
	});
}
function drag_to(client_y) {
	const items = [...column_list.value.children];
	const from = options.columns.findIndex((c) => c.key === drag_key.value);
	const box = items[from].getBoundingClientRect();
	if (client_y >= box.top && client_y <= box.bottom) return;
	const to = items.reduce((target, el, i) => {
		const rect = el.getBoundingClientRect();
		if (client_y > rect.top + rect.height / 2) return i;
		return target;
	}, 0);
	if (to === from) return;
	slide_columns(() => {
		const next = [...options.columns];
		next.splice(to, 0, next.splice(from, 1)[0]);
		options.columns = next;
	});
}
function on_drag_move(event) {
	drag_y = event.clientY;
	drag_to(drag_y);
}
function drag_scroll() {
	const box = columns_box.value;
	if (!drag_key.value || !box) return;
	const rect = box.getBoundingClientRect();
	const step = drag_y < rect.top + SCROLL_EDGE ? -6 : drag_y > rect.bottom - SCROLL_EDGE ? 6 : 0;
	if (step) {
		box.scrollTop += step;
		drag_to(drag_y);
	}
	drag_frame = requestAnimationFrame(drag_scroll);
}
function stop_drag() {
	drag_key.value = null;
	cancelAnimationFrame(drag_frame);
	window.removeEventListener("pointermove", on_drag_move);
	window.removeEventListener("pointerup", stop_drag);
	window.removeEventListener("pointercancel", stop_drag);
}
function start_drag(event, key) {
	if (event.button !== 0) return;
	event.preventDefault();
	drag_key.value = key;
	drag_y = event.clientY;
	// ฟังที่ window เพราะแถวถูกย้ายใน DOM ระหว่างลาก
	window.addEventListener("pointermove", on_drag_move);
	window.addEventListener("pointerup", stop_drag);
	window.addEventListener("pointercancel", stop_drag);
	drag_frame = requestAnimationFrame(drag_scroll);
}

const frame = ref(null);
const stage = ref(null);
const stage_w = ref(0);
const manual_zoom = ref(null);
const printing = ref(false);

const sheet_w = computed(() => {
	const [short, long] = result.value.size || [297, 420];
	return (options.orientation === "landscape" ? long : short) * MM + 2 * GUTTER;
});
const sheet_h = computed(() => {
	const [short, long] = result.value.size || [297, 420];
	const paper = (options.orientation === "landscape" ? short : long) * MM;
	return GUTTER + (result.value.pages || 1) * (paper + GUTTER);
});
const fit_zoom = computed(() => (stage_w.value ? Math.min(stage_w.value / sheet_w.value, 2) : 0.5));
const zoom = computed(() => manual_zoom.value ?? fit_zoom.value);
const sheet_style = computed(() => ({
	width: `${sheet_w.value * zoom.value}px`,
	height: `${sheet_h.value * zoom.value}px`,
}));
const frame_style = computed(() => ({
	width: `${sheet_w.value}px`,
	height: `${sheet_h.value}px`,
	transform: `scale(${zoom.value})`,
}));
function step_zoom(direction) {
	const current = zoom.value;
	const next =
		direction > 0
			? ZOOM_STEPS.find((z) => z > current + 0.001)
			: [...ZOOM_STEPS].reverse().find((z) => z < current - 0.001);
	if (next) manual_zoom.value = next;
}

function write(html) {
	const doc = frame.value?.contentDocument;
	if (!doc) return;
	doc.open();
	doc.write(html);
	doc.close();
}
let timer = null;
watch(
	() => result.value.html,
	(html) => {
		clearTimeout(timer);
		if (html) timer = setTimeout(() => write(html), 80);
	}
);

function print() {
	const win = frame.value?.contentWindow;
	if (!win || result.value.error) return;
	clearTimeout(timer);
	write(result.value.html);
	printing.value = true;
	// รอฟอนต์ไทยโหลดก่อนสั่งพิมพ์ ไม่งั้นอาจใช้ฟอนต์สำรอง
	win.document.fonts
		.load('10px "Noto Sans Thai"', "ก")
		.finally(() => {
			printing.value = false;
			win.focus();
			win.print();
		});
}

let observer = null;
onMounted(() => {
	if (result.value.html) write(result.value.html);
	observer = new ResizeObserver(([entry]) => (stage_w.value = entry.contentRect.width));
	observer.observe(stage.value);
});
onBeforeUnmount(() => {
	stop_drag();
	clearTimeout(timer);
	observer?.disconnect();
});
</script>
