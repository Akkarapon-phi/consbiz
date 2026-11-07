<template>
	<div
		class="ss-app"
		:class="{ 'has-nav': show_nav, 'has-side': has_shell }"
		:data-section="state.section"
	>
		<!-- แถบล่าง/ปุ่มลอยของแต่ละหน้า (Teleport มาที่นี่: ไม่ให้ transform ตอนเปลี่ยนหน้าดึงตำแหน่ง fixed) -->
		<div id="ss-layer"></div>
		<main class="ss-stage">
			<Transition :name="`ss-${state.direction}`">
				<component
					:is="view"
					v-if="ready"
					:key="route_key"
					class="ss-view"
					@pick-project="picker = true"
				/>
			</Transition>
		</main>

		<!-- แท็บเล็ต/จอใหญ่: Dock แถบเดียว (กว้างเท่า Dock ของ Frappe) หมวดของกลุ่มแอปนี้
		     เมนูของหมวดอยู่บนแถบบนของหน้า (SectionTabs.vue) พับ = ไอคอน, ปักหมุด = ไอคอน + ชื่อ -->
		<Transition name="ss-rail">
			<aside
				v-if="has_shell"
				class="ss-rail"
				aria-label="เมนูหลัก"
			>
				<button
					type="button"
					class="ss-rail-row ss-rail-logo"
					:class="{ 'is-active': desktop }"
					title="หน้าแรก"
					@click="switch_section('desktop')"
				>
					<img class="ss-rail-logo-img" :src="LOGO" alt="" />
					<span class="ss-rail-text ss-rail-brand">ConsERP</span>
				</button>
				<nav class="ss-rail-list">
					<template v-for="m in rail_modules" :key="m.key">
						<component
							:is="m.local ? 'button' : 'a'"
							:type="m.local ? 'button' : undefined"
							:href="m.local ? undefined : m.url"
							class="ss-rail-row ss-rail-mod"
							:class="{ 'is-open': is_open(m), 'is-active': is_open(m) && active_view === section.home }"
							:style="{ '--sw': m.colors[0], '--sw2': m.colors[1] }"
							:title="m.title"
							@click="m.local && switch_section(m.section)"
						>
							<span class="ss-rail-icon">
								<Icon :name="m.icon" :size="18" :stroke="2.1" />
								<span v-if="module_badge(m, state)" class="ss-rail-badge">{{
									module_badge(m, state)
								}}</span>
							</span>
							<span class="ss-rail-text">{{ m.label }}</span>
						</component>
					</template>
				</nav>
				<!-- ท้าย Dock: บริษัท (ออฟฟิศ) + ผู้ใช้ (เมนู: ระบบเต็ม / ออกจากระบบ) แบบ Dock ของ Frappe -->
				<div class="ss-rail-foot">
					<button
						v-if="app.project_filter && companies.length > 1"
						type="button"
						class="ss-rail-row ss-rail-ctx"
						:title="`บริษัท: ${company_label}`"
						@click="company_sheet = true"
					>
						<span class="ss-avatar" :class="`tone-${tone(state.company || 'all')}`">{{
							state.company ? initials(company_label) : "ทั้ง"
						}}</span>
						<span class="ss-rail-text ss-rail-ctx-text">
							<span>{{ company_label }}</span>
							<small>บริษัท</small>
						</span>
					</button>
					<button
						type="button"
						class="ss-rail-row ss-rail-ctx ss-rail-user"
						:class="{ 'is-open': user_menu }"
						:title="boot.full_name"
						aria-haspopup="menu"
						:aria-expanded="user_menu"
						@click="user_menu = !user_menu"
					>
						<span class="ss-avatar ss-user-avatar" :class="`tone-${tone(boot.user || '')}`">
							<img v-if="boot.user_image" :src="boot.user_image" alt="" />
							<template v-else>{{ initials(boot.full_name || boot.user || "") }}</template>
						</span>
						<span class="ss-rail-text ss-rail-ctx-text">
							<span>{{ boot.full_name }}</span>
							<small>{{ boot.user }}</small>
						</span>
					</button>
				</div>
			</aside>
		</Transition>

		<!-- ปุ่มพับ/กาง Dock: ปุ่มกลมเล็กที่ขอบขวาของ Dock (ไม่กินแถว) จอใช้เมาส์แสดงเมื่อชี้ที่ Dock -->
		<button
			v-if="has_shell"
			type="button"
			class="ss-rail-toggle"
			:title="pin_label"
			:aria-label="pin_label"
			:aria-pressed="side === 'expanded' || peek"
			@click="toggle_side"
		>
			<Icon :name="side === 'expanded' || peek ? 'chevron-left' : 'chevron-right'" :size="14" :stroke="2.6" />
		</button>

		<Transition name="ss-pop">
			<div v-if="user_menu" class="ss-user-menu" role="menu">
				<div class="ss-user-menu-head">
					<span class="ss-user-menu-name">{{ boot.full_name }}</span>
					<span class="ss-user-menu-mail">{{ boot.user }}</span>
				</div>
				<a v-if="boot.desk" class="ss-user-menu-item" role="menuitem" href="/app">
					<Icon name="monitor" :size="16" /> ระบบเต็ม
				</a>
				<button type="button" class="ss-user-menu-item is-danger" role="menuitem" @click="logout">
					<Icon name="external" :size="16" /> ออกจากระบบ
				</button>
			</div>
		</Transition>

		<!-- มือถือ: แถบเมนูล่างของหมวด (เฉพาะหน้าหลักของแต่ละเมนู) -->
		<Transition name="ss-nav">
			<nav
				v-if="show_nav"
				class="ss-nav"
				:style="{ '--count': mobile_tabs.length }"
				aria-label="เมนูของหมวด"
			>
				<span class="ss-nav-pill" :style="{ '--tab': tab_index }"></span>
				<button
					v-for="(tab, i) in mobile_tabs"
					:key="`${state.section}:${tab.view}`"
					type="button"
					class="ss-nav-item"
					:class="{ 'is-active': tab.view === active_view }"
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
			</nav>
		</Transition>

		<Sheet
			:open="picker"
			title="เลือกโครงการ"
			:subtitle="
				app.project_filter ? 'แสดงเอกสารเฉพาะโครงการที่เลือก' : 'ข้อมูลทุกหน้าเป็นของโครงการที่เลือก'
			"
			half
			@close="close_picker"
		>
			<div class="ss-search">
				<Icon name="search" :size="18" />
				<input v-model="project_txt" type="search" placeholder="ค้นหาชื่อหรือรหัสโครงการ" />
			</div>
			<div v-if="projects === null" class="ss-options-note"><span class="ss-spinner"></span></div>
			<div v-else class="ss-options">
				<!-- ออฟฟิศ: ไม่กรองโครงการ -->
				<button
					v-if="app.project_filter"
					type="button"
					class="ss-option ss-option--project"
					:class="{ 'is-active': !state.project }"
					@click="choose_project(null)"
				>
					<span class="ss-avatar tone-blue"><Icon name="layers" :size="18" /></span>
					<span class="ss-option-main">
						<span class="ss-option-label">ทุกโครงการ</span>
						<span class="ss-option-desc">{{
							state.company ? `ทุกโครงการของ ${company_label}` : "ไม่กรองโครงการ"
						}}</span>
					</span>
					<Icon v-if="!state.project" name="check" :size="18" />
				</button>
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

		<!-- ออฟฟิศ: เลือกบริษัท -->
		<Sheet
			:open="company_sheet"
			title="เลือกบริษัท"
			subtitle="กรองเอกสาร/ตัวเลข และใช้เป็นบริษัทของเอกสารใหม่"
			half
			@close="company_sheet = false"
		>
			<div class="ss-options">
				<button
					v-for="c in company_options"
					:key="c.value"
					type="button"
					class="ss-option ss-option--project"
					:class="{ 'is-active': c.value === state.company }"
					@click="choose_company(c.value)"
				>
					<span class="ss-avatar" :class="`tone-${tone(c.value || 'all')}`">{{ c.short }}</span>
					<span class="ss-option-main">
						<span class="ss-option-label">{{ c.label }}</span>
						<span v-if="c.desc" class="ss-option-desc">{{ c.desc }}</span>
					</span>
					<Icon v-if="c.value === state.company" name="check" :size="18" />
				</button>
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
import Desktop from "./components/Desktop.vue";
import { app, is_desktop, is_tab } from "./app.js";
import { module_badge, module_list, MODULE_META } from "./modules.js";
import {
	boot,
	call,
	go,
	init_app,
	initials,
	remember_project,
	remembered_project,
	scope_key,
	set_company,
	show_error,
	start_router,
	state,
	switch_section,
	tone,
} from "./api.js";

