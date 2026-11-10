<!-- ตารางงาน + Gantt ของหน้าแก้แผนในแอป (PlanEdit.vue) กล่องเลื่อนเดียว: ตารางติดซ้าย (sticky) Timeline เลื่อนแนวนอน
     แถวของตารางและแถบจึงตรงกันเสมอ หัวตาราง/หัวเวลาติดบน
     แก้ในช่อง: วันเริ่ม/จบ (ปฏิทิน), วัน, งานก่อนหน้า (WBS เช่น 1.2, 1.3SS+2), % จริง ณ วัน Cut-off
     ลากแถบ (เมาส์/ปากกา): กลางแถบ = เลื่อน, ขอบซ้าย/ขวา = ยืด-หด  แตะ/คลิกแถบหรือชื่องาน = เลือกงาน (แผงขวา)
     คลิกขวาที่แถว = เมนู (PlanMenu.vue, สร้างรายการใน PlanEdit.vue) ลากขอบหัวคอลัมน์ = ปรับความกว้าง, ลากตัวแบ่ง = แบ่งที่ตาราง/Gantt (ดับเบิลคลิก = ค่าเดิม) ตารางแคบกว่าคอลัมน์ = มีแถบเลื่อนท้ายตาราง -->
<template>
	<div
		ref="scroller"
		class="pl-scroll"
		:class="{ 'is-dragging': drag.task, 'is-compact': compact, 'is-resizing': resizing, 'no-grid': hide_grid }"
		:style="{ '--grid-w': `${grid_w}px`, '--grid-x': `${grid_x}px`, '--row-h': `${ROW_H}px` }"
	>
		<div class="pl-sheet" :style="{ width: `${grid_w + timeline_w}px` }">
			<div class="pl-head">
				<div class="pl-head-cells">
					<div
						v-for="col in columns"
						:key="col.key"
						class="pl-hcell"
						:class="[`is-${col.align || 'start'}`, `col-${col.key}`]"
						:style="{ width: `${col.w}px` }"
					>
						{{ col.label }}
						<span
							v-if="!compact"
							class="pl-col-grip"
							title="ลากเพื่อปรับความกว้าง ดับเบิลคลิก = ค่าเดิม"
							@pointerdown.stop.prevent="on_col_down($event, col)"
							@dblclick.stop="reset_col(col)"
						></span>
					</div>
				</div>
				<div class="pl-head-time" :style="{ width: `${timeline_w}px` }">
					<div class="pl-head-row">
						<span
							v-for="period in top_periods"
							:key="period.start"
							:style="{ left: `${x(period.start)}px`, width: `${x(period.end) - x(period.start)}px` }"
							><b>{{ period.label }}</b></span
						>
					</div>
					<div class="pl-head-row is-bottom">
						<span
							v-for="period in bottom_periods"
							:key="period.start"
							:class="{ 'is-today': period.today, 'is-off': period.off }"
							:style="{ left: `${x(period.start)}px`, width: `${x(period.end) - x(period.start)}px` }"
							>{{ period.label }}</span
						>
					</div>
					<span class="pl-cutoff-flag" :style="{ left: `${day_mid(p.cutoff_day)}px` }">Cut-off</span>
				</div>
			</div>

			<div class="pl-body" :style="{ height: `${Math.max(rows.length * ROW_H, 0)}px` }">
				<!-- S-Curve: ติดอยู่ในจอเมื่อเลื่อนแถวงาน เลื่อนแนวนอนพร้อมแกนเวลา -->
				<div
					v-if="curve_lines.length"
					class="pl-curve-layer"
					:style="{ width: `${timeline_w}px`, height: `${curve_h}px`, marginLeft: `${grid_w}px` }"
				>
					<svg :width="timeline_w" :height="curve_h">
						<line v-for="tick in CURVE_TICKS" :key="tick" class="pl-curve-tick" x1="0" x2="100%" :y1="curve_y(tick)" :y2="curve_y(tick)" />
						<g v-for="line in curve_lines" :key="line.key" class="pl-curve" :class="`is-${line.key}`">
							<path class="is-halo" :d="line.d" />
							<path :d="line.d" />
							<circle v-for="point in line.points" :key="point.day" :cx="point.x" :cy="point.y" r="2.5" :data-tip="point.title" />
						</g>
					</svg>
				</div>

				<svg class="pl-bg" :width="timeline_w" :height="body_h" aria-hidden="true">
					<rect
						v-for="day in off_days"
						:key="day"
						class="pl-off"
						:x="x(day)"
						y="0"
						:width="x(day + 1) - x(day)"
						:height="body_h"
					/>
					<line
						v-for="period in bottom_periods"
						:key="period.start"
						class="pl-vline"
						:x1="x(period.start)"
						:x2="x(period.start)"
						y1="0"
						:y2="body_h"
					/>
					<rect
						v-if="today_in_range"
						class="pl-today"
						:x="x(today_day)"
						y="0"
						:width="Math.max(x(today_day + 1) - x(today_day), 2)"
						:height="body_h"
					/>
					<line
						class="pl-cutoff"
						:x1="day_mid(p.cutoff_day)"
						:x2="day_mid(p.cutoff_day)"
						y1="0"
						:y2="body_h"
					/>
				</svg>

				<!-- เส้นอยู่ใต้แถวงาน แถบและป้ายท้ายแถบจึงไม่ถูกเส้นทับ -->
				<svg v-if="show.links" class="pl-links" :width="timeline_w" :height="body_h" aria-hidden="true">
					<defs>
						<marker
							v-for="arrow in ARROWS"
							:id="`pl-arrow${arrow}`"
							:key="arrow"
							viewBox="0 0 8 8"
							refX="7"
							refY="4"
							markerWidth="7"
							markerHeight="7"
							markerUnits="userSpaceOnUse"
							orient="auto"
						>
							<path d="M0 .8 7.5 4 0 7.2z" class="pl-arrow" :class="arrow && `is${arrow}`" />
						</marker>
					</defs>
					<path
						v-for="link in links"
						:key="link.key"
						class="pl-link"
						:class="{ 'is-critical': link.critical, 'is-hot': link.hot }"
						:d="link.d"
						:marker-end="`url(#pl-arrow${link.hot ? '-hot' : link.critical ? '-critical' : ''})`"
					/>
				</svg>

				<div
					v-for="(task, i) in rows"
					:key="task.name"
					class="pl-row"
					:class="{
						'is-group': task.is_group,
						'is-selected': selected === task.name || multi_set.has(task.name),
						'is-context': context === task.name,
						'is-variation': task.is_variation,
						[`is-level-${Math.min(task.indent || 0, 3)}`]: task.is_group,
					}"
					:style="{ top: `${i * ROW_H}px` }"
					@contextmenu="on_row_context($event, task)"
				>
					<div class="pl-cells" @mousedown="$event.shiftKey && $event.preventDefault()" @click="on_row_click(task, $event)">
						<div
							v-for="col in columns"
							:key="col.key"
							class="pl-cell"
							:class="[`is-${col.align || 'start'}`, `col-${col.key}`, { 'is-editable': editable(task, col) }]"
							:style="{ width: `${col.w}px` }"
							@click="start_edit(task, col, $event)"
						>
							<template v-if="col.key === 'item_name'">
								<span class="pl-indent" :style="{ width: `${(task.indent || 0) * 16}px` }"></span>
								<button
									v-if="task.is_group"
									type="button"
									class="pl-caret"
									:class="{ 'is-closed': collapsed.has(task.name) }"
									:aria-label="collapsed.has(task.name) ? 'ขยาย' : 'ย่อ'"
									@click.stop="toggle(task)"
								>
									<Icon name="chevron-down" :size="14" :stroke="2.4" />
								</button>
								<span v-else class="pl-dot" :class="`tone-${metric(task).status.tone}`"></span>
								<span class="pl-name" :title="task.item_name">{{ task.item_name }}</span>
								<button
									v-if="p.plan_marks.has(task.name)"
									type="button"
									class="pl-marks"
									:title="marks_title(task)"
									:aria-label="marks_title(task)"
									@click.stop="$emit('resources', task)"
								>
									<span v-if="p.plan_marks.get(task.name).resources.length">
										<Icon name="users" :size="11" />{{ p.plan_marks.get(task.name).resources.length }}
									</span>
									<span v-if="p.plan_marks.get(task.name).materials.length">
										<Icon name="cart" :size="11" />{{ p.plan_marks.get(task.name).materials.length }}
									</span>
								</button>
							</template>
							<DateInput
								v-else-if="col.edit === 'date' && editable(task, col)"
								:model-value="task[col.key]"
								variant="cell"
								:label="col.label"
								@update:model-value="(value) => p.update_task(task, col.key, value)"
							/>
							<input
								v-else-if="is_editing(task, col)"
								ref="editor"
								class="pl-input"
								:class="`is-${col.align || 'start'}`"
								:value="edit_value"
								:inputmode="col.edit === 'text' ? 'text' : 'decimal'"
								@keydown.enter.prevent="commit"
								@keydown.esc.prevent="cancel"
								@keydown.tab="commit"
								@blur="commit"
							/>
							<span
								v-else-if="col.key === 'status' && (task.is_group || metric(task).status)"
								class="pl-status"
								:class="`tone-${metric(task).status.tone}`"
								>{{ metric(task).status.label }}</span
							>
							<template v-else>{{ cell_text(task, col) }}</template>
						</div>
					</div>
					<div class="pl-track" :style="{ width: `${timeline_w}px` }" @click="on_track_click(task)">
						<div
							v-if="show.baseline && task.baseline_start_date"
							class="pl-base"
							:style="span(to_day(task.baseline_start_date), to_day(task.baseline_end_date))"
						></div>
						<template v-if="bar(task)">
							<div
								v-if="task.is_group"
								class="pl-sum"
								:class="{ 'is-done': metric(task).actual_pct >= 99.995 }"
								:style="span(bar(task).start, bar(task).end)"
							>
								<i :style="{ width: `${metric(task).actual_pct}%` }"></i>
							</div>
							<div
								v-else
								class="pl-bar"
								:class="{
									'is-critical': show.critical && metric(task).critical,
									'is-done': metric(task).actual_pct >= 99.995,
									'is-active': drag.task === task,
									'can-drag': p.can_write,
								}"
								:style="span(bar(task).start, bar(task).end)"
								:title="bar_title(task)"
								@pointerdown="on_bar_down($event, task, 'move')"
								@click.stop="on_bar_click(task)"
							>
								<!-- ตัวเลข % มี 2 ชั้น: ชั้นล่างสีเข้มบนพื้นอ่อน ชั้นในแถบ % จริงสีขาว (ถูกตัดตามความยาวแถบ) ตัวเลขจึงอ่านออกทุกช่วง -->
								<span
									v-for="item in splits.get(task.name)?.labels"
									:key="item.left"
									class="pl-bar-share"
									:style="{ left: `${item.left}px`, width: `${item.width}px` }"
									>{{ item.text }}</span
								>
								<i class="pl-bar-fill" :style="{ width: `${metric(task).actual_pct}%` }">
									<span
										v-for="item in splits.get(task.name)?.labels"
										:key="item.left"
										class="pl-bar-share is-on-fill"
										:style="{ left: `${item.left}px`, width: `${item.width}px` }"
										>{{ item.text }}</span
									>
								</i>
								<i
									v-for="left in splits.get(task.name)?.dividers"
									:key="left"
									class="pl-bar-divider"
									:style="{ left: `${left}px` }"
								></i>
								<template v-if="p.can_write">
									<span class="pl-grip is-start" @pointerdown.stop="on_bar_down($event, task, 'start')"></span>
									<span class="pl-grip is-end" @pointerdown.stop="on_bar_down($event, task, 'end')"></span>
								</template>
							</div>
							<span
								v-if="show.labels || show.progress || drag.task === task"
								class="pl-label"
								:class="{ 'is-group': task.is_group }"
								:style="{ left: `${x(bar(task).end + 1) + 6}px` }"
							>
								<template v-if="drag.task === task">{{ drag_hint }}</template>
								<template v-else>
									<span v-if="show.labels">{{ task.item_name }}</span>
									<span v-if="show.progress" class="pl-pill" :class="`tone-${metric(task).status.tone}`">
										<span class="is-plan">แผน {{ metric(task).plan_pct.toFixed(3) }}%</span>
										<span class="is-actual">จริง {{ metric(task).actual_pct.toFixed(3) }}%</span>
									</span>
								</template>
							</span>
						</template>
					</div>
				</div>
			</div>

			<!-- ตารางสรุปใต้ Gantt + แถบเลื่อนของตารางเมื่อฝั่งตารางแคบกว่าคอลัมน์ -->
			<div v-if="show_summary || clipped" class="pl-foot">
				<div class="pl-foot-cells">
					<template v-if="show_summary">
						<div v-for="row in summary_rows" :key="row.key" class="pl-foot-label" :class="[`is-${row.tone}`, { 'is-cum': row.cum }]">
							{{ row.label }}
						</div>
					</template>
					<div v-if="clipped" class="pl-grid-bar" @scroll="(e) => (grid_scroll = e.target.scrollLeft)">
						<div :style="{ width: `${cols_w}px` }"></div>
					</div>
				</div>
				<div v-if="show_summary" class="pl-foot-time" :style="{ width: `${timeline_w}px` }">
					<div v-for="row in summary_rows" :key="row.key" class="pl-foot-row" :class="[`is-${row.tone}`, { 'is-cum': row.cum }]">
						<span
							v-for="cell in summary_cells"
							:key="cell.left"
							:style="{ left: `${cell.left}px`, width: `${cell.width}px` }"
							:title="cell.title(row)"
							>{{ cell.text(row) }}</span
						>
					</div>
				</div>
			</div>
		</div>
	</div>

	<div
		v-if="curve_lines.length"
		class="pl-curve-axis"
		:style="{ height: `${curve_h}px`, right: `${scrollbar_w}px` }"
		aria-hidden="true"
	>
		<span v-for="tick in CURVE_TICKS" :key="tick" :style="{ top: `${curve_y(tick)}px` }">{{ tick }}%</span>
	</div>

	<div
		v-if="!compact"
		class="pl-splitter"
		:class="{ 'is-active': resizing === 'pane' }"
		:style="{ left: `${grid_w}px` }"
		role="separator"
		aria-orientation="vertical"
		title="ลากเพื่อแบ่งพื้นที่ตาราง/Gantt ดับเบิลคลิก = ค่าเดิม"
		@pointerdown.prevent="on_split_down"
		@dblclick="reset_split"
	></div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";
