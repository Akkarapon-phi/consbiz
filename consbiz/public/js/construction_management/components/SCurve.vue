<script setup>
// ส่วนของ S-Curve ใน SVG ของ Timeline มี 3 แบบ
// - grid: เส้นประแนวนอนที่ 0/25/50/75/100%
// - axis: ตัวเลข % สำหรับแกนขวา
// - ปกติ: เส้นสะสม 1 เส้น (points: [{ x, value, day }] จาก Timeline)
import { computed } from "vue";
import { day_to_date, smooth_path } from "../schedule";

const props = defineProps({
	points: { type: Array, default: () => [] },
	color: String,
	label: String,
	height: Number,
	axis: Boolean,
	grid: Boolean,
});

const MARGIN = 10;
const TICKS = [0, 25, 50, 75, 100];

const y = (value) => MARGIN + (1 - value / 100) * (props.height - 2 * MARGIN);

const path = computed(() => smooth_path(props.points.map((p) => [p.x, y(p.value)])));

function title(point) {
	const date = frappe.datetime.str_to_user(day_to_date(point.day).toISOString().slice(0, 10));
	return `${props.label} ${date}: ${format_number(point.value, null, 2)}%`;
}
</script>

<template>
	<g v-if="axis" class="cs-scurve-axis">
		<g v-for="tick in TICKS" :key="tick">
			<line x1="34" x2="40" :y1="y(tick)" :y2="y(tick)" />
			<text x="32" :y="y(tick) + 4" text-anchor="end">{{ tick }}%</text>
		</g>
	</g>
	<g v-else-if="grid">
		<line
			v-for="tick in TICKS"
			:key="tick"
			x1="0"
			x2="100%"
			:y1="y(tick)"
			:y2="y(tick)"
			class="cs-scurve-tick"
		/>
	</g>
	<g v-else class="cs-scurve" :style="{ '--curve-color': color }">
		<path :d="path" />
		<circle v-for="point in points" :key="point.day" :cx="point.x" :cy="y(point.value)" r="3">
			<title>{{ title(point) }}</title>
		</circle>
	</g>
</template>

<style scoped>
.cs-scurve path {
	fill: none;
	stroke: var(--curve-color);
	stroke-width: 2;
	pointer-events: none;
}
.cs-scurve circle {
	fill: var(--card-bg);
	stroke: var(--curve-color);
	stroke-width: 2;
}
.cs-scurve-tick {
	stroke: var(--text-muted);
	stroke-opacity: 0.25;
	stroke-dasharray: 4 4;
	pointer-events: none;
}
.cs-scurve-axis text {
	fill: var(--text-muted);
	font-size: 10px;
	font-weight: 600;
	paint-order: stroke;
	stroke: var(--card-bg);
	stroke-width: 3px;
}
.cs-scurve-axis line {
	stroke: var(--text-muted);
}
</style>
