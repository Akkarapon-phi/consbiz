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

		<!-- มือถือ: แถบล่าง (เฉพาะหน้าหลักของแต่ละเมนู) / แท็บเล็ต-จอใหญ่: แถบข้างซ้าย (ทุกหน้า) -->
		<Transition name="ss-nav">
			<nav
				v-if="state.project"
				class="ss-nav"
				:class="{ 'is-sub': !show_nav, 'has-sections': boot.sections.length > 1 }"
				:style="{ '--count': mobile_tabs.length }"
				aria-label="เมนูหลัก"
			>
				<!-- ชื่อหมวด = ปุ่มเปิดตารางหมวดงาน (แท็บเล็ตเห็นแค่ไอคอน) -->
				<component
					:is="boot.sections.length > 1 ? 'button' : 'div'"
					:type="boot.sections.length > 1 ? 'button' : undefined"
					class="ss-nav-brand"
					:title="boot.sections.length > 1 ? 'เปลี่ยนหมวดงาน' : undefined"
					@click="boot.sections.length > 1 && (launcher = true)"
				>
					<span class="ss-nav-logo">
						<Icon :name="section.icon" :size="20" :stroke="2.2" />
						<span v-if="boot.sections.length > 1" class="ss-nav-logo-grid"
							><Icon name="grid" :size="11" :stroke="2.6"
						/></span>
						<span v-if="other_badges" class="ss-nav-logo-dot">{{ other_badges }}</span>
					</span>
					<span class="ss-nav-brand-text">
						<span>{{ section.title }}</span>
						<small v-if="boot.sections.length > 1">เปลี่ยนหมวดงาน</small>
					</span>
					<Icon
						v-if="boot.sections.length > 1"
						class="ss-nav-brand-more"
						name="chevron-down"
						:size="16"
					/>
				</component>
				<button type="button" class="ss-nav-project" @click="picker = true">
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
				<a v-if="boot.desk" class="ss-nav-item ss-nav-desk" href="/app" title="เปิดระบบเต็ม">
					<span class="ss-nav-icon"><Icon name="monitor" :size="22" /></span>
					<span class="ss-nav-label">ระบบเต็ม</span>
				</a>
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
import { computed, onMounted, provide, ref } from "vue";
import Icon from "./components/Icon.vue";
import Sheet from "./components/Sheet.vue";
import SectionLauncher from "./components/SectionLauncher.vue";
import { PARENT_TAB, SECTIONS, is_tab } from "./sections.js";
import {
	boot,
	call,
	go,
	initials,
	remember_project,
	remembered_project,
	show_error,
	start_router,
	state,
	tone,
} from "./api.js";
// สโตร์
import Home from "./views/store/Home.vue";
import Receive from "./views/store/Receive.vue";
import ReceiveForm from "./views/store/ReceiveForm.vue";
import ReceiptView from "./views/store/ReceiptView.vue";
import Issue from "./views/store/Issue.vue";
import Borrow from "./views/store/Borrow.vue";
import BorrowDetail from "./views/store/BorrowDetail.vue";
import BorrowNew from "./views/store/BorrowNew.vue";
import Stock from "./views/store/Stock.vue";
// ควบคุมงาน
import WorkHome from "./views/work/WorkHome.vue";
import ReportForm from "./views/work/ReportForm.vue";
import ReportView from "./views/work/ReportView.vue";
import Reports from "./views/work/Reports.vue";
import Inspections from "./views/work/Inspections.vue";
// บริหารโครงการ
import PmHome from "./views/pm/PmHome.vue";
import Plan from "./views/pm/Plan.vue";
import Lookahead from "./views/pm/Lookahead.vue";
import PmDocs from "./views/pm/PmDocs.vue";
import Resources from "./views/pm/Resources.vue";
import Concrete from "./views/work/Concrete.vue";
import ConcreteForm from "./views/work/ConcreteForm.vue";
// จัดซื้อ / ขาย (ชุดเดียวกัน แยกตาม kind)
import DocsHome from "./views/docs/DocsHome.vue";
import DocList from "./views/docs/DocList.vue";
import DocView from "./views/docs/DocView.vue";

const VIEWS = {
	home: Home,
	receive: Receive,
	"receive-form": ReceiveForm,
	receipt: ReceiptView,
	issue: Issue,
	concrete: Concrete,
	"concrete-form": ConcreteForm,
	borrow: Borrow,
	"borrow-detail": BorrowDetail,
	"borrow-new": BorrowNew,
	stock: Stock,
	work: WorkHome,
	reports: Reports,
	"report-form": ReportForm,
	"report-view": ReportView,
	inspections: Inspections,
	pm: PmHome,
	plan: Plan,
	lookahead: Lookahead,
	"pm-docs": PmDocs,
	resources: Resources,
	buy: DocsHome,
	sell: DocsHome,
	mr: DocList,
	po: DocList,
	pi: DocList,
	qtn: DocList,
	so: DocList,
	si: DocList,
	"buy-doc": DocView,
	"sell-doc": DocView,
};

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
const active_view = computed(() => PARENT_TAB[state.route.view] || state.route.view);
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

// summary ของแต่ละหมวด (ตัวเลขบนเมนูและบนปุ่มสลับหมวด)
const SUMMARY_API = {
	store: () => ["get_summary", {}],
	work: () => ["consbiz.site_app.get_work_summary", {}],
	pm: () => ["consbiz.site_app.get_pm_summary", {}],
	buy: () => ["consbiz.site_docs.get_summary", { section: "buy", scope: state.doc_scope }],
	sell: () => ["consbiz.site_docs.get_summary", { section: "sell", scope: state.doc_scope }],
};

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
provide("open_launcher", () => (launcher.value = true));
// งานที่รอในหมวดอื่น (จุดแดงบนปุ่มหมวดงาน)
const other_badges = computed(() =>
	boot.sections
		.filter((key) => key !== state.section)
		.reduce((sum, key) => sum + (SECTIONS[key].badge?.(state.summaries[key]) || 0), 0)
);

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
/* CSS ทั้งแอปอยู่ใน site.css (ต้องผ่าน <style> ของ .vue: Frappe ฝัง CSS เข้า bundle เฉพาะแบบนี้) */
@import "./site.css";
</style>
