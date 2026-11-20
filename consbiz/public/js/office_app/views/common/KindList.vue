<!-- รายการเอกสาร 1 ชนิดต่อเมนู ของหมวดสารบรรณและผู้รับเหมาช่วง (common/kinds.js) ต้นแบบหน้าตา = รายการ BOQ (BoqList.vue)
     ชนิด = ชื่อหน้า (letters-in / letters-out / transmittals / envelopes) กรองตามบริษัท/โครงการของแอปออฟฟิศ -->
<template>
	<div>
		<TopBar :title="kind.label">
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
					:aria-label="`สร้าง${kind.create_label || kind.label}`"
					@click="create"
				>
					<Icon name="plus" :size="18" :stroke="2.6" />
				</button>
			</template>
		</TopBar>

		<div class="ss-content">
			<ListHead
				v-model:search="txt"
				:search_placeholder="`ค้นหา${kind.label}`"
				v-if="wide"
				v-model="filter"
				:tabs="tabs"
				:loading="loading"
				@refresh="load"
				:create="can_create ? `สร้าง${kind.create_label || kind.label}` : ''"
				@create="create"
			>
				<template v-if="$slots.tools" #tools><slot name="tools" /></template>
				<template v-if="$slots.filters || project_filter" #filters><slot name="filters" /><ProjectFilter v-if="project_filter" /></template>
			</ListHead>
			<template v-else>
				<div :class="$slots.tools ? 'kind-search-tools' : 'kind-search-only'">
					<label class="ss-search">
						<Icon name="search" :size="17" />
						<input v-model="txt" type="search" :placeholder="`ค้นหา${kind.label}`" />
					</label>
					<slot name="tools" />
				</div>
				<StatusTabs v-if="kind.overflow_tabs" v-model="filter" :options="tabs" />
				<Segmented v-else v-model="filter" :options="tabs" />
				<slot name="filters" /><ProjectFilter v-if="project_filter" />
			</template>

			<!-- จอ ≥768: การ์ดเดียวต่อจากหัวรายการ (ListCard) ไม่มีข้อมูล = Empty กลางการ์ด -->
			<ListCard :on="wide">
			<Skeleton v-if="rows === null" />
			<Empty v-else-if="!shown.length" :icon="kind.icon" :title="`ไม่มี${kind.label}`" />
			<DataTable v-else-if="wide" :rows="shown" :columns="COLUMNS" @open="open">
				<template #name="{ row }">
					<span class="ss-doc-no">{{ row.name }}</span>
					<small v-if="table_pair && row.status_label">
						<span class="ss-tag" :class="`tone-${row.status_tone}`">{{ row.status_label }}</span>
					</small>
					<small v-if="kind.status_note?.(row)">{{ kind.status_note(row) }}</small>
				</template>
				<template #title="{ row }">
					<span class="ss-cell-main" :title="kind.title(row)">{{
						kind.title(row) || "—"
					}}</span>
					<small v-if="row.project || row.company">{{ row.project || row.company }}</small>
				</template>
				<template #party="{ row }">
					<template v-if="table_pair">
						<span class="ss-cell-main" :title="kind.party(row)">{{ kind.party(row) || "—" }}</span>
						<small v-if="table_pair.project && row.project" :title="project_text(row)">
							{{ project_text(row) }}
						</small>
					</template>
					<template v-else>{{ kind.party(row) || "—" }}</template>
				</template>
				<template v-for="column in detail_columns" :key="column.key" #[column.key]="{ row }">
					{{ (column.format ? column.format(row) : row[column.key]) || "—" }}
				</template>
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
					><b>{{ formatted_amount(row) }}</b></template
				>
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
							<span v-if="kind.card_details && row.project" class="ss-card-meta">{{ project_text(row) }}</span>
							<span class="ss-card-meta"
								>{{ row.name
								}}{{ !kind.card_details && kind.party(row) ? ` · ${kind.party(row)}` : "" }}</span
							>
						</span>
						<span class="ss-tag" :class="`tone-${row.status_tone}`">{{
							row.status_label
						}}</span>
					</div>
					<div class="ss-chips ss-chips--wrap">
						<span v-if="row[kind.date]" class="ss-chip ss-chip--keep">
							<Icon name="calendar" :size="12" />
							{{ thai_date(row[kind.date], { year: true }) }}
						</span>
						<span v-for="item in kind.card_details?.(row)" :key="item" class="ss-chip">{{ item }}</span>
						<span v-if="kind.status_note?.(row)" class="ss-tag tone-amber">{{ kind.status_note(row) }}</span>
						<span v-if="row.project && !kind.card_details" class="ss-chip">{{ row.project }}</span>
						<span v-if="kind.amount" class="ss-chip ss-chip--keep"
							><b>{{ formatted_amount(row) }}</b></span
						>
						<span v-if="kind.note?.(row)" class="ss-chip">
							<Icon name="user" :size="12" /> {{ kind.note(row) }}
						</span>
						<RowSocial :row="row" icons_only />
					</div>
				</button>
			</div>
			<footer v-if="rows !== null && $slots.totals" class="ss-list-foot">
				<slot name="totals" :rows="shown" />
			</footer>
			</ListCard>
		</div>
	</div>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import ProjectFilter from "../../../shared/docs/ProjectFilter.vue";
