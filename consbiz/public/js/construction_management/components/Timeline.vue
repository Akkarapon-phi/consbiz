<script setup>
// timeline ฝั่งขวา: หัว 2 แถว, แถบงาน (ลากย้าย/ยืดหดได้), แถบ baseline, แรเงาวันหยุด,
// เส้นวันนี้, เส้นวันที่เลือกดู, S-Curve หลายเส้น และตารางสรุปติดด้านล่าง
// แกน x: 1 วัน = ppd พิกเซล นับจาก range.start (เลขวันจาก schedule.js)
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import SCurve from "./SCurve.vue";
import {
	parse_distribution,
	period_shares,
	periods,
	sample_curve,
	segments,
	summary_values,
	to_day,
	today,
} from "../schedule";
import {
	format_money,
	format_percent,
	format_share,
	period_label,
	progress_status,
	text_width,
} from "../columns";

const props = defineProps({
	tasks: Array,
	range: Object,
	ppd: Number,
	units: Object,
	holidays: Set,
	curves: Array, // [{ key, label, color, curve }] เฉพาะเส้นที่เปิดแสดง
	allCurves: Object, // { baseline, plan, actual } ใช้กับตารางสรุป
	showBaselineBars: Boolean,
	showSplit: Boolean,
	showLabels: Boolean,
	showProgress: Boolean,
	showStatus: Boolean,
	countingHolidays: Set,
	summaryRows: Array,
	summaryRowHeight: Number,
	totalAmount: Number,
	statusDay: Number,
	metrics: Map,
	canWrite: Boolean,
	rowHeight: Number,
	headerHeight: Number,
	hovered: String,
});
const emit = defineEmits(["scroll", "hover", "set-dates", "edit-plan", "body-height"]);

const body = ref(null);
const scroll_top = ref(0);
const viewport_height = ref(0);
const scrollbar_width = ref(0);

const width = computed(() => (props.range.end - props.range.start) * props.ppd);
const rows_height = computed(() => props.tasks.length * props.rowHeight);
const summary_height = computed(() =>
	props.summaryRows.length ? props.summaryRows.length * props.summaryRowHeight + 1 : 0
);
// พื้นที่แถบงานสูงอย่างน้อยเท่าที่มองเห็น เพื่อไม่ให้ S-Curve แบนเมื่องานน้อย
const chart_height = computed(() =>
	Math.max(rows_height.value, viewport_height.value - props.headerHeight - summary_height.value)
);
watch(chart_height, (value) => emit("body-height", value), { immediate: true });
const curve_height = computed(() =>
	Math.max(viewport_height.value - props.headerHeight - summary_height.value, 100)
);

const x = (day) => (day - props.range.start) * props.ppd;

function header_row(unit, top_level) {
	return periods(props.range.start, props.range.end, unit).map((period) => ({
		...period,
		x: x(period.start),
		width: (period.end - period.start) * props.ppd,
		label: period_label(period, unit, top_level),
	}));
}

const top_header = computed(() => header_row(props.units.top, true));
const bottom_header = computed(() => header_row(props.units.bottom, false));

// ซ่อนป้ายที่ช่องแคบเกินจะอ่านได้
const show_bottom_labels = computed(() => (bottom_header.value[0]?.width || 0) >= 18);

const holiday_rects = computed(() => {
	if (props.ppd < 3) return [];
	return [...props.holidays]
		.filter((day) => day >= props.range.start && day < props.range.end)
		.map((day) => x(day));
});

const day_x = (day) => (day >= props.range.start && day < props.range.end ? x(day) : null);
// ช่องวันนี้ในหัว timeline และเส้นวันนี้ที่สิ้นวัน (ตำแหน่งเดียวกับเส้นวันที่เลือกดู เพราะ % คิด ณ สิ้นวัน)
const today_x = computed(() => day_x(today()));
const today_line_x = computed(() => day_x(today() + 1));
const status_x = computed(() => day_x(props.statusDay + 1));

