<!-- รายการ BOQ ของแอปออฟฟิศ (API consbiz/boq_app.py) สิทธิ์เฉพาะ Projects Manager / System Manager -->
<template>
	<div>
		<TopBar title="BOQ" no_project>
			<template #search>
				<HeaderSearch
					v-if="wide"
					v-model="txt"
					placeholder="ค้นหาเลขที่ ลูกค้า หรือโครงการ"
				/>
			</template>
			<template #actions>
				<button
					v-if="!wide"
					type="button"
					class="ss-icon-btn"
					:class="{ 'is-spinning': loading }"
					aria-label="โหลดใหม่"
					@click="load"
				>
					<Icon name="refresh" :size="20" />
				</button>
				<button
					v-if="!wide && boot.docs?.boq?.create"
					type="button"
					class="ss-btn ss-btn--primary ss-list-create"
					aria-label="สร้าง BOQ"
					@click="go('boq-form', { name: 'new' })"
				>
					<Icon name="plus" :size="18" :stroke="2.6" />
				</button>
			</template>
		</TopBar>

		<div class="ss-content">
			<div v-if="wide" class="ss-list-head">
				<StatusTabs v-model="filter" :options="tabs" />
				<div class="ss-list-tools">
					<button
						v-if="boot.docs?.boq?.create"
						type="button"
						class="ss-btn ss-btn--primary ss-list-create"
						@click="go('boq-form', { name: 'new' })"
					>
						<Icon name="plus" :size="18" :stroke="2.6" />
						<span>สร้าง BOQ</span>
					</button>
					<button
						type="button"
						class="ss-icon-btn"
						:class="{ 'is-spinning': loading }"
						aria-label="โหลดใหม่"
						title="โหลดใหม่"
						@click="load"
					>
						<Icon name="refresh" :size="17" />
					</button>
				</div>
			</div>
			<Segmented v-else v-model="filter" :options="tabs" />

			<Skeleton v-if="rows === null" />
			<Empty v-else-if="!shown.length" icon="calculator" title="ไม่มี BOQ" />
			<DataTable v-else-if="wide" :rows="shown" :columns="COLUMNS" @open="open">
				<template #name="{ row }">
					<span class="ss-doc-no">{{ row.name }}</span>
					<span class="ss-doc-meta">
						<span class="ss-tag" :class="`tone-${STATUS[row.docstatus].tone}`">{{
							STATUS[row.docstatus].label
						}}</span>
					</span>
				</template>
				<template #customer="{ row }">
					<span class="ss-cell-main" :title="row.customer">{{
						row.customer || "—"
					}}</span>
					<small>{{ row.project || row.location || "" }}</small>
				</template>
				<template #date="{ row }">{{ thai_date(row.date, { year: true }) }}</template>
				<template #grand_total="{ row }"
					><b>{{ money(row.grand_total) }}</b></template
				>
				<template #modified="{ row }">{{ time_ago(row.modified) }}</template>
			</DataTable>
			<div v-else class="ss-list">
				<button
					v-for="row in shown"
					:key="row.name"
					type="button"
					class="ss-card"
					@click="open(row)"
				>
					<div class="ss-card-head">
						<span class="ss-card-main">
							<span class="ss-card-title">{{ row.customer || row.name }}</span>
							<span class="ss-card-meta"
								>{{ row.name }} · {{ row.project || row.location || "" }}</span
							>
						</span>
						<span class="ss-tag" :class="`tone-${STATUS[row.docstatus].tone}`">{{
							STATUS[row.docstatus].label
						}}</span>
					</div>
					<div class="ss-chips">
						<span class="ss-chip">{{ thai_date(row.date, { year: true }) }}</span>
						<span class="ss-chip"
							><b>{{ money(row.grand_total) }}</b></span
						>
					</div>
				</button>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import Icon from "../../../shared/components/Icon.vue";
import TopBar from "../../../shared/components/TopBar.vue";
import Segmented from "../../../shared/components/Segmented.vue";
import Skeleton from "../../../shared/components/Skeleton.vue";
import Empty from "../../../shared/components/Empty.vue";
import DataTable from "../../../shared/components/DataTable.vue";
import StatusTabs from "../../../shared/components/StatusTabs.vue";
import HeaderSearch from "../../../shared/components/HeaderSearch.vue";
import { matches, use_wide } from "../../../shared/table.js";
import {
	call,
	go,
	money,
	remember_tab,
	show_error,
	state,
	thai_date,
	time_ago,
	boot,
} from "../../../shared/api.js";

const API = "consbiz.boq_app";
const STATUS = {
	0: { label: "ร่าง", tone: "gray" },
	1: { label: "Submit แล้ว", tone: "green" },
	2: { label: "ยกเลิก", tone: "rose" },
};
const COLUMNS = [
	{ key: "name", label: "เลขที่", sort: true, class: "col-no" },
	{ key: "customer", label: "ลูกค้า / โครงการ", sort: true, class: "col-subject" },
	{ key: "date", label: "วันที่", sort: true, class: "col-date is-date" },
	{ key: "grand_total", label: "มูลค่ารวม", sort: true, class: "is-num" },
	{ key: "modified", label: "แก้ไขล่าสุด", sort: true, class: "col-modified col-wide" },
];
const FILTERS = ["draft", "submitted", "all"];

const wide = use_wide();
const rows = ref(null);
const loading = ref(false);
const txt = ref("");
const filter = ref(
	FILTERS.includes(state.route.params.filter) ? state.route.params.filter : "draft"
);

const count = (status) => (rows.value || []).filter((row) => row.docstatus === status).length;
const tabs = computed(() => [
	{ value: "draft", label: "ร่าง", count: count(0) },
	{ value: "submitted", label: "Submit แล้ว", count: count(1) },
	{ value: "all", label: "ทั้งหมด", count: rows.value?.length || 0 },
]);
const shown = computed(() =>
	(rows.value || []).filter(
		(row) =>
			(filter.value === "all" || row.docstatus === (filter.value === "draft" ? 0 : 1)) &&
			matches(txt.value, row.name, row.customer, row.project, row.location)
	)
);

const open = (row) => go("boq-form", { name: row.name });

async function load() {
	loading.value = true;
	try {
		rows.value = await call(`${API}.get_boqs`, { company: state.company || undefined });
	} catch (error) {
		show_error(error);
		rows.value ??= [];
	} finally {
		loading.value = false;
	}
}

watch(filter, (value) => remember_tab("boq", value, "draft"));
watch(() => state.company, load);
load();
</script>