import Icon from "../../../../shared/components/Icon.vue";
import DateInput from "../../../../shared/components/DateInput.vue";
import {
	parse_distribution,
	parse_predecessors,
	period_shares,
	sample_curve,
	segments,
	smooth_path,
	summary_values,
	to_day,
	today,
} from "../../../../construction_management/schedule.js";
import { SUMMARY_ROWS, view_curves, view_summary, COLUMNS as ALL_COLUMNS, task_matches } from "./planner.js";
import { MONTHS, use_time_axis } from "./time_axis.js";

const props = defineProps({
	p: { type: Object, required: true },
	// columns: คีย์ของคอลัมน์ที่แสดง, scale: day/week/month, zoom: ตัวคูณ
	settings: { type: Object, required: true },
	selected: String,
	// แถวที่เลือกหลายงานด้วย Shift (เพิ่ม/เลื่อนระดับ/ลบ)
	multi: { type: Array, default: () => [] },
	// แถวที่เปิดเมนูคลิกขวาอยู่
	context: String,
	// ตัวกรองงาน (TASK_FILTERS) งานที่ผ่านตัวกรองคงหัวข้อของงานนั้นไว้
	filter: { type: String, default: "all" },
});
const emit = defineEmits(["select", "context", "resources"]);
const multi_set = computed(() => new Set(props.multi));

