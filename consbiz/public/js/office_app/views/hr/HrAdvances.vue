<!-- เบิกเงิน (หมวด hr ของแอปออฟฟิศ, API consbiz/hr_advances.py) ใบเบิก/ใบเคลียร์ทั้งบริษัท แท็บตามขั้น (stage ใน hr_advances.py)
     ใบที่รออนุมัติและผู้ใช้มีสิทธิ์ = อนุมัติในหน้านี้ได้ (ApprovalSheet ชุดเดียวกับโมดูลอนุมัติ) จ่ายเงิน/รับคืนที่ระบบเต็ม (ฝ่ายบัญชี) -->
<template>
	<div>
		<TopBar title="เบิกเงิน">
			<template #search>
				<HeaderSearch v-if="wide" v-model="txt" placeholder="ค้นหาชื่อพนักงาน เลขที่ หรือวัตถุประสงค์" />
			</template>
		</TopBar>

		<div class="ss-content">
			<div v-if="wide" class="ss-list-head ss-list-head--many">
				<StatusTabs v-model="filter" :options="tabs" />
				<div class="ss-list-tools">
					<button type="button" class="ss-icon-btn" :class="{ 'is-spinning': loading }" aria-label="โหลดใหม่" title="โหลดใหม่" @click="load">
						<Icon name="refresh" :size="17" />
					</button>
				</div>
			</div>
			<div v-else class="ss-tabs">
				<button v-for="t in tabs" :key="t.value" type="button" class="ss-tab" :class="{ 'is-active': filter === t.value }" @click="filter = t.value">
					{{ t.label }} <span class="ss-tab-count">{{ t.count }}</span>
				</button>
			</div>

			<Skeleton v-if="data === null" :rows="5" />
			<template v-else-if="filter === 'claims'">
				<Empty v-if="!claims.length" icon="file" title="ไม่มีใบเคลียร์/เบิกคืน" />
				<div v-else class="ss-list">
					<component
						:is="claim_status(c).label === 'รออนุมัติ' ? 'button' : 'a'"
						v-for="c in claims"
						:key="c.name"
						type="button"
						class="ss-card ss-card--row"
						:href="claim_status(c).label === 'รออนุมัติ' ? undefined : `/app/expense-claim/${c.name}`"
						target="_blank"
						@click="claim_status(c).label === 'รออนุมัติ' && review('claim', c.name)"
					>
						<span class="ss-card-main">
							<span class="ss-card-title">{{ c.employee_name }}</span>
							<span class="ss-card-meta">{{ c.name }} · {{ thai_date(c.posting_date, { year: true }) }}{{ c.total_advance_amount ? " · เคลียร์เงินสำรองจ่าย" : " · เบิกคืน" }}</span>
						</span>
						<span class="ss-leave-side">
							<b class="ss-money">{{ money(c.total_claimed_amount) }}</b>
							<span class="ss-tag" :class="`tone-${claim_status(c).tone}`">{{ claim_status(c).label }}</span>
						</span>
					</component>
				</div>
			</template>
			<template v-else>
				<Empty v-if="!shown.length" icon="swap" title="ไม่มีใบเบิก" />
				<DataTable v-else-if="wide" :rows="shown" :columns="COLUMNS" @open="open">
					<template #employee_name="{ row }">
						<span class="ss-cell-main">{{ row.employee_name }}</span>
						<small>{{ row.name }}</small>
					</template>
					<template #advance_type="{ row }">{{ TYPE[row.advance_type] }}</template>
					<template #posting_date="{ row }">{{ thai_date(row.posting_date, { year: true }) }}</template>
					<template #advance_amount="{ row }"><b>{{ money(row.advance_amount) }}</b></template>
					<template #outstanding="{ row }">{{ outstanding(row) }}</template>
					<template #stage="{ row }">
						<span class="ss-tag" :class="`tone-${STAGE[row.stage].tone}`">{{ row.overdue ? "เลยกำหนดเคลียร์" : STAGE[row.stage].label }}</span>
					</template>
				</DataTable>
				<div v-else class="ss-list">
					<button v-for="row in shown" :key="row.name" type="button" class="ss-card ss-card--row" @click="open(row)">
						<span class="ss-card-main">
							<span class="ss-card-title">{{ row.employee_name }}</span>
							<span class="ss-card-meta">{{ TYPE[row.advance_type] }} · {{ thai_date(row.posting_date) }}{{ outstanding(row) ? ` · ${outstanding(row)}` : "" }}</span>
						</span>
						<span class="ss-leave-side">
							<b class="ss-money">{{ money(row.advance_amount) }}</b>
							<span class="ss-tag" :class="`tone-${STAGE[row.stage].tone}`">{{ row.overdue ? "เลยกำหนด" : STAGE[row.stage].label }}</span>
						</span>
					</button>
				</div>
			</template>
		</div>

		<Sheet :open="!!viewing" :title="viewing?.employee_name" :subtitle="viewing && `${TYPE[viewing.advance_type]} · ${viewing.name}`" @close="viewing = null">
			<template v-if="viewing">
				<div class="ss-facts">
					<div class="ss-fact"><span>สถานะ</span><b>{{ STAGE[viewing.stage].label }}</b></div>
					<div class="ss-fact"><span>จำนวนเงิน</span><b>{{ money(viewing.advance_amount) }} บาท</b></div>
					<div class="ss-fact"><span>วัตถุประสงค์</span><b>{{ viewing.purpose }}</b></div>
					<div class="ss-fact"><span>วันที่ขอ</span><b>{{ thai_date(viewing.posting_date, { year: true }) }}</b></div>
					<div v-if="viewing.paid_amount" class="ss-fact"><span>จ่ายแล้ว</span><b>{{ money(viewing.paid_amount) }}</b></div>
					<div v-if="viewing.approved_by" class="ss-fact"><span>ผู้อนุมัติ</span><b>{{ viewing.approved_by }}{{ viewing.executive_approved_by ? ` · ผู้บริหาร ${viewing.executive_approved_by}` : "" }}</b></div>
					<div v-if="viewing.reject_reason" class="ss-fact"><span>เหตุผลที่ไม่อนุมัติ</span><b>{{ viewing.reject_reason }}</b></div>
					<div v-if="viewing.advance_type === 'Expense Advance' && viewing.docstatus === 1" class="ss-fact">
						<span>เคลียร์แล้ว / คืนแล้ว / ค้าง</span>
						<b>{{ money(viewing.claimed_amount) }} / {{ money(viewing.return_amount) }} / {{ money(viewing.unclaimed) }}</b>
					</div>
					<div v-if="viewing.clear_due_date" class="ss-fact"><span>กำหนดเคลียร์</span><b>{{ thai_date(viewing.clear_due_date, { year: true }) }}</b></div>
				</div>
				<template v-if="viewing.repayment">
					<div class="ss-field-label">หักคืนจากเงินเดือน (หักแล้ว {{ money(viewing.repayment.deducted) }} / {{ money(viewing.repayment.total) }})</div>
					<div class="ss-facts">
						<div v-for="r in viewing.repayment.rows" :key="r.name" class="ss-fact">
							<span>{{ month_of(r.payroll_date) }}</span>
							<b>{{ money(r.amount) }} · {{ r.deducted ? "หักแล้ว" : "รอหัก" }}</b>
						</div>
					</div>
				</template>
				<p v-if="viewing.stage === 'to_pay'" class="ss-note">อนุมัติแล้ว รอฝ่ายบัญชีจ่ายเงิน (Payment Entry ในระบบเต็ม) จ่ายแล้วระบบสร้างงวดหักคืนให้เอง</p>
				<EmployeeContext :employee="viewing.employee" kind="advance" />
			</template>
			<template v-if="viewing" #footer>
				<a class="ss-btn ss-btn--soft" :href="`/app/employee-advance/${viewing.name}`" target="_blank">เปิดในระบบเต็ม</a>
			</template>
		</Sheet>

		<ApprovalSheet :item="reviewing" @close="reviewing = null" @done="on_reviewed" />
	</div>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import Icon from "../../../shared/components/Icon.vue";
