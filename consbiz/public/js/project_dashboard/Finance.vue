<script setup>
// Tab "การเงิน" ของ Construction Management (ดูอย่างเดียว)
// - ตัวเลขสรุป ณ วันที่ดู: มูลค่าสัญญาปรับปรุง, Cash Plan / Cash Actual สะสม และส่วนต่าง
// - กราฟมูลค่าสะสม (แผนถึงวันจบ จริงถึงวันที่ดู) และตาราง Cash Flow รายเดือน
// - Earned Value (PV/EV/AC) เฉพาะผู้ที่เห็นงบต้นทุน
// ข้อมูลจาก construction_management/finance.get_finance (Cash Plan ตรงกับแถว Cash Plan ของตารางสรุปในหน้า Gantt)
import { computed, onMounted, ref } from "vue";
import FrappeControl from "../construction_management/components/FrappeControl.vue";
import Chart from "./components/Chart.vue";
import ProgressCurve from "./components/ProgressCurve.vue";
import { css_color, date, money, ratio } from "./format";

const API = "consbiz.consbiz.doctype.construction_management.finance.get_finance";

const props = defineProps({ name: String });
const data = ref(null);
const loading = ref(false);
const status_date = ref(frappe.datetime.get_today());

async function load() {
	loading.value = true;
	try {
		const { message } = await frappe.call(API, { name: props.name, date: status_date.value });
		data.value = message;
	} finally {
		loading.value = false;
	}
}
defineExpose({ load });
onMounted(load);

function set_date(value) {
	if (!value || value === status_date.value) return;
	status_date.value = value;
	load();
}

const icon = (name, size = "sm") => frappe.utils.icon(name, size);
const fmt = (value, narrow = false) => money(value, data.value?.currency, narrow);
const cell = (value) => (value === null || value === undefined ? "-" : fmt(value));

const locale = frappe.boot.lang === "th" ? "th-TH" : undefined;
const month_fmt = new Intl.DateTimeFormat(locale, { month: "long", year: "numeric" });
const month_label = (value) => month_fmt.format(frappe.datetime.str_to_obj(value));

// ---------- สรุป ----------

const tiles = computed(() => {
	const d = data.value;
	const amount = d.contract.revised_amount || d.contract.total_amount || 0;
	const share = (value) => (amount ? `${format_number((value / amount) * 100, null, 2)}%` : "");
	const variance = d.summary.actual - d.summary.plan;
	return [
		{ label: __("มูลค่าสัญญาปรับปรุง"), value: fmt(amount, true), note: d.contract.variation_amount ? __("งานเพิ่ม-ลด {0}", [fmt(d.contract.variation_amount, true)]) : __("ตามสัญญาเดิม") },
		{ label: __("Cash Plan สะสม"), value: fmt(d.summary.plan, true), note: share(d.summary.plan), tone: "blue" },
		{ label: __("Cash Actual สะสม"), value: fmt(d.summary.actual, true), note: share(d.summary.actual), tone: "green" },
		{
			label: __("ส่วนต่าง (จริง - แผน)"),
			value: `${variance > 0 ? "+" : ""}${fmt(variance, true)}`,
			note: variance >= 0 ? __("เร็วกว่าแผน") : __("ช้ากว่าแผน"),
			tone: Math.abs(variance) < 0.5 ? "gray" : variance > 0 ? "green" : "red",
		},
	];
});

// ---------- กราฟมูลค่าสะสม ----------
// จุด: ต้นเดือนแรก (0), สิ้นแต่ละเดือน และวันที่ดู (เดือนปัจจุบันเทียบแผน ณ วันที่ดู)
const curve = computed(() => {
	const months = data.value?.months || [];
	if (!months.length) return [];
	const day = data.value.date;
	const rows = [{ date: months[0].month, plan: 0, actual: months[0].month <= day ? 0 : null }];
	for (const m of months) {
		if (m.month <= day && day < m.month_end) {
			rows.push({ date: day, plan: m.plan_at_date, actual: m.actual_cum });
			rows.push({ date: m.month_end, plan: m.plan_cum, actual: null });
		} else {
			rows.push({ date: m.month_end, plan: m.plan_cum, actual: m.month_end <= day ? m.actual_cum : null });
		}
	}
	return rows;
});
const curve_max = computed(() => {
	const values = curve.value.flatMap((r) => [r.plan, r.actual]).filter((v) => v !== null);
	const top = Math.max(...values, data.value?.contract.revised_amount || 0, 1);
	// ปัดขึ้นให้ป้ายแกนเป็นเลขกลมๆ
	const step = 10 ** Math.floor(Math.log10(top / 4));
	return Math.ceil(top / 4 / step) * step * 4;
});
const short_money = (value) => {
	if (Math.abs(value) >= 1e6) return `${format_number(value / 1e6, null, value % 1e6 ? 1 : 0)}M`;
	if (Math.abs(value) >= 1e3) return `${format_number(value / 1e3, null, 0)}K`;
	return format_number(value, null, 0);
};

