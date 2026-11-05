<template>
	<div
		class="ss-app"
		:class="{ 'has-nav': show_nav, 'has-side': state.project }"
		:data-section="state.section"
	>
		<!-- แถบล่าง/ปุ่มลอยของแต่ละหน้า (Teleport มาที่นี่: ไม่ให้ transform ตอนเปลี่ยนหน้าดึงตำแหน่ง fixed) -->
		<div id="ss-layer"></div>
		<main class="ss-stage">
			<Transition :name="`ss-${state.direction}`">
				<component
					:is="view"
					v-if="state.project || state.route.view === section.home"
					:key="route_key"
					class="ss-view"
					@pick-project="picker = true"
				/>
			</Transition>
		</main>

		<!-- จอใหญ่: Dock หมวดงานซ้ายสุด (แท็บเล็ตอยู่บนสุดของแถบไอคอน, มือถือใช้ตารางหมวดงาน) -->
		<Transition name="ss-dock">
			<aside v-if="state.project && boot.sections.length > 1" class="ss-dock" aria-label="หมวดงาน">
				<span class="ss-dock-logo" :title="app.title"
					><Icon name="building" :size="20" :stroke="2.2"
				/></span>
				<SectionDock variant="dock" />
				<a v-if="boot.desk" class="ss-sec ss-dock-desk" href="/app" title="เปิดระบบเต็ม">
					<span class="ss-sec-icon"><Icon name="monitor" :size="20" /></span>
					<span class="ss-sec-label">ระบบเต็ม</span>
				</a>
			</aside>
		</Transition>

		<!-- มือถือ: แถบล่าง (เฉพาะหน้าหลักของแต่ละเมนู) / แท็บเล็ต-จอใหญ่: แถบข้างซ้าย (ทุกหน้า) -->
		<Transition name="ss-nav">
			<nav
				v-if="state.project"
				class="ss-nav"
				:class="{ 'is-sub': !show_nav, 'has-sections': boot.sections.length > 1 }"
				:style="{ '--count': mobile_tabs.length }"
				aria-label="เมนูหลัก"
				@mouseenter="hover_side(true)"
				@mouseleave="hover_side(false)"
			>
				<!-- หัว sidebar: ชื่อหมวด (แสดงเมื่อกาง) เปลี่ยนหมวดที่ Dock -->
				<div class="ss-nav-head">
					<div class="ss-nav-brand">
						<span class="ss-nav-logo"
							><Icon :name="section.icon" :size="20" :stroke="2.2"
						/></span>
						<span class="ss-nav-brand-text">{{ section.title }}</span>
					</div>
				</div>
				<button
					type="button"
					class="ss-nav-project"
					:title="`โครงการ: ${state.project.project_name || state.project.name}`"
					@click="picker = true"
				>
					<span class="ss-avatar" :class="`tone-${tone(state.project.name)}`">{{
						initials(state.project.project_name || state.project.name)
					}}</span>
					<span class="ss-nav-project-text">
						<span>{{ state.project.project_name || state.project.name }}</span>
						<small>{{ state.project.name }}</small>
					</span>
					<Icon name="swap" :size="16" />
				</button>
				<span class="ss-nav-pill" :style="{ '--tab': tab_index }"></span>
				<button
					v-for="(tab, i) in tabs"
					:key="`${state.section}:${tab.view}`"
					type="button"
					class="ss-nav-item"
					:class="{ 'is-active': tab.view === active_view, 'is-wide-only': tab.wide_only }"
					:title="tab.label"
					:style="{ '--i': i }"
					@click="open_tab(tab.view)"
				>
					<span class="ss-nav-icon">
						<Icon :name="tab.icon" :size="22" :stroke="tab.view === active_view ? 2.4 : 2" />
						<Transition name="ss-pop">
							<span
								v-if="tab.badge"
								:key="tab.badge"
								class="ss-badge"
								:class="tab.badge_tone"
								>{{ tab.badge }}</span
							>
						</Transition>
					</span>
					<span class="ss-nav-label">{{ tab.label }}</span>
				</button>
				<!-- ท้าย sidebar: ระบบเต็ม (ไม่มี Dock) + ปุ่มปักหมุด/พับ -->
				<div class="ss-nav-foot">
					<a v-if="boot.desk" class="ss-nav-item ss-nav-desk" href="/app" title="เปิดระบบเต็ม">
						<span class="ss-nav-icon"><Icon name="monitor" :size="22" /></span>
						<span class="ss-nav-label">ระบบเต็ม</span>
					</a>
					<button
						type="button"
						class="ss-nav-item ss-nav-pin"
						:title="pin_label"
						:aria-label="pin_label"
						:aria-pressed="side === 'expanded'"
						@click="toggle_side"
					>
						<span class="ss-nav-icon"
							><Icon :name="side === 'expanded' ? 'chevrons-left' : 'panel'" :size="20"
						/></span>
						<span class="ss-nav-label">{{ pin_label }}</span>
					</button>
				</div>
			</nav>
		</Transition>

		<Sheet
			:open="picker"
			title="เลือกโครงการ"
			subtitle="ข้อมูลทุกหน้าเป็นของโครงการที่เลือก"
			half
			@close="close_picker"
		>
			<div class="ss-search">
				<Icon name="search" :size="18" />
				<input v-model="project_txt" type="search" placeholder="ค้นหาชื่อหรือรหัสโครงการ" />
			</div>
			<div v-if="projects === null" class="ss-options-note"><span class="ss-spinner"></span></div>
			<div v-else class="ss-options">
				<button
					v-for="(p, i) in filtered_projects"
					:key="p.name"
					type="button"
					class="ss-option ss-option--project"
					:class="{ 'is-active': p.name === state.project?.name }"
					:style="{ '--i': i }"
					@click="choose_project(p)"
				>
					<span class="ss-avatar" :class="`tone-${tone(p.name)}`">{{
						initials(p.project_name || p.name)
					}}</span>
					<span class="ss-option-main">
						<span class="ss-option-label">{{ p.project_name || p.name }}</span>
						<span class="ss-option-desc">{{ p.name }} · {{ p.company }}</span>
					</span>
					<Icon v-if="p.name === state.project?.name" name="check" :size="18" />
				</button>
				<div v-if="!filtered_projects.length" class="ss-options-note">ไม่พบโครงการที่เปิดอยู่</div>
			</div>
		</Sheet>

		<SectionLauncher :open="launcher" @close="launcher = false" />

		<div class="ss-toasts" aria-live="polite">
			<TransitionGroup name="ss-toast">
				<div v-for="t in state.toasts" :key="t.id" class="ss-toast" :class="`is-${t.type}`">
					<Icon
						:name="t.type === 'error' ? 'alert' : t.type === 'warning' ? 'info' : 'check'"
						:size="18"
					/>
					<span>{{ t.message }}</span>
				</div>
			</TransitionGroup>
		</div>

		<Transition name="ss-success">
			<div v-if="state.success" class="ss-success">
				<div class="ss-success-card">
					<svg class="ss-check" viewBox="0 0 52 52">
						<circle cx="26" cy="26" r="24" />
						<path d="M15 27l7 7 15-16" />
					</svg>
					<div class="ss-success-title">{{ state.success.title }}</div>
					<div v-if="state.success.subtitle" class="ss-success-sub">
						{{ state.success.subtitle }}
					</div>
					<div class="ss-confetti">
						<i v-for="n in 14" :key="n" :style="{ '--n': n }"></i>
					</div>
				</div>
			</div>
		</Transition>
	</div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, provide, ref, watch } from "vue";
