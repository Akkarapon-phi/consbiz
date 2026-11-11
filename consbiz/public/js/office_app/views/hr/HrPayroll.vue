<!-- เงินเดือนรายเดือน (หมวด hr ของแอปออฟฟิศ, API consbiz/hr_payroll.py) เฉพาะ HR ที่ทำ Payroll Entry ได้
     ขั้นตอน: 1 ตรวจการเข้างาน (ต้องบันทึก Attendance ครบ) → 2 สร้างสลิป (Payroll Entry) → 3 ตรวจสลิป → ยืนยันสลิป
     บันทึกจ่ายเงิน (Bank Entry) เป็นงานบัญชี ทำในระบบเต็ม -->
<template>
	<div>
		<TopBar title="เงินเดือน">
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
			</template>
		</TopBar>

		<div class="ss-content">
			<div class="ss-list-head">
				<div class="hr-month">
					<button type="button" class="ss-icon-btn" aria-label="เดือนก่อน" title="เดือนก่อน" @click="shift(-1)">
						<Icon name="chevron-left" :size="17" />
					</button>
					<DateInput v-model="month" picker="month" variant="tool" :max="this_month" label="เลือกเดือน" />
					<button
						type="button"
						class="ss-icon-btn"
						aria-label="เดือนถัดไป"
						title="เดือนถัดไป"
						:disabled="month >= this_month"
						@click="shift(1)"
					>
						<Icon name="chevron-right" :size="17" />
					</button>
				</div>
				<div v-if="wide" class="ss-list-tools">
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
						v-if="step === 2"
						type="button"
						class="ss-btn ss-btn--primary ss-list-create"
						:disabled="busy || !ready"
						@click="create"
					>
						<Icon name="plus" :size="18" :stroke="2.6" />
						<span>สร้างสลิปเงินเดือน</span>
					</button>
					<button
						v-else-if="step === 3"
						type="button"
						class="ss-btn ss-btn--primary ss-list-create"
						:disabled="busy || !ready || !data.slips.length"
						@click="submit"
					>
						<Icon name="check" :size="18" :stroke="2.6" />
						<span>ยืนยันสลิป {{ data.slips.length }} ใบ</span>
					</button>
				</div>
			</div>

			<Skeleton v-if="data === null" :rows="5" />
			<template v-else>
				<!-- ขั้นตอน -->
				<ol class="hr-steps">
					<li :class="ready ? 'is-done' : 'is-current'">
						<b>1 ตรวจการเข้างาน</b>
						<span v-if="ready">บันทึก Attendance ครบแล้ว</span>
						<span v-else>
							รอตัดสิน {{ data.attendance.flag }} วัน · ยังไม่บันทึก {{ data.attendance.unsaved }} วัน
							<button type="button" class="ss-link" @click="go('hr-attendance', { month })">ไปหน้าสรุปวันทำงาน</button>
						</span>
						<small v-if="data.attendance.future">วันที่ยังไม่ถึง {{ data.attendance.future }} วัน นับเป็นมาทำงาน</small>
					</li>
					<li :class="step > 2 ? 'is-done' : step === 2 ? 'is-current' : ''">
						<b>2 สร้างสลิป</b>
						<span v-if="data.entry">{{ data.entry.name }} · {{ data.entry.number_of_employees }} คน</span>
						<span v-else>ดึงพนักงานที่มีโครงสร้างเงินเดือน แล้วคำนวณสลิปร่าง</span>
					</li>
					<li :class="step === 4 ? 'is-done' : step === 3 ? 'is-current' : ''">
						<b>3 ตรวจและยืนยันสลิป</b>
						<span v-if="step === 4">ยืนยันแล้ว รอฝ่ายบัญชีบันทึกจ่ายเงิน</span>
						<span v-else>ยืนยันแล้วแก้ไม่ได้ ระบบลงบัญชีเงินเดือนค้างจ่าย</span>
					</li>
				</ol>

				<p v-if="queued" class="ss-note">ระบบกำลังทำรายการในคิว (พนักงานเกิน 30 คน) รอสักครู่แล้วกดโหลดใหม่</p>
				<div v-if="data.entry?.error_message" class="ss-banner tone-rose hr-banner">
					<Icon name="alert" :size="20" />
					<div>
						<div class="ss-banner-title">ทำรายการไม่สำเร็จ</div>
						<RichText class="ss-banner-text" :html="data.entry.error_message" />
					</div>
				</div>
				<div v-if="data.no_structure.length" class="ss-banner tone-amber hr-banner">
					<Icon name="alert" :size="20" />
					<div>
						<div class="ss-banner-title">ไม่มีโครงสร้างเงินเดือน {{ data.no_structure.length }} คน (ไม่อยู่ในงวดนี้)</div>
						<div class="ss-banner-text">{{ data.no_structure.map((e) => e.employee_name).join(", ") }}</div>
					</div>
				</div>

				<template v-if="data.slips.length">
					<div class="ss-stats">
						<div class="ss-stat" style="--i: 0">
							<span class="ss-stat-icon"><Icon name="users" :size="20" /></span>
							<span class="ss-stat-value">{{ data.slips.length }}</span>
							<span class="ss-stat-label">สลิป</span>
						</div>
						<div class="ss-stat" style="--i: 1">
							<span class="ss-stat-icon"><Icon name="trending" :size="20" /></span>
							<span class="ss-stat-value ss-stat-value--money">{{ money(data.totals.gross_pay) }}</span>
							<span class="ss-stat-label">รวมรายได้</span>
						</div>
						<div class="ss-stat" style="--i: 2">
							<span class="ss-stat-icon"><Icon name="minus" :size="20" /></span>
							<span class="ss-stat-value ss-stat-value--money">{{ money(data.totals.total_deduction) }}</span>
							<span class="ss-stat-label">รวมรายการหัก</span>
						</div>
						<div class="ss-stat" style="--i: 3">
							<span class="ss-stat-icon"><Icon name="receive" :size="20" /></span>
							<span class="ss-stat-value ss-stat-value--money">{{ money(data.totals.net_pay) }}</span>
							<span class="ss-stat-label">สุทธิที่ต้องจ่าย</span>
						</div>
					</div>

					<DataTable v-if="wide" :rows="data.slips" :columns="COLUMNS" @open="open_slip">
						<template #employee_name="{ row }">
							<span class="ss-cell-main">{{ row.employee_name }}</span>
							<small>{{ row.designation || row.employee }}</small>
						</template>
						<template #payment_days="{ row }">{{ days(row.payment_days) }} / {{ days(row.total_working_days) }}</template>
						<template #absent="{ row }">{{ days(row.absent_days) || "" }}{{ row.leave_without_pay ? ` (ลา ${days(row.leave_without_pay)})` : "" }}</template>
						<template #gross_pay="{ row }">{{ money(row.gross_pay) }}</template>
						<template #total_deduction="{ row }">{{ money(row.total_deduction) }}</template>
						<template #net_pay="{ row }"><b>{{ money(row.net_pay) }}</b></template>
						<template #docstatus="{ row }">
							<span class="ss-tag" :class="`tone-${SLIP[row.docstatus].tone}`">{{ SLIP[row.docstatus].label }}</span>
						</template>
					</DataTable>
					<div v-else class="ss-list">
						<button v-for="row in data.slips" :key="row.name" type="button" class="ss-card" @click="open_slip(row)">
							<div class="ss-card-head">
								<span class="ss-card-main">
									<span class="ss-card-title">{{ row.employee_name }}</span>
									<span class="ss-card-meta">ทำงาน {{ days(row.payment_days) }} / {{ days(row.total_working_days) }} วัน</span>
								</span>
								<b class="ss-money">{{ money(row.net_pay) }}</b>
							</div>
						</button>
					</div>
				</template>
				<Empty
					v-else-if="!data.entry"
					icon="receive"
					title="ยังไม่ได้สร้างสลิปเดือนนี้"
					:text="ready ? 'กดสร้างสลิปเงินเดือน' : 'บันทึกการเข้างานให้ครบก่อน'"
				/>

				<div v-if="step === 3" class="hr-actions">
					<button type="button" class="ss-btn ss-btn--soft" :disabled="busy" @click="recalc">คำนวณสลิปใหม่</button>
					<button type="button" class="ss-btn ss-btn--ghost-danger" :disabled="busy" @click="cancel">ยกเลิกงวดนี้</button>
				</div>
			</template>
		</div>

		<Teleport to="#ss-layer">
			<div v-if="!wide && (step === 2 || step === 3)" class="ss-bottom-bar">
				<button
					type="button"
					class="ss-btn ss-btn--primary ss-btn--lg"
					:disabled="busy || !ready || (step === 3 && !data.slips.length)"
					@click="step === 2 ? create() : submit()"
				>
					<span v-if="busy" class="ss-spinner"></span>
					<span>{{ step === 2 ? "สร้างสลิปเงินเดือน" : `ยืนยันสลิป ${data.slips.length} ใบ` }}</span>
				</button>
			</div>
		</Teleport>

		<Sheet :open="!!slip" :title="slip?.employee_name" :subtitle="slip ? `${slip.name} · ${SLIP[slip.docstatus]?.label || ''}` : ''" @close="slip = null">
			<Skeleton v-if="slip && !slip.earnings" :rows="4" />
			<template v-else-if="slip">
				<div class="ss-facts">
					<div class="ss-fact"><span>งวด</span><b>{{ thai_date(slip.start_date) }} – {{ thai_date(slip.end_date, { year: true }) }}</b></div>
					<div class="ss-fact"><span>วันทำงาน</span><b>{{ days(slip.payment_days) }} / {{ days(slip.total_working_days) }} วัน</b></div>
					<div v-if="slip.absent_days" class="ss-fact"><span>ขาดงาน</span><b>{{ days(slip.absent_days) }} วัน</b></div>
					<div v-if="slip.leave_without_pay" class="ss-fact"><span>ลาไม่รับค่าจ้าง</span><b>{{ days(slip.leave_without_pay) }} วัน</b></div>
				</div>
				<div class="ss-field-label">รายได้</div>
				<div class="ss-facts">
					<div v-for="r in slip.earnings" :key="r.component" class="ss-fact"><span>{{ r.component }}</span><b>{{ money(r.amount) }}</b></div>
					<div class="ss-fact"><span><b>รวมรายได้</b></span><b>{{ money(slip.gross_pay) }}</b></div>
				</div>
				<div class="ss-field-label">รายการหัก</div>
				<div class="ss-facts">
					<div v-for="r in slip.deductions" :key="r.component" class="ss-fact"><span>{{ r.component }}</span><b>{{ money(r.amount) }}</b></div>
					<div class="ss-fact"><span><b>รวมรายการหัก</b></span><b>{{ money(slip.total_deduction) }}</b></div>
				</div>
				<div class="ss-facts">
					<div class="ss-fact"><span><b>สุทธิ</b></span><b>{{ money(slip.net_pay) }} บาท</b></div>
				</div>
			</template>
			<template v-if="slip?.pdf" #footer>
				<a class="ss-btn ss-btn--soft" :href="slip.pdf" target="_blank">พิมพ์สลิป</a>
			</template>
		</Sheet>
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
import DateInput from "../../../shared/components/DateInput.vue";
import RichText from "../../../shared/components/RichText.vue";
import { use_wide } from "../../../shared/table.js";
import { call, go, money, post, replace_params, show_error, state, thai_date, toast } from "../../../shared/api.js";

