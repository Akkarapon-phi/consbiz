<template>
	<div>
		<TopBar title="ภาษีถูกหัก ณ ที่จ่าย" />
		<div class="ss-content">
			<ListHead
				v-if="wide"
				v-model="tab"
				:tabs="tabs"
				v-model:search="search"
				search_placeholder="ค้นหาเลขที่ ลูกค้า โครงการ"
				@refresh="load"
			>
				<template #tools>
					<button
						class="ss-icon-btn"
						:disabled="!data"
						title="พิมพ์รายงาน"
						aria-label="พิมพ์รายงาน"
						@click="preview"
					>
						<Icon name="printer" :size="17" />
					</button>
					<a class="ss-icon-btn" :href="excel" title="Excel" aria-label="Excel"
						><Icon name="file" :size="17"
					/></a>
				</template>
				<template #filters
					><TaxReportFilters
						v-model:month="month"
						v-model:address="address"
						:addresses="addresses"
						@shift="shift" /><ProjectFilter
				/></template>
			</ListHead>
			<template v-else>
				<div class="mobile-tools">
					<label class="ss-search"
						><Icon name="search" :size="16" /><input
							v-model="search"
							type="search"
							placeholder="ค้นหาเลขที่ ลูกค้า โครงการ"
					/></label>
					<button
						class="ss-icon-btn"
						:disabled="!data"
						aria-label="พิมพ์รายงาน"
						@click="preview"
					>
						<Icon name="printer" :size="17" />
					</button>
					<a class="ss-icon-btn" :href="excel" aria-label="Excel"
						><Icon name="file" :size="17"
					/></a>
				</div>
				<StatusTabs v-model="tab" :options="tabs" />
				<div class="mobile-tools filters">
					<TaxReportFilters
						v-model:month="month"
						v-model:address="address"
						:addresses="addresses"
						@shift="shift"
					/><ProjectFilter />
				</div>
			</template>
			<ListCard :on="wide">
				<Empty v-if="failed" title="โหลดรายการไม่สำเร็จ" icon="alert" />
				<Skeleton v-else-if="!data" />
				<Empty v-else-if="!shown.length" title="ไม่มีรายการภาษีถูกหัก" icon="file" />
				<DataTable v-else-if="wide" :columns="columns" :rows="shown" @open="open">
					<template #name="{ row }"
						><b class="ss-doc-no">{{ row.name }}</b
						><small
							><span class="ss-tag" :class="'tone-' + row.status_tone">{{
								row.status_label
							}}</span></small
						></template
					>
					<template #party="{ row }"
						><span>{{ row.party_name || row.party }}</span
						><small>{{ row.project_name || row.project }}</small></template
					>
					<template #posting_date="{ row }">{{ date(row.posting_date) }}</template>
					<template #tax_base="{ row }">{{
						row.tax_base == null ? "—" : money(row.tax_base)
					}}</template>
					<template #amount="{ row }"
						><b>{{ money(row.amount) }}</b></template
					>
				</DataTable>
				<div v-else class="ss-list">
					<button v-for="r in shown" :key="r.name" class="ss-card" @click="open(r)">
						<div class="ss-card-head">
							<b>{{ r.name }}</b
							><span class="ss-tag" :class="'tone-' + r.status_tone">{{
								r.status_label
							}}</span>
						</div>
						<b>{{ r.party_name || r.party }}</b
						><small class="ss-card-meta">{{ r.project_name || r.project }}</small>
						<div class="ss-card-meta">{{ r.refs }}</div>
						<div class="ss-chips ss-chips--wrap">
							<span class="ss-chip">{{ date(r.posting_date) }}</span
							><span v-if="r.tax_base != null" class="ss-chip"
								>ฐาน {{ money(r.tax_base) }}</span
							><b class="ss-chip">ภาษี {{ money(r.amount) }}</b
							><RowSocial :row="r" icons_only />
						</div>
					</button>
				</div>
				<footer v-if="data" class="ss-list-foot"><TaxTotals :rows="shown" /></footer>
			</ListCard>
		</div>
		<div hidden>
			<table ref="paper">
				<thead>
					<tr>
						<th v-for="c in print_columns" :key="c.key">{{ c.label }}</th>
					</tr>
				</thead>
				<tbody>
					<tr v-for="r in selected" :key="r.name">
						<td v-for="c in print_columns" :key="c.key" :class="c.class">
							{{ cell(r, c.key) }}
						</td>
					</tr>
					<tr>
						<th :colspan="print_columns.length - 1">
							รวม {{ selected.length }} รายการ
						</th>
						<th class="is-num">
							{{ money(selected.reduce((n, r) => n + r.amount, 0)) }}
						</th>
					</tr>
				</tbody>
			</table>
		</div>
		<HtmlViewer
			:open="!!html"
			:html="html"
			:title="title"
			:name="month"
			:width="1123"
			:height="794"
			document_kind="received-wht"
			fit_height
			@close="html = ''"
		/>
	</div>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import { go, money, replace_params, state, thai_date } from "../../../shared/api.js";
