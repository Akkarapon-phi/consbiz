<!-- ตารางรายงานประจำวัน / ขออนุมัติปฏิบัติงาน (จอ ≥768) เลือกหลายแถวแล้วพิมพ์เป็น PDF ไฟล์เดียว
     ข้อมูลจาก site_app.get_report_list โหลดครบแล้ว DataTable แบ่งหน้าในเครื่อง ดู Design.md "ตารางเลือกหลายแถว" -->
<template>
	<div class="ss-list-head">
		<StatusTabs :model-value="tab" :options="tabs" @update:model-value="$emit('update:tab', $event)" />
		<div class="ss-list-tools">
			<span class="ss-report-range">
				<DateInput v-model="from_date" variant="tool" label="ตั้งแต่วันที่" />
				<span>ถึง</span>
				<DateInput v-model="to_date" variant="tool" label="ถึงวันที่" />
			</span>
			<button
				v-if="can_create"
				type="button"
				class="ss-btn ss-btn--primary ss-list-create"
				@click="go('report-form', { kind, name: 'new', date: today() })"
			>
				<Icon name="plus" :size="18" :stroke="2.6" />
				<span>{{ kind === "dr" ? "เขียนรายงาน" : "ขออนุมัติปฏิบัติงาน" }}</span>
			</button>
			<button
				type="button"
				class="ss-icon-btn"
				:class="{ 'is-spinning': loading }"
				aria-label="โหลดใหม่"
				@click="load"
			>
				<Icon name="refresh" :size="17" />
			</button>
		</div>
	</div>

	<Skeleton v-if="data === null" />
	<Empty
		v-else-if="data === false"
		icon="layers"
		title="โครงการนี้ยังไม่มีแผนงาน"
		text="รายงานประจำวันต้องอ้างแผนงานก่อสร้างของโครงการ"
	/>
	<Empty
		v-else-if="!shown.length"
		:icon="kind === 'dr' ? 'clipboard' : 'send'"
		:title="data.rows.length ? 'ไม่พบรายการ' : 'ยังไม่มีเอกสาร'"
	/>
	<DataTable
		v-else
		v-model:selected="selected"
		selectable
		:rows="shown"
		:columns="kind === 'dr' ? REPORT_COLUMNS : REQUEST_COLUMNS"
		@open="(r) => go('report-view', { kind, name: r.name })"
	>
		<template #name="{ row }">
			<span class="ss-doc-no">{{ row.name }}</span>
			<span class="ss-doc-meta">
				<span class="ss-tag" :class="`tone-${row.status_tone}`">{{ row.status_label }}</span>
			</span>
		</template>
		<template #date="{ row }">{{ thai_date(row.date, { year: true }) }}</template>
		<template #today_progress="{ row }">{{ pct(row.today_progress) }}%</template>
		<template #cumulative_progress="{ row }">{{ pct(row.cumulative_progress) }}%</template>
		<template #expected_progress="{ row }">{{ pct(row.expected_progress) }}%</template>
		<template #problems="{ row }">
			<span class="ss-cell-main" :title="row.problems">{{ row.problems }}</span>
		</template>
		<template #requested_by="{ row }">
			<span class="ss-cell-main" :title="row.requested_by">{{ row.requested_by }}</span>
		</template>
	</DataTable>

	<Teleport to="#ss-layer">
		<Transition name="ss-bar">
			<div v-if="selected.size" class="ss-bottom-bar ss-bulk-bar">
				<span class="ss-bar-summary">
					เลือก <b>{{ selected.size }}</b> รายการ
					<small v-if="over_limit"> · พิมพ์ได้ครั้งละไม่เกิน {{ data.print_limit }} รายการ</small>
					<small v-else-if="printable.length < selected.size">
						· ร่างพิมพ์ไม่ได้ {{ selected.size - printable.length }} รายการ</small
					>
				</span>
				<button type="button" class="ss-btn ss-btn--ghost" @click="selected = new Set()">
					ยกเลิกเลือก
				</button>
				<button
					type="button"
					class="ss-btn ss-btn--primary"
					:disabled="!printable.length || over_limit"
					@click="pdf_open = true"
				>
					<Icon name="printer" :size="16" /> พิมพ์ ({{ printable.length }})
				</button>
			</div>
		</Transition>
	</Teleport>

	<PdfViewer
		:open="pdf_open"
		:url="pdf_url"
		:name="`${title} ${printable.length} รายการ`"
		:title="title"
		@close="pdf_open = false"
	/>
</template>

