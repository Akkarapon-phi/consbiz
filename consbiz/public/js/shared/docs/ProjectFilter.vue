<!-- ตัวกรองโครงการของแอปออฟฟิศ (app.project_filter): ปุ่มเปิดหน้าเลือกโครงการ (ใน AppShell) ว่าง = ทุกโครงการ
     แอปหน้างานใช้ ScopeSwitch / ตัวเลือกขอบเขต (โครงการที่ทำงานอยู่ / ทุกโครงการ) แทน -->
<template>
	<span class="ss-project-filter" :class="{ 'is-active': state.project }">
		<button
			type="button"
			class="ss-tool"
			:title="state.project ? `โครงการ: ${name}` : 'กรองโครงการ'"
			@click="open_picker()"
		>
			<Icon name="building" :size="15" />
			<span class="ss-project-filter-text">{{ state.project ? name : "ทุกโครงการ" }}</span>
			<Icon name="chevron-down" :size="14" />
		</button>
		<button
			v-if="state.project"
			type="button"
			class="ss-project-filter-clear"
			aria-label="เลิกกรองโครงการ"
			title="เลิกกรองโครงการ"
			@click="clear"
		>
			<Icon name="x" :size="14" :stroke="2.6" />
		</button>
	</span>
</template>

<script setup>
import { computed, inject } from "vue";
import Icon from "../components/Icon.vue";
import { state } from "../api.js";

const open_picker = inject("open_project_picker");
const choose_project = inject("choose_project");
const name = computed(() => state.project?.project_name || state.project?.name || "");

// เลิกกรอง = ทุกโครงการ (AppShell จำค่าและโหลดตัวเลขใหม่)
const clear = () => choose_project(null);
</script>