import Icon from "./components/Icon.vue";
import Sheet from "./components/Sheet.vue";
import SectionLauncher from "./components/SectionLauncher.vue";
import SectionDock from "./components/SectionDock.vue";
import { app, is_tab } from "./app.js";
import {
	boot,
	call,
	go,
	init_app,
	initials,
	remember_project,
	remembered_project,
	show_error,
	start_router,
	state,
	tone,
} from "./api.js";

// โครงกลางของทุกแอป: Dock หมวดงาน + sidebar/แถบล่าง + หน้าเลือกโครงการ + toast
// หมวด/หน้า/component ของแต่ละแอปมาจาก app.js (configure ใน bundle ของแอป)
init_app();
const SECTIONS = app.sections;
const VIEWS = app.views;

const section = computed(() => SECTIONS[state.section]);
const view = computed(() => VIEWS[state.route.view] || VIEWS[section.value.home]);
const route_key = computed(
	() => `${state.route.view}:${JSON.stringify(state.route.params)}:${state.project?.name}`
);
const show_nav = computed(() => is_tab(state.route.view) && state.project);

const tabs = computed(() => {
	const summary = state.summaries[state.section];
	return section.value.tabs.map((tab) => ({
		...tab,
		badge: tab.badge?.(summary) || 0,
		badge_tone: tab.alert?.(summary) ? "is-danger" : "",
	}));
});
const mobile_tabs = computed(() => tabs.value.filter((t) => !t.wide_only));
// หน้าเอกสารจัดซื้อ/ขาย (ดู/ฟอร์ม) ไฮไลต์เมนูของชนิดเอกสาร (params.kind)
const active_view = computed(
	() =>
		app.parent_tab[state.route.view] ||
		(app.kind_pages.includes(state.route.view) && state.route.params.kind) ||
		state.route.view
);
// ตำแหน่งแถบไฮไลต์ของแถบล่าง (มือถือไม่มีเมนู wide_only)
const tab_index = computed(() =>
	Math.max(
		0,
		mobile_tabs.value.findIndex((t) => t.view === active_view.value)
	)
);