// ---------- ตารางรายเดือน ----------

const current_month = computed(() => {
	const day = data.value?.date;
	return (data.value?.months || []).find((m) => m.month <= day && day <= m.month_end)?.month;
});
const totals = computed(() => {
	const months = data.value?.months || [];
	return {
		plan: months.at(-1)?.plan_cum || 0,
		actual: [...months].reverse().find((m) => m.actual_cum !== null)?.actual_cum || 0,
	};
});

// ---------- EVM ----------

const evm_label = new Intl.DateTimeFormat(locale, { month: "short", year: "2-digit" });
const evm_chart = computed(() => {
	const series = data.value.evm?.series || [];
	return {
		labels: series.map((row, i) =>
			i === series.length - 1 && row.date === data.value.date
				? date(row.date)
				: evm_label.format(frappe.datetime.str_to_obj(row.date))
		),
		datasets: [
			{ name: "PV", values: series.map((row) => Math.round(row.pv)) },
			{ name: "EV", values: series.map((row) => Math.round(row.ev)) },
			{ name: "AC", values: series.map((row) => Math.round(row.ac)) },
		],
	};
});
const evm_colors = [
	css_color("--consbiz-gantt-plan"),
	css_color("--consbiz-gantt-actual"),
	css_color("--consbiz-gantt-late"),
];
const index_color = (value) =>
	value === null || value === undefined ? "gray" : value >= 1 ? "green" : "red";
const evm_indices = computed(() => {
	const e = data.value.evm;
	return [
		{ key: "spi", label: "SPI", hint: __("ประสิทธิภาพเวลา"), value: ratio(e.spi), color: index_color(e.spi) },
		{ key: "cpi", label: "CPI", hint: __("ประสิทธิภาพต้นทุน"), value: ratio(e.cpi), color: index_color(e.cpi) },
		{ key: "eac", label: "EAC", hint: __("ต้นทุนรวมที่คาด"), value: e.eac === null ? "-" : fmt(e.eac, true) },
		{ key: "vac", label: "VAC", hint: __("ส่วนต่างงบ"), value: e.vac === null ? "-" : fmt(e.vac, true) },
	];
});

function open_evm_report() {
	frappe.set_route("query-report", "Construction Earned Value", {
		construction_management: props.name,
		to_date: status_date.value,
	});
}
</script>