// ---------- แถบงาน ----------

const drag = ref(null); // { task, mode, origin_x, start, end, new_start, new_end }

const bars = computed(() =>
	props.tasks.map((task, i) => {
		let start = to_day(task.start_date);
		let end = to_day(task.end_date);
		if (drag.value?.task === task) {
			start = drag.value.new_start;
			end = drag.value.new_end;
		}
		const bar = { task, y: i * props.rowHeight };
		const base_start = to_day(task.baseline_start_date);
		const base_end = to_day(task.baseline_end_date);
		if (props.showBaselineBars && base_start !== null && base_end !== null) {
			bar.baseline = {
				x: x(base_start),
				width: Math.max((base_end - base_start + 1) * props.ppd, 2),
			};
		}
		if (start === null || end === null) return bar;
		const actual = props.metrics.get(task.name)?.actual_pct || 0;
		const bar_width = Math.max((end - start + 1) * props.ppd, 2);
		const distribution = task.is_group ? null : parse_distribution(task.plan_distribution);
		const parts = distribution ? segments(start, end, distribution.unit) : [];
		const custom = parts.length && parts.length === distribution.weights.length;
		const metrics = props.metrics.get(task.name);
		// สี Status: เสร็จ = เขียว, ช้าไม่เกินเกณฑ์ = ส้ม, ช้าเกินเกณฑ์ = แดง (ที่เหลือใช้สีปกติ)
		const status =
			props.showStatus && metrics
				? progress_status(metrics.plan_pct, metrics.actual_pct)
				: null;
		const status_class =
			status && ["green", "orange", "red"].includes(status.color)
				? `cs-status-${status.color}`
				: "";
		return {
			...bar,
			start,
			end,
			x: x(start),
			width: bar_width,
			progress_width: (bar_width * Math.min(actual, 100)) / 100,
			// เส้นแบ่งช่วงบนแถบงานที่กำหนด % แผนเอง
			dividers: custom ? parts.slice(1).map((part) => x(part.start)) : [],
			// % ของแต่ละช่วงบนแถบ (เฉพาะช่วงที่กว้างพอจะอ่านได้)
			// % บนแถบตามช่องเวลาที่ดูอยู่ (การแบ่งจริงยังเป็นหน่วยที่กำหนดไว้ เช่นรายสัปดาห์)
			split:
				custom && props.showSplit
					? period_shares(
							start,
							end,
							distribution,
							props.countingHolidays,
							props.units.bottom
					  )
							.map((part) => ({
								x: x(part.start) + ((part.end - part.start + 1) * props.ppd) / 2,
								width: (part.end - part.start + 1) * props.ppd,
								text: format_share(part.percent),
							}))
							.filter((item) => item.width >= 26)
					: [],
			tail: end_label(task, metrics, x(end + 1) + 6),
			status_class,
			status_label: status_class ? status.label : "",
			title: [
				`${task.wbs || ""} ${task.item_name || ""}`.trim(),
				`${__("แผน")}: ${frappe.datetime.str_to_user(
					task.start_date
				)} - ${frappe.datetime.str_to_user(task.end_date)} (${task.duration || 0} ${__(
					"วัน"
				)})`,
				task.baseline_start_date
					? `${__("Baseline")}: ${frappe.datetime.str_to_user(
							task.baseline_start_date
					  )} - ${frappe.datetime.str_to_user(task.baseline_end_date)}`
					: "",
				`${__("น้ำหนัก")}: ${format_number(task.weight || 0, null, 2)}%`,
				`${__("% จริง")}: ${format_number(actual, null, 2)}%`,
				custom
					? `${__("% แผนกำหนดเอง")}: ${distribution.weights
							.map((w) => format_number(w, null, 2))
							.join(" / ")}`
					: "",
				props.canWrite && !task.is_group ? __("คลิกเพื่อกำหนด % แผนรายช่วง") : "",
			]
				.filter(Boolean)
				.join("\n"),
		};
	})
);

