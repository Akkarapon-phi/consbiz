<!-- S-Curve: % แผนสะสม (เส้นประ) เทียบ % จริงสะสม (เส้นทึบสีหมวด) จุด = วันเริ่ม/สิ้นเดือน/วันนี้/วันจบ
     ข้อมูลจาก dashboard.progress_curve ชุดเดียวกับ Tab ภาพรวมของ CM แตะ/ชี้ดูค่าแต่ละจุด -->
<template>
	<div class="ss-curve">
		<div class="ss-curve-head">
			<div class="ss-curve-legend">
				<span class="is-actual"><i></i>จริง</span>
				<span class="is-plan"><i></i>{{ basis === "Baseline" ? "แผน (Baseline)" : "แผน" }}</span>
			</div>
			<button type="button" class="ss-link" @click="table = !table">
				{{ table ? "ดูกราฟ" : "ดูตาราง" }}
			</button>
		</div>

		<div v-if="!table" ref="box" class="ss-curve-plot" @pointerleave="hover = null">
			<svg
				v-if="width"
				:width="width"
				:height="HEIGHT"
				role="img"
				:aria-label="`S-Curve จริง ${fmt(last_actual?.actual)}% แผน ${fmt(last_actual?.plan)}%`"
				@pointermove="move"
				@pointerdown="move"
			>
				<defs>
					<linearGradient :id="`${uid}-fill`" x1="0" y1="0" x2="0" y2="1">
						<stop offset="0%" stop-color="var(--ss-brand)" stop-opacity="0.22" />
						<stop offset="100%" stop-color="var(--ss-brand)" stop-opacity="0" />
					</linearGradient>
				</defs>
				<!-- เส้นตาราง 0-100% -->
				<g class="ss-curve-grid">
					<g v-for="v in [0, 25, 50, 75, 100]" :key="v">
						<line :x1="PAD.l" :x2="width - PAD.r" :y1="y(v)" :y2="y(v)" />
						<text :x="PAD.l - 8" :y="y(v) + 4" text-anchor="end">{{ v }}%</text>
					</g>
					<text v-for="t in x_ticks" :key="t.i" :x="x(t.i)" :y="HEIGHT - 6" text-anchor="middle">
						{{ t.label }}
					</text>
				</g>
				<!-- วันนี้ -->
				<line
					v-if="today_index >= 0"
					class="ss-curve-today"
					:x1="x(today_index)"
					:x2="x(today_index)"
					:y1="PAD.t"
					:y2="y(0)"
				/>
				<path :d="area" :fill="`url(#${uid}-fill)`" />
				<path class="ss-curve-plan" :d="plan_path" />
				<path class="ss-curve-actual" :d="actual_path" />
				<circle
					v-if="last_actual"
					class="ss-curve-end"
					:cx="x(last_index)"
					:cy="y(last_actual.actual)"
					r="5"
				/>
				<!-- crosshair -->
				<g v-if="hover !== null" class="ss-curve-cross">
					<line :x1="x(hover)" :x2="x(hover)" :y1="PAD.t" :y2="y(0)" />
					<circle class="is-plan" :cx="x(hover)" :cy="y(points[hover].plan)" r="4" />
					<circle
						v-if="points[hover].actual !== null"
						class="is-actual"
						:cx="x(hover)"
						:cy="y(points[hover].actual)"
						r="5"
					/>
				</g>
			</svg>
			<div
				v-if="hover !== null"
				class="ss-curve-tip"
				:style="{ left: `${Math.min(Math.max(x(hover), 80), width - 80)}px` }"
			>
				<b>{{ thai_date(points[hover].date, { year: true }) }}</b>
				<span v-if="points[hover].actual !== null"
					><i class="is-actual"></i>จริง {{ fmt(points[hover].actual) }}%</span
				>
				<span><i class="is-plan"></i>แผน {{ fmt(points[hover].plan) }}%</span>
				<span v-if="points[hover].actual !== null" class="ss-curve-tip-diff">
					{{ diff_text(points[hover]) }}
				</span>
			</div>
		</div>

		<div v-else class="ss-curve-table">
			<table>
				<thead>
					<tr>
						<th>วันที่</th>
						<th>แผน</th>
						<th>จริง</th>
					</tr>
				</thead>
				<tbody>
					<tr v-for="p in points" :key="p.date">
						<td>{{ thai_date(p.date, { year: true }) }}</td>
						<td>{{ fmt(p.plan) }}%</td>
						<td>{{ p.actual === null ? "–" : `${fmt(p.actual)}%` }}</td>
					</tr>
				</tbody>
			</table>
		</div>
	</div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { thai_date } from "../api.js";

