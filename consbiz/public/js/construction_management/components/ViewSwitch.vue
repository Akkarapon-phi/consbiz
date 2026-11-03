<script setup>
// สลับมุมมองของหน้า Gantt: แผนงาน (ตาราง WBS + Timeline) | ทรัพยากร (ResourceGantt) ใช้ใน Toolbar และ ViewBar
// settings เป็น reactive ของ App แก้ settings.view ตรงได้ (บันทึกลง User Settings พร้อมค่าอื่น)
defineProps({ settings: Object });

const VIEWS = [
	{ key: "tasks", label: __("แผนงาน"), icon: "chart-gantt", title: __("Gantt ของงานตาม WBS") },
	{
		key: "resources",
		label: __("ทรัพยากร"),
		icon: "users",
		title: __("Gantt ของแรงงาน เครื่องจักร และวัสดุ: ใช้อะไร เมื่อไหร่ ต้องสั่ง/จองเมื่อไหร่"),
	},
];
const icon = (name) => frappe.utils.icon(name, "sm");
</script>

<template>
	<div class="cs-segment" role="group" :aria-label="__('มุมมอง')">
		<button
			v-for="view in VIEWS"
			:key="view.key"
			type="button"
			class="cs-seg-btn cs-seg-text cs-view-btn"
			:class="{ active: settings.view === view.key }"
			:aria-pressed="settings.view === view.key"
			:title="view.title"
			@click="settings.view = view.key"
		>
			<span class="cs-view-icon" v-html="icon(view.icon)" />
			<span class="cs-view-label">{{ view.label }}</span>
		</button>
	</div>
</template>

<style scoped>
.cs-view-btn {
	display: inline-flex;
	align-items: center;
	gap: 4px;
}
.cs-view-icon {
	display: inline-flex;
}
@container (max-width: 1100px) {
	.cs-view-label {
		display: none;
	}
}
</style>