// ท้ายแถบ: ชื่องาน (ข้อความ) แล้วตามด้วยกรอบ 2 ช่อง % แผน (ฟ้า) | % จริง (เขียว)
let font_family;
function end_label(task, metrics, x0) {
	font_family = font_family || getComputedStyle(document.body).fontFamily;
	const label = props.showLabels ? `${task.wbs || ""} ${task.item_name || ""}`.trim() : "";
	let pill = null;
	if (props.showProgress && metrics) {
		const part = (text) => ({ text, width: text_width(text, `600 10px ${font_family}`) + 14 });
		const plan = part(`${__("แผน")} ${format_number(metrics.plan_pct, null, 1)}%`);
		const actual = part(`${__("จริง")} ${format_number(metrics.actual_pct, null, 1)}%`);
		const label_width = label
			? text_width(label, `${task.is_group ? 600 : 400} 11px ${font_family}`) + 8
			: 0;
		pill = { x: x0 + label_width, plan, actual };
	}
	return label || pill ? { label, pill } : null;
}

// แถบงานสูงเต็มแถวถ้าไม่แสดง baseline ไม่งั้นแบ่งที่ให้แถบ baseline ด้านล่าง
const bar_y = computed(() => (props.showBaselineBars ? 6 : 8));
const bar_h = computed(() => (props.showBaselineBars ? 13 : props.rowHeight - 16));

function start_drag(bar, mode, event) {
	if (!props.canWrite || bar.task.is_group || event.button !== 0) return;
	event.preventDefault();
	drag.value = {
		task: bar.task,
		mode,
		origin_x: event.clientX,
		start: bar.start,
		end: bar.end,
		new_start: bar.start,
		new_end: bar.end,
		moved: false,
	};
	window.addEventListener("pointermove", on_drag);
	window.addEventListener("pointerup", end_drag, { once: true });
	document.body.classList.add(mode === "move" ? "cs-moving" : "cs-resizing");
}

function on_drag(event) {
	const d = drag.value;
	if (Math.abs(event.clientX - d.origin_x) > 3) d.moved = true;
	const delta = Math.round((event.clientX - d.origin_x) / props.ppd);
	if (d.mode === "move") {
		d.new_start = d.start + delta;
		d.new_end = d.end + delta;
	} else if (d.mode === "start") {
		d.new_start = Math.min(d.start + delta, d.end);
	} else {
		d.new_end = Math.max(d.end + delta, d.start);
	}
}

function end_drag() {
	window.removeEventListener("pointermove", on_drag);
	document.body.classList.remove("cs-moving", "cs-resizing");
	const d = drag.value;
	drag.value = null;
	if (d && (d.new_start !== d.start || d.new_end !== d.end)) {
		emit("set-dates", d.task, d.new_start, d.new_end);
	} else if (d && !d.moved && d.mode === "move") {
		emit("edit-plan", d.task);
	}
}

const drag_label = computed(() => {
	const d = drag.value;
	if (!d) return null;
	const bar = bars.value.find((b) => b.task === d.task);
	if (!bar) return null;
	const fmt = (day) =>
		frappe.datetime.str_to_user(new Date(day * 86400000).toISOString().slice(0, 10));
	return {
		x: bar.x,
		y: bar.y - 2,
		text: `${fmt(d.new_start)} - ${fmt(d.new_end)} (${d.new_end - d.new_start + 1} ${__(
			"วัน"
		)})`,
	};
});

// ---------- S-Curve และตารางสรุป ----------

const curve_lines = computed(() =>
	props.curves.map((c) => ({
		...c,
		points: sample_curve(c.curve, bottom_header.value).map((p) => ({ ...p, x: x(p.day + 1) })),
	}))
);

const summary_font = () =>
	`10px ${(font_family = font_family || getComputedStyle(document.body).fontFamily)}`;