import TopBar from "../../../shared/components/TopBar.vue";
import Skeleton from "../../../shared/components/Skeleton.vue";
import Empty from "../../../shared/components/Empty.vue";
import Sheet from "../../../shared/components/Sheet.vue";
import DataTable from "../../../shared/components/DataTable.vue";
import StatusTabs from "../../../shared/components/StatusTabs.vue";
import HeaderSearch from "../../../shared/components/HeaderSearch.vue";
import EmployeeContext from "../../../shared/components/EmployeeContext.vue";
import ApprovalSheet from "../../../shared/approvals/ApprovalSheet.vue";
import { find_pending } from "../../../shared/approvals/kinds.js";
import { matches, use_wide } from "../../../shared/table.js";
import { call, money, remember_tab, show_error, state, thai_date, toast } from "../../../shared/api.js";

const TYPE = { "Salary Advance": "เงินเดือนล่วงหน้า", "Expense Advance": "เงินสำรองจ่าย" };
const STAGE = {
	pending: { label: "รออนุมัติ", tone: "amber" },
	rejected: { label: "ไม่อนุมัติ", tone: "rose" },
	to_pay: { label: "รอจ่าย", tone: "blue" },
	repaying: { label: "กำลังหักคืน", tone: "violet" },
	to_clear: { label: "รอเคลียร์", tone: "orange" },
	done: { label: "เสร็จแล้ว", tone: "green" },
};
const COLUMNS = [
	{ key: "employee_name", label: "พนักงาน", sort: true, class: "col-subject" },
	{ key: "advance_type", label: "ประเภท", class: "col-nowrap" },
	{ key: "posting_date", label: "วันที่", sort: true, class: "col-date" },
	{ key: "advance_amount", label: "จำนวนเงิน", sort: true, class: "is-num" },
	{ key: "outstanding", label: "ค้าง", class: "is-num col-nowrap" },
	{ key: "stage", label: "สถานะ", class: "col-status" },
];
const FILTERS = ["pending", "to_pay", "repaying", "to_clear", "claims", "all"];

