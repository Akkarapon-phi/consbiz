<script setup>
// Tab "ทรัพยากร" ของ Construction Management: สิ่งที่ต้องเตรียมก่อนเริ่มงาน (ดูอย่างเดียว)
// - วัสดุที่ต้องสั่ง เรียงตามวันต้องสั่ง และปุ่มสร้าง Material Request (construction_material_plan.make_material_request)
//   สถานะคิดจากยอดที่ขอ/สั่งซื้อ/รับแล้วรวมของโครงการ ตัดให้แถวที่ต้องการก่อนก่อน (coverage ของแถว)
// - ยอดรวมต่อ Item: ต้องใช้ เทียบขอ/สั่งซื้อ/รับแล้ว แยกซื้อเอง / ผู้ว่าจ้างจัดหา (Customer Provided)
// - คน/เครื่องจักร รวมตามชื่อ: ช่วงที่ใช้ จำนวนสูงสุดต่อวัน และวันต้องจองของงานถัดไป
// - กราฟคน-วัน/คัน-วันรายสัปดาห์ แผนเทียบใช้จริง (Daily Report)
// ข้อมูลจาก construction_management/resources.get_overview กำหนดรายการได้ที่แผงด้านขวาของหน้า Gantt (คลิกชื่องาน)
import { computed, onMounted, ref } from "vue";
import Chart from "./components/Chart.vue";
import { css_color, date } from "./format";

const API = "consbiz.consbiz.doctype.construction_management.resources.get_overview";
const REQUEST_API = "consbiz.consbiz.doctype.construction_material_plan.construction_material_plan.make_material_request";

const props = defineProps({ name: String });
const data = ref(null);
const loading = ref(false);
const pending_only = ref(true);

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
const qty = (value) => format_number(value || 0, null, value % 1 ? 1 : 0);
const TYPE_LABELS = { Labour: __("แรงงาน"), Equipment: __("เครื่องจักร") };
const UNITS = { Labour: __("คน"), Equipment: __("คัน") };

// ป้ายสถานะวัสดุที่ขอครบแล้ว: ขั้นล่าสุดที่ครบจำนวน
const STAGE_LABELS = {
	received: { color: "green", label: __("รับแล้ว"), customer: __("ผู้ว่าจ้างส่งแล้ว") },
	ordered: { color: "green", label: __("สั่งซื้อแล้ว"), customer: __("ขอผู้ว่าจ้างแล้ว") },
	requested: { color: "blue", label: __("ขอซื้อแล้ว"), customer: __("ขอผู้ว่าจ้างแล้ว") },
};
function material_pill(row) {
	const stage = STAGE_LABELS[row.coverage?.state];
	if (stage) return { color: stage.color, label: row.customer_provided ? stage.customer : stage.label };
	return pill(row);
}

// ยอดที่ตัดให้แถว เช่น "ขอแล้ว 20 / 70 · ขาด 50"
function coverage_text(row) {
	const cov = row.coverage;
	if (!cov || !cov.requested) return __("ยังไม่ได้ขอ");
	const parts = [`${__("ขอแล้ว")} ${qty(cov.requested)}/${qty(row.qty)}`];
	if (cov.received) parts.push(`${__("รับ")} ${qty(cov.received)}`);
	if (cov.state === "partial") parts.push(`${__("ขาด")} ${qty(row.qty - cov.requested)}`);
	return parts.join(" · ");
}

// ป้ายสถานะ (indicator ของ Frappe) จาก status ของ resources.prep_status
function pill(row, ordered_label = __("สั่งแล้ว")) {
	switch (row.status) {
		case "done":
			return { color: "green", label: ordered_label };
		case "late":
			return { color: "red", label: __("เลยกำหนด {0} วัน", [-row.days_left]) };
		case "due":
			return { color: "orange", label: row.days_left ? __("อีก {0} วัน", [row.days_left]) : __("วันนี้") };
		case "later":
			return { color: "gray", label: __("อีก {0} วัน", [row.days_left]) };
		default:
			return { color: "gray", label: __("ยังไม่มีวันเริ่มงาน") };
	}
}

