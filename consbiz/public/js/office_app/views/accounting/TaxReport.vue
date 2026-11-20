<!-- รายการภาษีและรายงานยื่นแบบ ใช้เดือนและสาขาชุดเดียวกัน -->
<template>
	<div>
		<KindList v-if="is_list" class="tax-list" :list_params="list_params" @filter="tab = $event">
			<template v-if="report" #tools>
				<SelectBox
					v-if="tabs.length > 1"
					v-model="report"
					:options="tabs"
					label="แบบรายงาน"
					variant="tool"
				/>
				<button
					type="button"
					class="ss-icon-btn"
					:disabled="printing"
					:aria-label="`พิมพ์${print_title}`"
					:title="`พิมพ์${print_title}`"
					@click="preview"
				>
					<Icon name="printer" :size="17" />
				</button>
				<a class="ss-icon-btn" :href="excel_url" aria-label="Excel" title="Excel"
					><Icon name="file" :size="17"
				/></a>
			</template>
			<template #filters>
				<TaxReportFilters
					v-model:month="month"
					v-model:address="address"
					:addresses="addresses"
					@shift="shift"
				/>
			</template>
			<template #totals="{ rows }"><TaxTotals :rows="rows" /></template>
		</KindList>
		<TopBar v-if="!is_list" title="รายงานภาษี" />
		<div v-if="!is_list" class="ss-content">
			<div v-if="data" :class="wide ? 'ss-stats ss-stats--3' : 'ss-card ss-facts'">
				<div v-for="stat in stats" :key="stat.label" :class="wide ? 'ss-stat' : 'ss-fact'">
					<template v-if="wide">
						<span
							class="ss-stat-value"
							:class="{ 'ss-stat-value--money': stat.amount }"
							>{{ stat.value }}</span
						>
						<span class="ss-stat-label">{{ stat.label }}</span>
					</template>
					<template v-else
						><span>{{ stat.label }}</span
						><b>{{ stat.value }}</b></template
					>
				</div>
			</div>
			<ListHead v-if="wide" v-model="report" :tabs="tabs">
				<!-- ปุ่ม Excel (ลิงก์) เป็นปุ่มหลักขวาสุด: โหลดใหม่จึงอยู่ใน tools ก่อนหน้า -->
				<template #tools>
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
						type="button"
						class="ss-icon-btn"
						:disabled="printing || !data"
						title="พิมพ์รายงาน"
						aria-label="พิมพ์รายงาน"
						@click="preview"
					>
						<Icon name="printer" :size="17" />
					</button>
					<a class="ss-btn ss-btn--primary ss-list-create" :href="excel_url">
						<Icon name="file" :size="18" /> <span>Excel</span>
					</a>
				</template>
				<!-- แถวตัวกรอง: เดือน → ที่อยู่บริษัท -->
				<template #filters>
					<TaxReportFilters
						v-model:month="month"
						v-model:address="address"
						:addresses="addresses"
						@shift="shift"
					/>
				</template>
			</ListHead>
			<template v-else>
				<Segmented v-model="report" :options="tabs" />
				<TaxReportFilters
					v-model:month="month"
					v-model:address="address"
					:addresses="addresses"
					@shift="shift"
				/>
				<div class="acc-month">
					<button
						type="button"
						class="ss-icon-btn"
						:disabled="printing || !data"
						title="พิมพ์รายงาน"
						aria-label="พิมพ์รายงาน"
						@click="preview"
					>
						<Icon name="printer" :size="17" />
					</button>
					<a class="ss-icon-btn" :href="excel_url" aria-label="Excel"
						><Icon name="file" :size="18"
					/></a>
				</div>
			</template>

			<ListCard :on="wide">
				<Empty v-if="failed" icon="alert" title="โหลดรายงานไม่สำเร็จ" />
				<Skeleton v-else-if="!data" :rows="6" />
				<template v-else>
					<Empty
						v-if="!data.rows.length"
						icon="list"
						:title="`ไม่มีรายการ${current_label}เดือนนี้`"
					/>
					<TaxReportTable v-show="data.rows.length" :data="data" @open="open" />
					<footer class="ss-list-foot">
						{{
							is_vat
								? "เรียงตามเลขที่ เดือนตามวันที่ยื่น (รวมใบที่ยื่นล่าช้าเข้าเดือนนี้)"
								: "เฉพาะหนังสือรับรองที่ยืนยันแล้ว ตามวันที่จ่าย"
						}}
					</footer>
				</template>
			</ListCard>
		</div>
		<HtmlViewer
			:open="!!print_html"
			:html="print_html"
			:title="print_title"
			:name="month"
			:width="1123"
			:height="794"
			:document_kind="`tax-${report}`"
			fit_height
			@close="print_html = ''"
		/>
	</div>
</template>

<script setup>
import HtmlViewer from "../../../shared/components/HtmlViewer.vue";
import ListCard from "../../../shared/components/ListCard.vue";
import { render } from "../../../shared/microtemplate.js";
import KindList from "../common/KindList.vue";
import TaxReportFilters from "./TaxReportFilters.vue";
import TaxReportTable from "./TaxReportTable.vue";
import { computed, ref, watch } from "vue";
import Empty from "../../../shared/components/Empty.vue";
import Icon from "../../../shared/components/Icon.vue";
import Segmented from "../../../shared/components/Segmented.vue";
import Skeleton from "../../../shared/components/Skeleton.vue";
import TopBar from "../../../shared/components/TopBar.vue";
import ListHead from "../../../shared/components/ListHead.vue";
import { use_wide } from "../../../shared/table.js";
import {
	boot,
	call,
	go,
	money,
	replace_params,
	show_error,
	state,
	toast,
} from "../../../shared/api.js";
import SelectBox from "../../../shared/components/SelectBox.vue";
import TaxTotals from "./TaxTotals.vue";
import { API, TAX_STATUS_FILTERS } from "./kinds.js";
import { report_scope } from "./report_data.js";
import { use_tax_period } from "./tax_period.js";

