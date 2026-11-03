<script setup>
// เมนู S-Curve (ปุ่มไอคอนบนแถบเครื่องมือ): เลือกเส้นบน Gantt และแถวของตารางสรุปใต้ Gantt
import { computed } from "vue";

const props = defineProps({
	settings: Object,
	curves: Array,
	summaryOptions: Array,
});

// แถวของตารางสรุปจัดกลุ่มตามเส้น (Baseline / แผน / จริง)
const summary_groups = computed(() =>
	props.curves
		.map((curve) => ({
			...curve,
			rows: props.summaryOptions.filter((row) => row.curve === curve.key),
		}))
		.filter((group) => group.rows.length)
);

function toggle_summary_row(key) {
	const keys = props.settings.summary_keys;
	props.settings.summary_keys = keys.includes(key)
		? keys.filter((k) => k !== key)
		: props.summaryOptions.map((r) => r.key).filter((k) => k === key || keys.includes(k));
}
</script>

<template>
	<div class="cs-curves-menu" @click.stop>
		<div class="cs-curves-title">{{ __("เส้นบน Gantt") }}</div>
		<label v-for="curve in curves" :key="curve.key" class="switch-control cs-curves-switch">
			<span class="switch-text">
				<span class="label-area">
					<span class="cs-dot" :style="{ background: curve.color }" />{{ curve.label }}
				</span>
			</span>
			<span class="input-area"><input v-model="settings.curves[curve.key]" type="checkbox" /></span>
			<span class="switch-visual"><span class="switch-thumb" /></span>
		</label>

		<div class="cs-curves-title">{{ __("ตารางสรุปใต้ Gantt") }}</div>
		<label class="switch-control cs-curves-switch">
			<span class="switch-text"><span class="label-area">{{ __("แสดงตารางสรุป") }}</span></span>
			<span class="input-area"><input v-model="settings.show_summary" type="checkbox" /></span>
			<span class="switch-visual"><span class="switch-thumb" /></span>
		</label>
		<template v-for="group in summary_groups" :key="group.key">
			<div class="cs-curves-group">
				<span class="cs-dot" :style="{ background: group.color }" />{{ group.label }}
			</div>
			<label v-for="row in group.rows" :key="row.key" class="cs-curves-check">
				<input
					type="checkbox"
					:checked="settings.summary_keys.includes(row.key)"
					:disabled="!settings.show_summary"
					@change="toggle_summary_row(row.key)"
				/>
				{{ row.label }}
			</label>
		</template>
	</div>
</template>

<style scoped>
.cs-curves-menu {
	width: 260px;
	max-height: 70vh;
	overflow-y: auto;
	padding: 4px 14px 10px;
}
.cs-curves-title {
	margin: 10px 0 2px;
	color: var(--text-muted);
	font-size: var(--text-xs);
	font-weight: 700;
	letter-spacing: 0.04em;
	text-transform: uppercase;
}
.cs-curves-title:first-child {
	margin-top: 4px;
}
.cs-curves-switch {
	width: 100%;
	padding: 5px 0;
	gap: var(--padding-md);
}
.cs-curves-switch .label-area {
	display: flex;
	align-items: center;
	gap: 6px;
	font-size: var(--text-sm);
}
.cs-curves-group {
	display: flex;
	align-items: center;
	gap: 6px;
	margin: 8px 0 2px;
	font-size: var(--text-sm);
	font-weight: 600;
}
.cs-curves-check {
	display: flex;
	align-items: center;
	gap: 8px;
	margin: 0;
	padding: 3px 0 3px 14px;
	font-size: var(--text-sm);
	font-weight: 400;
}
.cs-curves-check input {
	margin: 0;
}
.cs-dot {
	display: inline-block;
	width: 8px;
	height: 8px;
	border-radius: 50%;
}
</style>