const API = "consbiz.hr_payroll";
const SLIP = {
	0: { label: "ร่าง", tone: "gray" },
	1: { label: "ยืนยันแล้ว", tone: "green" },
	2: { label: "ยกเลิก", tone: "rose" },
};
const COLUMNS = [
	{ key: "employee_name", label: "พนักงาน", sort: true, class: "col-subject" },
	{ key: "payment_days", label: "วันทำงาน", class: "is-num col-nowrap" },
	{ key: "absent", label: "ขาด", class: "is-num col-nowrap" },
	{ key: "gross_pay", label: "รายได้", sort: true, class: "is-num col-nowrap" },
	{ key: "total_deduction", label: "รายการหัก", sort: true, class: "is-num col-nowrap" },
	{ key: "net_pay", label: "สุทธิ", sort: true, class: "is-num col-nowrap" },
	{ key: "docstatus", label: "สถานะ", class: "col-status" },
];

const wide = use_wide();
const now = new Date();
const this_month = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
const month = ref(/^\d{4}-\d{2}$/.test(state.route.params.month || "") ? state.route.params.month : this_month);
const data = ref(null);
const loading = ref(false);
const busy = ref(false);
const slip = ref(null);

const ready = computed(() => !!data.value && !data.value.attendance.flag && !data.value.attendance.unsaved);
// 2 = ยังไม่มีงวด, 3 = มีสลิปร่าง, 4 = ยืนยันแล้ว
const step = computed(() => {
	const d = data.value;
	if (!d) return 0;
	if (!d.entry) return 2;
	if (d.entry.salary_slips_submitted || (d.slips.length && d.slips.every((s) => s.docstatus === 1))) return 4;
	return 3;
});
const queued = computed(() => data.value?.entry?.status === "Queued");
const days = (value) => (value ? Number(value).toLocaleString("th-TH", { maximumFractionDigits: 1 }) : 0);