const REPORTS = [
	{ value: "sales", label: "ภาษีขาย" },
	{ value: "purchase", label: "ภาษีซื้อ" },
	{ value: "pnd3", label: "ภ.ง.ด.3" },
	{ value: "pnd53", label: "ภ.ง.ด.53" },
];
const list_reports = {
	"acc-purchase-tax": ["purchase"],
	"acc-sales-tax": ["sales"],
	"acc-wht": ["pnd3", "pnd53"],
};
const view = state.route.view;
const keys = list_reports[view];
const is_list = !!keys;
const allowed = boot.accounting?.reports || [];
const tabs = REPORTS.filter(
	(r) => allowed.includes(r.value) && (!is_list || keys.includes(r.value))
);

const wide = use_wide();
const params = state.route.params;
const report = ref(tabs.some((t) => t.value === params.report) ? params.report : tabs[0]?.value);
const tab = ref(TAX_STATUS_FILTERS.some((t) => t.value === params.tab) ? params.tab : "submitted");
const { month, address, addresses, list_params, shift } = use_tax_period();
const data = ref(null);
const loading = ref(false);
const printing = ref(false);
const print_html = ref("");

const is_vat = computed(() => report.value === "sales" || report.value === "purchase");
const stats = computed(() => [
	{ label: "รายการ", value: data.value.totals.count },
	{
		label: is_vat.value ? "มูลค่าสินค้า/บริการ" : "จำนวนเงินที่จ่าย",
		value: money(data.value.totals.tax_base),
		amount: true,
	},
	{
		label: is_vat.value ? "ภาษีมูลค่าเพิ่ม" : "ภาษีที่หัก",
		value: money(data.value.totals.tax_amount),
		amount: true,
	},
]);
const current_label = computed(() => REPORTS.find((r) => r.value === report.value)?.label || "");
const print_title = computed(() => `รายงาน${current_label.value}`);
const report_args = computed(() => ({
	key: report.value,
	...list_params.value,
	company: report_scope().company,
}));
const query = computed(() =>
	new URLSearchParams(
		Object.entries(report_args.value).filter(([, value]) => value != null)
	).toString()
);
const excel_url = computed(() => `/api/method/${API}.export_report?${query.value}`);

async function preview() {
	const key = query.value;
	printing.value = true;
	try {
		if (is_vat.value) {
			const result = await call(
				"consbiz.vat_report_print.render_vat_report",
				report_args.value
			);
			if (key === query.value) print_html.value = result.html;
		} else {
			const form = await call(`${API}.get_official_form`, report_args.value);
			if (key !== query.value) return;
			if (form.empty) {
				toast(`ไม่มีรายการ${current_label.value}ในเดือนที่เลือก`);
				return;
			}
			const body = render(form.template, { data: form.data, filters: form.filters });
			// ภ.ง.ด. = แบบเต็มหน้า (ภาพพื้น 295x210mm)
			print_html.value = `<!doctype html><html lang="th"><head><meta charset="utf-8"><link rel="stylesheet" href="${form.print_bundle}"><style>${form.print_css}
@page { size: A4 landscape; margin: 0; } body { background: #fff; margin: 0; } .print-format-gutter { padding: 0 !important; background: #fff !important; } .print-format { margin: 0 !important; box-shadow: none !important; border-radius: 0 !important; max-width: none !important; min-height: 0 !important; padding: 0 !important; }</style></head><body><div class="print-format-gutter"><div class="print-format landscape">${body}</div></div></body></html>`;
		}
	} catch (error) {
		if (key === query.value) show_error(error);
	} finally {
		printing.value = false;
	}
}

function open(r) {
	if (!r.name) return;
	// รายงานภาษีขาย/ซื้อต่อท้ายใบที่ยกเลิกด้วย " (CANCEL)"
	if (is_vat.value)
		go("acc-tax-doc", {
			kind: report.value === "sales" ? "acc-sales-tax" : "acc-purchase-tax",
			name: r.docname,
		});
	else go("acc-wht-doc", { name: r.name });
}

let report_job = 0;
const failed = ref(false);
async function load() {
	const job = ++report_job;
	failed.value = false;
	print_html.value = "";
	if (!report.value) return;
	loading.value = true;
	try {
		const result = await call(`${API}.get_report`, report_args.value);
		if (job === report_job) data.value = result;
	} catch (e) {
		if (job !== report_job) return;
		show_error(e);
		data.value = null;
		failed.value = true;
	} finally {
		if (job === report_job) loading.value = false;
	}
}

if (is_list) {
	watch([month, address, report, tab], () =>
		replace_params(view, {
			month: month.value,
			...(address.value ? { address: address.value } : {}),
			...(keys.length > 1 && report.value ? { report: report.value } : {}),
			...(tab.value === "submitted" ? {} : { tab: tab.value }),
		})
	);
	watch(query, () => {
		print_html.value = "";
	});
} else {
	watch([report, month], () =>
		replace_params(view, { report: report.value, month: month.value })
	);
	watch(query, load, { immediate: true });
}
</script>

<style scoped>
.tax-list {
	display: contents;
}
.acc-month {
	display: inline-flex;
	align-items: center;
	gap: 4px;
}
</style>