<script setup>
import { computed, onBeforeUnmount, ref, watch } from "vue";
import Icon from "../../../shared/components/Icon.vue";
import Skeleton from "../../../shared/components/Skeleton.vue";
import Empty from "../../../shared/components/Empty.vue";
import StatusTabs from "../../../shared/components/StatusTabs.vue";
import DataTable from "../../../shared/components/DataTable.vue";
import DateInput from "../../../shared/components/DateInput.vue";
import PdfViewer from "../../../shared/components/PdfViewer.vue";
import { matches } from "../../../shared/table.js";
import { boot, call, go, show_error, state, thai_date, today } from "../../../shared/api.js";

const props = defineProps({
	kind: { type: String, required: true }, // dr / drq
	tab: String,
	tabs: Array,
	search: String,
});
defineEmits(["update:tab"]);

const REPORT_COLUMNS = [
	{ key: "name", label: "เลขที่", sort: true, class: "col-no" },
	{ key: "date", label: "วันที่", sort: true, class: "col-date is-date" },
	{ key: "owner_name", label: "ผู้จัดทำ", sort: true, class: "col-date" },
	{ key: "weather", label: "สภาพอากาศ", sort: true, class: "col-date col-wide" },
	{ key: "problems", label: "ปัญหา/อุปสรรค", class: "col-subject" },
	{ key: "today_progress", label: "วันนี้", sort: true, class: "is-num" },
	{ key: "cumulative_progress", label: "สะสม", sort: true, class: "is-num" },
];
const REQUEST_COLUMNS = [
	{ key: "name", label: "เลขที่", sort: true, class: "col-no" },
	{ key: "date", label: "วันที่", sort: true, class: "col-date is-date" },
	{ key: "requested_by", label: "ผู้ขออนุมัติ", sort: true, class: "col-subject" },
	{ key: "owner_name", label: "ผู้จัดทำ", sort: true, class: "col-date col-wide" },
	{ key: "expected_progress", label: "คาดว่าสะสม", sort: true, class: "is-num" },
];

const doctype = computed(() => (props.kind === "dr" ? "Daily Report" : "Daily Request"));
const title = computed(() => (props.kind === "dr" ? "รายงานประจำวัน" : "ขออนุมัติปฏิบัติงาน"));
const can_create = computed(() =>
	props.kind === "dr" ? boot.can.daily_report : boot.can.daily_request
);

const data = ref(null); // null = กำลังโหลด, false = ไม่มีแผนงาน
const loading = ref(false);
const from_date = ref("");
const to_date = ref("");
const selected = ref(new Set());
const pdf_open = ref(false);

const pct = (value) => (Number(value) || 0).toLocaleString("th-TH", { maximumFractionDigits: 2 });

const shown = computed(() =>
	(data.value?.rows || []).filter(
		(r) =>
			(!from_date.value || String(r.date) >= from_date.value) &&
			(!to_date.value || String(r.date) <= to_date.value) &&
			matches(props.search, r.name, r.owner_name, r.requested_by, r.problems, r.weather)
	)
);

// เอกสารเรียงตามวันที่ในไฟล์ ไม่ว่าเลือกตอนเรียงคอลัมน์ไหน
const printable = computed(() =>
	shown.value
		.filter((r) => selected.value.has(r.name) && (r.docstatus === 1 || data.value.can_print_draft))
		.sort((a, b) => String(a.date).localeCompare(String(b.date)) || a.name.localeCompare(b.name))
);
const over_limit = computed(() => printable.value.length > (data.value?.print_limit || 0));
const pdf_url = computed(
	() =>
		`/api/method/consbiz.site_app.reports_pdf?doctype=${encodeURIComponent(
			doctype.value
		)}&names=${encodeURIComponent(JSON.stringify(printable.value.map((r) => r.name)))}`
);

// เปลี่ยนตัวกรองแล้วล้างที่เลือก: ไม่ให้พิมพ์เอกสารที่มองไม่เห็นในตาราง
watch([from_date, to_date, () => props.search], () => (selected.value = new Set()));

let request_id = 0;
let alive = true;
onBeforeUnmount(() => (alive = false));
async function load() {
	const id = ++request_id;
	loading.value = true;
	try {
		const result = await call("consbiz.site_app.get_report_list", {
			project: state.project.name,
			kind: props.kind,
		});
		if (alive && id === request_id) {
			data.value = result || false;
			selected.value = new Set();
		}
	} catch (error) {
		show_error(error);
		if (id === request_id) data.value ??= { rows: [], can_print_draft: false, print_limit: 0 };
	} finally {
		if (id === request_id) loading.value = false;
	}
}
load();
</script>
