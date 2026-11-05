<template>
	<!-- หัวหน้าหลักของทุกหมวด: หมวดงาน (มือถือ) / ทักทาย / ปุ่มระบบเต็ม / โครงการที่เลือก
	     แท็บเล็ต/จอใหญ่: แถบเตี้ยแถวเดียว (ชื่อหมวด + ทักทาย | โครงการ | ระบบเต็ม) ไม่กินพื้นที่เนื้อหา -->
	<section class="ss-hero">
		<div class="ss-hero-glow"></div>
		<div class="ss-hero-top">
			<button
				v-if="boot.sections.length > 1"
				type="button"
				class="ss-hero-section"
				aria-label="เปลี่ยนหมวดงาน"
				@click="open_launcher()"
			>
				<span class="ss-hero-section-icon"
					><Icon :name="section.icon" :size="18" :stroke="2.2"
				/></span>
				<span>{{ section.title }}</span>
				<Icon name="grid" :size="16" />
				<span v-if="others" class="ss-hero-section-dot">{{ others }}</span>
			</button>
			<span v-else></span>
			<a v-if="boot.desk" class="ss-icon-btn ss-icon-btn--glass" href="/app" aria-label="เปิดระบบเต็ม">
				<Icon name="monitor" :size="20" />
			</a>
		</div>
		<div class="ss-hero-greet">
			<div class="ss-hero-title">{{ section.title }}</div>
			<div class="ss-hero-hello">{{ greeting }}</div>
			<div class="ss-hero-name">{{ boot.full_name }}</div>
		</div>
		<button type="button" class="ss-project-chip" @click="$emit('pick-project')">
			<span class="ss-project-chip-icon"><Icon name="building" :size="20" /></span>
			<span class="ss-project-chip-text">
				<span class="ss-project-chip-label">โครงการ</span>
				<span class="ss-project-chip-name">{{
					state.project?.project_name || state.project?.name || "แตะเพื่อเลือกโครงการ"
				}}</span>
			</span>
			<Icon name="swap" :size="18" />
		</button>
	</section>
</template>

<script setup>
import { computed, inject } from "vue";
import Icon from "./Icon.vue";
import { SECTIONS } from "../sections.js";
import { boot, state } from "../api.js";

defineEmits(["pick-project"]);
const open_launcher = inject("open_launcher");

const section = computed(() => SECTIONS[state.section]);
// งานที่รอในหมวดอื่น (เตือนให้สลับไปดู)
const others = computed(() =>
	boot.sections
		.filter((key) => key !== state.section)
		.reduce((sum, key) => sum + (SECTIONS[key].badge?.(state.summaries[key]) || 0), 0)
);

const greeting = computed(() => {
	const h = new Date().getHours();
	if (h < 11) return "อรุณสวัสดิ์";
	if (h < 16) return "สวัสดีตอนบ่าย";
	return "สวัสดีตอนเย็น";
});
</script>