import { use_wide, matches } from "../../../shared/table.js";
import TopBar from "../../../shared/components/TopBar.vue";
import StatusTabs from "../../../shared/components/StatusTabs.vue";
import ListHead from "../../../shared/components/ListHead.vue";
import ListCard from "../../../shared/components/ListCard.vue";
import DataTable from "../../../shared/components/DataTable.vue";
import Icon from "../../../shared/components/Icon.vue";
import HtmlViewer from "../../../shared/components/HtmlViewer.vue";
import Empty from "../../../shared/components/Empty.vue";
import Skeleton from "../../../shared/components/Skeleton.vue";
import ProjectFilter from "../../../shared/docs/ProjectFilter.vue";
import TaxReportFilters from "./TaxReportFilters.vue";
import { tax_print } from "./tax_print.js";
import { report_scope, use_report } from "./report_data.js";
import { TAX_STATUS_FILTERS } from "./kinds.js";
import { use_tax_period } from "./tax_period.js";
import TaxTotals from "./TaxTotals.vue";
import RowSocial from "../../../shared/components/RowSocial.vue";

const wide = use_wide();
const title = "รายงานภาษีถูกหัก ณ ที่จ่าย";
const date = (value) => thai_date(value, { year: true });
const { month, address, addresses, period, shift } = use_tax_period();
const tab = ref(
	TAX_STATUS_FILTERS.some((filter) => filter.value === state.route.params.tab)
		? state.route.params.tab
		: "submitted"
);
const search = ref("");
const paper = ref(null);
const html = ref("");
const args = () => ({
	...report_scope(),
	month: month.value,
	...(address.value ? { company_address: address.value } : {}),
});
const { data, failed, load } = use_report("consbiz.received_wht.receipts", () => ({
	...args(),
	status: "all",
}));
const tabs = computed(() =>
	TAX_STATUS_FILTERS.map(({ value, label, test }) => ({
		value,
		label,
		count: (data.value || []).filter(test).length,
	}))
);
const selected = computed(() =>
	(data.value || []).filter(TAX_STATUS_FILTERS.find((filter) => filter.value === tab.value).test)
);
const shown = computed(() =>
	selected.value.filter((r) =>
		matches(search.value, r.name, r.party_name, r.party, r.refs, r.project_name, r.project)
	)
);
const cols = (base) => [
	{ key: "name", label: "เลขที่ / สถานะ", class: "col-no" },
	{ key: "party", label: "ลูกค้า / โครงการ", class: "col-flex-party" },
	{ key: "refs", label: "ใบแจ้งหนี้", class: "col-nowrap" },
	{ key: "posting_date", label: "วันที่รับ", class: "col-nowrap" },
	...(base ? [{ key: "tax_base", label: "ฐานภาษี", class: "is-num" }] : []),
	{ key: "amount", label: "ภาษีถูกหัก", class: "is-num" },
];
const columns = computed(() => cols(shown.value.some((r) => r.tax_base != null)));
const print_columns = computed(() => cols(selected.value.some((r) => r.tax_base != null)));
function cell(r, key) {
	if (key === "name") return [r.name, r.status_label].join(" · ");
	if (key === "party")
		return [r.party_name || r.party, r.project_name || r.project].filter(Boolean).join(" · ");
	if (key === "posting_date") return date(r[key]);
	if (key === "tax_base" || key === "amount") return r[key] == null ? "—" : money(r[key]);
	return r[key];
}
function preview() {
	const scope = [
		state.company || "ทุกบริษัท",
		addresses.value.find((option) => option.value === address.value)?.label,
		state.project?.project_name,
	];
	html.value = tax_print(paper.value, title, period.value, scope.filter(Boolean).join(" · "));
}
const excel = computed(
	() =>
		"/api/method/consbiz.received_wht.export_month?" +
		new URLSearchParams({ ...args(), status: tab.value })
);
watch([tab, month, address], () => {
	html.value = "";
	replace_params("acc-wht-received", {
		month: month.value,
		...(address.value ? { address: address.value } : {}),
		...(tab.value === "submitted" ? {} : { tab: tab.value }),
	});
});
const open = (r) => go("acc-payment", { kind: "acc-wht-received", name: r.name });
</script>

<style scoped>
.mobile-tools {
	display: flex;
	align-items: center;
	gap: 6px;
	min-width: 0;
}
.mobile-tools .ss-search {
	flex: 1;
	min-width: 0;
}
.filters {
	flex-wrap: wrap;
}
</style>
