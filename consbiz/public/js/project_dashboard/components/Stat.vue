<script setup>
// การ์ดตัวเลขเดียว: ไอคอนในกรอบสีอ่อนตามสถานะ กดแล้วไปหน้ารายการ/รายงาน (route) ได้
defineProps({
	label: String,
	value: [String, Number],
	note: String,
	icon: String, // ชื่อไอคอน lucide ของ Frappe
	color: { type: String, default: "gray" }, // green / orange / red / blue / gray
	route: Function,
});
</script>

<template>
	<component
		:is="route ? 'button' : 'div'"
		type="button"
		class="pd-stat"
		:class="[`pd-tone-${color}`, { 'pd-stat-link': route }]"
		@click="route && route()"
	>
		<span class="pd-stat-icon" v-html="frappe.utils.icon(icon, 'md')" />
		<span class="pd-stat-body">
			<span class="pd-stat-label">{{ label }}</span>
			<span class="pd-stat-value">{{ value }}</span>
			<span v-if="note" class="pd-stat-note">{{ note }}</span>
		</span>
	</component>
</template>

<style scoped>
.pd-stat {
	display: flex;
	align-items: flex-start;
	gap: 14px;
	padding: 18px;
	border: 1px solid var(--pd-border);
	border-radius: var(--pd-radius);
	background: var(--card-bg);
	box-shadow: var(--pd-shadow);
	text-align: left;
	color: var(--text-color);
	transition:
		transform 0.15s ease,
		box-shadow 0.15s ease;
}
.pd-stat-link {
	cursor: pointer;
}
.pd-stat-link:hover {
	transform: translateY(-2px);
	box-shadow: var(--pd-shadow-hover);
}
.pd-stat-icon {
	display: grid;
	flex: none;
	place-items: center;
	width: 40px;
	height: 40px;
	border-radius: 12px;
	background: var(--pd-tone-bg);
	color: var(--pd-tone-fg);
}
.pd-stat-icon :deep(svg) {
	stroke: currentColor;
}
.pd-stat-body {
	display: flex;
	flex-direction: column;
	gap: 2px;
	min-width: 0;
}
.pd-stat-label {
	color: var(--text-muted);
	font-size: var(--text-sm);
}
.pd-stat-value {
	color: var(--heading-color);
	font-size: 22px;
	font-weight: 700;
	line-height: 1.25;
	font-variant-numeric: tabular-nums;
}
.pd-stat-note {
	color: var(--text-muted);
	font-size: var(--text-xs);
}
</style>
