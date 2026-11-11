<!-- รายการเพิ่ม/หักรายเดือน (หมวด hr ของแอปออฟฟิศ, API consbiz/hr_salary.py) = Additional Salary ของ HRMS
     เช่น OT โบนัส หักเครดิตร้านค้า หักอื่นๆ รายการที่ระบบสร้างเอง (หักคืนเงินเบิก/หักเวลาที่ไม่ได้ทำงาน) แสดงแต่ยกเลิกที่หน้าต้นทาง -->
<template>
	<div>
		<TopBar title="รายการเพิ่ม/หัก">
			<template #search>
				<HeaderSearch v-if="wide" v-model="txt" placeholder="ค้นหาชื่อพนักงานหรือรายการ" />
			</template>
			<template #actions>
				<button v-if="!wide" type="button" class="ss-btn ss-btn--primary ss-list-create" aria-label="ลงรายการ" @click="open_form">
					<Icon name="plus" :size="18" :stroke="2.6" />
				</button>
			</template>
		</TopBar>

		<div class="ss-content">
			<div class="ss-list-head">
				<div class="hr-month">
					<button type="button" class="ss-icon-btn" aria-label="เดือนก่อน" @click="shift(-1)"><Icon name="chevron-left" :size="17" /></button>
					<DateInput v-model="month" picker="month" variant="tool" label="เลือกเดือน" />
					<button type="button" class="ss-icon-btn" aria-label="เดือนถัดไป" @click="shift(1)"><Icon name="chevron-right" :size="17" /></button>
				</div>
				<div v-if="wide" class="ss-list-tools">
					<button type="button" class="ss-icon-btn" :class="{ 'is-spinning': loading }" aria-label="โหลดใหม่" title="โหลดใหม่" @click="load">
						<Icon name="refresh" :size="17" />
					</button>
					<button type="button" class="ss-btn ss-btn--primary ss-list-create" @click="open_form">
						<Icon name="plus" :size="18" :stroke="2.6" />
						<span>ลงรายการ</span>
					</button>
				</div>
			</div>

			<Skeleton v-if="data === null" :rows="5" />
			<template v-else>
				<div class="ss-stats ss-stats--3">
					<div class="ss-stat" style="--i: 0">
						<span class="ss-stat-icon"><Icon name="list" :size="20" /></span>
						<span class="ss-stat-value">{{ data.rows.length }}</span>
						<span class="ss-stat-label">รายการ</span>
					</div>
					<div class="ss-stat" style="--i: 1">
						<span class="ss-stat-icon"><Icon name="plus" :size="20" /></span>
						<span class="ss-stat-value ss-stat-value--money">{{ money(data.totals.earning) }}</span>
						<span class="ss-stat-label">รายได้เพิ่ม</span>
					</div>
					<div class="ss-stat" style="--i: 2">
						<span class="ss-stat-icon"><Icon name="minus" :size="20" /></span>
						<span class="ss-stat-value ss-stat-value--money">{{ money(data.totals.deduction) }}</span>
						<span class="ss-stat-label">รายการหัก</span>
					</div>
				</div>

				<Empty v-if="!shown.length" icon="list" title="ยังไม่มีรายการเดือนนี้" text="เช่น OT โบนัส หักเครดิตร้านค้า" />
				<DataTable v-else-if="wide" :rows="shown" :columns="COLUMNS" @open="open_row">
					<template #employee_name="{ row }">
						<span class="ss-cell-main">{{ row.employee_name }}</span>
						<small>{{ row.employee }}</small>
					</template>
					<template #salary_component="{ row }">
						<span class="ss-tag" :class="row.type === 'Earning' ? 'tone-green' : 'tone-rose'">{{ row.type === "Earning" ? "เพิ่ม" : "หัก" }}</span>
						{{ row.salary_component }}
					</template>
					<template #amount="{ row }"><b>{{ money(row.amount) }}</b></template>
					<template #note="{ row }">
						<span class="ss-cell-main">{{ strip(row.note) || (row.managed ? "ระบบสร้าง" : "") }}</span>
					</template>
				</DataTable>
				<div v-else class="ss-list">
					<button v-for="row in shown" :key="row.name" type="button" class="ss-card ss-card--row" @click="open_row(row)">
						<span class="ss-card-main">
							<span class="ss-card-title">{{ row.employee_name }}</span>
							<span class="ss-card-meta">{{ row.salary_component }}{{ row.note ? ` · ${strip(row.note)}` : "" }}</span>
						</span>
						<b class="ss-money" :class="{ 'is-red': row.type !== 'Earning' }">{{ row.type === "Earning" ? "+" : "−" }}{{ money(row.amount) }}</b>
					</button>
				</div>
			</template>
		</div>

		<Sheet :open="form_open" title="ลงรายการเพิ่ม/หัก" :subtitle="month_label" @close="form_open = false">
			<Picker v-model="form.employee" label="พนักงาน" :options="data?.employees || []" required />
			<div class="ss-field">
				<span class="ss-field-label">รายการ<em>*</em></span>
				<SelectBox v-model="form.salary_component" :options="data?.components || []" placeholder="เลือกรายการ" />
			</div>
			<label class="ss-field">
				<span class="ss-field-label">จำนวนเงิน<em>*</em></span>
				<MoneyInput v-model="form.amount" />
			</label>
			<label class="ss-field">
				<span class="ss-field-label">หมายเหตุ</span>
				<textarea v-model="form.note" class="ss-input" rows="2" placeholder="เช่น OT 10 ชม. วันที่ 5-9"></textarea>
			</label>
			<p class="ss-note">มีผลกับสลิปเดือน{{ month_label }} รายการที่ไม่มีให้เลือก = ระบบคำนวณเอง หรือบริษัทยังไม่ได้ผูกบัญชีของรายการนั้น</p>
			<template #footer>
				<button type="button" class="ss-btn ss-btn--ghost" @click="form_open = false">ยกเลิก</button>
				<button type="button" class="ss-btn ss-btn--soft" :disabled="busy || !valid" @click="save(true)">บันทึกแล้วลงต่อ</button>
				<button type="button" class="ss-btn ss-btn--primary ss-btn--lg" :disabled="busy || !valid" @click="save(false)">
					<span v-if="busy" class="ss-spinner"></span><span>บันทึก</span>
				</button>
			</template>
		</Sheet>

		<Sheet :open="!!viewing" :title="viewing?.employee_name" :subtitle="viewing?.name" @close="viewing = null">
			<div v-if="viewing" class="ss-facts">
				<div class="ss-fact"><span>รายการ</span><b>{{ viewing.salary_component }} ({{ viewing.type === "Earning" ? "รายได้" : "รายการหัก" }})</b></div>
				<div class="ss-fact"><span>จำนวนเงิน</span><b>{{ money(viewing.amount) }} บาท</b></div>
				<div class="ss-fact"><span>งวด</span><b>{{ thai_date(viewing.payroll_date, { year: true }) }}</b></div>
				<div v-if="viewing.note" class="ss-fact"><span>หมายเหตุ</span><b>{{ strip(viewing.note) }}</b></div>
			</div>
			<p v-if="viewing?.managed" class="ss-note">รายการนี้ระบบสร้างจากหน้าอื่น (หักคืนเงินเบิก / หักเวลาที่ไม่ได้ทำงาน) ยกเลิกที่หน้าต้นทาง</p>
			<p v-else-if="viewing?.locked" class="ss-note">ยืนยันสลิปเดือนนี้แล้ว ยกเลิกไม่ได้</p>
			<template v-if="viewing && !viewing.managed && !viewing.locked" #footer>
				<button type="button" class="ss-btn ss-btn--ghost-danger" :disabled="busy" @click="cancel">ยกเลิกรายการ</button>
			</template>
		</Sheet>
	</div>
