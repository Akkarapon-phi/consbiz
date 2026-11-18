<!-- พนักงาน (กลุ่มพนักงานของหมวดบุคคล, API consbiz/hr_people.py, ตกลง 2026-11-17)
     รายการพนักงานของบริษัท แท็บ ทำงานอยู่ / ทดลองงาน / มีใบเตือน / ออกแล้ว
     จอ ≥ 1180 = ตาราง + แผงตัวอย่างขวา (คลิกแถว = ดูตัวอย่าง, ดับเบิลคลิก = หน้าเต็ม) จอเล็ก = แตะ = หน้าเต็ม (hr-employee) -->
<template>
	<div>
		<TopBar title="พนักงาน" />

		<div class="ss-content">
			<ListHead
				v-model="filter"
				v-model:search="txt"
				search_placeholder="ค้นหาชื่อ รหัส ตำแหน่ง หรือโครงการ"
				:tabs="tabs"
				:loading="loading"
				create="เพิ่มพนักงาน"
				@refresh="load"
				@create="go('md-doc', { kind: 'md-employees', name: 'new' })"
			/>

			<!-- จอ ≥768: ตารางในการ์ด (ListCard) + แผงตัวอย่างขวา (จอ ≥1180) แบบรายการเอกสาร
			     คลิกแถว = ตัวอย่าง (ไม่เปิดเองตอนโหลด) คลิกแถวเดิม = หน้าเต็ม X = ปิด / จอเล็ก = แตะ = หน้าเต็ม -->
			<ListCard :on="table">
				<Skeleton v-if="data === null" :rows="6" />
				<Empty v-else-if="!shown.length" icon="users" title="ไม่พบพนักงาน" />
				<DataTable v-else-if="table" :rows="shown" :columns="COLUMNS" :active="preview_name" @open="open">
					<template #employee_name="{ row: r }">
						<span class="hr-emp-cell">
							<span class="ss-avatar" :class="`tone-${tone(r.employee_name)}`">
								<img v-if="r.image" :src="r.image" alt="" />
								<template v-else>{{ initials(r.employee_name) }}</template>
							</span>
							<span>
								<span class="ss-cell-main">{{ r.employee_name }}</span>
								<small>{{ r.name }}</small>
							</span>
						</span>
					</template>
					<template #project="{ row: r }">{{ r.project_name || r.project || "—" }}</template>
					<template #date_of_joining="{ row: r }">{{ r.date_of_joining ? thai_date(r.date_of_joining, { year: true }) : "—" }}</template>
					<template #status="{ row: r }">
						<span v-if="r.status !== 'Active'" class="ss-tag tone-gray">{{ STATUS[r.status] || r.status }}</span>
						<span v-else-if="r.probation" class="ss-tag tone-blue">ทดลองงาน</span>
						<span v-else class="ss-tag tone-green">ทำงานอยู่</span>
						<span v-if="r.warnings" class="ss-tag tone-rose">เตือน {{ r.warnings }}</span>
					</template>
				</DataTable>
				<div v-else class="ss-list">
					<button
						v-for="r in shown"
						:key="r.name"
						type="button"
						class="ss-card ss-card--row hr-emp-row"
						@click="open(r)"
					>
						<span class="ss-avatar" :class="`tone-${tone(r.employee_name)}`">
							<img v-if="r.image" :src="r.image" alt="" />
							<template v-else>{{ initials(r.employee_name) }}</template>
						</span>
						<span class="ss-card-main">
							<span class="ss-card-title">
								{{ r.employee_name }}
								<span v-if="r.probation" class="ss-tag tone-blue">ทดลองงาน</span>
								<span v-if="r.warnings" class="ss-tag tone-rose">เตือน {{ r.warnings }}</span>
								<span v-if="r.status !== 'Active'" class="ss-tag tone-gray">{{ STATUS[r.status] || r.status }}</span>
							</span>
							<span class="ss-card-meta">{{ [r.designation, r.project_name || r.project].filter(Boolean).join(" · ") || r.name }}</span>
						</span>
						<Icon name="chevron-right" :size="16" />
					</button>
				</div>
				<template #side>
					<aside v-if="split && preview_name" class="ss-preview hr-emp-preview">
						<header class="ss-preview-head">
							<div class="ss-preview-title"><b>{{ preview?.employee_name || preview_name }}</b></div>
							<button type="button" class="ss-icon-btn ss-icon-btn--sm" aria-label="ปิดตัวอย่าง" @click="close_preview">
								<Icon name="x" :size="17" />
							</button>
						</header>
						<div class="hr-emp-preview-body">
							<Skeleton v-if="!preview" :rows="3" />
							<EmployeePanel v-else :data="preview" compact />
						</div>
					</aside>
				</template>
			</ListCard>
		</div>
	</div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import Icon from "../../../shared/components/Icon.vue";
