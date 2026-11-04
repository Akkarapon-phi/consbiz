<script setup>
// Tab "คลังวัสดุ" ของ Construction Management (ดูอย่างเดียว ข้อมูลจาก construction_management/stock.get_overview)
// - วัสดุคงเหลือต่อ Item หลัก แยกของบริษัท / ผู้ว่าจ้างจัดหา: รับเข้า เบิกออก คงเหลือ (คลังของโครงการ)
//   เทียบตามแผนวัสดุ ยอดที่ยังไม่ส่ง (สั่งแล้ว - รับแล้ว) และที่ยังไม่ได้ขอ
// - PO ค้างส่ง, ใช้ตามงาน (เบิกที่ระบุ WBS เทียบแผน), รับของล่าสุด
// หน่วยสต็อกทั้งหมด ปุ่มรับของ/เบิกเปิด Stock Entry ใหม่ของโครงการ
import { computed, onMounted, ref } from "vue";
import { date } from "./format";

const API = "consbiz.consbiz.doctype.construction_management.stock.get_overview";
// PO ที่ต้องได้รับภายในกี่วันถือว่าใกล้กำหนด
const DUE_DAYS = 7;

const props = defineProps({ name: String });
const data = ref(null);
const loading = ref(false);
const active_only = ref(true);

async function load() {
	loading.value = true;
	try {
		const { message } = await frappe.call(API, { name: props.name });
		data.value = message;
	} finally {
		loading.value = false;
	}
}
defineExpose({ load });
onMounted(load);

const icon = (name, size = "sm") => frappe.utils.icon(name, size);
const qty = (value) => format_number(value || 0, null, value % 1 ? 2 : 0);
const cell = (value) => (Math.abs(value || 0) > 1e-9 ? qty(value) : "-");

// รายการที่ยังมีของ / ค้างส่ง / ยังไม่ได้ขอ (ซ่อนรายการที่จบแล้ว)
const is_active = (row) =>
	Math.abs(row.balance) > 1e-9 || row.company.pending > 1e-9 || row.employer.pending > 1e-9 || row.short > 1e-9;
const items = computed(() => (data.value?.items || []).filter((row) => !active_only.value || is_active(row)));
const has_employer = computed(() =>
	(data.value?.items || []).some((row) => row.employer.requested || row.employer.qty_in || row.employer.balance)
);

function order_pill(row) {
	if (row.days_late > 0) return { color: "red", label: __("เลยกำหนด {0} วัน", [row.days_late]) };
	const left = row.schedule_date ? frappe.datetime.get_day_diff(row.schedule_date, frappe.datetime.get_today()) : null;
	if (left !== null && left <= DUE_DAYS) return { color: "orange", label: left ? __("อีก {0} วัน", [left]) : __("วันนี้") };
	return { color: "gray", label: left === null ? "-" : __("อีก {0} วัน", [left]) };
}

const summary = computed(() => {
	const d = data.value || {};
	return {
		items: (d.items || []).filter(is_active).length,
		late: (d.late_orders || []).filter((row) => row.days_late > 0).length,
		pending: (d.late_orders || []).length,
		over: (d.usage || []).filter((row) => row.planned && row.variance > 1e-9).length,
		short: (d.items || []).filter((row) => row.short > 1e-9).length,
	};
});

function new_entry(purpose) {
	frappe.new_doc("Stock Entry", { purpose, stock_entry_type: purpose, company: data.value.company, project: data.value.project });
}

function open_report(report) {
	frappe.set_route("query-report", report, { company: data.value.company, project: data.value.project });
}

function open_doc(doctype, name) {
	frappe.set_route("Form", doctype, name);
}
</script>

