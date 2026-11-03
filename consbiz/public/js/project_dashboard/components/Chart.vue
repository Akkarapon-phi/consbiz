<script setup>
// ห่อ frappe.Chart ให้วาดใหม่เมื่อข้อมูลเปลี่ยน
import { onBeforeUnmount, onMounted, ref, watch } from "vue";

const props = defineProps({
	data: { type: Object, required: true }, // { labels, datasets }
	type: { type: String, default: "line" },
	colors: Array,
	height: { type: Number, default: 240 },
	format: Function, // แปลงค่าใน tooltip
	fill: Boolean, // แรเงาใต้เส้น
});

const el = ref(null);
let chart = null;

function draw() {
	if (!el.value) return;
	el.value.innerHTML = "";
	if (!props.data.labels.length) return;
	chart = new frappe.Chart(el.value, {
		data: props.data,
		type: props.type,
		colors: props.colors,
		height: props.height,
		axisOptions: { xIsSeries: 1, xAxisMode: "tick", yAxisMode: "span", shortenYAxisNumbers: 1 },
		lineOptions: { regionFill: props.fill ? 1 : 0, hideDots: 1, spline: 1 },
		barOptions: { spaceRatio: 0.4 },
		tooltipOptions: props.format ? { formatTooltipY: props.format } : {},
	});
}

onMounted(draw);
watch(() => props.data, draw, { deep: true });
onBeforeUnmount(() => {
	chart = null;
});
</script>

<template>
	<div ref="el" />
</template>
