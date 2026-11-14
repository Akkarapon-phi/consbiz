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
			<aside v-if="has_shell" class="ss-rail" aria-label="เมนูหลัก">
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
							:class="{
								'is-open': is_open(m),
								'is-active': is_open(m) && active_view === section.home,
							}"
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
					<!-- ปุ่มพับ/กาง Dock: แถวบนสุดของโซนท้าย Dock -->
					<button
						type="button"
						class="ss-rail-row ss-rail-toggle"
						:title="pin_label"
						:aria-pressed="side === 'expanded' || peek"
						@click="toggle_side"
					>
						<span class="ss-rail-icon">
							<Icon
								:name="side === 'expanded' || peek ? 'chevrons-left' : 'chevron-right'"
								:size="18"
								:stroke="2.1"
							/>
						</span>
						<span class="ss-rail-text">{{ pin_label }}</span>
					</button>
					<button
						v-if="app.project_filter && companies.length > 1"
						ref="company_button"
						type="button"
						class="ss-rail-row ss-rail-ctx"
						:class="{ 'is-open': dock_menu === 'company' }"
						:title="`บริษัท: ${company_label}`"
						aria-haspopup="menu"
						:aria-expanded="dock_menu === 'company'"
						@click="toggle_dock_menu('company')"
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
						ref="user_button"
						type="button"
						class="ss-rail-row ss-rail-ctx ss-rail-user"
						:class="{ 'is-open': dock_menu === 'user' }"
						:title="boot.full_name"
						aria-haspopup="menu"
						:aria-expanded="dock_menu === 'user'"
						@click="toggle_dock_menu('user')"
					>
						<span
							class="ss-avatar ss-user-avatar"
							:class="`tone-${tone(boot.user || '')}`"
						>
							<img v-if="boot.user_image" :src="boot.user_image" alt="" />
							<template v-else>{{
								initials(boot.full_name || boot.user || "")
							}}</template>
						</span>
						<span class="ss-rail-text ss-rail-ctx-text">
							<span>{{ boot.full_name }}</span>
							<small>{{ boot.user }}</small>
						</span>
					</button>
				</div>
			</aside>
		</Transition>

		<AppTooltip />
		<ProfileSheet :open="profile_open" @close="profile_open = false" />
		<SettingsDialog v-if="boot.can?.settings || boot.can?.labour_settings" :open="settings_open" @close="settings_open = false" />

		<DockMenu
			:open="dock_menu === 'company'"
			:anchor="company_button"
			:groups="company_groups"
			@close="dock_menu = ''"
		/>
		<DockMenu
			:open="dock_menu === 'user'"
			:anchor="user_button"
			:groups="user_groups"
			@close="dock_menu = ''"
		/>

		<!-- มือถือ: แถบเมนูล่างของหมวด (เฉพาะหน้าหลักของแต่ละเมนู) -->
		<Transition name="ss-nav">
			<nav
				v-if="show_nav"
				class="ss-nav"
				:style="{ '--count': nav_tabs.length }"
				aria-label="เมนูของหมวด"
			>
				<span class="ss-nav-pill" :style="{ '--tab': tab_index }"></span>
				<button
					v-for="(tab, i) in nav_tabs"
					:key="`${state.section}:${tab.view}`"
					type="button"
					class="ss-nav-item"
					:class="{ 'is-active': tab.view === MORE ? more_active : tab.view === active_view }"
					:title="tab.label"
					:style="{ '--i': i }"
					@click="tab.view === MORE ? (more_open = true) : open_tab(tab.view)"
				>
					<span class="ss-nav-icon">
						<Icon
							:name="tab.icon"
							:size="22"
							:stroke="tab.view === active_view ? 2.4 : 2"
						/>
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

		<!-- มือถือ: เมนูที่เกินแถบล่าง (เกิน NAV_MAX) -->
		<Sheet :open="more_open" title="เมนูอื่นๆ" @close="more_open = false">
			<div class="ss-list">
				<button
					v-for="tab in more_tabs"
					:key="tab.view"
					type="button"
					class="ss-card ss-card--row"
					:class="{ 'is-active': tab.view === active_view }"
					@click="(more_open = false), open_tab(tab.view)"
				>
					<span class="ss-nav-icon"><Icon :name="tab.icon" :size="22" /></span>
					<span class="ss-card-main"><span class="ss-card-title">{{ tab.label }}</span></span>
					<span v-if="tab.badge" class="ss-badge" :class="tab.badge_tone">{{ tab.badge }}</span>
				</button>
			</div>
		</Sheet>

		<Sheet
			:open="picker"
			title="เลือกโครงการ"
			:subtitle="
				app.project_filter
					? 'แสดงเอกสารเฉพาะโครงการที่เลือก'
					: 'ข้อมูลทุกหน้าเป็นของโครงการที่เลือก'
			"
			half
			@close="close_picker"
		>
			<div class="ss-search">
				<Icon name="search" :size="18" />
				<input
					v-model="project_txt"
					type="search"
					placeholder="ค้นหาชื่อหรือรหัสโครงการ"
				/>
			</div>
			<div v-if="projects === null" class="ss-options-note">
				<span class="ss-spinner"></span>
			</div>
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
						project_abbr(p)
					}}</span>
					<span class="ss-option-main">
						<span class="ss-option-label">{{ p.project_name || p.name }}</span>
						<span class="ss-option-desc">{{ p.name }} · {{ p.company }}</span>
					</span>
					<Icon v-if="p.name === state.project?.name" name="check" :size="18" />
				</button>
				<div v-if="!filtered_projects.length" class="ss-options-note">
					ไม่พบโครงการที่เปิดอยู่
				</div>
			</div>
		</Sheet>

		<SectionLauncher :open="launcher" @close="launcher = false" />

		<div class="ss-toasts" aria-live="polite">
			<TransitionGroup name="ss-toast">
				<div
					v-for="t in state.toasts"
					:key="t.id"
					class="ss-toast"
					:class="`is-${t.type}`"
				>
					<Icon
						:name="
							t.type === 'error' || t.type === 'warning' ? 'alert' : 'check'
						"
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
import DockMenu from "./components/DockMenu.vue";
import AppTooltip from "./components/AppTooltip.vue";
import ProfileSheet from "./components/ProfileSheet.vue";
import SettingsDialog from "./components/SettingsDialog.vue";
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
	project_abbr,
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
const has_shell = computed(
	() => !!(state.project || app.project_filter || app.no_project || desktop.value)
);
const ready = computed(
	() => has_shell.value || state.route.view === SECTIONS[state.section]?.home
);