// โครงกลางของทุกแอป: Dock หมวดงาน + sidebar/แถบล่าง + หน้าเลือกโครงการ + toast
// หมวด/หน้า/component ของแต่ละแอปมาจาก app.js (configure ใน bundle ของแอป)
init_app();
const SECTIONS = app.sections;
const VIEWS = { ...app.views, desktop: Desktop };
const LOGO = "/assets/consbiz/site_app/logo-96.png";

const section = computed(() => SECTIONS[state.section]);
const view = computed(() => VIEWS[state.route.view] || VIEWS[section.value.home]);
const route_key = computed(
	() => `${state.route.view}:${JSON.stringify(state.route.params)}:${state.project?.name}`
);
const desktop = computed(() => is_desktop(state.section));
// ออฟฟิศ / หน้าแรก: แสดงทั้งเปลือกแอปและหน้าโดยไม่ต้องเลือกโครงการ
const has_shell = computed(() => !!(state.project || app.project_filter || desktop.value));
const ready = computed(() => has_shell.value || state.route.view === SECTIONS[state.section]?.home);

// มือถือ: แถบล่างเฉพาะหน้าหลักของเมนู (หน้าแรกไม่มี)
const show_nav = computed(() => is_tab(state.route.view) && has_shell.value && !desktop.value);

