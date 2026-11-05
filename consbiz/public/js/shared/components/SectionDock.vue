<template>
	<!-- ปุ่มหมวดงานเรียงลง (กดครั้งเดียวสลับหมวด พร้อมตัวเลขงานค้างของแต่ละหมวด)
	     อยู่ใน Dock คอลัมน์ซ้ายสุดของแท็บเล็ต/จอใหญ่ (App.vue .ss-dock)
	     มือถือไม่แสดง (สลับหมวดผ่านตารางไอคอน SectionLauncher.vue) -->
	<div class="ss-sections" :class="`ss-sections--${variant}`" role="tablist" aria-label="หมวดงาน">
		<button
			v-for="s in sections"
			:key="s.key"
			type="button"
			role="tab"
			class="ss-sec"
			:class="{ 'is-active': s.key === state.section }"
			:style="{ '--sw': s.colors[0], '--sw2': s.colors[1] }"
			:aria-selected="s.key === state.section"
			:title="`${s.title}: ${s.note}`"
			@click="switch_section(s.key)"
		>
			<span class="ss-sec-icon">
				<Icon :name="s.icon" :size="20" :stroke="2.1" />
				<span v-if="badge(s)" class="ss-sec-badge">{{ badge(s) }}</span>
			</span>
			<span class="ss-sec-label">{{ s.label }}</span>
		</button>
	</div>
</template>

<script setup>
import { computed } from "vue";
import Icon from "./Icon.vue";
import { app } from "../app.js";
import { boot, state, switch_section } from "../api.js";

const SECTIONS = app.sections;

defineProps({ variant: { type: String, default: "dock" } });

const sections = computed(() => boot.sections.map((key) => SECTIONS[key]));
const badge = (section) => section.badge?.(state.summaries[section.key]) || 0;
</script>