const ROW_H = 36;
// ตำแหน่งแถบงานในแถว (ตรงกับ .pl-bar) เส้นงานก่อนหน้าคิดจากค่านี้
const BAR_TOP = 7;
const BAR_H = 17;
const ARROWS = ["", "-critical", "-hot"];
// ความกว้างต่ำสุด: คอลัมน์ / ฝั่งตาราง / ฝั่ง Gantt
const MIN_COLUMN = 36;
const MIN_PANE = 160;
const MIN_TIMELINE = 160;
// ช่องแคบกว่านี้ไม่แสดงตัวเลข (ดูจาก tooltip)
// ตัวเลข 3 ตำแหน่งกว้างสุด "100.000" ช่องรายวันที่ซูม 100% (SCALES.day.px) จึงต้องไม่แคบกว่านี้
const MIN_SUMMARY_WIDTH = 44;
const HEAD_H = 52;
const SUMMARY_ROW_H = 22;
const CURVE_MARGIN = 10;
const CURVE_TICKS = [0, 25, 50, 75, 100];
const CURVE_LABELS = { baseline: "แผนสัญญา", plan: "แผน", actual: "จริง" };

const p = computed(() => props.p);
const show = computed(() => props.settings.show);
const scroller = ref(null);
const editor = ref(null);
const today_day = today();