const tabs = computed(() => {
	const summary = state.summaries[state.section];
	return section.value.tabs.map((tab) => ({
		...tab,
		badge: tab.badge?.(summary) || 0,
		badge_tone: tab.alert?.(summary) ? "is-danger" : "",
	}));
});
const mobile_tabs = computed(() => tabs.value.filter((t) => !t.wide_only));

// Dock: เฉพาะหมวดของกลุ่มแอปนี้ (กลุ่มอื่นเปิดจากหน้าแรก) + หมวดที่เปิดอยู่ถ้าไม่อยู่ในรายการ
// (เช่น ขอซื้อของหน้างานที่ซ่อนเพราะมีจัดซื้อของออฟฟิศ)
const ALL_MODULES = module_list().filter((m) => m.app === app.key);
const rail_modules = computed(() => {
	if (desktop.value || ALL_MODULES.some((m) => m.local && m.section === state.section))
		return ALL_MODULES;
	const meta = MODULE_META[app.key]?.[state.section];
	if (!meta) return ALL_MODULES;
	const current = { ...meta, app: app.key, section: state.section, key: `${app.key}:${state.section}`, local: true };
	const at = ALL_MODULES.findLastIndex((m) => m.app === app.key) + 1;
	return [...ALL_MODULES.slice(0, at), current, ...ALL_MODULES.slice(at)];
});
const is_open = (m) => m.local && m.section === state.section;
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
	// ออฟฟิศ: เฉพาะโครงการของบริษัทที่เลือก
	const list = (projects.value || []).filter(
		(p) => !app.project_filter || !state.company || p.company === state.company
	);
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
	const changed = project?.name !== state.project?.name;
	state.project = project;
	if (changed) state.summaries = {};
	remember_project(project);
	picker.value = false;
	load_summaries();
}

function close_picker() {
	picker.value = false;
	// หน้างานยังไม่เลือกโครงการ: กลับหน้าแรก
	if (!state.project && !app.project_filter && !desktop.value) go("desktop", {}, { replace: true });
}
// เปิดหมวดของหน้างานโดยยังไม่เลือกโครงการ: ถามโครงการ
watch(
	() => state.section,
	(section) => {
		if (projects.value && !app.project_filter && !state.project && !is_desktop(section)) picker.value = true;
	}
);

// ---------------------------------------------------------------- บริษัท (ออฟฟิศ)

const company_sheet = ref(false);
const companies = boot.companies || [];
const company_label = computed(() => state.company || "ทุกบริษัท");
const company_options = [
	{ value: "", label: "ทุกบริษัท", short: "ทั้ง", desc: "รวมเอกสารของทุกบริษัท" },
	...companies.map((c) => ({ value: c.name, label: c.name, short: c.abbr || initials(c.name), desc: "" })),
];
function choose_company(company) {
	const changed = company !== state.company;
	set_company(company);
	company_sheet.value = false;
	if (!changed) return;
	// โครงการที่กรองอยู่เป็นของบริษัทอื่น: เลิกกรอง
	if (state.project && company && state.project.company !== company) {
		state.project = null;
		remember_project(null);
	}
	state.summaries = {};
	load_summaries();
}
provide("open_company_picker", () => (company_sheet.value = true));