</template>

<script setup>
import { computed, reactive, ref, watch } from "vue";
import Icon from "../../../shared/components/Icon.vue";
import TopBar from "../../../shared/components/TopBar.vue";
import Skeleton from "../../../shared/components/Skeleton.vue";
import Empty from "../../../shared/components/Empty.vue";
import Sheet from "../../../shared/components/Sheet.vue";
import Picker from "../../../shared/components/Picker.vue";
import SelectBox from "../../../shared/components/SelectBox.vue";
import MoneyInput from "../../../shared/components/MoneyInput.vue";
import DataTable from "../../../shared/components/DataTable.vue";
import DateInput from "../../../shared/components/DateInput.vue";
import HeaderSearch from "../../../shared/components/HeaderSearch.vue";
import { matches, use_wide } from "../../../shared/table.js";
import { call, money, post, replace_params, show_error, state, strip_html, thai_date, toast } from "../../../shared/api.js";

const API = "consbiz.hr_salary";
const COLUMNS = [
	{ key: "employee_name", label: "พนักงาน", sort: true, class: "col-subject" },
	{ key: "salary_component", label: "รายการ", sort: true, class: "col-nowrap" },
	{ key: "amount", label: "จำนวนเงิน", sort: true, class: "is-num col-nowrap" },
	{ key: "note", label: "หมายเหตุ", class: "col-wide" },
];