// มือถือ: เหลือ WBS + ชื่องาน (แก้ในแผงงาน)
const narrow = window.matchMedia("(max-width: 767px)");
const compact = ref(narrow.matches);
const on_narrow = () => (compact.value = narrow.matches);
// มือถือแนวตั้ง: ไม่มีตาราง Gantt เต็มจอ (ชื่องานอยู่ท้ายแถบ) แตะแถว = เลือกงาน / ย่อ-ขยายกลุ่ม
const portrait = window.matchMedia("(max-width: 767px) and (orientation: portrait)");
const hide_grid = ref(portrait.matches);
const on_portrait = () => (hide_grid.value = portrait.matches);

// คอลัมน์ WBS พอดีเลขที่ยาวที่สุด (เลข 6.8px จุด 3px ที่ตัวอักษร 11px) ลากเองแล้วใช้ค่าที่ลาก
const wbs_w = computed(() => {
	const longest = Math.max(
		0,
		...p.value.tasks.map((t) => {
			const text = String(t.wbs || "");
			const dots = text.split(".").length - 1;
			return (text.length - dots) * 6.8 + dots * 3;
		})
	);
	return Math.max(42, Math.ceil(longest) + 18);
});
const base_columns = computed(() => {
	if (hide_grid.value) return [];
	const keys = compact.value ? ["wbs", "item_name"] : props.settings.columns;
	return keys
		.filter((key) => ALL_COLUMNS[key])
		.map((key) => {
			const auto = key === "wbs" ? wbs_w.value : ALL_COLUMNS[key].w;
			return {
				key,
				...ALL_COLUMNS[key],
				w: compact.value ? { wbs: 44, item_name: 156 }[key] : props.settings.widths?.[key] ?? auto,
			};
		});
});
const cols_w = computed(() => base_columns.value.reduce((sum, col) => sum + col.w, 0));

// ฝั่งตาราง: ตามตัวแบ่งที่ลากไว้ (ไม่ลาก = พอดีคอลัมน์) และเหลือที่ให้ Gantt เสมอ
const view_w = ref(0);
const grid_w = computed(() => {
	if (compact.value) return cols_w.value;
	const wanted = props.settings.pane_w ?? cols_w.value;
	const max = view_w.value ? Math.max(view_w.value - MIN_TIMELINE, MIN_PANE) : wanted;
	return Math.round(Math.min(Math.max(wanted, MIN_PANE), max));
});
// ตารางกว้างกว่าคอลัมน์ = ชื่องานยืดเต็ม, แคบกว่า = ตัดขวา เลื่อนด้วยแถบท้ายตาราง
const columns = computed(() => {
	const extra = Math.max(grid_w.value - cols_w.value, 0);
	return base_columns.value.map((col) => ({ ...col, base: col.w, w: col.key === "item_name" ? col.w + extra : col.w }));
});
const clipped = computed(() => cols_w.value - grid_w.value > 0.5);
const grid_scroll = ref(0);
const grid_x = computed(() => (clipped.value ? Math.min(grid_scroll.value, cols_w.value - grid_w.value) : 0));

// ---------- ปรับความกว้างคอลัมน์ / ตัวแบ่ง ----------
const resizing = ref(null); // key ของคอลัมน์ หรือ "pane"
let resize = null;