// summary ของแต่ละหมวด (ตัวเลขบนเมนูและบนปุ่มสลับหมวด) ตาม app.summary_api
const SUMMARY_API = app.summary_api;

async function load_summary(key = state.section) {
	// หน้างานต้องมีโครงการ / ออฟฟิศ: โครงการเป็นตัวกรอง (ไม่มี = ทุกโครงการ)
	if ((!state.project && !app.project_filter) || !SUMMARY_API[key]) return;
	const stamp = scope_key();
	try {
		const [method, args] = SUMMARY_API[key]();
		const summary = await call(method, { project: state.project?.name, ...args });
		// เปลี่ยนโครงการ/บริษัทระหว่างโหลด: ทิ้งผลของขอบเขตเดิม
		if (scope_key() === stamp) state.summaries[key] = summary;
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
provide("choose_project", (project) => choose_project(project));

// ---------------------------------------------------------------- หมวดงาน

const launcher = ref(false);

// Dock แท็บเล็ต/จอใหญ่ (ความกว้างใน --ss-side ดู style.css)
// - พับ (ค่าเริ่มต้น): ไอคอนอย่างเดียว (ชี้แล้วไม่กางเอง ชื่อเมนูดูจาก tooltip)
//   จอสัมผัส = กดปุ่มล่างสุดแล้วกางทับเนื้อหา (html[data-peek]) เลือกเมนู/แตะนอกแถบแล้วพับ
// - ปักหมุด (expanded): กางค้างและดันเนื้อหา (ปุ่มล่างสุด) จำในเครื่อง
// ทุกแอปใน ConsERP ใช้ค่าเดียวกัน (สลับหมวดข้าม bundle แล้ว Dock ไม่เปลี่ยนสถานะ)
const SIDE_KEY = "consbiz.conserp.sidebar";
const can_hover = window.matchMedia("(hover: hover) and (pointer: fine)").matches;
function saved_side() {
	try {
		return localStorage.getItem(SIDE_KEY);
	} catch {
		return null;
	}
}
const side = ref(["expanded", "collapsed"].includes(saved_side()) ? saved_side() : app.side_default);
const peek = ref(false);
document.documentElement.dataset.side = side.value;

watch(peek, (value) => {
	if (value) document.documentElement.dataset.peek = "1";
	else delete document.documentElement.dataset.peek;
});
const pin_label = computed(() => {
	if (side.value === "expanded") return "พับแถบเมนู";
	return can_hover ? "กางแถบเมนู" : peek.value ? "ซ่อนชื่อเมนู" : "แสดงชื่อเมนู";
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

// เปลี่ยนหน้า / แตะนอกแถบ: พับกลับ
watch(
	() => state.route,
	() => (peek.value = false)
);
function close_peek(event) {
	if (peek.value && !event.target.closest?.(".ss-rail, .ss-rail-toggle")) peek.value = false;
	if (user_menu.value && !event.target.closest?.(".ss-user-menu, .ss-rail-user")) user_menu.value = false;
}

// ---------------------------------------------------------------- ผู้ใช้

const user_menu = ref(false);
async function logout() {
	try {
		await call("frappe.handler.logout", {}, { post: true });
	} catch {
		// ออกไม่สำเร็จก็ไปหน้าเข้าสู่ระบบ (session อาจหมดแล้ว)
	}
	window.location.href = "/login";
}
document.addEventListener("pointerdown", close_peek);
onBeforeUnmount(() => document.removeEventListener("pointerdown", close_peek));
provide("open_launcher", () => (launcher.value = true));
// เมนูของหมวดบนแถบบน (SectionTabs.vue ใน TopBar / Hero จอ ≥768)
provide("section_nav", { tabs, active_view, open_tab });

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
	// ออฟฟิศ: โครงการเป็นแค่ตัวกรอง ไม่ต้องเลือกก่อน (ตัวกรองต้องเป็นของบริษัทที่เลือก)
	if (app.project_filter) {
		if (state.project && state.company && state.project.company !== state.company) state.project = null;
		load_summaries();
	} else if (!state.project && projects.value.length === 1) {
		choose_project(projects.value[0]);
	} else if (!state.project) {
		picker.value = !desktop.value;
	} else {
		load_summaries();
	}
});
</script>

<style>
/* CSS ของทุกแอปอยู่ใน style.css (ต้องผ่าน <style> ของ .vue: Frappe ฝัง CSS เข้า bundle เฉพาะแบบนี้) */
@import "./style.css";
</style>