const summary_cells = computed(() => {
	if (!props.summaryRows.length) return [];
	const narrow = (bottom_header.value[0]?.width || 0) < 70;
	return bottom_header.value.map((period) => {
		const values = summary_values(period, props.allCurves, props.totalAmount);
		return {
			x: period.x,
			width: period.width,
			// ช่องที่แคบกว่าข้อความไม่แสดงตัวเลข (ดูได้จาก tooltip) ไม่ให้ตัวเลขซ้อนกัน
			texts: props.summaryRows
				.map((row) =>
					row.money
						? format_money(values[row.key], narrow)
						: format_percent(values[row.key])
				)
				.map((text) => (text_width(text, summary_font()) > period.width - 4 ? "" : text)),
			title: props.summaryRows
				.map((row) =>
					row.money
						? `${row.label}: ${format_money(values[row.key], false)}`
						: `${row.label}: ${format_percent(values[row.key], 2)}%`
				)
				.join("\n"),
		};
	});
});

// ---------- เลื่อนและขนาด ----------

function scroll_to_day(day) {
	if (!body.value) return;
	body.value.scrollLeft = Math.max(x(day) - 40, 0);
}

function viewport_width() {
	return body.value?.clientWidth || 0;
}

function on_scroll() {
	scroll_top.value = body.value.scrollTop;
	emit("scroll", body.value.scrollTop);
}

let observer;
onMounted(() => {
	observer = new ResizeObserver(() => {
		viewport_height.value = body.value.clientHeight;
		scrollbar_width.value = body.value.offsetWidth - body.value.clientWidth;
	});
	observer.observe(body.value);
});
onBeforeUnmount(() => {
	observer?.disconnect();
	window.removeEventListener("pointermove", on_drag);
});

defineExpose({ body, scroll_to_day, viewport_width });
</script>