function stop_resize() {
	window.removeEventListener("pointermove", on_col_move);
	window.removeEventListener("pointermove", on_split_move);
	resizing.value = null;
	resize = null;
}
function on_col_down(event, col) {
	if (event.button !== 0) return;
	resize = { key: col.key, x0: event.clientX, base: col.base, pane: props.settings.pane_w };
	resizing.value = col.key;
	window.addEventListener("pointermove", on_col_move);
	window.addEventListener("pointerup", stop_resize, { once: true });
}
function on_col_move(event) {
	const { key, x0, base, pane } = resize;
	const width = Math.max(Math.round(base + event.clientX - x0), MIN_COLUMN);
	props.settings.widths = { ...props.settings.widths, [key]: width };
	// ลากตัวแบ่งไว้แล้ว: ฝั่งตารางกว้างตามคอลัมน์ ไม่ให้ชื่องานเป็นฝ่ายหดแทน
	if (pane !== null && pane !== undefined) props.settings.pane_w = pane + width - base;
}
function reset_col(col) {
	const { [col.key]: removed, ...rest } = props.settings.widths || {};
	if (removed === undefined) return;
	props.settings.widths = rest;
}
function on_split_down(event) {
	if (event.button !== 0) return;
	resize = { x0: event.clientX, base: grid_w.value };
	resizing.value = "pane";
	window.addEventListener("pointermove", on_split_move);
	window.addEventListener("pointerup", stop_resize, { once: true });
}
function on_split_move(event) {
	const max = Math.max(view_w.value - MIN_TIMELINE, MIN_PANE);
	props.settings.pane_w = Math.round(Math.min(Math.max(resize.base + event.clientX - resize.x0, MIN_PANE), max));
}
function reset_split() {
	props.settings.pane_w = null;
}

// ---------- แถวที่แสดง (ย่อ/ขยายกลุ่ม) ----------
const collapsed = reactive(new Set());
// null = ไม่กรอง
const filtered_names = computed(() => {
	if (props.filter === "all") return null;
	const kept = new Set();
	const parents = [];
	for (const task of p.value.tasks) {
		while (parents.length && parents[parents.length - 1].indent >= task.indent) parents.pop();
		if (task.is_group) parents.push(task);
		else if (task_matches(metric(task), props.filter)) {
			kept.add(task.name);
			parents.forEach((parent) => kept.add(parent.name));
		}
	}
	return kept;
});
const rows = computed(() => {
	const result = [];
	const kept = filtered_names.value;
	let hide_below = null;
	for (const task of p.value.tasks) {
		if (kept && !kept.has(task.name)) continue;
		if (hide_below !== null && task.indent > hide_below) continue;
		hide_below = task.is_group && collapsed.has(task.name) ? task.indent : null;
		result.push(task);
	}
	return result;
});
const body_h = computed(() => rows.value.length * ROW_H);
function toggle(task) {
	if (collapsed.has(task.name)) collapsed.delete(task.name);
	else collapsed.add(task.name);
}
// หน้าดูอย่างเดียว: เปิดมาเห็นงานที่กำลังทำก่อน หัวข้อที่เสร็จหมดแล้วพับไว้
function collapse_done() {
	collapsed.clear();
	p.value.tasks.filter((t) => t.is_group && metric(t).actual_pct >= 99.995).forEach((t) => collapsed.add(t.name));
}
// แสดงถึงระดับ level (1 = หัวข้อหลัก) null = ทั้งหมด
function set_level(level) {
	collapsed.clear();
	if (!level) return;
	p.value.tasks.filter((t) => t.is_group && t.indent >= level - 1).forEach((t) => collapsed.add(t.name));
}

const metric = (task) =>
	p.value.metrics.get(task.name) || { plan_pct: 0, actual_pct: 0, status: { tone: "gray", label: "" } };

// ---------- แกนเวลา (time_axis.js ใช้ร่วมกับ Gantt ทรัพยากร) ----------
const { scale, ppd, range, axis, timeline_w, x, day_mid, span, top_periods, bottom_periods, off_days } = use_time_axis(p, props.settings);
const today_in_range = computed(() => today_day >= range.value.start && today_day < range.value.end);


// ---------- แถบงาน (ระหว่างลากใช้วันที่ชั่วคราว) ----------
const drag = reactive({ task: null, mode: null, x0: 0, anchor: 0, delta: 0, moved: false });
let suppress_click = false;

function bar(task) {
	if (drag.task === task) return p.value.drag_dates(task, drag.mode, drag.delta);
	const start = to_day(task.start_date);
	const end = to_day(task.end_date);
	return start === null || end === null ? null : { start, end };
}
const drag_hint = computed(() => {
	if (!drag.task) return "";
	const next = bar(drag.task);
	const sign = drag.delta > 0 ? "+" : "";
	return `${short_date(next.start)} – ${short_date(next.end)}${drag.delta ? `  (${sign}${drag.delta} วัน)` : ""}`;
});

