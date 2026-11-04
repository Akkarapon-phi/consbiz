<template>
	<div class="ss-app" :class="{ 'has-nav': show_nav }">
		<main class="ss-stage">
			<Transition :name="`ss-${state.direction}`">
				<component
					:is="view"
					v-if="state.project || state.route.view === 'home'"
					:key="route_key"
					class="ss-view"
					@pick-project="picker = true"
				/>
			</Transition>
		</main>

		<Transition name="ss-nav">
			<nav v-if="show_nav" class="ss-nav" aria-label="เมนูหลัก">
				<span class="ss-nav-pill" :style="{ '--tab': tab_index }"></span>
				<button
					v-for="tab in tabs"
					:key="tab.view"
					type="button"
					class="ss-nav-item"
					:class="{ 'is-active': tab.view === state.route.view }"
					@click="open_tab(tab.view)"
				>
					<span class="ss-nav-icon">
						<Icon :name="tab.icon" :size="22" :stroke="tab.view === state.route.view ? 2.4 : 2" />
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
			subtitle="ข้อมูลทุกหน้าเป็นของโครงการที่เลือก"
			full
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
import {
	TABS,
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
import Home from "./views/Home.vue";
import Receive from "./views/Receive.vue";
import ReceiveForm from "./views/ReceiveForm.vue";
import ReceiptView from "./views/ReceiptView.vue";
import Issue from "./views/Issue.vue";
import Concrete from "./views/Concrete.vue";
import ConcreteForm from "./views/ConcreteForm.vue";
import Borrow from "./views/Borrow.vue";
import BorrowDetail from "./views/BorrowDetail.vue";
import BorrowNew from "./views/BorrowNew.vue";
import Stock from "./views/Stock.vue";

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
};

const view = computed(() => VIEWS[state.route.view] || Home);
const route_key = computed(
	() => `${state.route.view}:${JSON.stringify(state.route.params)}:${state.project?.name}`
);
const show_nav = computed(() => TABS.includes(state.route.view) && state.project);

const tabs = computed(() => [
	{ view: "home", label: "หน้าหลัก", icon: "home" },
	{
		view: "receive",
		label: "รับของ",
		icon: "receive",
		badge: state.summary?.pending_count || 0,
	},
	{ view: "issue", label: "เบิก", icon: "issue" },
	{
		view: "borrow",
		label: "ยืม-คืน",
		icon: "wrench",
		badge: state.summary?.borrow_count || 0,
		badge_tone: state.summary?.overdue_count ? "is-danger" : "",
	},
	{ view: "stock", label: "คลัง", icon: "warehouse" },
]);
const tab_index = computed(() =>
	Math.max(
		0,
		tabs.value.findIndex((t) => t.view === state.route.view)
	)
);

function open_tab(name) {
	if (name === state.route.view) {
		window.scrollTo({ top: 0, behavior: "smooth" });
		return;
	}
	go(name, {}, { replace: true });
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
	state.project = project;
	state.summary = null;
	remember_project(project);
	picker.value = false;
	load_summary();
}

function close_picker() {
	if (state.project) picker.value = false;
}

async function load_summary() {
	if (!state.project) return;
	try {
		state.summary = await call("get_summary", { project: state.project.name });
	} catch (error) {
		show_error(error);
	}
}
provide("reload_summary", load_summary);
provide("open_project_picker", () => (picker.value = true));

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
		load_summary();
	}
});
</script>

<style>
/* CSS ทั้งแอปอยู่ใน store.css (ต้องผ่าน <style> ของ .vue: Frappe ฝัง CSS เข้า bundle เฉพาะแบบนี้) */
@import "./store.css";
</style>