function open_tab(name) {
	if (name === state.route.view) {
		window.scrollTo({ top: 0, behavior: "smooth" });
		return;
	}
	// สลับเมนูหลักแทนที่ประวัติ, จากหน้าย่อย (จอใหญ่) เพิ่มประวัติให้ย้อนกลับได้
	go(name, {}, { replace: is_tab(state.route.view) });
}

// ---------------------------------------------------------------- โครงการ

const picker = ref(false);
const projects = ref(null);
const project_txt = ref("");

const filtered_projects = computed(() => {
	const q = project_txt.value.trim().toLowerCase();
	const list = projects.value || [];
	return q
		? list.filter((p) => `${p.name} ${p.project_name} ${p.company}`.toLowerCase().includes(q))
		: list;
});

async function load_projects() {
	try {
		projects.value = await call("get_projects");
	} catch (error) {
		projects.value = [];
		show_error(error);
	}
}

function choose_project(project) {
	const changed = project.name !== state.project?.name;
	state.project = project;
	if (changed) state.summaries = {};
	remember_project(project);
	picker.value = false;
	load_summaries();
}

function close_picker() {
	if (state.project) picker.value = false;
}

// summary ของแต่ละหมวด (ตัวเลขบนเมนูและบนปุ่มสลับหมวด) ตาม app.summary_api
const SUMMARY_API = app.summary_api;

async function load_summary(key = state.section) {
	if (!state.project || !SUMMARY_API[key]) return;
	const project = state.project.name;
	try {
		const [method, args] = SUMMARY_API[key]();
		const summary = await call(method, { ...args, project });
		// เปลี่ยนโครงการระหว่างโหลด: ทิ้งผลของโครงการเดิม
		if (state.project?.name === project) state.summaries[key] = summary;
	} catch (error) {
		show_error(error);
	}
}

// หมวดที่เปิดอยู่ก่อน แล้วหมวดอื่น (ตัวเลขบนปุ่มสลับหมวด)
function load_summaries() {
	load_summary(state.section).then(() =>
		boot.sections
			.filter((key) => key !== state.section && !SECTIONS[key].lazy)
			.forEach((key) => load_summary(key))
	);
}
provide("reload_summary", (key) => load_summary(typeof key === "string" ? key : undefined));
provide("open_project_picker", () => (picker.value = true));

// ---------------------------------------------------------------- หมวดงาน