// มือถือ: แถบล่างเฉพาะหน้าหลักของเมนู (หน้าแรกไม่มี)
const show_nav = computed(() => is_tab(state.route.view) && has_shell.value && !desktop.value);

// tab.when(boot) = เมนูที่เห็นตามสิทธิ์ (ไม่มี when = ทุกคน)
const visible_tabs = (s) => s.tabs.filter((tab) => !tab.when || tab.when(boot));

const tabs = computed(() => {
	const summary = state.summaries[state.section];
	return visible_tabs(section.value).map((tab) => ({
		...tab,
		badge: tab.badge?.(summary) || 0,
		badge_tone: tab.alert?.(summary) ? "is-danger" : "",
	}));
});
const mobile_tabs = computed(() => tabs.value.filter((t) => !t.wide_only));
// แถบล่างมีได้ NAV_MAX ช่อง เกินแล้วช่องสุดท้ายเป็น "อื่นๆ" (เปิด sheet เลือกเมนูที่เหลือ)
const NAV_MAX = 5;
const MORE = "__more";
const more_open = ref(false);
const more_tabs = computed(() => (mobile_tabs.value.length > NAV_MAX ? mobile_tabs.value.slice(NAV_MAX - 1) : []));
const more_active = computed(() => more_tabs.value.some((t) => t.view === active_view.value));
const nav_tabs = computed(() => {
	if (!more_tabs.value.length) return mobile_tabs.value;
	const badge = more_tabs.value.reduce((sum, t) => sum + (Number(t.badge) || 0), 0);
	const more = {
		view: MORE,
		label: "อื่นๆ",
		icon: "more",
		badge,
		badge_tone: more_tabs.value.some((t) => t.badge_tone) ? "is-danger" : "",
	};
	return [...mobile_tabs.value.slice(0, NAV_MAX - 1), more];
});