function on_bar_down(event, task, mode) {
	// จอสัมผัส: ไม่ลาก (ปัดเลื่อนดู) แตะ = เลือกงานแล้วแก้ในแผง
	if (!p.value.can_write || event.button !== 0 || event.pointerType === "touch") return;
	event.preventDefault();
	// จุดอ้างอิงของการลาก: ลากปลาย = ปลายแถบ, อื่นๆ = ต้นแถบ แปลงระยะเมาส์เป็นวันผ่านแกนเวลา
	const anchor = mode === "end" ? to_day(task.end_date) + 1 : to_day(task.start_date);
	Object.assign(drag, { task, mode, x0: event.clientX, anchor, delta: 0, moved: false });
	window.addEventListener("pointermove", on_drag_move);
	window.addEventListener("pointerup", on_drag_end, { once: true });
}
function on_drag_move(event) {
	const dx = event.clientX - drag.x0;
	if (Math.abs(dx) > 3) drag.moved = true;
	drag.delta = Math.round(axis.value.day_at(x(drag.anchor) + dx) - drag.anchor);
}
function on_drag_end() {
	window.removeEventListener("pointermove", on_drag_move);
	const { task, mode, delta, moved } = drag;
	drag.task = null;
	if (!moved) return;
	suppress_click = true;
	setTimeout(() => (suppress_click = false), 0);
	p.value.apply_drag(task, mode, delta);
}
function on_bar_click(task) {
	if (suppress_click) return;
	emit("select", task.name);
}
function bar_title(task) {
	const m = metric(task);
	const weights = parse_distribution(task.plan_distribution)?.weights;
	return `${task.wbs} ${task.item_name}\n${short_date(to_day(task.start_date))} – ${short_date(
		to_day(task.end_date)
	)} (${task.duration} วัน)\nแผน ${m.plan_pct.toFixed(3)}% · จริง ${m.actual_pct.toFixed(3)}%${
		weights ? `\n% แผนกำหนดเอง: ${weights.join(" / ")}` : ""
	}`;
}

const format_share = (value) => `${value.toFixed(3)}%`;

// งานที่กำหนด % แผนเอง: เส้นแบ่งตามหน่วยที่กำหนด + % ตามช่องเวลาที่ดูอยู่ (เฉพาะช่องที่กว้างพอ)
// จำนวนช่วงไม่ตรงกับวันที่ (เช่นระหว่างลาก) = ไม่แสดง เพราะตอนนั้นระบบคิดตามจำนวนวัน
const MIN_SHARE_WIDTH = 48;
const splits = computed(() => {
	const result = new Map();
	for (const task of rows.value) {
		if (task.is_group || !task.plan_distribution) continue;
		const distribution = parse_distribution(task.plan_distribution);
		const span_days = bar(task);
		if (!distribution || !span_days) continue;
		const { start, end } = span_days;
		const parts = segments(start, end, distribution.unit);
		if (parts.length !== distribution.weights.length) continue;
		result.set(task.name, {
			dividers: parts.slice(1).map((part) => x(part.start) - x(start)),
			labels: show.value.split
				? period_shares(start, end, distribution, p.value.counting, scale.value.bottom)
						.map((part) => ({
							left: x(part.start) - x(start),
							width: x(part.end + 1) - x(part.start),
							text: format_share(part.percent),
						}))
						.filter((item) => item.width >= MIN_SHARE_WIDTH)
				: [],
		});
	}
	return result;
});

function marks_title(task) {
	const { resources, materials } = p.value.plan_marks.get(task.name);
	return [
		resources.length ? `คน/เครื่องจักร: ${resources.join(", ")}` : "",
		materials.length ? `วัสดุ: ${materials.join(", ")}` : "",
	]
		.filter(Boolean)
		.join("\n");
}

// ---------- ตารางสรุปใต้ Gantt ----------
// รายช่วง = ตามช่องเวลาที่ดูอยู่, สะสม = ณ สิ้นช่วง (summary_values ชุดเดียวกับตารางสรุปของระบบเต็ม)
// แถวที่เลือกแสดงในแท็บมุมมอง
const summary_rows = computed(() => {
	const on = view_summary(props.settings, p.value);
	return SUMMARY_ROWS.filter((row) => on[row.key] && (row.curve !== "baseline" || p.value.curves.baseline)).map((row) => ({
		...row,
		tone: row.curve,
		cum: !row.key.endsWith("_period"),
	}));
});
const show_summary = computed(() => summary_rows.value.length > 0 && !compact.value);
const summary_cells = computed(() => {
	if (!show_summary.value) return [];
	return bottom_periods.value.map((period) => {
		const values = summary_values(period, p.value.curves, p.value.data?.total_amount);
		const width = x(period.end) - x(period.start);
		const value_of = (row) => {
			const value = values[row.key];
			// ช่องรายช่วงที่เป็นศูนย์เว้นว่าง ตารางจึงเห็นเฉพาะช่วงที่มีงาน
			return value === null || value === undefined || (row.key.endsWith("_period") && Math.abs(value) < 0.005)
				? ""
				: value.toFixed(3);
		};
		return {
			left: x(period.start),
			width,
			text: (row) => (width < MIN_SUMMARY_WIDTH ? "" : value_of(row)),
			title: (row) => (value_of(row) ? `${row.label}: ${value_of(row)}%` : ""),
		};
	});
});