const materials = computed(() =>
	(data.value?.materials || []).filter((row) => !pending_only.value || row.status !== "done")
);
const resources = computed(() => data.value?.resources || []);
const supply = computed(() => data.value?.supply || []);
const supply_cell = (s, stage) => (s && s[stage] ? qty(s[stage]) : "-");
const supply_short = (row) => Math.max(row.need - (row.total?.requested || 0), 0);

const summary = computed(() => {
	const rows = data.value?.materials || [];
	return {
		late: rows.filter((r) => r.status === "late").length,
		due: rows.filter((r) => r.status === "due").length,
		ordered: rows.filter((r) => r.status === "done").length,
		total: rows.length,
		book: resources.value.filter((r) => r.status === "late" || r.status === "due").length,
	};
});

const chart = computed(() => {
	const source = data.value?.chart;
	if (!source) return null;
	// ซ่อนชุดที่เป็น 0 ทั้งหมด (เช่น ยังไม่ได้กำหนดเครื่องจักร)
	const datasets = source.datasets.filter((d) => d.values.some((v) => v));
	return datasets.length ? { labels: source.labels, datasets } : null;
});
const CHART_COLORS = {
	planned_Labour: "--blue-500",
	actual_Labour: "--green-500",
	planned_Equipment: "--orange-400",
	actual_Equipment: "--purple-500",
};
const chart_colors = computed(() => chart.value?.datasets.map((d) => css_color(CHART_COLORS[d.key])) || []);

function open_gantt() {
	frappe.set_route("construction-gantt", props.name);
}

function open_plan(doctype) {
	frappe.set_route("Form", doctype, props.name);
}

function open_histogram() {
	frappe.set_route("query-report", "Construction Resource Histogram", { construction_management: props.name });
}

function make_request() {
	frappe.prompt(
		{
			fieldname: "days",
			label: __("รวมวัสดุที่ต้องสั่งภายใน (วัน)"),
			fieldtype: "Int",
			default: data.value.due_days,
			reqd: 1,
		},
		async ({ days }) => {
			const { message } = await frappe.call({
				method: REQUEST_API,
				args: { name: props.name, days },
				freeze: true,
			});
			// ซื้อเอง / ผู้ว่าจ้างจัดหา ได้ 1-2 ฉบับ
			if (message.length === 1) frappe.set_route("Form", "Material Request", message[0]);
			else frappe.set_route("List", "Material Request", { name: ["in", message] });
		},
		__("สร้าง Material Request")
	);
}
</script>

