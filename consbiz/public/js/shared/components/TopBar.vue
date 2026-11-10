<!-- แถบบนของทุกหน้า แถวเดียว สีพื้นตามหมวด สูงเท่ากันทุกหน้า ปุ่มจึงไม่ขยับเมื่อเปลี่ยนหน้า
     หมวด (จอ ≥768 ไอคอน + ชื่อ, มือถือ ไอคอน = ปุ่มเปลี่ยนหมวด) / ย้อนกลับ / ชื่อหน้า / โครงการ / ปุ่มของหน้า (slot actions) / แจ้งเตือน
     โครงการ: หน้างาน = โครงการที่ทำงาน, ออฟฟิศ = ตัวกรองโครงการ (ว่าง = ทุกโครงการ) กดแล้วเปิดหน้าเลือกโครงการของ AppShell
     แสดงเฉพาะหน้าเมนูหลัก (ไม่มีปุ่มย้อนกลับ) หน้าดู/ฟอร์มไม่ให้เปลี่ยนโครงการกลางคัน มือถือเหลือ avatar -->
<template>
	<header
		class="ss-topbar"
		:class="{ 'is-scrolled': scrolled, 'ss-topbar--hero': hero, 'has-tabs': show_tabs }"
	>
		<component
			:is="show_launcher ? 'button' : 'div'"
			v-if="section"
			:type="show_launcher ? 'button' : undefined"
			class="ss-topbar-module"
			:class="{ 'has-back': back_to }"
			:aria-label="show_launcher ? 'เปลี่ยนหมวดงาน' : undefined"
			@click="show_launcher && open_launcher()"
		>
			<span class="ss-topbar-module-icon"
				><Icon :name="section.icon" :size="16" :stroke="2.2"
			/></span>
			<span class="ss-topbar-module-name">{{ section.title }}</span>
			<span v-if="show_launcher && others" class="ss-topbar-launch-dot">{{ others }}</span>
		</component>
		<button
			v-if="back_to"
			type="button"
			class="ss-icon-btn"
			aria-label="ย้อนกลับ"
			@click="go_back"
		>
			<Icon name="chevron-left" :size="20" :stroke="2.4" />
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
				project_initials
			}}</span>
			<span class="ss-topbar-project-text">{{ project_label }}</span>
			<Icon name="chevron-down" :size="14" />
		</button>
		<slot name="search" />
		<NotificationBell />
		<slot name="actions" />
	</header>
	<!-- มือถือ: ปุ่มโครงการเต็มแถวใต้แถบบน แสดงชื่อเต็ม (จอ ≥768 ใช้ปุ่มในแถบบน) -->
	<button v-if="show_project" type="button" class="ss-project-bar" @click="open_picker()">
		<span class="ss-avatar" :class="`tone-${tone(state.project?.name || 'all')}`">{{
			project_initials
		}}</span>
		<span class="ss-project-bar-text">
			<small>โครงการ</small>
			<b>{{ project_label }}</b>
		</span>
		<Icon name="chevron-down" :size="16" />
	</button>
</template>

<script setup>
import { computed, inject, onBeforeUnmount, onMounted, ref } from "vue";
import Icon from "./Icon.vue";
import SectionTabs from "./SectionTabs.vue";
import NotificationBell from "./NotificationBell.vue";
import { app } from "../app.js";
import { back, boot, project_abbr, state, tone } from "../api.js";
import { module_list } from "../modules.js";

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
const open_launcher = inject("open_launcher", null);
const section = computed(() => app.sections[state.section]);
const project_name = computed(() => state.project?.project_name || state.project?.name || "");
const project_initials = computed(() =>
	state.project ? project_abbr(state.project) : app.project_filter ? "ทั้ง" : "?"
);
const project_label = computed(() =>
	state.project ? project_name.value : app.project_filter ? "ทุกโครงการ" : "เลือกโครงการ"
);
const show_project = computed(() => !props.no_project && !props.back_to && open_picker);
// ปุ่มเปลี่ยนหมวด (ซ่อนที่จอ ≥768 เพราะมี Dock): หน้าเมนูหลัก มีหมวดอื่นหรือระบบเต็มให้ไป
const show_launcher = computed(
	() =>
		!props.back_to &&
		open_launcher &&
		state.section !== "desktop" &&
		(module_list().length > 1 || boot.desk)
);
// งานที่รอในหมวดอื่น (เตือนให้สลับไปดู)
const others = computed(() =>
	(boot.sections || [])
		.filter((key) => key !== state.section)
		.reduce((sum, key) => sum + (app.sections[key]?.badge?.(state.summaries[key]) || 0), 0)
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