<template>
	<div class="cs-timeline">
		<div ref="body" class="cs-timeline-body" @scroll="on_scroll">
			<div :style="{ width: width + 'px' }">
				<svg
					class="cs-header"
					:width="width"
					:height="headerHeight"
					:style="{ height: headerHeight + 'px' }"
				>
					<g v-for="period in top_header" :key="'t' + period.start">
						<rect
							:x="period.x"
							y="0"
							:width="period.width"
							:height="headerHeight / 2"
							class="cs-header-cell"
						/>
						<text :x="period.x + 6" :y="headerHeight / 2 - 8" class="cs-header-text">
							{{ period.label }}
						</text>
					</g>
					<g v-for="period in bottom_header" :key="'b' + period.start">
						<rect
							:x="period.x"
							:y="headerHeight / 2"
							:width="period.width"
							:height="headerHeight / 2"
							class="cs-header-cell"
						/>
						<text
							v-if="show_bottom_labels"
							:x="period.x + period.width / 2"
							:y="headerHeight - 8"
							class="cs-header-text"
							text-anchor="middle"
						>
							{{ period.label }}
						</text>
					</g>
					<rect
						v-if="today_x !== null"
						:x="today_x"
						:y="headerHeight - 4"
						:width="Math.max(ppd, 2)"
						height="4"
						class="cs-today-mark"
					/>
					<path
						v-if="status_x !== null"
						:d="`M${status_x - 5},${headerHeight - 7} h10 l-5,7 z`"
						class="cs-status-mark"
					/>
				</svg>

				<svg class="cs-chart" :width="width" :height="chart_height">
					<rect
						v-for="hx in holiday_rects"
						:key="'h' + hx"
						:x="hx"
						y="0"
						:width="ppd"
						:height="chart_height"
						class="cs-holiday"
					/>
					<line
						v-for="period in bottom_header"
						:key="'g' + period.start"
						:x1="period.x"
						:x2="period.x"
						y1="0"
						:y2="chart_height"
						class="cs-grid-line"
					/>

					<g
						v-for="bar in bars"
						:key="bar.task.name"
						@mouseenter="emit('hover', bar.task.name)"
						@mouseleave="emit('hover', null)"
					>
						<rect
							x="0"
							:y="bar.y"
							:width="width"
							:height="rowHeight"
							class="cs-row-bg"
							:class="{ 'cs-hover': hovered === bar.task.name }"
						/>
						<line
							x1="0"
							:x2="width"
							:y1="bar.y + rowHeight"
							:y2="bar.y + rowHeight"
							class="cs-row-line"
						/>
						<rect
							v-if="bar.baseline"
							:x="bar.baseline.x"
							:y="bar.y + rowHeight - 9"
							:width="bar.baseline.width"
							height="4"
							rx="1"
							class="cs-baseline-bar"
						/>
						<template v-if="bar.width">
							<g
								v-if="bar.task.is_group"
								class="cs-group-bar"
								:class="bar.status_class"
							>
								<title>{{ bar.title }}</title>
								<rect
									:x="bar.x"
									:y="bar.y + bar_y + 2"
									:width="bar.width"
									height="7"
								/>
								<rect :x="bar.x" :y="bar.y + bar_y + 2" width="4" height="12" />
								<rect
									:x="bar.x + bar.width - 4"
									:y="bar.y + bar_y + 2"
									width="4"
									height="12"
								/>
							</g>
							<g v-else :class="[{ 'cs-draggable': canWrite }, bar.status_class]">
								<title>{{ bar.title }}</title>
								<rect
									:x="bar.x"
									:y="bar.y + bar_y"
									:width="bar.width"
									:height="bar_h"
									rx="3"
									class="cs-bar"
									@pointerdown="start_drag(bar, 'move', $event)"
								/>
								<line
									v-for="dx in bar.dividers"
									:key="dx"
									:x1="dx"
									:x2="dx"
									:y1="bar.y + bar_y"
									:y2="bar.y + bar_y + bar_h"
									class="cs-divider"
								/>
								<rect
									v-if="bar.progress_width"
									:x="bar.x"
									:y="bar.y + bar_y"
									:width="bar.progress_width"
									:height="bar_h"
									rx="3"
									class="cs-bar-progress"
								/>
								<template v-if="canWrite">
									<rect
										:x="bar.x - 3"
										:y="bar.y + bar_y"
										width="7"
										:height="bar_h"
										class="cs-handle"
										@pointerdown="start_drag(bar, 'start', $event)"
									/>
									<rect
										:x="bar.x + bar.width - 4"
										:y="bar.y + bar_y"
										width="7"
										:height="bar_h"
										class="cs-handle"
										@pointerdown="start_drag(bar, 'end', $event)"
									/>
								</template>
							</g>
							<text
								v-for="item in bar.split"
								:key="'s' + item.x"
								:x="item.x"
								:y="bar.y + bar_y + bar_h / 2 + 4"
								text-anchor="middle"
								class="cs-split-text"
							>
								{{ item.text }}
							</text>
							<template v-if="bar.tail">
								<text
									v-if="bar.tail.label"
									:x="bar.x + bar.width + 6"
									:y="bar.y + rowHeight / 2 + 4"
									class="cs-end-text"
									:class="{ 'cs-end-group': bar.task.is_group }"
								>
									{{ bar.tail.label }}
								</text>
								<g v-if="bar.tail.pill" class="cs-pill">
									<title>{{ bar.status_label || bar.title }}</title>
									<g class="cs-pill-blue">
										<rect
											:x="bar.tail.pill.x"
											:y="bar.y + rowHeight / 2 - 9"
											:width="bar.tail.pill.plan.width + 9"
											height="18"
											rx="9"
										/>
										<text
											:x="bar.tail.pill.x + bar.tail.pill.plan.width / 2"
											:y="bar.y + rowHeight / 2 + 4"
											text-anchor="middle"
										>
											{{ bar.tail.pill.plan.text }}
										</text>
									</g>
									<g class="cs-pill-green">
										<rect
											:x="bar.tail.pill.x + bar.tail.pill.plan.width"
											:y="bar.y + rowHeight / 2 - 9"
											:width="bar.tail.pill.actual.width"
											height="18"
											rx="9"
										/>
										<!-- ปิดมุมโค้งด้านซ้ายของช่องจริง ให้สองช่องต่อกันเป็นกรอบเดียว -->
										<rect
											:x="bar.tail.pill.x + bar.tail.pill.plan.width"
											:y="bar.y + rowHeight / 2 - 9"
											width="9"
											height="18"
										/>
										<text
											:x="
												bar.tail.pill.x +
												bar.tail.pill.plan.width +
												bar.tail.pill.actual.width / 2
											"
											:y="bar.y + rowHeight / 2 + 4"
											text-anchor="middle"
										>
											{{ bar.tail.pill.actual.text }}
										</text>
									</g>
								</g>
							</template>
						</template>
					</g>

					<line
						v-if="today_line_x !== null"
						:x1="today_line_x"
						:x2="today_line_x"
						y1="0"
						:y2="chart_height"
						class="cs-today"
					>
						<title>{{ __("วันนี้") }}</title>
					</line>
					<line
						v-if="status_x !== null"
						:x1="status_x"
						:x2="status_x"
						y1="0"
						:y2="chart_height"
						class="cs-status"
					>
						<title>{{ __("วันที่เลือกดู") }}</title>
					</line>

					<!-- S-Curve สูงเท่าพื้นที่ที่มองเห็นและอยู่กับที่เมื่อเลื่อนแนวตั้ง (งานหลายร้อยแถวก็ยังเห็นทั้งเส้น) -->
					<g v-if="curve_lines.length" :transform="`translate(0, ${scroll_top})`">
						<SCurve grid :height="curve_height" />
						<SCurve
							v-for="line in curve_lines"
							:key="line.key"
							:points="line.points"
							:color="line.color"
							:label="line.label"
							:height="curve_height"
						/>
					</g>

					<text
						v-if="drag_label"
						:x="drag_label.x"
						:y="drag_label.y"
						class="cs-drag-label"
					>
						{{ drag_label.text }}
					</text>
				</svg>

				<svg
					v-if="summaryRows.length"
					class="cs-summary"
					:width="width"
					:height="summary_height"
				>
					<line x1="0" :x2="width" y1="0.5" y2="0.5" class="cs-row-line" />
					<g v-for="cell in summary_cells" :key="cell.x">
						<title>{{ cell.title }}</title>
						<rect
							v-for="(text, i) in cell.texts"
							:key="'r' + i"
							:x="cell.x"
							:y="i * summaryRowHeight + 1"
							:width="cell.width"
							:height="summaryRowHeight"
							class="cs-summary-cell"
						/>
						<text
							v-for="(text, i) in cell.texts"
							:key="'t' + i"
							:x="cell.x + cell.width / 2"
							:y="i * summaryRowHeight + summaryRowHeight / 2 + 5"
							text-anchor="middle"
							class="cs-summary-text"
						>
							{{ text }}
						</text>
					</g>
				</svg>
			</div>
		</div>

		<!-- แกน % ของ S-Curve อยู่ขวาตลอด -->
		<div
			v-if="curve_lines.length"
			class="cs-axis"
			:style="{
				top: headerHeight + 'px',
				right: scrollbar_width + 'px',
				height: viewport_height - headerHeight - summary_height + 'px',
			}"
		>
			<svg width="40" :height="curve_height">
				<SCurve axis :height="curve_height" />
			</svg>
		</div>
	</div>
