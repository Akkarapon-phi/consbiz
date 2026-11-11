<!-- ค่าจ้างพนักงาน (หมวด hr ของแอปออฟฟิศ, API consbiz/hr_salary.py) = Salary Structure Assignment ของ HRMS
     แถวละคน: เงินเดือนปัจจุบัน / ที่จะมีผล คลิก = ประวัติ + กำหนด/ปรับเงินเดือน (ใบใหม่ ใบเดิมคงเป็นประวัติ) -->
<template>
	<div>
		<TopBar title="ค่าจ้างพนักงาน">
			<template #search>
				<HeaderSearch v-if="wide" v-model="txt" placeholder="ค้นหาชื่อ ตำแหน่ง แผนก" />
			</template>
		</TopBar>

		<div class="ss-content">
			<div v-if="wide" class="ss-list-head">
				<StatusTabs v-model="filter" :options="tabs" />
				<div class="ss-list-tools">
					<button type="button" class="ss-icon-btn" :class="{ 'is-spinning': loading }" aria-label="โหลดใหม่" title="โหลดใหม่" @click="load">
						<Icon name="refresh" :size="17" />
					</button>
				</div>
			</div>
			<Segmented v-else v-model="filter" :options="tabs" />

			<Skeleton v-if="data === null" :rows="6" />
			<template v-else>
				<Empty v-if="!shown.length" icon="users" :title="filter === 'missing' ? 'ทุกคนมีเงินเดือนแล้ว' : 'ไม่มีพนักงาน'" />
				<DataTable v-else-if="wide" :rows="shown" :columns="COLUMNS" @open="open">
					<template #employee_name="{ row }">
						<span class="ss-cell-main">{{ row.employee_name }}</span>
						<small>{{ row.designation || row.name }}</small>
					</template>
					<template #base="{ row }">
						<b v-if="row.current">{{ money(row.current.base) }}</b>
						<span v-else class="ss-tag tone-rose">ยังไม่กำหนด</span>
					</template>
					<template #structure="{ row }">{{ row.current?.salary_structure || "" }}</template>
					<template #from_date="{ row }">{{ row.current ? thai_date(row.current.from_date, { year: true }) : "" }}</template>
					<template #upcoming="{ row }">
						<span v-if="row.upcoming" class="ss-tag tone-blue">{{ money(row.upcoming.base) }} · {{ thai_date(row.upcoming.from_date) }}</span>
					</template>
				</DataTable>
				<div v-else class="ss-list">
					<button v-for="row in shown" :key="row.name" type="button" class="ss-card ss-card--row" @click="open(row)">
						<span class="ss-card-main">
							<span class="ss-card-title">{{ row.employee_name }}</span>
							<span class="ss-card-meta">{{ row.designation || row.name }}</span>
						</span>
						<b v-if="row.current" class="ss-money">{{ money(row.current.base) }}</b>
						<span v-else class="ss-tag tone-rose">ยังไม่กำหนด</span>
					</button>
				</div>
			</template>
		</div>

		<Sheet :open="!!person" :title="person?.employee_name" :subtitle="person?.designation || person?.name" @close="person = null">
			<template v-if="person">
				<div class="ss-field-label">{{ person.current ? "ปรับเงินเดือน" : "กำหนดเงินเดือน" }}</div>
				<div class="ss-field">
					<span class="ss-field-label">โครงสร้างเงินเดือน<em>*</em></span>
					<SelectBox v-model="form.salary_structure" :options="data.structures" placeholder="เลือกโครงสร้าง" />
				</div>
				<label class="ss-field">
					<span class="ss-field-label">เงินเดือน (บาท/เดือน)<em>*</em></span>
					<MoneyInput v-model="form.base" />
				</label>
				<div class="ss-field">
					<span class="ss-field-label">มีผลตั้งแต่<em>*</em></span>
					<DateInput v-model="form.from_date" :min="person.date_of_joining" />
				</div>
				<label class="ss-field">
					<span class="ss-field-label">หมายเหตุ</span>
					<textarea v-model="form.note" class="ss-input" rows="2" placeholder="เช่น ปรับประจำปี / ผ่านทดลองงาน"></textarea>
				</label>

				<div class="ss-field-label">ประวัติ</div>
				<Skeleton v-if="history === null" :rows="2" />
				<p v-else-if="!history.length" class="ss-note">ยังไม่มีประวัติเงินเดือน</p>
				<div v-else class="ss-facts">
					<div v-for="h in history" :key="h.name" class="ss-fact">
						<span>{{ thai_date(h.from_date, { year: true }) }}{{ h.note ? ` · ${strip(h.note)}` : "" }}</span>
						<b>{{ money(h.base) }}</b>
					</div>
				</div>
			</template>
			<template v-if="person" #footer>
				<button type="button" class="ss-btn ss-btn--ghost" @click="person = null">ปิด</button>
				<button type="button" class="ss-btn ss-btn--primary ss-btn--lg" :disabled="busy || !valid" @click="save">
					<span v-if="busy" class="ss-spinner"></span><span>บันทึกเงินเดือน</span>
				</button>
			</template>
		</Sheet>
	</div>