<template>
	<div class="pd pst">
		<div v-if="!data" class="text-muted p-4">{{ __("กำลังโหลด...") }}</div>
		<div v-else-if="!data.project" class="pst-empty">{{ __("แผนงานนี้ยังไม่ได้ระบุโครงการ (Project)") }}</div>
		<div v-else class="pst-body" :class="{ 'pd-loading': loading }">
			<!-- สรุป + คำสั่ง -->
			<div class="pst-toolbar">
				<div class="pst-pills">
					<span class="pd-pill pd-tone-gray">
						<span v-html="icon('package', 'xs')" />{{ __("วัสดุที่ยังเคลื่อนไหว {0}", [summary.items]) }}
					</span>
					<span class="pd-pill" :class="summary.late ? 'pd-tone-red' : 'pd-tone-gray'">
						<span v-html="icon('truck', 'xs')" />{{ __("PO เลยกำหนดส่ง {0}", [summary.late]) }}
					</span>
					<span class="pd-pill" :class="summary.short ? 'pd-tone-orange' : 'pd-tone-gray'">
						{{ __("ยังไม่ได้ขอครบตามแผน {0}", [summary.short]) }}
					</span>
					<span class="pd-pill" :class="summary.over ? 'pd-tone-orange' : 'pd-tone-gray'">
						{{ __("ใช้เกินแผน {0}", [summary.over]) }}
					</span>
				</div>
				<div class="pst-actions">
					<button type="button" class="btn btn-sm btn-default" @click="open_report('Site Delivery Summary')">
						<span v-html="icon('file-text', 'xs')" />{{ __("สรุปใบส่งของ") }}
					</button>
					<button type="button" class="btn btn-sm btn-default" @click="open_report('Project Stock Summary')">
						<span v-html="icon('table', 'xs')" />{{ __("รายงานคลังวัสดุ") }}
					</button>
					<button type="button" class="btn btn-sm btn-default" @click="new_entry('Material Issue')">
						<span v-html="icon('log-out', 'xs')" />{{ __("เบิกวัสดุ") }}
					</button>
					<button type="button" class="btn btn-sm btn-primary" @click="new_entry('Material Receipt')">
						<span v-html="icon('log-in', 'xs')" />{{ __("รับของ") }}
					</button>
				</div>
			</div>

			<!-- วัสดุคงเหลือ -->
			<section class="pd-card">
				<header class="pd-card-head">
					<div>
						<h4 class="pd-card-title">{{ __("วัสดุของโครงการ") }}</h4>
						<div class="pd-card-sub">
							<template v-if="data.warehouses.length">
								{{ __("หน่วยสต็อก · คลัง") }}
								<span v-for="wh in data.warehouses" :key="wh.name" class="pst-chip" :class="{ 'pst-chip-owner': wh.owner }">
									{{ wh.name }}<template v-if="wh.owner"> · {{ __("ผู้ว่าจ้าง") }}</template>
								</span>
							</template>
							<template v-else>
								{{ __("ยังไม่มีคลังของโครงการ (ตั้ง Project ที่ Warehouse) แสดงเฉพาะยอดขอ/สั่งซื้อ") }}
							</template>
						</div>
					</div>
					<label class="pst-check">
						<input v-model="active_only" type="checkbox" />
						{{ __("เฉพาะที่ยังมีของ / ค้างส่ง") }}
					</label>
				</header>
				<div v-if="!items.length" class="pst-empty">{{ __("ไม่มีรายการ") }}</div>
				<div v-else class="pst-table-wrap">
					<table class="pst-table">
						<thead>
							<tr>
								<th rowspan="2">{{ __("วัสดุ") }}</th>
								<th rowspan="2" class="text-right">{{ __("ตามแผน") }}</th>
								<th colspan="4" class="text-center">{{ __("ซื้อเอง") }}</th>
								<th v-if="has_employer" colspan="4" class="text-center">{{ __("ผู้ว่าจ้างจัดหา") }}</th>
								<th rowspan="2" class="text-right">{{ __("คงเหลือรวม") }}</th>
								<th rowspan="2" class="text-right">{{ __("ยังไม่ได้ขอ") }}</th>
							</tr>
							<tr>
								<th class="text-right">{{ __("ยังไม่ส่ง") }}</th>
								<th class="text-right">{{ __("รับเข้า") }}</th>
								<th class="text-right">{{ __("เบิกออก") }}</th>
								<th class="text-right">{{ __("คงเหลือ") }}</th>
								<template v-if="has_employer">
									<th class="text-right">{{ __("ยังไม่ส่ง") }}</th>
									<th class="text-right">{{ __("รับเข้า") }}</th>
									<th class="text-right">{{ __("เบิกออก") }}</th>
									<th class="text-right">{{ __("คงเหลือ") }}</th>
								</template>
							</tr>
						</thead>
						<tbody>
							<tr v-for="row in items" :key="row.item_code">
								<td class="pst-name" :title="row.item_code">
									{{ row.item_name || row.item_code }}
									<span class="text-muted small">{{ row.stock_uom }}</span>
								</td>
								<td class="text-right">{{ cell(row.need) }}</td>
								<template v-for="source in has_employer ? ['company', 'employer'] : ['company']" :key="source">
									<td class="text-right" :class="{ 'text-warning': row[source].pending > 1e-9 }">{{ cell(row[source].pending) }}</td>
									<td class="text-right">{{ cell(row[source].qty_in) }}</td>
									<td class="text-right">{{ cell(row[source].qty_out) }}</td>
									<td class="text-right" :class="{ 'text-danger': row[source].balance < -1e-9 }">{{ cell(row[source].balance) }}</td>
								</template>
								<td class="text-right"><b>{{ cell(row.balance) }}</b></td>
								<td class="text-right" :class="{ 'text-danger': row.short > 1e-9 }">{{ cell(row.short) }}</td>
							</tr>
						</tbody>
					</table>
				</div>
			</section>

			<!-- PO ค้างส่ง -->
			<section class="pd-card">
				<header class="pd-card-head">
					<div>
						<h4 class="pd-card-title">{{ __("PO ค้างส่ง") }}</h4>
						<div class="pd-card-sub">{{ __("รายการ PO ของโครงการที่ยังรับไม่ครบ เรียงตามวันที่ต้องได้รับ") }}</div>
					</div>
				</header>
				<div v-if="!data.late_orders.length" class="pst-empty">{{ __("ไม่มี PO ค้างส่ง") }}</div>
				<div v-else class="pst-table-wrap">
					<table class="pst-table">
						<thead>
							<tr>
								<th>{{ __("PO") }}</th>
								<th>{{ __("ผู้ขาย") }}</th>
								<th>{{ __("วัสดุ") }}</th>
								<th class="text-right">{{ __("ค้างส่ง") }}</th>
								<th>{{ __("ต้องได้รับ") }}</th>
								<th>{{ __("สถานะ") }}</th>
							</tr>
						</thead>
						<tbody>
							<tr v-for="row in data.late_orders" :key="`${row.purchase_order}|${row.item_code}|${row.schedule_date}`">
								<td>
									<a href="#" @click.prevent="open_doc('Purchase Order', row.purchase_order)">{{ row.purchase_order }}</a>
								</td>
								<td class="pst-name">{{ row.supplier_name }}</td>
								<td class="pst-name" :title="row.item_code">{{ row.item_name || row.item_code }}</td>
								<td class="text-right">{{ qty(row.pending_qty) }} {{ row.stock_uom }}</td>
								<td>{{ date(row.schedule_date) }}</td>
								<td>
									<span class="indicator-pill no-indicator-dot" :class="order_pill(row).color">{{ order_pill(row).label }}</span>
								</td>
							</tr>
						</tbody>
					</table>
				</div>
			</section>

			<!-- ใช้ตามงาน -->
			<section class="pd-card">
				<header class="pd-card-head">
					<div>
						<h4 class="pd-card-title">{{ __("ใช้ตามงาน") }}</h4>
						<div class="pd-card-sub">{{ __("ตามแผนวัสดุ เทียบเบิกใช้จริง (ใบเบิกที่ระบุ WBS) รวมของบริษัทและผู้ว่าจ้างจัดหา") }}</div>
					</div>
				</header>
				<div v-if="!data.usage.length" class="pst-empty">{{ __("ยังไม่มีแผนวัสดุหรือใบเบิกที่ระบุ WBS") }}</div>
				<div v-else class="pst-table-wrap">
					<table class="pst-table">
						<thead>
							<tr>
								<th>{{ __("งาน") }}</th>
								<th>{{ __("วัสดุ") }}</th>
								<th class="text-right">{{ __("ตามแผน") }}</th>
								<th class="text-right">{{ __("เบิกใช้") }}</th>
								<th class="text-right">{{ __("ส่วนต่าง") }}</th>
							</tr>
						</thead>
						<tbody>
							<tr v-for="row in data.usage" :key="`${row.wbs}|${row.item_code}`">
								<td class="pst-name">
									<span class="pst-wbs">{{ row.wbs }}</span> {{ row.task_name || "" }}
								</td>
								<td class="pst-name" :title="row.item_code">{{ row.item_name || row.item_code }}</td>
								<td class="text-right">{{ cell(row.planned) }}</td>
								<td class="text-right">{{ cell(row.used) }}</td>
								<td class="text-right" :class="{ 'text-danger': row.planned && row.variance > 1e-9 }">
									{{ row.variance > 1e-9 ? "+" : "" }}{{ cell(row.variance) }} {{ row.stock_uom }}
								</td>
							</tr>
						</tbody>
					</table>
				</div>
			</section>

			<!-- รับของล่าสุด -->
			<section class="pd-card">
				<header class="pd-card-head">
					<div>
						<h4 class="pd-card-title">{{ __("รับของ 30 วันล่าสุด") }}</h4>
						<div class="pd-card-sub">{{ __("ข้อมูลเดียวกับรายงานสรุปใบส่งของ") }}</div>
					</div>
				</header>
				<div v-if="!data.deliveries.length" class="pst-empty">{{ __("ไม่มีการรับของ") }}</div>
				<div v-else class="pst-table-wrap">
					<table class="pst-table">
						<thead>
							<tr>
								<th>{{ __("วันที่") }}</th>
								<th>{{ __("เลขที่ใบส่งของ") }}</th>
								<th>{{ __("ผู้ส่ง") }}</th>
								<th>{{ __("วัสดุ") }}</th>
								<th class="text-right">{{ __("จำนวน") }}</th>
								<th>{{ __("แหล่ง") }}</th>
								<th>{{ __("เอกสาร") }}</th>
							</tr>
						</thead>
						<tbody>
							<tr v-for="row in data.deliveries" :key="`${row.voucher_no}|${row.idx}`">
								<td>{{ date(row.posting_date) }}</td>
								<td>{{ row.delivery_note || "-" }}</td>
								<td class="pst-name">{{ row.delivered_by || "-" }}</td>
								<td class="pst-name" :title="row.item_code">{{ row.item_name || row.item_code }}</td>
								<td class="text-right">{{ qty(row.qty) }} {{ row.uom }}</td>
								<td>{{ row.supply }}</td>
								<td>
									<a href="#" @click.prevent="open_doc(row.voucher_type, row.voucher_no)">{{ row.voucher_no }}</a>
								</td>
							</tr>
						</tbody>
					</table>
				</div>
			</section>
		</div>
	</div>