<template>
	<div class="pd pf">
		<div class="pf-toolbar">
			<div class="pf-toolbar-group">
				<span class="pf-toolbar-icon" v-html="icon('calendar')" />
				<span>{{ __("ณ วันที่") }}</span>
				<FrappeControl
					class="pf-date-input"
					:df="{ fieldtype: 'Date' }"
					:model-value="status_date"
					@update:model-value="set_date"
				/>
				<button type="button" class="pf-btn" @click="set_date(frappe.datetime.get_today())">
					{{ __("วันนี้") }}
				</button>
				<button
					type="button"
					class="pf-btn pf-icon-btn"
					:disabled="loading"
					:title="__('โหลดใหม่')"
					@click="load"
					v-html="icon('refresh')"
				/>
			</div>
			<button v-if="data?.evm" type="button" class="pf-btn pf-btn-outline" @click="open_evm_report">
				<span v-html="icon('trending-up')" />{{ __("รายงาน Earned Value") }}
			</button>
		</div>

		<div v-if="!data" class="pf-skeleton" />
		<div v-else class="pf-body" :class="{ 'pd-loading': loading }">
			<div class="pf-tiles">
				<div v-for="tile in tiles" :key="tile.label" class="pf-tile">
					<span class="pf-tile-label">
						<i v-if="tile.tone" class="pf-dot" :class="`pd-tone-${tile.tone}`" />{{ tile.label }}
					</span>
					<strong class="pf-tile-value" :class="tile.tone === 'red' && 'pf-text-red'">{{ tile.value }}</strong>
					<span class="pf-tile-note">{{ tile.note }}</span>
				</div>
			</div>

			<section class="pd-card">
				<header class="pd-card-head">
					<div>
						<h4 class="pd-card-title">{{ __("มูลค่างานสะสม") }}</h4>
						<div class="pd-card-sub">
							{{ __("Cash Plan = % แผนปัจจุบัน x มูลค่าสัญญาปรับปรุง · Cash Actual = มูลค่างานที่ทำได้จริง") }}
						</div>
					</div>
				</header>
				<ProgressCurve
					v-if="curve.length"
					:rows="curve"
					:status-date="data.date"
					:plan-label="__('Cash Plan')"
					:actual-label="__('Cash Actual')"
					:max="curve_max"
					:format="(v) => fmt(v)"
					:tick-format="short_money"
					:height="280"
				/>
				<div v-else class="pf-empty">{{ __("ยังไม่ได้กำหนดวันที่ของแผนงาน") }}</div>
			</section>

			<section class="pd-card">
				<header class="pd-card-head">
					<div>
						<h4 class="pd-card-title">{{ __("Cash Flow รายเดือน") }}</h4>
						<div class="pd-card-sub">{{ __("เดือนหลังวันที่ดูแสดงเฉพาะแผน") }}</div>
					</div>
				</header>
				<div class="pf-table-wrap">
					<table class="pf-table">
						<thead>
							<tr>
								<th rowspan="2">{{ __("เดือน") }}</th>
								<th colspan="2" class="text-center pf-plan">{{ __("Cash Plan") }}</th>
								<th colspan="2" class="text-center pf-actual">{{ __("Cash Actual") }}</th>
								<th rowspan="2" class="text-right">{{ __("ส่วนต่างสะสม") }}</th>
							</tr>
							<tr>
								<th class="text-right">{{ __("รายเดือน") }}</th>
								<th class="text-right">{{ __("สะสม") }}</th>
								<th class="text-right">{{ __("รายเดือน") }}</th>
								<th class="text-right">{{ __("สะสม") }}</th>
							</tr>
						</thead>
						<tbody>
							<tr
								v-for="row in data.months"
								:key="row.month"
								:class="{ 'pf-current': row.month === current_month, 'pf-future': row.actual === null }"
							>
								<td class="pf-month">
									{{ month_label(row.month) }}
									<span v-if="row.month === current_month" class="pd-pill pd-pill-sm pd-tone-blue">
										{{ __("ถึง {0}", [date(data.date)]) }}
									</span>
								</td>
								<td class="text-right">{{ cell(row.plan) }}</td>
								<td class="text-right">{{ cell(row.plan_cum) }}</td>
								<td class="text-right">{{ cell(row.actual) }}</td>
								<td class="text-right">{{ cell(row.actual_cum) }}</td>
								<td
									class="text-right"
									:class="row.variance !== null && (row.variance < -0.5 ? 'pf-text-red' : row.variance > 0.5 ? 'pf-text-green' : '')"
								>
									{{ row.variance === null ? "-" : `${row.variance > 0 ? "+" : ""}${fmt(row.variance)}` }}
								</td>
							</tr>
						</tbody>
						<tfoot>
							<tr>
								<td>{{ __("รวม") }}</td>
								<td class="text-right" colspan="2">{{ fmt(totals.plan) }}</td>
								<td class="text-right" colspan="2">{{ fmt(totals.actual) }}</td>
								<td />
							</tr>
						</tfoot>
					</table>
				</div>
			</section>

			<section v-if="data.evm" class="pd-card">
				<header class="pd-card-head">
					<div>
						<h4 class="pd-card-title">{{ __("Earned Value") }}</h4>
						<div class="pd-card-sub">BAC {{ fmt(data.evm.bac, true) }}</div>
					</div>
				</header>
				<div class="pf-evm">
					<div class="pf-indices">
						<div v-for="item in evm_indices" :key="item.key" class="pf-index">
							<span class="pf-index-label">{{ item.label }}</span>
							<span class="pf-index-value" :class="item.color && `pf-text-${item.color}`">{{ item.value }}</span>
							<span class="pf-index-hint">{{ item.hint }}</span>
						</div>
					</div>
					<Chart :data="evm_chart" :colors="evm_colors" :height="220" :format="(v) => fmt(v)" />
				</div>
			</section>
		</div>
	</div>
</template>

<style scoped>
.pf {
	container-type: inline-size;
	padding: var(--padding-sm) 0 var(--padding-xl);
}
.pf-body {
	display: flex;
	flex-direction: column;
	gap: 20px;
	transition: opacity 0.2s;
}