// ---------- S-Curve (Baseline ตามปุ่ม Baseline) จุดอยู่ปลายแต่ละช่องเวลา เหมือนหน้า Gantt ของระบบเต็ม ----------
const view_h = ref(0);
const scrollbar_w = ref(0);
const foot_h = computed(() => (show_summary.value ? summary_rows.value.length * SUMMARY_ROW_H + 1 : 0));
const curve_h = computed(() => Math.max(Math.min(view_h.value - HEAD_H - foot_h.value, Math.max(body_h.value, 120)), 100));
const curve_y = (value) => CURVE_MARGIN + (1 - value / 100) * (curve_h.value - 2 * CURVE_MARGIN);
const curve_lines = computed(() => {
	if (compact.value) return [];
	const on = view_curves(props.settings, p.value);
	return ["baseline", "plan", "actual"]
		.filter((key) => p.value.curves[key] && on[key])
		.map((key) => {
			const points = sample_curve(p.value.curves[key], bottom_periods.value).map((point) => ({
				day: point.day,
				x: x(point.day + 1),
				y: curve_y(point.value),
				title: `${CURVE_LABELS[key]} ${short_date(point.day)}: ${point.value.toFixed(3)}%`,
			}));
			return { key, points, d: smooth_path(points.map((point) => [point.x, point.y])) };
		});
});

// ---------- เส้นงานก่อนหน้า ----------
// ออกจากขอบล่าง/บนของแถบ (ใกล้ปลายหรือต้นแถบ) แล้วเข้าข้างแถบงานที่ตามมา จึงไม่วิ่งผ่านชื่องานท้ายแถบในแถวเดียวกัน
// เส้นลงตรงๆ ไม่ได้ (งานถัดไปเริ่มก่อน) ให้อ้อมผ่านเส้นแบ่งแถวของงานที่ตามมา
const LINK_INSET = 6;
const LINK_GAP = 10;

function rounded_path(points, radius = 4) {
	let d = `M${points[0][0]} ${points[0][1]}`;
	for (let i = 1; i < points.length - 1; i++) {
		const [ax, ay] = points[i - 1];
		const [bx, by] = points[i];
		const [cx, cy] = points[i + 1];
		const in_len = Math.hypot(bx - ax, by - ay);
		const out_len = Math.hypot(cx - bx, cy - by);
		if (!in_len || !out_len) continue;
		const r = Math.min(radius, in_len / 2, out_len / 2);
		d += `L${bx - ((bx - ax) / in_len) * r} ${by - ((by - ay) / in_len) * r}`;
		d += `Q${bx} ${by} ${bx + ((cx - bx) / out_len) * r} ${by + ((cy - by) / out_len) * r}`;
	}
	const last = points[points.length - 1];
	return `${d}L${last[0]} ${last[1]}`;
}

const links = computed(() => {
	const index = new Map(rows.value.map((task, i) => [task.name, i]));
	const result = [];
	for (const task of rows.value) {
		if (task.is_group || !task.predecessors) continue;
		const to = bar(task);
		if (!to) continue;
		for (const link of parse_predecessors(task.predecessors)) {
			const i = index.get(link.task);
			const from_task = p.value.by_name.get(link.task);
			const from = from_task && bar(from_task);
			if (i === undefined || !from) continue;
			const type = link.type || "FS";
			const from_end = type[0] === "F";
			const to_start = type[1] === "S";
			const j = index.get(task.name);
			const down = j > i;
			const from_left = x(from.start);
			const from_right = x(from.end + 1);
			const inset = Math.min(LINK_INSET, (from_right - from_left) / 2);
			const x1 = from_end ? from_right - inset : from_left + inset;
			const x2 = to_start ? x(to.start) : x(to.end + 1);
			const y1 = i * ROW_H + (down ? BAR_TOP + BAR_H : BAR_TOP);
			const y2 = j * ROW_H + BAR_TOP + BAR_H / 2;
			const b = to_start ? x2 - LINK_GAP : x2 + LINK_GAP;
			const straight = to_start ? x1 <= b : x1 >= b;
			const ym = j * ROW_H + (down ? 0 : ROW_H);
			const d = rounded_path(
				straight
					? [[x1, y1], [x1, y2], [x2, y2]]
					: [[x1, y1], [x1, ym], [b, ym], [b, y2], [x2, y2]]
			);
			const critical = show.value.critical && metric(task).critical && metric(from_task).critical;
			const hot = props.selected === task.name || props.selected === link.task;
			result.push({ key: `${link.task}>${task.name}`, d, critical, hot });
		}
	}
	return result;
});

// ---------- แก้ในช่อง ----------
const editing = reactive({ task: null, key: null });
const edit_value = ref("");

function editable(task, col) {
	return Boolean(col.edit) && !task.is_group && p.value.can_write && !compact.value;
}
const is_editing = (task, col) => editing.task === task && editing.key === col.key;

function start_edit(task, col, event) {
	if (event.shiftKey) return;
	if (!editable(task, col) || col.edit === "date" || is_editing(task, col)) return;
	event.stopPropagation();
	editing.task = task;
	editing.key = col.key;
	edit_value.value =
		col.key === "predecessors"
			? metric(task).predecessors
			: col.key === "actual_pct"
			? round(metric(task).actual_pct, 3)
			: task[col.key] ?? "";
	nextTick(() => {
		const input = Array.isArray(editor.value) ? editor.value[0] : editor.value;
		input?.focus();
		input?.select();
	});
}
function commit(event) {
	if (!editing.task) return;
	const { task, key } = editing;
	const value = event?.target?.value ?? edit_value.value;
	editing.task = null;
	const before =
		key === "predecessors" ? metric(task).predecessors : key === "actual_pct" ? round(metric(task).actual_pct, 3) : task[key];
	if (String(value).trim() === String(before ?? "").trim()) return;
	p.value.update_task(task, key, key === "predecessors" ? value : Number(String(value).replace(/,/g, "")));
}
function cancel() {
	editing.task = null;
}