<template>
	<div class="pd prs">
		<div v-if="!data" class="text-muted p-4">{{ __("กำลังโหลด...") }}</div>
		<div v-else class="prs-body" :class="{ 'pd-loading': loading }">
			<!-- สรุป + คำสั่ง -->
			<div class="prs-toolbar">
				<div class="prs-pills">
					<span class="pd-pill" :class="summary.late ? 'pd-tone-red' : 'pd-tone-gray'">
						<span v-html="icon('package', 'xs')" />{{ __("วัสดุเลยวันต้องสั่ง {0}", [summary.late]) }}
					</span>
					<span class="pd-pill" :class="summary.due ? 'pd-tone-orange' : 'pd-tone-gray'">
						{{ __("ต้องสั่งใน {0} วัน {1}", [data.due_days, summary.due]) }}
					</span>
					<span class="pd-pill" :class="summary.book ? 'pd-tone-orange' : 'pd-tone-gray'">
						<span v-html="icon('users', 'xs')" />{{ __("คน/เครื่องจักรต้องจองใน {0} วัน {1}", [data.due_days, summary.book]) }}
					</span>
				</div>
				<div class="prs-actions">
					<button type="button" class="btn btn-sm btn-default" @click="open_histogram">
						<span v-html="icon('activity', 'xs')" />{{ __("แผนเทียบใช้จริง") }}
					</button>
					<button type="button" class="btn btn-sm btn-default" @click="open_gantt">
						<span v-html="icon('pencil', 'xs')" />{{ __("กำหนดในหน้า Gantt") }}
					</button>
					<button v-if="data.can_request" type="button" class="btn btn-sm btn-primary" @click="make_request">
						<span v-html="icon('shopping-cart', 'xs')" />{{ __("สร้าง Material Request") }}
					</button>
				</div>
			</div>

			<!-- วัสดุ -->
			<section v-if="data.material_plan" class="pd-card">
				<header class="pd-card-head">
					<div>
						<h4 class="pd-card-title">{{ __("วัสดุที่ต้องสั่ง") }}</h4>
						<div class="pd-card-sub">
							{{ __("ต้องสั่งภายใน = วันเริ่มงาน - Buffer {0} วัน - Lead Time · ขอครบแล้ว {1}/{2} รายการ (นับ MR/PO ของโครงการ ตัดให้งานที่ต้องการก่อน)", [data.material_plan.buffer_days || 0, summary.ordered, summary.total]) }}
						</div>
					</div>
					<div class="prs-head-actions">
						<label class="prs-check">
							<input v-model="pending_only" type="checkbox" />
							{{ __("เฉพาะที่ยังขอไม่ครบ") }}
						</label>
						<a v-if="data.material_plan.exists" class="pd-link" href="#" @click.prevent="open_plan('Construction Material Plan')">
							{{ __("เปิดแผนวัสดุ") }} →
						</a>
					</div>
				</header>
				<div v-if="!materials.length" class="prs-empty">
					{{ data.materials.length ? __("ขอวัสดุครบแล้ว") : __("ยังไม่ได้กำหนดวัสดุ คลิกชื่องานในหน้า Gantt เพื่อกำหนด") }}
				</div>
				<div v-else class="prs-table-wrap">
					<table class="prs-table">
						<thead>
							<tr>
								<th>{{ __("งาน") }}</th>
								<th>{{ __("วัสดุ") }}</th>
								<th class="text-right">{{ __("จำนวน") }}</th>
								<th class="text-right">{{ __("Lead Time") }}</th>
								<th>{{ __("ต้องสั่งภายใน") }}</th>
								<th>{{ __("ต้องการภายใน") }}</th>
								<th>{{ __("สถานะ") }}</th>
								<th>{{ __("ยอดที่ตัดให้") }}</th>
							</tr>
						</thead>
						<tbody>
							<tr v-for="row in materials" :key="row.name">
								<td class="prs-task">
									<span class="prs-wbs">{{ row.wbs }}</span> {{ row.item_name }}
								</td>
								<td :title="row.item_code">
									{{ row.item_label || row.item_code }}
									<span v-if="row.customer_provided" class="text-muted small">· {{ __("ผู้ว่าจ้างจัดหา") }}</span>
								</td>
								<td class="text-right">{{ qty(row.qty) }} {{ row.uom }}</td>
								<td class="text-right">{{ __("{0} วัน", [row.lead_time_days || 0]) }}</td>
								<td>{{ date(row.order_by) }}</td>
								<td>{{ date(row.required_by) }}</td>
								<td>
									<span class="indicator-pill no-indicator-dot" :class="material_pill(row).color">{{ material_pill(row).label }}</span>
								</td>
								<td class="text-muted">{{ coverage_text(row) }} {{ row.uom }}</td>
							</tr>
						</tbody>
					</table>
				</div>
			</section>

			<!-- ยอดรวมต่อ Item แยกซื้อเอง / ผู้ว่าจ้างจัดหา -->
			<section v-if="supply.length" class="pd-card">
				<header class="pd-card-head">
					<div>
						<h4 class="pd-card-title">{{ __("ยอดวัสดุของโครงการ") }}</h4>
						<div class="pd-card-sub">
							{{ __("หน่วยสต็อก · นับ MR (รวมฉบับร่าง) / PO / รับของ ที่ระบุโครงการนี้ ไม่ว่าจะสร้างจากแผนหรือจากหน้า Material Request") }}
						</div>
					</div>
				</header>
				<div class="prs-table-wrap">
					<table class="prs-table">
						<thead>
							<tr>
								<th rowspan="2">{{ __("วัสดุ") }}</th>
								<th rowspan="2" class="text-right">{{ __("ต้องใช้") }}</th>
								<th colspan="3" class="text-center">{{ __("ซื้อเอง") }}</th>
								<th colspan="2" class="text-center">{{ __("ผู้ว่าจ้างจัดหา") }}</th>
								<th rowspan="2" class="text-right">{{ __("ยังขาด") }}</th>
							</tr>
							<tr>
								<th class="text-right">{{ __("ขอซื้อ") }}</th>
								<th class="text-right">{{ __("สั่งซื้อ") }}</th>
								<th class="text-right">{{ __("รับ") }}</th>
								<th class="text-right">{{ __("ขอ") }}</th>
								<th class="text-right">{{ __("รับ") }}</th>
							</tr>
						</thead>
						<tbody>
							<tr v-for="row in supply" :key="row.item_code">
								<td :title="row.item_code">{{ row.item_label || row.item_code }}</td>
								<td class="text-right">{{ qty(row.need) }} {{ row.stock_uom }}</td>
								<td class="text-right" :title="row.purchase?.draft ? __('ฉบับร่าง {0}', [qty(row.purchase.draft)]) : ''">
									{{ supply_cell(row.purchase, "requested") }}
								</td>
								<td class="text-right">{{ supply_cell(row.purchase, "ordered") }}</td>
								<td class="text-right">{{ supply_cell(row.purchase, "received") }}</td>
								<td class="text-right" :title="row.customer?.draft ? __('ฉบับร่าง {0}', [qty(row.customer.draft)]) : ''">
									{{ supply_cell(row.customer, "requested") }}
								</td>
								<td class="text-right">{{ supply_cell(row.customer, "received") }}</td>
								<td class="text-right" :class="{ 'text-danger': supply_short(row) > 0 }">
									{{ supply_short(row) > 0 ? qty(supply_short(row)) : "-" }}
								</td>
							</tr>
						</tbody>
					</table>
				</div>
			</section>

			<!-- คน / เครื่องจักร -->
			<section v-if="data.resource_plan" class="pd-card">
				<header class="pd-card-head">
					<div>
						<h4 class="pd-card-title">{{ __("คน / เครื่องจักร") }}</h4>
						<div class="pd-card-sub">
							{{ __("ต้องจองภายใน = วันเริ่มของงานถัดไปที่ยังไม่เริ่ม - จำนวนวันจองล่วงหน้า") }}
						</div>
					</div>
					<a v-if="data.resource_plan.exists" class="pd-link" href="#" @click.prevent="open_plan('Construction Resource Plan')">
						{{ __("เปิดแผนทรัพยากร") }} →
					</a>
				</header>
				<div v-if="!resources.length" class="prs-empty">
					{{ __("ยังไม่ได้กำหนดคน/เครื่องจักร คลิกชื่องานในหน้า Gantt เพื่อกำหนด") }}
				</div>
				<div v-else class="prs-table-wrap">
					<table class="prs-table">
						<thead>
							<tr>
								<th>{{ __("ทรัพยากร") }}</th>
								<th>{{ __("ช่วงที่ใช้") }}</th>
								<th class="text-right">{{ __("สูงสุดต่อวัน") }}</th>
								<th class="text-right">{{ __("รวม (วัน)") }}</th>
								<th>{{ __("ต้องจองภายใน") }}</th>
								<th>{{ __("สถานะ") }}</th>
								<th>{{ __("งาน") }}</th>
							</tr>
						</thead>
						<tbody>
							<tr v-for="row in resources" :key="`${row.resource_type}|${row.resource}`">
								<td>
									<b>{{ row.resource }}</b>
									<div class="text-muted small">{{ TYPE_LABELS[row.resource_type] }}</div>
								</td>
								<td>{{ date(row.start_date) }} - {{ date(row.end_date) }}</td>
								<td class="text-right">{{ qty(row.peak) }} {{ UNITS[row.resource_type] }}</td>
								<td class="text-right">{{ qty(row.total) }}</td>
								<td>
									{{ date(row.book_by) }}
									<div v-if="row.next_task" class="text-muted small">{{ __("งาน {0}", [row.next_task]) }}</div>
								</td>
								<td>
									<span v-if="row.book_by" class="indicator-pill no-indicator-dot" :class="pill(row).color">{{ pill(row).label }}</span>
									<span v-else class="indicator-pill no-indicator-dot blue">{{ __("เริ่มงานแล้ว") }}</span>
								</td>
								<td class="prs-tasks">
									<span
										v-for="task in row.tasks"
										:key="task.wbs"
										class="prs-task-chip"
										:title="`${task.wbs} ${task.item_name} · ${date(task.start_date)} - ${date(task.end_date)}`"
									>
										{{ task.wbs }} × {{ qty(task.qty_per_day) }}
									</span>
								</td>
							</tr>
						</tbody>
					</table>
				</div>
			</section>

			<!-- กราฟรายสัปดาห์ -->
			<section v-if="data.resource_plan" class="pd-card">
				<header class="pd-card-head">
					<div>
						<h4 class="pd-card-title">{{ __("คน-วัน / คัน-วัน รายสัปดาห์") }}</h4>
						<div class="pd-card-sub">{{ __("แผนจากแผนทรัพยากร × วันทำงานของงาน, ใช้จริงจาก Daily Report ที่ Submit แล้ว") }}</div>
					</div>
				</header>
				<Chart v-if="chart" :data="chart" type="bar" :colors="chart_colors" :height="240" :format="(v) => qty(v)" />
				<div v-else class="prs-empty">{{ __("ยังไม่มีข้อมูล") }}</div>
			</section>

			<div v-if="!data.resource_plan && !data.material_plan" class="prs-empty">
				{{ __("ไม่มีสิทธิ์ดูแผนทรัพยากรและแผนวัสดุ") }}
			</div>
		</div>
	</div>
