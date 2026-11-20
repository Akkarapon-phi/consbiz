<!-- เบิกเงิน (หมวด hr ของแอปออฟฟิศ) แยกตามหน้า (ตกลง 2026-11-17): hr-salary-advances = เบิกล่วงหน้า (กลุ่มเงินเดือน),
     hr-expense-advances = ทดรองจ่าย + ใบเคลียร์ / hr-claims = สำรองจ่าย (กลุ่มค่าใช้จ่าย) hr-advances = ทั้งหมด (URL เดิม)
     (หมวด hr ของแอปออฟฟิศ, API consbiz/hr_advances.py) ใบเบิก/ใบเคลียร์ทั้งบริษัท แท็บตามขั้น (stage ใน hr_advances.py)
     ใบที่รออนุมัติและผู้ใช้มีสิทธิ์ = อนุมัติในหน้านี้ได้ (ApprovalSheet ชุดเดียวกับโมดูลอนุมัติ) จ่ายเงิน/รับคืนที่ระบบเต็ม (ฝ่ายบัญชี)
     บันทึกแทน (ตกลง 2026-11-18, พนักงานที่ไม่มีมือถือ): เลือกพนักงาน → ประเภท (ตามหน้า MODE.types) หรือเงินทดรองที่รอเคลียร์
     → ฟอร์มชุดเดียวกับ Self Service (shared/components/AdvanceForms.vue ส่ง employee) ใบที่รอเคลียร์ในแผงรายละเอียดมีปุ่ม "เคลียร์แทน" -->
<template>
	<div>
		<TopBar :title="MODE.title">
		</TopBar>

		<div class="ss-content">
			<ListHead
				v-model:search="txt"
				search_placeholder="ค้นหาชื่อพนักงาน เลขที่ หรือวัตถุประสงค์"
				v-if="wide"
				many
				v-model="filter"
				:tabs="tabs"
				:loading="loading"
				:create="can_act_on_behalf ? 'บันทึกแทน' : ''"
				create_title="บันทึกใบเบิกแทนพนักงาน (คนที่ไม่มีมือถือ)"
				@refresh="load"
				@create="start_behalf"
			/>
			<div v-else class="ss-tabs">
				<button v-for="t in tabs" :key="t.value" type="button" class="ss-tab" :class="{ 'is-active': filter === t.value }" @click="filter = t.value">
					{{ t.label }} <span class="ss-tab-count">{{ t.count }}</span>
				</button>
			</div>

			<ListCard :on="wide">
			<Skeleton v-if="data === null" :rows="5" />
			<template v-else-if="filter === 'claims'">
				<Empty v-if="!claims.length" icon="file" title="ไม่มีใบเคลียร์/สำรองจ่าย" />
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
							<span class="ss-card-meta">{{ c.name }} · {{ thai_date(c.posting_date, { year: true }) }}{{ c.total_advance_amount ? " · เคลียร์เงินทดรองจ่าย" : " · เบิกสำรองจ่าย" }}</span>
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
			</ListCard>
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
				<button v-if="viewing.can_clear && can_act_on_behalf" type="button" class="ss-btn ss-btn--primary" @click="clear_for(viewing)">
					<Icon name="file" :size="16" /><span>เคลียร์แทน</span>
				</button>
				<a class="ss-btn ss-btn--soft" :href="`/app/employee-advance/${viewing.name}`" target="_blank">เปิดในระบบเต็ม</a>
			</template>
		</Sheet>

		<ApprovalSheet :item="reviewing" @close="reviewing = null" @done="on_reviewed" />

		<Teleport to="#ss-layer">
			<Transition name="ss-pop">
				<button v-if="data && !wide && can_act_on_behalf" type="button" class="ss-fab" @click="start_behalf">
					<Icon name="plus" :size="26" :stroke="2.6" />
					<span>บันทึกแทน</span>
				</button>
			</Transition>
		</Teleport>

		<!-- บันทึกแทน: เลือกพนักงาน → ประเภท -->
		<Sheet :open="behalf.open" title="บันทึกแทนพนักงาน" subtitle="สำหรับพนักงานที่ส่งเองในแอปไม่ได้ ผ่านผู้อนุมัติตามปกติ" form @close="behalf.open = false">
			<Picker
				v-model="behalf.employee"
				label="พนักงาน"
				:options="employee_options"
				:display_value="behalf.employee_name"
				:empty_text="employee_options.length ? undefined : 'กำลังโหลด...'"
				required
				@select="pick_employee"
			/>
			<Skeleton v-if="behalf.employee && !behalf.data" :rows="2" />
			<template v-else-if="behalf.data">
				<div class="ss-options ss-advance-types">
					<button v-for="t in behalf_types" :key="t.value" type="button" class="ss-option" @click="begin(t.value)">
						<span class="ss-avatar" :class="`tone-${t.tone}`"><Icon :name="t.icon" :size="18" /></span>
						<span class="ss-option-main">
							<span class="ss-option-label">{{ t.label }}</span>
							<span class="ss-option-desc">{{ t.desc }}</span>
						</span>
						<Icon name="chevron-right" :size="16" />
					</button>
					<button v-for="a in clearable" :key="a.name" type="button" class="ss-option" @click="begin('clear', a)">
						<span class="ss-avatar tone-teal"><Icon name="file" :size="18" /></span>
						<span class="ss-option-main">
							<span class="ss-option-label">เคลียร์ {{ a.name }}</span>
							<span class="ss-option-desc">{{ a.purpose }} · คงค้าง {{ money(a.unclaimed) }} บาท</span>
						</span>
						<Icon name="chevron-right" :size="16" />
					</button>
				</div>
			</template>
		</Sheet>

		<AdvanceForms
			ref="forms"
			:data="behalf.data"
			:employee="behalf.employee"
			:employee_name="behalf.employee_name"
			@done="on_behalf_done"
		/>
	</div>