const wide = use_wide();
const now = new Date();
const this_month = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
const month = ref(/^\d{4}-\d{2}$/.test(state.route.params.month || "") ? state.route.params.month : this_month);
const data = ref(null);
const loading = ref(false);
const busy = ref(false);
const txt = ref("");
const form_open = ref(false);
const viewing = ref(null);
const form = reactive({ employee: null, salary_component: null, amount: null, note: "" });

const strip = (html) => strip_html(html || "");
const month_label = computed(() =>
	new Date(`${month.value}-01T00:00:00`).toLocaleDateString("th-TH-u-ca-buddhist", { month: "long", year: "numeric" })
);
const shown = computed(() =>
	(data.value?.rows || []).filter((r) => matches(txt.value, r.employee_name, r.employee, r.salary_component, r.note))
);
const valid = computed(() => form.employee && form.salary_component && Number(form.amount) > 0);

function shift(n) {
	const d = new Date(`${month.value}-01T00:00:00`);
	d.setMonth(d.getMonth() + n);
	month.value = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

function open_form() {
	Object.assign(form, { employee: null, salary_component: null, amount: null, note: "" });
	form_open.value = true;
}
const open_row = (row) => (viewing.value = row);

async function load() {
	loading.value = true;
	try {
		data.value = await call(`${API}.get_adjustments`, { month: month.value, company: state.company || undefined });
	} catch (error) {
		show_error(error);
	} finally {
		loading.value = false;
	}
}

async function save(keep_open) {
	busy.value = true;
	try {
		await post(`${API}.add_adjustment`, { ...form, month: month.value });
		toast("บันทึกแล้ว", "success");
		if (keep_open) Object.assign(form, { employee: null, amount: null, note: "" });
		else form_open.value = false;
		await load();
	} catch (error) {
		show_error(error);
	} finally {
		busy.value = false;
	}
}

async function cancel() {
	if (!confirm("ยกเลิกรายการนี้?")) return;
	busy.value = true;
	try {
		await post(`${API}.cancel_adjustment`, { name: viewing.value.name });
		toast("ยกเลิกแล้ว", "success");
		viewing.value = null;
		await load();
	} catch (error) {
		show_error(error);
	} finally {
		busy.value = false;
	}
}

watch(month, (value) => {
	replace_params("hr-adjustments", { month: value === this_month ? undefined : value });
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
.ss-money.is-red {
	color: var(--tone-rose);
}
</style>
