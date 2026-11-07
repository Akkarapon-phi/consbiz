<!-- แถบบนของหน้าย่อย: ย้อนกลับ / ชื่อหน้า / (จอ ≥768) โครงการ / ปุ่มของหน้า (slot actions)
     โครงการ: หน้างาน = โครงการที่ทำงาน, ออฟฟิศ = ตัวกรองโครงการ (ว่าง = ทุกโครงการ) กดแล้วเปิดหน้าเลือกโครงการของ AppShell
     แสดงเฉพาะหน้าเมนูหลัก (ไม่มีปุ่มย้อนกลับ) หน้าดู/ฟอร์มไม่ให้เปลี่ยนโครงการกลางคัน -->
<template>
	<header
		class="ss-topbar"
		:class="{ 'is-scrolled': scrolled, 'ss-topbar--hero': hero, 'has-tabs': show_tabs }"
	>
		<button v-if="back_to" type="button" class="ss-icon-btn" aria-label="ย้อนกลับ" @click="go_back">
			<Icon name="chevron-left" :size="24" :stroke="2.4" />
		</button>
		<div class="ss-topbar-title">
			<div class="ss-topbar-main">{{ title }}</div>
			<div v-if="subtitle" class="ss-topbar-sub" :class="{ 'is-project': sub_is_project }">
				{{ subtitle }}
			</div>
		</div>
		<!-- จอ ≥768 หน้าเมนูหลัก: แท็บเมนูของหมวดแทนชื่อหน้า (ชื่อหน้า = แท็บที่เลือก) -->
		<SectionTabs v-if="show_tabs" />
		<button
			v-if="show_project"
			type="button"
			class="ss-topbar-project"
			:class="{ 'is-active': state.project }"
			:title="state.project ? `โครงการ: ${project_name}` : 'กรองโครงการ'"
			@click="open_picker()"
		>
			<span class="ss-avatar" :class="`tone-${tone(state.project?.name || 'all')}`">{{
				state.project ? initials(project_name) : "ทั้ง"
			}}</span>
			<span class="ss-topbar-project-text">{{ state.project ? project_name : "ทุกโครงการ" }}</span>
			<Icon name="chevron-down" :size="14" />
		</button>
		<slot name="actions" />
	</header>
</template>

<script setup>
import { computed, inject, onBeforeUnmount, onMounted, ref } from "vue";
import Icon from "./Icon.vue";
import SectionTabs from "./SectionTabs.vue";
import { app } from "../app.js";
import { back, initials, state, tone } from "../api.js";

const props = defineProps({
	title: String,
	subtitle: String,
	back_to: [String, Boolean],
	back_params: { type: Object, default: () => ({}) },
	hero: Boolean,
	// ซ่อนปุ่มโครงการ (หน้าที่ไม่ขึ้นกับโครงการ)
	no_project: Boolean,
});

const open_picker = inject("open_project_picker", null);
const project_name = computed(() => state.project?.project_name || state.project?.name || "");
const show_project = computed(
	() => !props.no_project && !props.back_to && open_picker && (state.project || app.project_filter)
);
// แท็บเมนูของหมวด: เฉพาะหน้าเมนูหลัก (หน้าดู/ฟอร์มไม่ให้กดออกกลางคัน)
const show_tabs = computed(() => !props.back_to);
// คำอธิบาย = ชื่อโครงการ: จอ ≥768 ซ่อน (ปุ่มโครงการบอกแล้ว)
const sub_is_project = computed(() => show_project.value && props.subtitle === project_name.value);

const scrolled = ref(false);
const on_scroll = () => (scrolled.value = window.scrollY > 6);
onMounted(() => window.addEventListener("scroll", on_scroll, { passive: true }));
onBeforeUnmount(() => window.removeEventListener("scroll", on_scroll));

function go_back() {
	back(typeof props.back_to === "string" ? props.back_to : "home", props.back_params);
}
</script>