</template>

<script setup>
import { computed, reactive, ref, watch } from "vue";
import Icon from "../../../shared/components/Icon.vue";
import Picker from "../../../shared/components/Picker.vue";
import AdvanceForms from "../../../shared/components/AdvanceForms.vue";
import TopBar from "../../../shared/components/TopBar.vue";
import Skeleton from "../../../shared/components/Skeleton.vue";
import Empty from "../../../shared/components/Empty.vue";
import Sheet from "../../../shared/components/Sheet.vue";
import DataTable from "../../../shared/components/DataTable.vue";
import EmployeeContext from "../../../shared/components/EmployeeContext.vue";
import ApprovalSheet from "../../../shared/approvals/ApprovalSheet.vue";
import ListHead from "../../../shared/components/ListHead.vue";
import ListCard from "../../../shared/components/ListCard.vue";
import { find_pending } from "../../../shared/approvals/kinds.js";
import { matches, use_wide } from "../../../shared/table.js";
import { boot, call, celebrate, money, remember_tab, replace_params, show_error, state, thai_date, toast } from "../../../shared/api.js";

const TYPE = { "Salary Advance": "เงินเดือนล่วงหน้า", "Expense Advance": "เงินทดรองจ่าย" };
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
// หน้า → ชนิดใบเบิกที่แสดง + แท็บ (claims = ใบเคลียร์/สำรองจ่าย: "clear" = มีเงินทดรองที่ตัด, "reimburse" = ไม่มี)
const MODES = {
	"hr-salary-advances": { title: "เบิกล่วงหน้า", type: "Salary Advance", types: ["Salary Advance"], filters: ["pending", "to_pay", "repaying", "all"] },
	"hr-expense-advances": { title: "ทดรองจ่าย", type: "Expense Advance", types: ["Expense Advance"], clear: true, claims: "clear", filters: ["pending", "to_pay", "to_clear", "claims", "all"] },
	"hr-claims": { title: "สำรองจ่าย", types: ["reimburse"], claims: "reimburse", only_claims: true, filters: ["claims"] },
	"hr-advances": { title: "เบิกเงิน", types: ["Salary Advance", "Expense Advance", "reimburse"], clear: true, filters: ["pending", "to_pay", "repaying", "to_clear", "claims", "all"] },
};
const view = state.route.view;
const accounting = view === "acc-expense-advances";
const can_act_on_behalf = !accounting || boot.sections.includes("hr");
const MODE = accounting
	? { ...MODES["hr-expense-advances"], title: "เงินทดรองจ่าย" }
	: MODES[view] || MODES["hr-advances"];
const FILTERS = MODE.filters;

const wide = use_wide();
const data = ref(null);
const loading = ref(false);
const txt = ref("");
const filter = ref(FILTERS.includes(state.route.params.filter) ? state.route.params.filter : FILTERS[0]);
const viewing = ref(null);