</template>

<style scoped>
.cs-timeline {
	position: relative;
	flex: 1 1 auto;
	min-width: 0;
}
.cs-timeline-body {
	height: 100%;
	overflow-x: scroll;
	overflow-y: auto;
}
.cs-header {
	position: sticky;
	top: 0;
	z-index: 2;
	display: block;
	background: var(--subtle-fg);
}
.cs-header-cell {
	fill: var(--subtle-fg);
	stroke: var(--border-color);
}
.cs-header-text {
	fill: var(--text-muted);
	font-size: 11px;
}
.cs-chart {
	display: block;
}
.cs-holiday {
	fill: var(--consbiz-gantt-holiday);
}
.cs-grid-line {
	stroke: var(--border-color);
	stroke-dasharray: 2 3;
}
.cs-row-bg {
	fill: transparent;
}
.cs-row-bg.cs-hover {
	fill: var(--consbiz-gantt-row-hover);
	opacity: 0.6;
}
.cs-row-line {
	stroke: var(--border-color);
}
.cs-bar {
	fill: var(--consbiz-gantt-bar);
	opacity: 0.55;
}
.cs-bar-progress {
	fill: var(--consbiz-gantt-bar);
	pointer-events: none;
}
.cs-draggable .cs-bar {
	cursor: grab;
}
.cs-split-text {
	font-size: 10px;
	font-weight: 600;
	fill: var(--text-color);
	paint-order: stroke;
	stroke: var(--card-bg);
	stroke-width: 3px;
	pointer-events: none;
}
.cs-end-text {
	font-size: 11px;
	fill: var(--text-muted);
	pointer-events: none;
}
.cs-end-text.cs-end-group {
	font-weight: 600;
	fill: var(--text-color);
}
/* กรอบท้ายแถบ: % แผน สีฟ้า | % จริง สีเขียว (สี indicator ของ Frappe) */
.cs-pill text {
	font-size: 10px;
	font-weight: 600;
}
.cs-pill-green rect {
	fill: var(--bg-green);
}
.cs-pill-green text {
	fill: var(--text-on-green);
}
.cs-pill-blue rect {
	fill: var(--bg-blue);
}
.cs-pill-blue text {
	fill: var(--text-on-blue);
}
.cs-divider {
	stroke: var(--card-bg);
	stroke-width: 1.5;
	pointer-events: none;
}
.cs-handle {
	fill: transparent;
	cursor: ew-resize;
}
.cs-baseline-bar {
	fill: var(--consbiz-gantt-baseline);
}
.cs-group-bar rect {
	fill: var(--consbiz-gantt-group);
}
.cs-status-green .cs-bar,
.cs-status-green .cs-bar-progress,
.cs-group-bar.cs-status-green rect {
	fill: var(--consbiz-gantt-done);
}
.cs-status-orange .cs-bar,
.cs-status-orange .cs-bar-progress,
.cs-group-bar.cs-status-orange rect {
	fill: var(--consbiz-gantt-late);
}
.cs-status-red .cs-bar,
.cs-status-red .cs-bar-progress,
.cs-group-bar.cs-status-red rect {
	fill: var(--consbiz-gantt-critical);
}
.cs-today {
	stroke: var(--consbiz-gantt-today);
	stroke-width: 1.5;
}
.cs-today-mark {
	fill: var(--consbiz-gantt-today);
}
.cs-status {
	stroke: var(--consbiz-gantt-status-date);
	stroke-width: 1.5;
	stroke-dasharray: 6 3;
}
.cs-status-mark {
	fill: var(--consbiz-gantt-status-date);
}
.cs-drag-label {
	font-size: 11px;
	font-weight: 600;
	fill: var(--text-color);
	paint-order: stroke;
	stroke: var(--card-bg);
	stroke-width: 3px;
}
.cs-summary {
	position: sticky;
	bottom: 0;
	z-index: 2;
	display: block;
	background: var(--subtle-fg);
}
.cs-summary-cell {
	fill: var(--subtle-fg);
	stroke: var(--border-color);
}
.cs-summary-text {
	fill: var(--text-color);
	font-size: 10px;
}
.cs-axis {
	position: absolute;
	width: 40px;
	overflow: hidden;
	pointer-events: none;
}
</style>

<style>
body.cs-moving {
	cursor: grabbing;
	user-select: none;
}
</style>