/* แถบเครื่องมือ (รูปแบบเดียวกับ Tab ภาพรวม) */
.pf-toolbar {
	display: flex;
	flex-wrap: wrap;
	align-items: center;
	justify-content: space-between;
	gap: var(--padding-sm);
	margin-bottom: 20px;
}
.pf-toolbar-group {
	display: flex;
	align-items: center;
	gap: 8px;
	padding: 4px 4px 4px 14px;
	border: 1px solid var(--pd-border);
	border-radius: var(--radius);
	background: var(--card-bg);
	box-shadow: var(--pd-shadow);
}
.pf-toolbar-icon {
	display: flex;
}
.pf-date-input :deep(.form-control) {
	width: 120px;
	height: 30px;
	border-radius: var(--radius);
}
.pf-btn {
	display: inline-flex;
	align-items: center;
	gap: 6px;
	height: 32px;
	padding: 0 14px;
	border: 1px solid transparent;
	border-radius: var(--radius);
	background: var(--control-bg);
	color: var(--text-color);
	font-size: var(--text-sm);
	font-weight: 500;
}
.pf-btn:hover {
	background: var(--fg-hover-color);
}
.pf-btn-outline {
	border-color: var(--pd-border);
	background: var(--card-bg);
}
.pf-icon-btn {
	justify-content: center;
	width: 32px;
	padding: 0;
}

/* ตัวเลขสรุป */
.pf-tiles {
	display: grid;
	grid-template-columns: repeat(4, minmax(0, 1fr));
	gap: 14px;
}
.pf-tile {
	display: flex;
	flex-direction: column;
	gap: 4px;
	padding: 16px 18px;
	border: 1px solid var(--pd-border);
	border-radius: var(--pd-radius);
	background: var(--card-bg);
	box-shadow: var(--pd-shadow);
}
.pf-tile-label {
	display: flex;
	align-items: center;
	gap: 6px;
	font-size: var(--text-xs);
	font-weight: 600;
}
.pf-dot {
	width: 8px;
	height: 8px;
	border-radius: 50%;
	background: var(--pd-tone-fg);
}
.pf-tile-value {
	color: var(--heading-color);
	font-size: var(--text-2xl, 22px);
	font-weight: 700;
	font-variant-numeric: tabular-nums;
}
.pf-tile-note {
	font-size: var(--text-xs);
}
.pf-text-red {
	color: var(--red-600) !important;
}
.pf-text-green {
	color: var(--green-600) !important;
}
.pf-empty {
	padding: 24px;
	text-align: center;
}

/* ตารางรายเดือน */
.pf-table-wrap {
	overflow-x: auto;
}
.pf-table {
	width: 100%;
	border-collapse: collapse;
	font-size: var(--text-sm);
	font-variant-numeric: tabular-nums;
}
.pf-table th {
	padding: 6px 10px;
	border-bottom: 1px solid var(--pd-border);
	color: var(--text-muted);
	font-size: var(--text-xs);
	font-weight: 600;
	white-space: nowrap;
}
.pf-table th.pf-plan {
	color: var(--consbiz-gantt-plan);
}
.pf-table th.pf-actual {
	color: var(--consbiz-gantt-actual);
}
.pf-table td {
	padding: 7px 10px;
	border-bottom: 1px solid color-mix(in srgb, var(--border-color) 45%, transparent);
	color: var(--text-color);
	white-space: nowrap;
}
.pf-month {
	display: flex;
	align-items: center;
	gap: 8px;
}
.pf-current td {
	background: var(--consbiz-highlight, color-mix(in srgb, var(--blue-500) 8%, transparent));
}
.pf-future td {
	color: var(--text-muted);
}
.pf-table tfoot td {
	border-top: 1px solid var(--pd-border);
	border-bottom: none;
	font-weight: 700;
}

/* EVM */
.pf-evm {
	display: flex;
	flex-direction: column;
	gap: 16px;
}
.pf-indices {
	display: grid;
	grid-template-columns: repeat(4, minmax(0, 1fr));
	gap: 10px;
}
.pf-index {
	display: flex;
	flex-direction: column;
	gap: 2px;
	padding: 12px 14px;
	border-radius: var(--pd-radius-sm);
	background: var(--subtle-fg);
}
.pf-index-label {
	font-size: var(--text-xs);
	font-weight: 600;
	letter-spacing: 0.04em;
}
.pf-index-value {
	color: var(--heading-color);
	font-size: var(--text-xl);
	font-weight: 700;
	font-variant-numeric: tabular-nums;
}
.pf-index-hint {
	font-size: var(--text-xs);
}
.pf-skeleton {
	height: 420px;
	border-radius: 16px;
	background: var(--subtle-fg);
}

@container (max-width: 760px) {
	.pf-tiles,
	.pf-indices {
		grid-template-columns: repeat(2, minmax(0, 1fr));
	}
}
</style>
