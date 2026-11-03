<script setup>
// % Baseline / แผน / จริง ณ วันที่เลือกดู + ส่วนต่าง (ใช้ใน Toolbar และ ViewBar)
// เทียบ % จริงกับ Baseline ยังไม่ตั้ง Baseline เทียบกับแผนปัจจุบัน (ตรงกับ target_progress ฝั่ง Python)
// ต่างกันไม่ถึง 0.005% ถือว่าตามแผน สีใช้ indicator มาตรฐานของ Frappe ตัวเลขกว้างคงที่ไม่ให้แถบขยับ
import { computed } from "vue";

const props = defineProps({
	curves: Array, // [{ key, label, color }]
	readout: Object, // { baseline, plan, actual } (null = ไม่มีค่า)
});

const variance = computed(() => {
	const { baseline, plan, actual } = props.readout;
	const target = baseline ?? plan;
	if (target === null || actual === null) return null;
	const diff = actual - target;
	const label = baseline !== null ? "Baseline" : __("แผน");
	if (Math.abs(diff) < 0.005) return { short: "±0%", text: __("ตาม{0}", [label]), color: "gray" };
	return diff > 0
		? { short: "▲ " + percent(diff), text: __("เร็วกว่า{0} {1}", [label, percent(diff)]), color: "green" }
		: { short: "▼ " + percent(-diff), text: __("ช้ากว่า{0} {1}", [label, percent(-diff)]), color: "red" };
});

const items = computed(() => props.curves.filter((curve) => props.readout[curve.key] !== null));

const percent = (value) =>
	value === null || value === undefined ? "-" : format_number(value, null, 2) + "%";
</script>

<template>
	<div v-if="items.length" class="cs-readout" :title="__('ค่า ณ วันที่เลือกดู')">
		<span v-for="curve in items" :key="curve.key" class="cs-readout-item" :class="'cs-readout-' + curve.key">
			<span class="cs-dot" :style="{ background: curve.color }" />
			<span class="cs-readout-label">{{ curve.label }}</span>
			<span class="cs-readout-value">{{ percent(readout[curve.key]) }}</span>
		</span>
		<span
			v-if="variance"
			class="indicator-pill no-indicator-dot cs-variance"
			:class="variance.color"
			:title="variance.text"
		>
			{{ variance.short }}
		</span>
	</div>
</template>

<style scoped>
.cs-readout {
	display: inline-flex;
	align-items: center;
	gap: 12px;
	height: 30px;
	padding: 0 4px 0 10px;
	border: 1px solid var(--border-color);
	border-radius: var(--radius);
	font-size: var(--text-sm);
	white-space: nowrap;
}
.cs-readout-item {
	display: inline-flex;
	align-items: center;
	gap: 5px;
}
.cs-readout-label {
	color: var(--text-muted);
}
.cs-readout-value {
	min-width: 4.2em;
	color: var(--text-color);
	font-weight: 600;
	font-variant-numeric: tabular-nums;
	text-align: right;
}
.cs-variance {
	min-width: 5.5em;
	justify-content: center;
	font-variant-numeric: tabular-nums;
}
.cs-dot {
	display: inline-block;
	flex: none;
	width: 8px;
	height: 8px;
	border-radius: 50%;
}
@media (pointer: coarse) {
	.cs-readout {
		height: 36px;
	}
}
/* พื้นที่แคบ (container ของแถบที่ใช้): ซ่อน % Baseline (ส่วนต่างยังเทียบกับ Baseline) */
@container (max-width: 860px) {
	.cs-readout-baseline {
		display: none;
	}
}
@container (max-width: 640px) {
	.cs-readout {
		width: 100%;
		justify-content: space-between;
	}
	.cs-readout-baseline {
		display: inline-flex;
	}
}
@container (max-width: 400px) {
	.cs-readout-baseline {
		display: none;
	}
}
</style>