const launcher = ref(false);
// แท็บเล็ต/จอใหญ่: Dock หมวดงานซ้ายสุด (มีมากกว่า 1 หมวด) ความกว้างรวมใน --ss-side (ดู site.css)
if (boot.sections.length > 1) document.documentElement.dataset.dock = "1";

// sidebar แท็บเล็ต/จอใหญ่
// - พับ (ค่าเริ่มต้น): ไอคอนอย่างเดียว กางชั่วคราวทับเนื้อหาเอง (html[data-peek])
//   ใช้เมาส์ = ชี้แล้วกาง เอาออกแล้วพับ, จอสัมผัส = กดปุ่มล่างสุดแล้วกาง เลือกเมนู/แตะนอกแถบแล้วพับ
// - ปักหมุด (expanded): กางค้างและดันเนื้อหา (ปุ่มล่างสุด) จำในเครื่อง
const SIDE_KEY = `${app.storage}.sidebar`;
const can_hover = window.matchMedia("(hover: hover) and (pointer: fine)").matches;
function saved_side() {
	try {
		return localStorage.getItem(SIDE_KEY);
	} catch {
		return null;
	}
}
const side = ref(saved_side() === "expanded" ? "expanded" : "collapsed");
const peek = ref(false);
document.documentElement.dataset.side = side.value;

watch(peek, (value) => {
	if (value) document.documentElement.dataset.peek = "1";
	else delete document.documentElement.dataset.peek;
});
const pin_label = computed(() => {
	if (side.value === "expanded") return "พับแถบเมนู";
	return can_hover ? "ปักหมุดแถบเมนู" : peek.value ? "ซ่อนชื่อเมนู" : "แสดงชื่อเมนู";
});

function toggle_side() {
	// จอสัมผัสตอนพับ: กาง/ซ่อนชั่วคราว (ไม่ปักหมุด เพื่อไม่บังเนื้อหาถาวรบนจอแท็บเล็ต)
	if (!can_hover && side.value === "collapsed") {
		peek.value = !peek.value;
		return;
	}
	side.value = side.value === "expanded" ? "collapsed" : "expanded";
	peek.value = false;
	document.documentElement.dataset.side = side.value;
	try {
		localStorage.setItem(SIDE_KEY, side.value);
	} catch {
		// private mode
	}
}

let peek_timer = null;
function hover_side(inside) {
	if (!can_hover || side.value === "expanded" || window.innerWidth < 768) return;
	clearTimeout(peek_timer);
	// หน่วงเล็กน้อย: เมาส์ผ่านเฉยๆ ไม่กาง, ออกแล้วไม่พับทันที
	peek_timer = setTimeout(() => (peek.value = inside), inside ? 150 : 250);
}
// เปลี่ยนหน้า / แตะนอกแถบ: พับกลับ
watch(
	() => state.route,
	() => (peek.value = false)
);
function close_peek(event) {
	if (peek.value && !event.target.closest?.(".ss-nav")) peek.value = false;
}
document.addEventListener("pointerdown", close_peek);
onBeforeUnmount(() => document.removeEventListener("pointerdown", close_peek));
provide("open_launcher", () => (launcher.value = true));

onMounted(async () => {
	// ?project=<รหัส> เลือกโครงการให้เลย (ลิงก์จากฟอร์ม Project / CM)
	const wanted = new URLSearchParams(location.search).get("project");
	start_router();
	state.project = remembered_project();
	await load_projects();
	const linked = wanted && projects.value.find((p) => p.name === wanted);
	if (linked) {
		choose_project(linked);
		return;
	}
	if (state.project && !projects.value.some((p) => p.name === state.project.name)) {
		state.project = null;
	}
	if (!state.project && projects.value.length === 1) {
		choose_project(projects.value[0]);
	} else if (!state.project) {
		picker.value = true;
	} else {
		load_summaries();
	}
});
</script>

<style>
/* CSS ของทุกแอปอยู่ใน style.css (ต้องผ่าน <style> ของ .vue: Frappe ฝัง CSS เข้า bundle เฉพาะแบบนี้) */
@import "./style.css";
</style>