</template>

<script setup>
import { computed, reactive, ref, watch } from "vue";
import Icon from "../../../shared/components/Icon.vue";
import TopBar from "../../../shared/components/TopBar.vue";
import Segmented from "../../../shared/components/Segmented.vue";
import Skeleton from "../../../shared/components/Skeleton.vue";
import Empty from "../../../shared/components/Empty.vue";
import Sheet from "../../../shared/components/Sheet.vue";
import SelectBox from "../../../shared/components/SelectBox.vue";
import MoneyInput from "../../../shared/components/MoneyInput.vue";
import DateInput from "../../../shared/components/DateInput.vue";
import DataTable from "../../../shared/components/DataTable.vue";
import StatusTabs from "../../../shared/components/StatusTabs.vue";
import HeaderSearch from "../../../shared/components/HeaderSearch.vue";
import { matches, use_wide } from "../../../shared/table.js";
import { call, money, post, show_error, state, strip_html, thai_date, toast } from "../../../shared/api.js";

const API = "consbiz.hr_salary";
const COLUMNS = [
	{ key: "employee_name", label: "พนักงาน", sort: true, class: "col-subject" },
	{ key: "base", label: "เงินเดือน", class: "is-num col-nowrap" },
	{ key: "structure", label: "โครงสร้าง", class: "col-wide col-nowrap" },
	{ key: "from_date", label: "มีผลตั้งแต่", class: "col-date" },
	{ key: "upcoming", label: "ปรับครั้งถัดไป", class: "col-nowrap" },
];

const wide = use_wide();
const data = ref(null);
const loading = ref(false);
const busy = ref(false);
const txt = ref("");
const filter = ref(state.route.params.filter === "missing" ? "missing" : "all");
const person = ref(null);
const history = ref(null);
const form = reactive({ salary_structure: null, base: null, from_date: null, note: "" });

const strip = (html) => strip_html(html || "");
const rows = computed(() => data.value?.rows || []);
const tabs = computed(() => [
	{ value: "all", label: "ทั้งหมด", count: rows.value.length },
	{ value: "missing", label: "ยังไม่กำหนด", count: rows.value.filter((r) => !r.current).length },
]);
const shown = computed(() =>
	rows.value.filter(
		(r) => (filter.value === "all" || !r.current) && matches(txt.value, r.employee_name, r.name, r.designation, r.department)
	)
);
const valid = computed(() => form.salary_structure && Number(form.base) > 0 && form.from_date);

// วันที่มีผลเริ่มต้น: คนใหม่ = วันเริ่มงาน (หรือต้นเดือนนี้), ปรับเงินเดือน = ต้นเดือนถัดไป
function default_from(row) {
	const d = new Date();
	if (row.current) return `${new Date(d.getFullYear(), d.getMonth() + 1, 1).toLocaleDateString("sv")}`;
	const first = new Date(d.getFullYear(), d.getMonth(), 1).toLocaleDateString("sv");
	return row.date_of_joining > first ? row.date_of_joining : first;
}

async function open(row) {
	person.value = row;
	history.value = null;
	Object.assign(form, {
		salary_structure: row.current?.salary_structure || data.value.structures[0]?.value || null,
		base: row.current?.base || null,
		from_date: default_from(row),
		note: "",
	});
	try {
		history.value = await call(`${API}.get_salary_history`, { employee: row.name });
	} catch (error) {
		show_error(error);
		history.value = [];
	}
}

async function load() {
	loading.value = true;
	try {
		data.value = await call(`${API}.get_salaries`, { company: state.company || undefined });
	} catch (error) {
		show_error(error);
	} finally {
		loading.value = false;
	}
}

async function save() {
	busy.value = true;
	try {
		await post(`${API}.set_salary`, { employee: person.value.name, ...form });
		toast("บันทึกเงินเดือนแล้ว", "success");
		person.value = null;
		await load();
	} catch (error) {
		show_error(error);
	} finally {
		busy.value = false;
	}
}

watch(() => state.company, load);
load();
</script>