// คลิกขวาที่แถว: day = วันใต้เมาส์ (เฉพาะฝั่ง Gantt) ช่องกรอกยังใช้เมนูของเบราว์เซอร์ (วาง/คัดลอก)
function on_row_context(event, task) {
	if (event.target.closest("input, textarea")) return;
	event.preventDefault();
	const track = event.target.closest(".pl-track");
	const day = track
		? Math.floor(axis.value.day_at(event.clientX - track.getBoundingClientRect().left))
		: null;
	emit("context", { task, day, x: event.clientX, y: event.clientY });
}

function on_track_click(task) {
	if (!hide_grid.value) return;
	if (task.is_group) toggle(task);
	else emit("select", task.name);
}

function on_row_click(task, event) {
	if (event.shiftKey) {
		emit("select", task.name, { shift: true });
		return;
	}
	if (event.target.closest(".pl-cell.is-editable, button, input")) return;
	emit("select", task.name);
	// เลือกจากตาราง: เลื่อน Gantt ไปที่แถบของงาน (ถ้ายังไม่เห็น)
	reveal_bar(task);
}

// ---------- ข้อความในช่อง ----------
const round = (value, digits) => Math.round((Number(value) || 0) * 10 ** digits) / 10 ** digits;
function short_date(day) {
	if (day === null || day === undefined) return "";
	const date = new Date(day * 86400000);
	return `${date.getUTCDate()} ${MONTHS[date.getUTCMonth()]} ${date.getUTCFullYear() + 543}`;
}
function pct(value) {
	return `${(Number(value) || 0).toFixed(3)}%`;
}
function cell_text(task, col) {
	const m = metric(task);
	switch (col.key) {
		case "start_date":
		case "end_date":
			return short_date(to_day(task[col.key]));
		case "duration":
			return task.duration || "";
		case "predecessors":
			return m.predecessors;
		case "plan_pct":
			return pct(m.plan_pct);
		case "actual_pct":
			return pct(m.actual_pct);
		case "diff": {
			const diff = m.actual_pct - m.plan_pct;
			return `${diff >= 0.0005 ? "+" : ""}${(Math.abs(diff) < 0.0005 ? 0 : diff).toFixed(3)}`;
		}
		case "total_float":
			return m.total_float ?? "";
		default:
			return task[col.key] ?? "";
	}
}

// ---------- เลื่อนไปวัน/งาน ----------
function scroll_to_day(day, align = 0.3) {
	const el = scroller.value;
	if (!el) return;
	const view = el.clientWidth - grid_w.value;
	el.scrollTo({ left: Math.max(x(day) - view * align, 0), behavior: "smooth" });
}
function reveal_bar(task) {
	const el = scroller.value;
	const start = to_day(task.start_date);
	if (!el || start === null) return;
	const view = el.clientWidth - grid_w.value;
	const left = x(start);
	if (left < el.scrollLeft || left > el.scrollLeft + view - 60) scroll_to_day(start, 0.15);
}
function scroll_to_task(name) {
	const task = p.value.by_name.get(name);
	if (!task) return;
	const i = rows.value.indexOf(task);
	const el = scroller.value;
	if (i >= 0 && el) {
		const top = i * ROW_H;
		if (top < el.scrollTop || top > el.scrollTop + el.clientHeight - 120)
			el.scrollTo({ top: Math.max(top - 80, 0), behavior: "smooth" });
	}
	const start = to_day(task.start_date);
	if (start !== null) scroll_to_day(start, 0.15);
}

// เปลี่ยนมาตราส่วน/ซูม: คงวันที่อยู่กึ่งกลางจอไว้
watch(axis, (next, prev) => {
	const el = scroller.value;
	if (!el || !prev || next.key === prev.key) return;
	const view = el.clientWidth - grid_w.value;
	const center = prev.day_at(el.scrollLeft + view / 2);
	nextTick(() => (el.scrollLeft = Math.max(next.x(center) - view / 2, 0)));
});

let observer = null;
onMounted(() => {
	narrow.addEventListener("change", on_narrow);
	portrait.addEventListener("change", on_portrait);
	observer = new ResizeObserver(([entry]) => {
		view_w.value = entry.contentRect.width;
		view_h.value = entry.contentRect.height;
		scrollbar_w.value = entry.target.offsetWidth - entry.target.clientWidth;
	});
	if (scroller.value) observer.observe(scroller.value);
	nextTick(() => {
		const el = scroller.value;
		if (el) el.scrollLeft = Math.max(x(p.value.cutoff_day) - (el.clientWidth - grid_w.value) * 0.3, 0);
	});
});
onBeforeUnmount(() => {
	narrow.removeEventListener("change", on_narrow);
	portrait.removeEventListener("change", on_portrait);
	window.removeEventListener("pointermove", on_drag_move);
	window.removeEventListener("pointerup", stop_resize);
	stop_resize();
	observer?.disconnect();
});

const is_collapsed = (task) => collapsed.has(task.name);

defineExpose({ filtered_names, set_level, collapse_done, scroll_to_day, scroll_to_task, toggle, is_collapsed });
</script>