import Icon from "../../../shared/components/Icon.vue";
import TopBar from "../../../shared/components/TopBar.vue";
import StatusTabs from "../../../shared/components/StatusTabs.vue";
import Segmented from "../../../shared/components/Segmented.vue";
import Skeleton from "../../../shared/components/Skeleton.vue";
import Empty from "../../../shared/components/Empty.vue";
import RowSocial from "../../../shared/components/RowSocial.vue";
import DataTable from "../../../shared/components/DataTable.vue";
import ListHead from "../../../shared/components/ListHead.vue";
import ListCard from "../../../shared/components/ListCard.vue";
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
} from "../../../shared/api.js";
import { LIST_KINDS } from "./kinds.js";

const props = defineProps({ list_params: Object });
const view = state.route.view;
const kind = LIST_KINDS[view];
const project_filter = view.startsWith("acc-") && (kind.table_pair?.project || ["acc-sales-tax", "acc-purchase-tax"].includes(view));
const can_create = !!boot[kind.boot]?.[view]?.create;
const formatted_amount = (row) => [money(row[kind.amount]), kind.amount_currency && row.currency].filter(Boolean).join(" ");
const table_pair = kind.table_pair;
const project_text = (row) => row.project_name || row.project;
const doc_number = { key: "name", label: "เลขที่", sort: true, class: "col-no" };
const date_column = { key: kind.date, label: kind.date_label, sort: true, class: "col-date is-date" };
const amount_columns = kind.amount
	? [{ key: kind.amount, label: kind.amount_label, sort: true, class: "is-num col-nowrap" }]
	: [];
const detail_column = (column) => ({ class: "col-nowrap", sort: true, ...column });
const before_date = (table_pair?.fields || []).map(detail_column);
const after_date = (table_pair?.after_date || []).map(detail_column);
const detail_columns = [...before_date, ...after_date];
const COLUMNS = table_pair
	? [
			{ ...doc_number, label: "เลขที่ / สถานะ" },
			{
				key: "party",
				label: table_pair.project ? `${kind.party_label} / โครงการ` : kind.party_label,
				sort: kind.party,
				class: "col-flex-party",
			},
			...before_date,
			date_column,
			...after_date,
			...amount_columns,
	  ]
	: [
			doc_number,
			{ key: "title", label: kind.title_label || "เรื่อง", sort: true, class: "col-subject" },
			{ key: "party", label: kind.party_label, class: "col-wide" },
			date_column,
			...amount_columns,
			{ key: "status", label: "สถานะ", class: "col-status" },
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

let list_job = 0;
async function load() {
	const job = ++list_job;
	loading.value = true;
	try {
		const { company, project } = scope_args();
		const result = await call(`${kind.api}.get_list`, { kind: view, company, project, ...props.list_params });
		if (job === list_job) rows.value = result.map(with_title);
	} catch (error) {
		if (job !== list_job) return;
		show_error(error);
		rows.value = [];
	} finally {
		if (job === list_job) loading.value = false;
	}
}

const emit = defineEmits(["filter"]);
watch(filter, (value) => {
	if (!props.list_params) remember_tab(view, value, default_filter);
	emit("filter", value);
});
watch([scope_key, () => JSON.stringify(props.list_params)], () => {
	if (props.list_params) rows.value = null;
	load();
}, { immediate: true });
</script>

<style scoped>
.kind-search-only { display: contents; }
.kind-search-tools { display: flex; align-items: center; gap: 6px; }
.kind-search-tools .ss-search { flex: 1; min-width: 0; }
</style>