const advances = computed(() => (MODE.only_claims ? [] : (data.value?.advances || []).filter((a) => !MODE.type || a.advance_type === MODE.type)));
const all_claims = computed(() =>
	(data.value?.claims || []).filter(
		(c) => !MODE.claims || (MODE.claims === "clear" ? Number(c.total_advance_amount) > 0 : !Number(c.total_advance_amount))
	)
);
const count = (stage) => advances.value.filter((a) => a.stage === stage).length;
const CLAIM_LABEL = { clear: "ใบเคลียร์", reimburse: "ใบสำรองจ่าย" };
const tabs = computed(() =>
	[
		{ value: "pending", label: "รออนุมัติ", count: count("pending") },
		{ value: "to_pay", label: "รอจ่าย", count: count("to_pay") },
		{ value: "repaying", label: "กำลังหักคืน", count: count("repaying") },
		{ value: "to_clear", label: "รอเคลียร์", count: count("to_clear") },
		{ value: "claims", label: CLAIM_LABEL[MODE.claims] || "ใบเคลียร์/สำรองจ่าย", count: all_claims.value.length },
		{ value: "all", label: "ทั้งหมด", count: advances.value.length },
	].filter((t) => FILTERS.includes(t.value))
);
const shown = computed(() =>
	advances.value.filter(
		(a) => (filter.value === "all" || a.stage === filter.value) && matches(txt.value, a.employee_name, a.name, a.purpose)
	)
);
const claims = computed(() => all_claims.value.filter((c) => matches(txt.value, c.employee_name, c.name)));

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

// ---------------------------------------------------------------- บันทึกแทนพนักงาน

const BEHALF_TYPES = [
	{ value: "Salary Advance", label: "เบิกเงินเดือนล่วงหน้า", desc: "รับก่อน หักคืนจากเงินเดือน", icon: "wallet", tone: "green" },
	{ value: "Expense Advance", label: "เบิกทดรองจ่าย", desc: "รับเงินไปจ่ายงาน แล้วเคลียร์ด้วยบิล", icon: "calculator", tone: "blue" },
	{ value: "reimburse", label: "เบิกสำรองจ่าย", desc: "จ่ายเองไปแล้ว ส่งบิลเบิกคืน", icon: "receive", tone: "amber" },
];
const behalf_types = BEHALF_TYPES.filter((t) => MODE.types.includes(t.value));
const forms = ref(null);
const behalf = reactive({ open: false, employee: null, employee_name: "", data: null });
const employees = ref([]);
const employee_options = computed(() =>
	employees.value.map((e) => ({ value: e.name, label: e.employee_name, description: [e.designation, e.name, e.user_id ? "" : "ไม่มีบัญชีแอป"].filter(Boolean).join(" · ") }))
);
const clearable = computed(() => (MODE.clear ? (behalf.data?.advances || []).filter((a) => a.can_clear) : []));

async function load_employees() {
	if (employees.value.length) return;
	try {
		const res = await call("consbiz.hr_people.get_employees", { company: state.company || undefined });
		employees.value = res.rows.filter((e) => e.status === "Active");
	} catch (error) {
		show_error(error);
	}
}
async function load_behalf(employee) {
	behalf.data = null;
	behalf.data = await call("consbiz.self_advance.get_advance_data", { employee });
}
function start_behalf() {
	Object.assign(behalf, { open: true, employee: null, employee_name: "", data: null });
	load_employees();
}
async function pick_employee(option) {
	if (!option) return;
	behalf.employee_name = option.label;
	try {
		await load_behalf(option.value);
	} catch (error) {
		show_error(error);
		behalf.employee = null;
	}
}
function begin(type, advance = null) {
	behalf.open = false;
	if (type === "clear") forms.value.open_clear(advance);
	else forms.value.open_request(type);
}
// แผงรายละเอียดใบที่รอเคลียร์: เคลียร์แทนเจ้าของใบ
async function clear_for(row) {
	const advance = { ...row };
	viewing.value = null;
	Object.assign(behalf, { employee: row.employee, employee_name: row.employee_name });
	try {
		await load_behalf(row.employee);
		forms.value.open_clear(advance);
	} catch (error) {
		show_error(error);
	}
}
async function on_behalf_done({ kind, over_limit }) {
	celebrate(
		`บันทึกแทน ${behalf.employee_name} แล้ว`,
		kind === "advance" && over_limit ? "รอผู้อนุมัติ และผู้บริหาร (เกินวงเงิน)" : "รอผู้อนุมัติ"
	);
	if (kind === "claim" && FILTERS.includes("claims")) filter.value = "claims";
	else if (FILTERS.includes("pending")) filter.value = "pending";
	await load();
}
watch(
	() => state.company,
	() => (employees.value = [])
);

async function load() {
	loading.value = true;
	try {
		const method = accounting ? "get_accounting_advances" : "get_advances";
		data.value = await call(`consbiz.hr_advances.${method}`, { company: state.company || undefined });
	} catch (error) {
		show_error(error);
	} finally {
		loading.value = false;
	}
}

watch(filter, (value) => {
	if (accounting) replace_params(view, value === FILTERS[0] ? {} : { filter: value });
	else remember_tab(view, value, FILTERS[0]);
});
watch(() => state.company, load);
load();
</script>