const props = defineProps({
	points: { type: Array, default: () => [] }, // [{date, plan, actual|null}]
	basis: String,
});

const HEIGHT = 210;
const PAD = { t: 12, r: 14, b: 26, l: 42 };
const uid = `curve-${Math.random().toString(36).slice(2, 8)}`;
const MONTHS = [
	"ม.ค.",
	"ก.พ.",
	"มี.ค.",
	"เม.ย.",
	"พ.ค.",
	"มิ.ย.",
	"ก.ค.",
	"ส.ค.",
	"ก.ย.",
	"ต.ค.",
	"พ.ย.",
	"ธ.ค.",
];

const box = ref(null);
const width = ref(0);
const hover = ref(null);
const table = ref(false);

const fmt = (v) => (Number(v) || 0).toLocaleString("th-TH", { maximumFractionDigits: 1 });
// แกน x ตามลำดับจุด (ระยะห่างเท่ากัน: จุดเป็นสิ้นเดือน อ่านง่ายกว่าตามวันจริงบนจอมือถือ)
const x = (i) =>
	PAD.l + (props.points.length > 1 ? (i / (props.points.length - 1)) * (width.value - PAD.l - PAD.r) : 0);
const y = (v) => PAD.t + (1 - Math.max(0, Math.min(100, Number(v) || 0)) / 100) * (HEIGHT - PAD.t - PAD.b);

const line = (key) =>
	props.points
		.map((p, i) => (p[key] === null || p[key] === undefined ? null : `${x(i)},${y(p[key])}`))
		.filter(Boolean)
		.map((pt, i) => `${i ? "L" : "M"}${pt}`)
		.join("");
const plan_path = computed(() => width.value && line("plan"));
const actual_path = computed(() => width.value && line("actual"));
const last_index = computed(() => {
	for (let i = props.points.length - 1; i >= 0; i--) if (props.points[i].actual !== null) return i;
	return -1;
});
const last_actual = computed(() => props.points[last_index.value]);
const today_index = computed(() => last_index.value);
const area = computed(() => {
	if (!width.value || last_index.value < 0) return "";
	return `${actual_path.value}L${x(last_index.value)},${y(0)}L${x(0)},${y(0)}Z`;
});

// ป้ายเดือนไม่ให้ชนกัน: เว้นตามความกว้าง
const x_ticks = computed(() => {
	const n = props.points.length;
	if (!n || !width.value) return [];
	const room = Math.max(1, Math.floor((width.value - PAD.l - PAD.r) / 52));
	const step = Math.max(1, Math.ceil(n / room));
	const ticks = props.points.map((p, i) => ({ i, date: String(p.date) })).filter((t) => t.i % step === 0);
	// จุดสุดท้าย (วันจบ) ใส่เมื่อห่างจากป้ายก่อนหน้าพอ
	if (ticks[ticks.length - 1].i !== n - 1 && n - 1 - ticks[ticks.length - 1].i >= step * 0.7) {
		ticks.push({ i: n - 1, date: String(props.points[n - 1].date) });
	}
	return ticks.map((t) => {
		const [yy, mm] = t.date.split("-").map(Number);
		return { i: t.i, label: `${MONTHS[mm - 1]}${String((yy + 543) % 100)}` };
	});
});

function move(event) {
	const rect = event.currentTarget.getBoundingClientRect();
	const px = event.clientX - rect.left;
	const n = props.points.length;
	if (n < 2) return;
	const i = Math.round(((px - PAD.l) / (width.value - PAD.l - PAD.r)) * (n - 1));
	hover.value = Math.max(0, Math.min(n - 1, i));
}

function diff_text(p) {
	const d = p.actual - p.plan;
	if (Math.abs(d) < 0.05) return "ตามแผน";
	return `${d > 0 ? "เร็วกว่า" : "ช้ากว่า"}แผน ${fmt(Math.abs(d))}%`;
}

let observer = null;
function observe() {
	observer?.disconnect();
	if (!box.value) return;
	width.value = box.value.clientWidth;
	observer = new ResizeObserver(([entry]) => (width.value = Math.round(entry.contentRect.width)));
	observer.observe(box.value);
}
onMounted(observe);
watch(table, async (value) => {
	if (!value) {
		await nextTick();
		observe();
	}
});
onBeforeUnmount(() => observer?.disconnect());
</script>
