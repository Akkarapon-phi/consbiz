<!-- รายการเอกสาร 1 ชนิดต่อเมนู ของหมวดสารบรรณและผู้รับเหมาช่วง (common/kinds.js) ต้นแบบหน้าตา = รายการ BOQ (BoqList.vue)
     ชนิด = ชื่อหน้า (letters-in / letters-out / transmittals / envelopes) กรองตามบริษัท/โครงการของแอปออฟฟิศ -->
<template>
	<div>
		<TopBar :title="kind.label">
			<template #search>
				<HeaderSearch v-if="wide" v-model="txt" :placeholder="`ค้นหา${kind.label}`" />
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
					v-if="!wide && can_create"
					type="button"
					class="ss-btn ss-btn--primary ss-list-create"
					:aria-label="`สร้าง${kind.label}`"
					@click="create"
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
						type="button"
						class="ss-icon-btn"
						:class="{ 'is-spinning': loading }"
						aria-label="โหลดใหม่"
						title="โหลดใหม่"
						@click="load"
					>
						<Icon name="refresh" :size="17" />
					</button>
					<button
						v-if="can_create"
						type="button"
						class="ss-btn ss-btn--primary ss-list-create"
						@click="create"
					>
						<Icon name="plus" :size="18" :stroke="2.6" />
						<span>สร้าง{{ kind.label }}</span>
					</button>
				</div>
			</div>
			<template v-else>
				<label class="ss-search">
					<Icon name="search" :size="17" />
					<input v-model="txt" type="search" :placeholder="`ค้นหา${kind.label}`" />
				</label>
				<Segmented v-model="filter" :options="tabs" />
			</template>

			<Skeleton v-if="rows === null" />
			<Empty v-else-if="!shown.length" :icon="kind.icon" :title="`ไม่มี${kind.label}`" />
			<DataTable v-else-if="wide" :rows="shown" :columns="COLUMNS" @open="open">
				<template #name="{ row }">
					<span class="ss-doc-no">{{ row.name }}</span>
				</template>
				<template #title="{ row }">
					<span class="ss-cell-main" :title="kind.title(row)">{{
						kind.title(row) || "—"
					}}</span>
					<small>{{ row.project || row.company }}</small>
				</template>
				<template #party="{ row }">{{ kind.party(row) || "—" }}</template>
				<template #[kind.date]="{ row }">{{
					row[kind.date] ? thai_date(row[kind.date], { year: true }) : "—"
				}}</template>
				<template #status="{ row }">
					<span class="ss-tag" :class="`tone-${row.status_tone}`">{{
						row.status_label
					}}</span>
					<small v-if="kind.note?.(row)">{{ kind.note(row) }}</small>
				</template>
				<template v-if="kind.amount" #[kind.amount]="{ row }"
					><b>{{ money(row[kind.amount]) }}</b></template
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
							<span class="ss-card-title">{{ kind.title(row) || row.name }}</span>
							<span class="ss-card-meta"
								>{{ row.name
								}}{{ kind.party(row) ? ` · ${kind.party(row)}` : "" }}</span
							>
						</span>
						<span class="ss-tag" :class="`tone-${row.status_tone}`">{{
							row.status_label
						}}</span>
					</div>
					<div class="ss-chips">
						<span v-if="row[kind.date]" class="ss-chip">
							<Icon name="calendar" :size="12" />
							{{ thai_date(row[kind.date], { year: true }) }}
						</span>
						<span v-if="row.project" class="ss-chip">{{ row.project }}</span>
						<span v-if="kind.amount" class="ss-chip"
							><b>{{ money(row[kind.amount]) }}</b></span
						>
						<span v-if="kind.note?.(row)" class="ss-chip">
							<Icon name="user" :size="12" /> {{ kind.note(row) }}
						</span>
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
	boot,
	call,
	go,
	money,
	remember_tab,
	scope_args,
	scope_key,
	show_error,
	state,
	thai_date,
	time_ago,
} from "../../../shared/api.js";
import { LIST_KINDS } from "./kinds.js";

const view = state.route.view;
const kind = LIST_KINDS[view];
const can_create = !!boot[kind.boot]?.[view]?.create;
const COLUMNS = [
	{ key: "name", label: "เลขที่", sort: true, class: "col-no" },
	{ key: "title", label: kind.title_label || "เรื่อง", sort: true, class: "col-subject" },
	{ key: "party", label: kind.party_label, class: "col-wide" },
	{ key: kind.date, label: kind.date_label, sort: true, class: "col-date is-date" },
	...(kind.amount
		? [{ key: kind.amount, label: kind.amount_label, sort: true, class: "is-num col-nowrap" }]
		: []),
	{ key: "status", label: "สถานะ", class: "col-status" },
	{ key: "modified", label: "แก้ไขล่าสุด", sort: true, class: "col-modified col-wide" },
];
// DataTable ใช้ key ของคอลัมน์เป็นค่าเรียง: ใส่ title ให้ทุกแถว (หนังสือ/ใบนำส่งมีช่อง title อยู่แล้ว)
const with_title = (row) => ({ ...row, title: kind.title(row) });

const wide = use_wide();
const rows = ref(null);
const loading = ref(false);
const txt = ref("");
const default_filter = kind.filters[0].value;
const filter = ref(
	kind.filters.some((f) => f.value === state.route.params.tab)
		? state.route.params.tab
		: default_filter
);

const in_filter = (f, row) => f.test(row, boot.user);
const tabs = computed(() =>
	kind.filters
		.map((f) => ({
			value: f.value,
			label: f.label,
			count: (rows.value || []).filter((row) => in_filter(f, row)).length,
		}))
		// "รอฉันอนุมัติ" แสดงเมื่อมีเท่านั้น (คนส่วนใหญ่ไม่ใช่ผู้อนุมัติ)
		.filter((t) => t.value !== "mine" || t.count || filter.value === "mine")
);
const shown = computed(() => {
	const active = kind.filters.find((f) => f.value === filter.value) || kind.filters[0];
	return (rows.value || []).filter(
		(row) =>
			in_filter(active, row) && matches(txt.value, ...kind.search.map((field) => row[field]))
	);
});

const open = (row) => go(...kind.open(row));
const create = () => go(...kind.create());

async function load() {
	loading.value = true;
	try {
		const { company, project } = scope_args();
		rows.value = (await call(`${kind.api}.get_list`, { kind: view, company, project })).map(
			with_title
		);
	} catch (error) {
		show_error(error);
		rows.value ??= [];
	} finally {
		loading.value = false;
	}
}

watch(filter, (value) => remember_tab(view, value, default_filter));
watch(scope_key, load);
load();
</script>
