<script setup>
// S-Curve ของ Tab ภาพรวม (SVG เอง เพราะ frappe.Chart แทนค่าว่างด้วย 0 เส้นจริงจะตกลงศูนย์หลังวันที่ดู)
// แกน x เป็นเวลาจริง (จุดห่างไม่เท่ากันได้) เส้นแผน/Baseline ยาวถึงวันจบของแผน (100%) เส้นจริงหยุดที่วันที่ดู
// rows: [{ date, plan, actual (null = หลังวันที่ดู) }] จาก dashboard.progress_curve (%)
// หรือเป็นเงินใน Tab การเงิน: max = ค่าสูงสุดของแกน, format = รูปแบบตัวเลข (ป้ายแกนใช้ tick_format)
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { date, percent } from "../format";

const props = defineProps({
	rows: Array,
	statusDate: String,
	planLabel: String,
	actualLabel: { type: String, default: () => __("จริง") },
	height: { type: Number, default: 290 },
	max: { type: Number, default: 100 },
	format: { type: Function, default: (v) => percent(v) },
	tickFormat: { type: Function, default: (v) => `${v}%` },
});

const PAD = { top: 26, right: 16, bottom: 28, left: 52 };
const DAY = 86400000;

const el = ref(null);
const width = ref(600);
const hover = ref(null);

const to_ms = (value) => frappe.datetime.str_to_obj(value).getTime();
const points = computed(() =>
	(props.rows || []).map((row) => ({ ...row, t: to_ms(row.date) }))
);
const domain = computed(() => {
	const list = points.value;
	if (!list.length) return null;
	const first = list[0].t;
	const last = list.at(-1).t;
	return { first, last: last > first ? last : first + DAY };
});

const inner_w = computed(() => Math.max(width.value - PAD.left - PAD.right, 10));
const inner_h = computed(() => props.height - PAD.top - PAD.bottom);
const x = (t) => PAD.left + ((t - domain.value.first) / (domain.value.last - domain.value.first)) * inner_w.value;
const top = computed(() => props.max || 1);
const y = (v) => PAD.top + inner_h.value * (1 - Math.min(Math.max(v, 0), top.value) / top.value);

function path(key) {
	const list = points.value.filter((p) => p[key] !== null && p[key] !== undefined);
	return list.length ? list.map((p, i) => `${i ? "L" : "M"}${x(p.t).toFixed(1)},${y(p[key]).toFixed(1)}`).join(" ") : "";
}
function area(key) {
	const list = points.value.filter((p) => p[key] !== null && p[key] !== undefined);
	if (list.length < 2) return "";
	const base = y(0).toFixed(1);
	return `${path(key)} L${x(list.at(-1).t).toFixed(1)},${base} L${x(list[0].t).toFixed(1)},${base} Z`;
}

const plan_path = computed(() => (domain.value ? path("plan") : ""));
const plan_area = computed(() => (domain.value ? area("plan") : ""));
const actual_path = computed(() => (domain.value ? path("actual") : ""));
const actual_area = computed(() => (domain.value ? area("actual") : ""));

const y_ticks = computed(() => [0, 0.25, 0.5, 0.75, 1].map((f) => f * top.value));

// ป้ายเดือนบนแกน x เว้นระยะไม่ให้ชนกัน (อย่างน้อย ~64px ต่อป้าย)
const month_fmt = new Intl.DateTimeFormat(frappe.boot.lang === "th" ? "th-TH" : undefined, {
	month: "short",
	year: "2-digit",
});
const x_ticks = computed(() => {
	if (!domain.value) return [];
	const months = [];
	const cursor = new Date(domain.value.first);
	cursor.setDate(1);
	if (cursor.getTime() < domain.value.first) cursor.setMonth(cursor.getMonth() + 1);
	while (cursor.getTime() <= domain.value.last) {
		months.push(cursor.getTime());
		cursor.setMonth(cursor.getMonth() + 1);
	}
	const step = Math.max(1, Math.ceil((months.length * 64) / inner_w.value));
	return months.filter((_, i) => i % step === 0).map((t) => ({ t, x: x(t), label: month_fmt.format(new Date(t)) }));
});

const status_x = computed(() => {
	if (!domain.value || !props.statusDate) return null;
	const t = to_ms(props.statusDate);
	return t >= domain.value.first && t <= domain.value.last ? x(t) : null;
});

function on_move(event) {
	if (!domain.value || !points.value.length) return;
	const box = el.value.getBoundingClientRect();
	const px = event.clientX - box.left;
	let best = points.value[0];
	for (const p of points.value) if (Math.abs(x(p.t) - px) < Math.abs(x(best.t) - px)) best = p;
	hover.value = best;
}

const tooltip_style = computed(() => {
	if (!hover.value) return {};
	const left = x(hover.value.t);
	return left > width.value / 2
		? { right: `${width.value - left + 10}px`, top: `${PAD.top}px` }
		: { left: `${left + 10}px`, top: `${PAD.top}px` };
});

let observer;
onMounted(() => {
	observer = new ResizeObserver(([entry]) => (width.value = entry.contentRect.width || 600));
	observer.observe(el.value);
});
onBeforeUnmount(() => observer?.disconnect());
</script>