const wide = use_wide();
const data = ref(null);
const loading = ref(false);
const txt = ref("");
const filter = ref(FILTERS.includes(state.route.params.filter) ? state.route.params.filter : "pending");
const viewing = ref(null);

const advances = computed(() => data.value?.advances || []);
const count = (stage) => advances.value.filter((a) => a.stage === stage).length;
const tabs = computed(() => [
	{ value: "pending", label: "รออนุมัติ", count: count("pending") },
	{ value: "to_pay", label: "รอจ่าย", count: count("to_pay") },
	{ value: "repaying", label: "กำลังหักคืน", count: count("repaying") },
	{ value: "to_clear", label: "รอเคลียร์", count: count("to_clear") },
	{ value: "claims", label: "ใบเคลียร์/เบิกคืน", count: data.value?.claims.length || 0 },
	{ value: "all", label: "ทั้งหมด", count: advances.value.length },
]);
const shown = computed(() =>
	advances.value.filter(
		(a) => (filter.value === "all" || a.stage === filter.value) && matches(txt.value, a.employee_name, a.name, a.purpose)
	)
);
const claims = computed(() => (data.value?.claims || []).filter((c) => matches(txt.value, c.employee_name, c.name)));

function outstanding(row) {
	if (row.repayment?.remaining) return `หัก ${money(row.repayment.remaining)}`;
	if (row.unclaimed) return `เคลียร์ ${money(row.unclaimed)}`;
	return "";
}
function claim_status(c) {
	if (c.docstatus === 0) return c.approval_status === "Rejected" ? { label: "ไม่อนุมัติ", tone: "rose" } : { label: "รออนุมัติ", tone: "amber" };
	return c.status === "Paid" ? { label: "จ่ายแล้ว", tone: "green" } : { label: "รอจ่าย", tone: "blue" };
}
const month_of = (d) => new Date(`${String(d).slice(0, 10)}T00:00:00`).toLocaleDateString("th-TH-u-ca-buddhist", { month: "long", year: "numeric" });
const reviewing = ref(null);

// ใบที่รออนุมัติ: ผู้ใช้อนุมัติได้ = เปิดแผงอนุมัติ ไม่ได้ = ดูรายละเอียดอย่างเดียว
async function review(kind, name, row = null) {
	try {
		const item = await find_pending(call, kind, name);
		if (item) reviewing.value = item;
		else if (row) viewing.value = row;
		else toast("รอผู้มีสิทธิ์อนุมัติ (คุณอนุมัติใบนี้ไม่ได้)", "info");
	} catch (error) {
		show_error(error);
	}
}
const open = (row) => (row.stage === "pending" ? review("advance", row.name, row) : (viewing.value = row));
async function on_reviewed() {
	reviewing.value = null;
	await load();
}

async function load() {
	loading.value = true;
	try {
		data.value = await call("consbiz.hr_advances.get_advances", { company: state.company || undefined });
	} catch (error) {
		show_error(error);
	} finally {
		loading.value = false;
	}
}

watch(filter, (value) => remember_tab("hr-advances", value, "pending"));
watch(() => state.company, load);
load();
</script>