import TopBar from "../../../shared/components/TopBar.vue";
import Skeleton from "../../../shared/components/Skeleton.vue";
import Empty from "../../../shared/components/Empty.vue";
import ListHead from "../../../shared/components/ListHead.vue";
import ListCard from "../../../shared/components/ListCard.vue";
import DataTable from "../../../shared/components/DataTable.vue";
import EmployeePanel from "./EmployeePanel.vue";
import { call, go, initials, remember_tab, show_error, state, thai_date, tone } from "../../../shared/api.js";
import { matches, use_wide } from "../../../shared/table.js";

const API = "consbiz.hr_people";
const COLUMNS = [
	{ key: "employee_name", label: "พนักงาน", sort: true, class: "col-subject" },
	{ key: "designation", label: "ตำแหน่ง", sort: true },
	{ key: "department", label: "แผนก", sort: true, class: "col-wide" },
	{ key: "project", label: "โครงการ", sort: (r) => r.project_name || r.project || "" },
	{ key: "date_of_joining", label: "เริ่มงาน", sort: true, class: "col-date col-wide" },
	{ key: "status", label: "สถานะ", class: "col-status" },
];
const STATUS = { Active: "ทำงานอยู่", Inactive: "ไม่ใช้งาน", Suspended: "พักงาน", Left: "ลาออกแล้ว" };
const FILTERS = {
	active: (r) => r.status === "Active",
	probation: (r) => r.status === "Active" && r.probation,
	warned: (r) => r.warnings > 0,
	left: (r) => r.status !== "Active",
	all: () => true,
};

const data = ref(null);
const loading = ref(false);
const txt = ref("");
const filter = ref(FILTERS[state.route.params.filter] ? state.route.params.filter : "active");
const preview = ref(null);
const preview_name = ref(null);

// ตาราง (จอ ≥768) / แผงตัวอย่างเมื่อเนื้อหากว้างพอ (จอ ≥ 1180)
const table = use_wide();
const wide = ref(window.matchMedia("(min-width: 1180px)").matches);
const media = window.matchMedia("(min-width: 1180px)");
const on_media = (e) => (wide.value = e.matches);
onMounted(() => media.addEventListener("change", on_media));
onBeforeUnmount(() => media.removeEventListener("change", on_media));
const split = computed(() => wide.value);

const rows = computed(() => data.value?.rows || []);
const count = (key) => rows.value.filter(FILTERS[key]).length;
const tabs = computed(() => [
	{ value: "active", label: "ทำงานอยู่", count: count("active") },
	{ value: "probation", label: "ทดลองงาน", count: count("probation") },
	{ value: "warned", label: "มีใบเตือน", count: count("warned") },
	{ value: "left", label: "ออกแล้ว", count: count("left") },
	{ value: "all", label: "ทั้งหมด", count: rows.value.length },
]);
const shown = computed(() =>
	rows.value.filter(
		(r) => FILTERS[filter.value](r) && matches(txt.value, r.employee_name, r.name, r.designation, r.project_name, r.department)
	)
);

async function load() {
	loading.value = true;
	try {
		data.value = await call(`${API}.get_employees`, { company: state.company || undefined });
	} catch (error) {
		show_error(error);
		data.value ??= { rows: [] };
	} finally {
		loading.value = false;
	}
}

async function open(r) {
	if (!split.value || preview_name.value === r.name) return go("hr-employee", { name: r.name });
	preview_name.value = r.name;
	preview.value = null;
	try {
		const result = await call(`${API}.get_employee`, { name: r.name });
		if (preview_name.value === r.name) preview.value = result;
	} catch (error) {
		show_error(error);
	}
}

function close_preview() {
	preview_name.value = null;
	preview.value = null;
}

watch(filter, (value) => remember_tab("hr-employees", value, "active"));
watch(() => state.company, load);
load();
</script>

<style scoped>
.hr-emp-cell { display: inline-flex; align-items: center; gap: 10px; min-width: 0; }
.hr-emp-cell .ss-avatar { width: 30px; height: 30px; flex: none; font-size: var(--ss-fs-sm); }
.hr-emp-cell .ss-avatar img,
.hr-emp-row .ss-avatar img { width: 100%; height: 100%; object-fit: cover; border-radius: inherit; }
.hr-emp-preview { display: flex; flex-direction: column; }
.hr-emp-preview-body { flex: 1; min-height: 0; overflow-y: auto; padding: 12px 14px; }
</style>