<template>
	<div ref="el" class="pc" :style="{ height: height + 'px' }" @mousemove="on_move" @mouseleave="hover = null">
		<svg v-if="domain" :width="width" :height="height" class="pc-svg">
			<g class="pc-grid">
				<template v-for="tick in y_ticks" :key="'y' + tick">
					<line :x1="PAD.left" :x2="width - PAD.right" :y1="y(tick)" :y2="y(tick)" />
					<text :x="PAD.left - 6" :y="y(tick) + 4" text-anchor="end">{{ tickFormat(tick) }}</text>
				</template>
				<text v-for="tick in x_ticks" :key="'x' + tick.t" :x="tick.x" :y="height - 8" text-anchor="middle">
					{{ tick.label }}
				</text>
			</g>
			<path :d="plan_area" class="pc-area pc-plan-area" />
			<path :d="actual_area" class="pc-area pc-actual-area" />
			<path :d="plan_path" class="pc-line pc-plan" />
			<path :d="actual_path" class="pc-line pc-actual" />
			<g v-if="status_x !== null" class="pc-status">
				<line :x1="status_x" :x2="status_x" :y1="PAD.top" :y2="PAD.top + inner_h" />
				<text :x="status_x + 4" :y="PAD.top + 10">{{ __("วันที่ดู") }}</text>
			</g>
			<g v-if="hover" class="pc-hover">
				<line :x1="x(hover.t)" :x2="x(hover.t)" :y1="PAD.top" :y2="PAD.top + inner_h" />
				<circle :cx="x(hover.t)" :cy="y(hover.plan)" r="4" class="pc-dot-plan" />
				<circle
					v-if="hover.actual !== null && hover.actual !== undefined"
					:cx="x(hover.t)"
					:cy="y(hover.actual)"
					r="4"
					class="pc-dot-actual"
				/>
			</g>
		</svg>
		<div v-if="hover" class="pc-tip" :style="tooltip_style">
			<div class="pc-tip-date">{{ date(hover.date) }}</div>
			<div><i class="pc-key pc-key-plan" />{{ planLabel }} <strong>{{ format(hover.plan) }}</strong></div>
			<div v-if="hover.actual !== null && hover.actual !== undefined">
				<i class="pc-key pc-key-actual" />{{ actualLabel }} <strong>{{ format(hover.actual) }}</strong>
			</div>
		</div>
		<div class="pc-legend">
			<span><i class="pc-key pc-key-plan" />{{ planLabel }}</span>
			<span><i class="pc-key pc-key-actual" />{{ actualLabel }}</span>
		</div>
	</div>
</template>

<style scoped>
.pc {
	position: relative;
	width: 100%;
}
.pc-svg {
	display: block;
}
.pc-grid line {
	stroke: color-mix(in srgb, var(--border-color) 70%, transparent);
}
.pc-grid text {
	fill: var(--text-muted);
	font-size: 11px;
}
.pc-line {
	fill: none;
	stroke-width: 2;
	stroke-linejoin: round;
}
.pc-plan {
	stroke: var(--consbiz-gantt-plan);
}
.pc-actual {
	stroke: var(--consbiz-gantt-actual);
	stroke-width: 2.5;
}
.pc-area {
	stroke: none;
}
.pc-plan-area {
	fill: var(--consbiz-gantt-plan);
	opacity: 0.08;
}
.pc-actual-area {
	fill: var(--consbiz-gantt-actual);
	opacity: 0.14;
}
.pc-status line {
	stroke: var(--consbiz-gantt-status-date);
	stroke-width: 1.5;
	stroke-dasharray: 5 3;
}
.pc-status text {
	fill: var(--consbiz-gantt-status-date);
	font-size: 10px;
	font-weight: 600;
}
.pc-hover line {
	stroke: var(--gray-400);
}
.pc-hover circle {
	stroke: var(--card-bg);
	stroke-width: 2;
}
.pc-dot-plan {
	fill: var(--consbiz-gantt-plan);
}
.pc-dot-actual {
	fill: var(--consbiz-gantt-actual);
}
.pc-tip {
	position: absolute;
	z-index: 2;
	padding: 6px 10px;
	border: 1px solid var(--border-color);
	border-radius: var(--border-radius-md, 8px);
	background: var(--card-bg);
	box-shadow: var(--shadow-sm);
	font-size: var(--text-xs);
	white-space: nowrap;
	pointer-events: none;
}
.pc-tip-date {
	margin-bottom: 2px;
	color: var(--text-muted);
}
.pc-legend {
	position: absolute;
	top: 2px;
	right: 16px;
	display: flex;
	gap: 12px;
	color: var(--text-muted);
	font-size: var(--text-xs);
}
.pc-key {
	display: inline-block;
	width: 10px;
	height: 3px;
	margin-right: 4px;
	border-radius: 2px;
	vertical-align: middle;
}
.pc-key-plan {
	background: var(--consbiz-gantt-plan);
}
.pc-key-actual {
	background: var(--consbiz-gantt-actual);
}
</style>