function shift(n) {
	const d = new Date(`${month.value}-01T00:00:00`);
	d.setMonth(d.getMonth() + n);
	const next = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
	if (next <= this_month) month.value = next;
}

async function load() {
	loading.value = true;
	try {
		data.value = await call(`${API}.get_payroll`, { month: month.value, company: state.company || undefined });
	} catch (error) {
		show_error(error);
	} finally {
		loading.value = false;
	}
}

async function run(method, args, message) {
	busy.value = true;
	try {
		const result = await post(`${API}.${method}`, args);
		toast(typeof message === "function" ? message(result) : message, "success");
		await load();
	} catch (error) {
		show_error(error);
	} finally {
		busy.value = false;
	}
}

const create = () =>
	run("create_payroll", { month: month.value, company: state.company || undefined }, (r) =>
		r.status === "Queued" ? `กำลังสร้างสลิป ${r.employees} คนในคิว` : `สร้างสลิป ${r.employees} คนแล้ว ตรวจก่อนยืนยัน`
	);
const recalc = () => run("recalculate", { payroll_entry: data.value.entry.name }, (r) => `คำนวณใหม่ ${r.count} ใบแล้ว`);
function submit() {
	if (!confirm(`ยืนยันสลิป ${data.value.slips.length} ใบ? ยืนยันแล้วแก้ไม่ได้ ระบบจะลงบัญชีเงินเดือนค้างจ่าย`)) return;
	run("submit_slips", { payroll_entry: data.value.entry.name }, (r) =>
		r.status === "Queued" ? "กำลังยืนยันสลิปในคิว" : "ยืนยันสลิปแล้ว แจ้งฝ่ายบัญชีบันทึกจ่ายเงิน"
	);
}
function cancel() {
	if (!confirm("ยกเลิกงวดนี้และลบสลิปร่างทั้งหมด?")) return;
	run("cancel_payroll", { payroll_entry: data.value.entry.name }, "ยกเลิกงวดแล้ว");
}