// Dock: เฉพาะหมวดของกลุ่มแอปนี้ (กลุ่มอื่นเปิดจากหน้าแรก) + หมวดที่เปิดอยู่ถ้าไม่อยู่ในรายการ
// (เช่น ขอซื้อของหน้างานที่ซ่อนเพราะมีจัดซื้อของออฟฟิศ)
const ALL_MODULES = module_list().filter((m) => m.app === app.key);
const rail_modules = computed(() => {
	if (desktop.value || ALL_MODULES.some((m) => m.local && m.section === state.section))
		return ALL_MODULES;
	const meta = MODULE_META[app.key]?.[state.section];
	if (!meta) return ALL_MODULES;
	const current = {
		...meta,
		app: app.key,
		section: state.section,
		key: `${app.key}:${state.section}`,
		local: true,
	};
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
		more_active.value ? NAV_MAX - 1 : nav_tabs.value.findIndex((t) => t.view === active_view.value)
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
		? list.filter((p) =>
				`${p.name} ${p.project_name} ${p.company} ${p.custom_abbr || ""}`
					.toLowerCase()
					.includes(q)
		  )
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
	if (!state.project && !app.project_filter && !desktop.value)
		go("desktop", {}, { replace: true });
}
// เปิดหมวดของหน้างานโดยยังไม่เลือกโครงการ: ถามโครงการ
watch(
	() => state.section,
	(section) => {
		if (projects.value && !app.project_filter && !app.no_project && !state.project && !is_desktop(section))
			picker.value = true;
	}
);

// ---------------------------------------------------------------- บริษัท (ออฟฟิศ)

const companies = boot.companies || [];
const company_label = computed(() => state.company || "ทุกบริษัท");
const company_groups = computed(() => [
	{
		label: "เปลี่ยนบริษัท",
		items: [
			{
				key: "",
				label: "ทุกบริษัท",
				icon: "layers",
				selected: !state.company,
				onclick: () => choose_company(""),
			},
			...companies.map((c) => ({
				key: c.name,
				label: c.name,
				image: c.company_logo,
				icon: "building",
				selected: c.name === state.company,
				onclick: () => choose_company(c.name),
			})),
		],
	},
]);
function choose_company(company) {
	const changed = company !== state.company;
	set_company(company);
	if (!changed) return;
	// โครงการที่กรองอยู่เป็นของบริษัทอื่น: เลิกกรอง
	if (state.project && company && state.project.company !== company) {
		state.project = null;
		remember_project(null);
	}
	state.summaries = {};
	load_summaries();
}

// summary ของแต่ละหมวด (ตัวเลขบนเมนูและบนปุ่มสลับหมวด) ตาม app.summary_api
const SUMMARY_API = app.summary_api;

async function load_summary(key = state.section) {
	// หน้างานต้องมีโครงการ / ออฟฟิศ: โครงการเป็นตัวกรอง (ไม่มี = ทุกโครงการ) / Self Service: ไม่ใช้โครงการ
	if ((!state.project && !app.project_filter && !app.no_project) || !SUMMARY_API[key]) return;
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
//   จอสัมผัส = กดปุ่มพับ/กางในโซนท้าย Dock แล้วกางทับเนื้อหา (html[data-peek]) เลือกเมนู/แตะนอกแถบแล้วพับ
// - ปักหมุด (expanded): กางค้างและดันเนื้อหา (ปุ่มพับ/กาง) จำในเครื่อง
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
const side = ref(
	["expanded", "collapsed"].includes(saved_side()) ? saved_side() : app.side_default
);
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
	if (peek.value && !event.target.closest?.(".ss-rail, .ss-menu")) peek.value = false;
}

// ---------------------------------------------------------------- เมนูท้าย Dock (บริษัท / ผู้ใช้)

const dock_menu = ref("");
const company_button = ref(null);
const user_button = ref(null);
function toggle_dock_menu(name) {
	dock_menu.value = dock_menu.value === name ? "" : name;
}
const profile_open = ref(false);
const settings_open = ref(false);
const user_groups = [
	{
		items: [
			{
				key: "profile",
				label: boot.full_name,
				sub: boot.user,
				avatar: {
					image: boot.user_image,
					text: initials(boot.full_name || boot.user || ""),
					tone: tone(boot.user || ""),
				},
				onclick: () => (profile_open.value = true),
			},
		],
	},
	...(boot.can?.settings || boot.can?.labour_settings
		? [{ items: [{ key: "settings", label: "ตั้งค่า", icon: "sliders", onclick: () => (settings_open.value = true) }] }]
		: []),
	...(boot.desk
		? [{ items: [{ key: "desk", label: "ระบบเต็ม", icon: "monitor", href: "/app" }] }]
		: []),
	{ items: [{ key: "logout", label: "ออกจากระบบ", icon: "log-out", onclick: logout }] },
];
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
// เมนูของหมวดบนแถบบน (SectionTabs.vue ใน TopBar จอ ≥768)
provide("section_nav", { tabs, active_view, open_tab });

onMounted(async () => {
	// ?project=<รหัส> เลือกโครงการให้เลย (ลิงก์จากฟอร์ม Project / CM, กดการแจ้งเตือน)
	const wanted = new URLSearchParams(location.search).get("project");
	const remembered = remembered_project();
	start_router();
	// Self Service: ไม่มีโครงการ (ผู้ใช้อาจไม่มีสิทธิ์อ่าน Project)
	if (app.no_project) {
		load_summaries();
		return;
	}
	// มี ?project: ยังไม่แสดงหน้าจนรู้โครงการ ไม่งั้นหน้าเอกสารโหลดด้วยโครงการเดิมแล้ว error
	state.project = wanted ? null : remembered;
	await load_projects();
	const linked = wanted && projects.value.find((p) => p.name === wanted);
	if (linked) {
		choose_project(linked);
		return;
	}
	state.project = remembered;
	// ค่าที่จำในเครื่องอาจเก่า (เช่น เพิ่งตั้งตัวย่อโครงการ): ใช้ข้อมูลล่าสุด
	if (state.project) {
		state.project = projects.value.find((p) => p.name === state.project.name) || null;
		remember_project(state.project);
	}
	// ออฟฟิศ: โครงการเป็นแค่ตัวกรอง ไม่ต้องเลือกก่อน (ตัวกรองต้องเป็นของบริษัทที่เลือก)
	if (app.project_filter) {
		if (state.project && state.company && state.project.company !== state.company)
			state.project = null;
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
