<!-- กราฟเส้นมูลค่าตามเวลา แกนเดียว points = [{ date, <key>: ค่าหรือ null }], series = [{ key, label, slot, dashed }]
     slot = สีตามชนิดข้อมูล (1 แผน/PV, 2 จริง/EV, 3 AC) ตารางตัวเลขอยู่ใต้กราฟในหน้าที่ใช้ -->
<template>
	<div class="ss-money-chart">
		<div class="ss-curve-legend">
			<span v-for="s in series" :key="s.key"><i :class="`is-slot-${s.slot}`" :style="s.dashed ? 'border-top-style: dashed' : ''"></i>{{ s.label }}</span>
		</div>
		<div ref="box" class="ss-curve-plot" @pointerleave="hover = null">
			<svg v-if="width && points.length > 1" :width="width" :height="HEIGHT" role="img" :aria-label="aria" @pointermove="move" @pointerdown="move">
				<g class="ss-curve-grid">
					<g v-for="v in y_ticks" :key="v">
						<line :x1="PAD.l" :x2="width - PAD.r" :y1="y(v)" :y2="y(v)" />
						<text :x="PAD.l - 8" :y="y(v) + 4" text-anchor="end">{{ short(v) }}</text>
					</g>
					<text v-for="t in x_ticks" :key="t.date" :x="x(t.date)" :y="HEIGHT - 6" text-anchor="middle">{{ t.label }}</text>
				</g>
				<line v-if="mark_date" class="ss-curve-today" :x1="x(mark_date)" :x2="x(mark_date)" :y1="PAD.t" :y2="y(y_min)" />
				<path
					v-for="s in series"
					:key="s.key"
					class="ss-money-line"
					:class="`is-slot-${s.slot}`"
					:stroke-dasharray="s.dashed ? '6 4' : null"
					:d="path(s.key)"
				/>
				<template v-for="label in end_labels" :key="label.key">
					<circle class="ss-money-end" :class="`is-slot-${label.slot}`" :cx="label.x" :cy="label.y" r="4" />
					<text class="ss-money-label" :x="label.x + label.dx" :y="label.text_y" :text-anchor="label.anchor">{{ label.text }}</text>
				</template>
				<g v-if="hover !== null" class="ss-curve-cross">
					<line :x1="x(points[hover].date)" :x2="x(points[hover].date)" :y1="PAD.t" :y2="y(y_min)" />
					<template v-for="s in series" :key="s.key">
						<circle v-if="has(points[hover][s.key])" class="ss-money-end" :class="`is-slot-${s.slot}`" :cx="x(points[hover].date)" :cy="y(points[hover][s.key])" r="4" />
					</template>
				</g>
			</svg>
			<div v-if="hover !== null" class="ss-curve-tip" :style="{ left: `${Math.min(Math.max(x(points[hover].date), 90), width - 90)}px` }">
				<b>{{ thai_date(points[hover].date, { year: true }) }}</b>
				<template v-for="s in series" :key="s.key">
					<span v-if="has(points[hover][s.key])"><i :class="`is-slot-${s.slot}`"></i>{{ s.label }} {{ money(points[hover][s.key]) }}</span>
				</template>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { money, thai_date } from "../../../shared/api.js";
import { MONTHS } from "../pm/planner/time_axis.js";

const props = defineProps({
	points: { type: Array, default: () => [] },
	series: { type: Array, default: () => [] },
	mark_date: String, // เส้นตั้งของวันที่ดู
	aria: String,
});

const HEIGHT = 260;
const PAD = { t: 18, r: 24, b: 26, l: 62 };
const NICE_STEPS = [1, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10];

const box = ref(null);
const width = ref(0);
const hover = ref(null);

const has = (value) => value !== null && value !== undefined;
const short = (value) => money(value, { short: true });
const time = (date) => Date.parse(String(date).slice(0, 10));