async function open_slip(row) {
	slip.value = { ...row };
	try {
		slip.value = await call(`${API}.get_slip`, { name: row.name });
	} catch (error) {
		show_error(error);
		slip.value = null;
	}
}

watch(month, (value) => {
	if (!value || value > this_month) return (month.value = this_month);
	replace_params("hr-payroll", { month: value === this_month ? undefined : value });
	data.value = null;
	load();
});
watch(() => state.company, load);
load();
</script>

<style scoped>
.hr-month {
	display: inline-flex;
	align-items: center;
	gap: 4px;
	padding: 0 6px;
}
.hr-banner {
	margin: 8px 0;
}
.hr-steps {
	display: grid;
	grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
	gap: 8px;
	margin: 8px 0;
	padding: 0;
	list-style: none;
}
.hr-steps li {
	display: flex;
	flex-direction: column;
	gap: 2px;
	padding: 10px 12px;
	border: 1px solid var(--ss-border);
	border-radius: 10px;
	background: var(--ss-surface);
	color: var(--ss-muted);
}
.hr-steps li b {
	color: var(--ss-text);
}
.hr-steps li small {
	font-size: var(--ss-fs-sm);
}
.hr-steps li.is-current {
	border-color: var(--ss-brand);
	background: var(--ss-brand-soft);
}
.hr-steps li.is-done b::after {
	content: " ✓";
	color: var(--tone-green, #15803d);
}
.hr-actions {
	display: flex;
	gap: 8px;
	justify-content: flex-end;
	margin-top: 12px;
}
</style>