</template>

<style scoped>
.prs {
	padding: var(--padding-sm) 0 var(--padding-xl);
}
.prs-body {
	display: flex;
	flex-direction: column;
	gap: 20px;
	transition: opacity 0.2s;
}
.prs-toolbar {
	display: flex;
	flex-wrap: wrap;
	align-items: center;
	justify-content: space-between;
	gap: var(--padding-sm);
}
.prs-pills,
.prs-actions {
	display: flex;
	flex-wrap: wrap;
	gap: 8px;
}
.prs-actions .btn {
	display: inline-flex;
	align-items: center;
	gap: 6px;
}
.prs-actions :deep(svg),
.prs-pills :deep(svg) {
	stroke: currentColor;
}
.prs-head-actions {
	display: flex;
	align-items: center;
	gap: 16px;
	flex-wrap: wrap;
}
.prs-check {
	display: flex;
	align-items: center;
	gap: 6px;
	margin: 0;
	color: var(--text-muted);
	font-size: var(--text-sm);
}
.prs-check input {
	margin: 0;
}
.pd-link {
	color: var(--text-muted);
	font-size: var(--text-sm);
	white-space: nowrap;
}
.prs-empty {
	padding: 18px;
	border-radius: var(--pd-radius-sm);
	background: var(--subtle-fg);
	color: var(--text-muted);
	font-size: var(--text-sm);
	text-align: center;
}
.prs-table-wrap {
	overflow-x: auto;
	margin: 0 -8px;
}
.prs-table {
	width: 100%;
	border-collapse: collapse;
	font-size: var(--text-sm);
	font-variant-numeric: tabular-nums;
}
.prs-table th {
	padding: 6px 8px;
	border-bottom: 1px solid var(--pd-border);
	color: var(--text-muted);
	font-size: var(--text-xs);
	font-weight: 600;
	white-space: nowrap;
}
.prs-table td {
	padding: 8px;
	border-bottom: 1px solid color-mix(in srgb, var(--border-color) 45%, transparent);
	vertical-align: top;
	white-space: nowrap;
}
.prs-table tbody tr:hover {
	background: var(--fg-hover-color);
}
.prs-task {
	max-width: 280px;
	overflow: hidden;
	text-overflow: ellipsis;
}
.prs-wbs {
	color: var(--text-muted);
	font-weight: 600;
}
.prs-tasks {
	white-space: normal !important;
}
.prs-task-chip {
	display: inline-block;
	margin: 0 4px 4px 0;
	padding: 1px 8px;
	border-radius: 999px;
	background: var(--subtle-fg);
	color: var(--text-color);
	font-size: var(--text-xs);
}
</style>