</template>

<style scoped>
.pst {
	padding: var(--padding-sm) 0 var(--padding-xl);
}
.pst-body {
	display: flex;
	flex-direction: column;
	gap: 20px;
	transition: opacity 0.2s;
}
.pst-toolbar {
	display: flex;
	flex-wrap: wrap;
	align-items: center;
	justify-content: space-between;
	gap: var(--padding-sm);
}
.pst-pills,
.pst-actions {
	display: flex;
	flex-wrap: wrap;
	gap: 8px;
}
.pst-actions .btn {
	display: inline-flex;
	align-items: center;
	gap: 6px;
}
.pst-actions :deep(svg),
.pst-pills :deep(svg) {
	stroke: currentColor;
}
.pst-check {
	display: flex;
	align-items: center;
	gap: 6px;
	margin: 0;
	color: var(--text-muted);
	font-size: var(--text-sm);
	white-space: nowrap;
}
.pst-check input {
	margin: 0;
}
.pst-chip {
	display: inline-block;
	margin: 2px 4px 0 0;
	padding: 0 8px;
	border-radius: 999px;
	background: var(--subtle-fg);
	color: var(--text-color);
	font-size: var(--text-xs);
}
.pst-chip-owner {
	background: var(--bg-blue);
	color: var(--text-on-blue);
}
.pst-empty {
	padding: 18px;
	border-radius: var(--pd-radius-sm);
	background: var(--subtle-fg);
	color: var(--text-muted);
	font-size: var(--text-sm);
	text-align: center;
}
.pst-table-wrap {
	overflow-x: auto;
	margin: 0 -8px;
}
.pst-table {
	width: 100%;
	border-collapse: collapse;
	font-size: var(--text-sm);
	font-variant-numeric: tabular-nums;
}
.pst-table th {
	padding: 6px 8px;
	border-bottom: 1px solid var(--pd-border);
	color: var(--text-muted);
	font-size: var(--text-xs);
	font-weight: 600;
	white-space: nowrap;
}
.pst-table td {
	padding: 8px;
	border-bottom: 1px solid color-mix(in srgb, var(--border-color) 45%, transparent);
	vertical-align: top;
	white-space: nowrap;
}
.pst-table tbody tr:hover {
	background: var(--fg-hover-color);
}
.pst-name {
	max-width: 260px;
	overflow: hidden;
	text-overflow: ellipsis;
}
.pst-wbs {
	color: var(--text-muted);
	font-weight: 600;
}
</style>