const first = computed(() => time(props.points[0].date));
const last = computed(() => time(props.points[props.points.length - 1].date));
const x = (date) => PAD.l + ((time(date) - first.value) / (last.value - first.value || 1)) * (width.value - PAD.l - PAD.r);

const values = computed(() => props.points.flatMap((p) => props.series.map((s) => p[s.key]).filter(has)));
const y_min = computed(() => Math.min(0, ...values.value));
// ปัดขึ้นให้ป้ายแกนเป็นเลขกลมๆ
const step = computed(() => {
	const span = Math.max(...values.value, 1) - y_min.value;
	const base = 10 ** Math.floor(Math.log10(span / 4 || 1));
	return (NICE_STEPS.find((nice) => nice * base >= span / 4) || 10) * base;
});
const y_max = computed(() => y_min.value + step.value * 4);
const y = (value) => PAD.t + (1 - (value - y_min.value) / (y_max.value - y_min.value)) * (HEIGHT - PAD.t - PAD.b);
const y_ticks = computed(() => Array.from({ length: 5 }, (_, i) => y_min.value + step.value * i));

const path = (key) =>
	props.points
		.filter((p) => has(p[key]))
		.map((p, i) => `${i ? "L" : "M"}${x(p.date)},${y(p[key])}`)
		.join("");

// ป้ายเดือนไม่ให้ชนกัน: เว้นตามความกว้าง
const x_ticks = computed(() => {
	// ป้ายวางที่ต้นเดือนเสมอ จุดข้อมูลมีทั้งสิ้นเดือนและวันที่ดูซึ่งอยู่ชิดกันได้
	const [start_year, start_month] = String(props.points[0].date).split("-").map(Number);
	const end = props.points[props.points.length - 1].date;
	const months = [];
	for (let index = start_year * 12 + start_month - 1; ; index++) {
		const year = Math.floor(index / 12);
		const month = (index % 12) + 1;
		const date = `${year}-${String(month).padStart(2, "0")}-01`;
		if (date > String(end)) break;
		months.push({ date, label: `${MONTHS[month - 1]}${(year + 543) % 100}` });
	}
	const room = Math.max(1, Math.floor((width.value - PAD.l - PAD.r) / 56));
	const every = Math.max(1, Math.ceil(months.length / room));
	return months.filter((_, i) => i % every === 0);
});

// ป้ายชื่อที่ปลายเส้น: เส้นที่จบใกล้กันดันป้ายให้ห่างกัน
const end_labels = computed(() => {
	const labels = props.series
		.map((s) => {
			const end = [...props.points].reverse().find((p) => has(p[s.key]));
			if (!end) return null;
			const px = x(end.date);
			const near_right = px > width.value - PAD.r - 56;
			return {
				key: s.key,
				slot: s.slot,
				text: s.label,
				x: px,
				y: y(end[s.key]),
				text_y: y(end[s.key]) - 9,
				dx: near_right ? -6 : 6,
				anchor: near_right ? "end" : "start",
			};
		})
		.filter(Boolean)
		.sort((a, b) => a.text_y - b.text_y);
	labels.forEach((label, i) => {
		const before = labels[i - 1];
		if (before && Math.abs(before.x - label.x) < 72 && label.text_y - before.text_y < 13) label.text_y = before.text_y + 13;
		label.text_y = Math.max(label.text_y, 11);
	});
	return labels;
});

function move(event) {
	const px = event.clientX - event.currentTarget.getBoundingClientRect().left;
	let nearest = 0;
	props.points.forEach((p, i) => {
		if (Math.abs(x(p.date) - px) < Math.abs(x(props.points[nearest].date) - px)) nearest = i;
	});
	hover.value = nearest;
}

let observer = null;
onMounted(() => {
	width.value = Math.round(box.value.clientWidth);
	observer = new ResizeObserver(([entry]) => (width.value = Math.round(entry.contentRect.width)));
	observer.observe(box.value);
});
onBeforeUnmount(() => observer?.disconnect());
</script>
