<!-- เบิกล่วงหน้าคนงานรายวัน (Labour Advance, API consbiz/labour.py) เฉพาะคนงานที่บริษัทจ่ายเอง
     ผู้มีสิทธิ์ Submit บันทึก = จ่ายเงินทันที (ลง Journal Entry) ไม่มีสิทธิ์ = ร่างรอผู้อนุมัติกดจ่าย
     หักคืนอัตโนมัติในใบลงเวลารอบที่ครอบวันเบิก (เก่าก่อน ไม่เกินค่าแรงที่เหลือ) -->
<template>
	<div>
		<TopBar title="เบิกล่วงหน้า" :subtitle="state.project?.project_name">
			<template #search>
				<HeaderSearch v-if="wide" v-model="txt" placeholder="ค้นหาชื่อคนงาน เลขที่" />
			</template>
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
			<Skeleton v-if="data === null" />
			<template v-else>
				<div class="ss-stats ss-stats--3">
					<div class="ss-stat ad-tone" style="--i: 0">
						<span class="ss-stat-icon"><Icon name="calculator" :size="20" /></span>
						<span class="ss-stat-value">{{ money(outstanding) }}</span>
						<span class="ss-stat-label">ค้างหักคืน</span>
					</div>
					<div class="ss-stat ad-tone" style="--i: 1">
						<span class="ss-stat-icon"><Icon name="users" :size="20" /></span>
						<span class="ss-stat-value">{{ owing }}</span>
						<span class="ss-stat-label">คนที่ค้าง</span>
					</div>
					<div class="ss-stat ad-tone" style="--i: 2">
						<span class="ss-stat-icon"><Icon name="clock" :size="20" /></span>
						<span class="ss-stat-value">{{ counts.draft }}</span>
						<span class="ss-stat-label">รอจ่าย</span>
					</div>
				</div>

				<div v-if="wide" class="ss-list-head">
					<StatusTabs v-model="tab" :options="tabs" />
					<div class="ss-list-tools">
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
							v-if="data.can_create"
							type="button"
							class="ss-btn ss-btn--primary ss-list-create"
							@click="open_new"
						>
							<Icon name="plus" :size="18" :stroke="2.6" />
							<span>เบิกล่วงหน้า</span>
						</button>
					</div>
				</div>
				<Segmented v-else v-model="tab" :options="tabs" />

				<Empty v-if="!shown.length" icon="inbox" :title="data.rows.length ? 'ไม่มีรายการ' : 'ยังไม่มีการเบิกล่วงหน้า'" />
				<DataTable v-else-if="wide" :rows="shown" :columns="COLUMNS" @open="open">
					<template #worker_name="{ row }">
						<span class="ss-cell-main">{{ row.worker_name }}</span>
						<small>{{ row.name }}<template v-if="row.remark"> · {{ row.remark }}</template></small>
					</template>
					<template #date="{ row }">{{ thai_date(row.date, { year: true }) }}</template>
					<template #amount="{ row }">{{ money(row.amount) }}</template>
					<template #outstanding_amount="{ row }">
						<b v-if="row.docstatus === 1">{{ money(row.outstanding_amount) }}</b>
					</template>
					<template #status="{ row }">
						<span class="ss-tag" :class="STATUS[row.status]?.tone">{{ STATUS[row.status]?.label || row.status }}</span>
					</template>
				</DataTable>
				<div v-else class="ss-list">
					<button v-for="row in shown" :key="row.name" type="button" class="ss-card" @click="open(row)">
						<div class="ss-card-head">
							<span class="ss-card-main">
								<span class="ss-card-title">{{ row.worker_name }}</span>
								<span class="ss-card-meta">{{ thai_date(row.date, { year: true }) }} · {{ row.name }}</span>
							</span>
							<span class="ss-qty"><b>{{ money(row.amount) }}</b><small>บาท</small></span>
						</div>
						<div class="ss-chips">
							<span class="ss-tag" :class="STATUS[row.status]?.tone">{{ STATUS[row.status]?.label || row.status }}</span>
							<span v-if="row.docstatus === 1 && row.outstanding_amount" class="ss-chip">
								ค้าง {{ money(row.outstanding_amount) }}
							</span>
						</div>
					</button>
				</div>
			</template>
		</div>

		<Teleport to="#ss-layer">
			<Transition name="ss-pop">
				<button v-if="!wide && data?.can_create" type="button" class="ss-fab" @click="open_new">
					<Icon name="plus" :size="26" :stroke="2.6" />
					<span>เบิกล่วงหน้า</span>
				</button>
			</Transition>
		</Teleport>

		<!-- เบิกใหม่ -->
		<Sheet :open="creating" title="เบิกล่วงหน้า" @close="creating = false">
			<div class="ad-form">
				<Picker
					v-model="form.worker"
					label="คนงาน"
					:options="(data?.workers || []).map((w) => ({ value: w.name, label: w.worker_name, description: w.position }))"
					required
					empty_text="ไม่มีคนงานที่บริษัทจ่ายเอง (คนงานของ ผรม. เบิกกับ ผรม.)"
				/>
				<label class="ss-field">
					<span class="ss-field-label">จำนวนเงิน<em>*</em></span>
					<MoneyInput v-model="form.amount" />
				</label>
				<div class="ss-field">
					<span class="ss-field-label">วันที่จ่าย</span>
					<DateInput v-model="form.date" :max="today()" />
				</div>
				<SelectBox v-model="form.paid_from_account" :options="data?.cash_accounts || []" label="จ่ายจากบัญชี" />
				<label class="ss-field">
					<span class="ss-field-label">หมายเหตุ</span>
					<input v-model="form.remark" class="ss-input" />
				</label>
				<p class="ss-note">
					{{
						data?.can_submit
							? "บันทึกแล้วลงบัญชีจ่ายเงินทันที ระบบหักคืนในใบลงเวลาของรอบนี้"
							: "บันทึกเป็นร่าง รอผู้อนุมัติกดจ่าย"
					}}
				</p>
			</div>
			<template #footer>
				<div class="ss-sheet-actions">
					<button
						type="button"
						class="ss-btn ss-btn--primary ss-btn--block ss-btn--lg"
						:disabled="busy || !form.worker || !(Number(form.amount) > 0) || !form.paid_from_account"
						@click="create"
					>
						<span v-if="busy" class="ss-spinner"></span>
						<template v-else>{{ data?.can_submit ? "บันทึกและจ่ายเงิน" : "บันทึกร่าง" }}</template>
					</button>
				</div>
			</template>
		</Sheet>

		<!-- รายละเอียด -->
		<Sheet :open="!!viewing" :title="viewing?.worker_name" :subtitle="viewing?.name" @close="viewing = null">
			<dl v-if="viewing" class="ad-detail">
				<dt>วันที่จ่าย</dt>
				<dd>{{ thai_date(viewing.date, { year: true }) }}</dd>
				<dt>จำนวนเงิน</dt>
				<dd>{{ money(viewing.amount) }}</dd>
				<dt>หักคืนแล้ว</dt>
				<dd>{{ money(viewing.deducted_amount) }}</dd>
				<dt>คงค้าง</dt>
				<dd><b>{{ money(viewing.outstanding_amount) }}</b></dd>
				<dt>สถานะ</dt>
				<dd>{{ STATUS[viewing.status]?.label || viewing.status }}</dd>
				<template v-if="viewing.remark">
					<dt>หมายเหตุ</dt>
					<dd>{{ viewing.remark }}</dd>
				</template>
			</dl>
			<template v-if="viewing && can_act(viewing)" #footer>
				<div class="ss-sheet-actions">
					<button
						v-if="viewing.docstatus === 0 ? data.can_create : data.can_cancel && !viewing.deducted_amount"
						type="button"
						class="ss-btn ss-btn--ghost-danger"
						:disabled="busy"
						@click="cancel(viewing)"
					>
						{{ viewing.docstatus === 0 ? "ลบร่าง" : "ยกเลิกการจ่าย" }}
					</button>
					<button
						v-if="viewing.docstatus === 0 && data.can_submit"
						type="button"
						class="ss-btn ss-btn--primary ss-btn--block"
						:disabled="busy"
						@click="pay(viewing)"
					>
						จ่ายเงิน
					</button>
				</div>
			</template>
		</Sheet>
	</div>
</template>

<script setup>
import { computed, reactive, ref } from "vue";
import Icon from "../../../shared/components/Icon.vue";
import TopBar from "../../../shared/components/TopBar.vue";
import Skeleton from "../../../shared/components/Skeleton.vue";
import Empty from "../../../shared/components/Empty.vue";
import StatusTabs from "../../../shared/components/StatusTabs.vue";
import Segmented from "../../../shared/components/Segmented.vue";
import DataTable from "../../../shared/components/DataTable.vue";
import HeaderSearch from "../../../shared/components/HeaderSearch.vue";
import Sheet from "../../../shared/components/Sheet.vue";
import Picker from "../../../shared/components/Picker.vue";
import MoneyInput from "../../../shared/components/MoneyInput.vue";
import DateInput from "../../../shared/components/DateInput.vue";
import SelectBox from "../../../shared/components/SelectBox.vue";
import { matches, use_wide } from "../../../shared/table.js";
import { call, money, post, show_error, state, thai_date, toast, today } from "../../../shared/api.js";

const API = "consbiz.labour.";
const STATUS = {
	Draft: { label: "รอจ่าย", tone: "tone-amber" },
	Unpaid: { label: "ค้างหักคืน", tone: "tone-orange" },
	"Partly Deducted": { label: "หักคืนบางส่วน", tone: "tone-indigo" },
	Deducted: { label: "หักคืนครบ", tone: "tone-green" },
};
const COLUMNS = [
	{ key: "worker_name", label: "คนงาน", sort: true, class: "col-subject" },
	{ key: "date", label: "วันที่จ่าย", sort: true, class: "col-date is-date" },
	{ key: "amount", label: "จำนวนเงิน", sort: true, class: "is-num" },
	{ key: "outstanding_amount", label: "คงค้าง", sort: true, class: "is-num" },
	{ key: "status", label: "สถานะ", class: "col-status" },
];

const wide = use_wide();
const data = ref(null);
const loading = ref(false);
const busy = ref(false);
const txt = ref("");
const tab = ref("open");
const creating = ref(false);
const viewing = ref(null);
const form = reactive({});

const rows = computed(() => data.value?.rows || []);
const is_open = (r) => r.docstatus === 0 || (r.docstatus === 1 && r.outstanding_amount > 0);
const counts = computed(() => ({
	open: rows.value.filter(is_open).length,
	draft: rows.value.filter((r) => r.docstatus === 0).length,
	all: rows.value.length,
}));
const tabs = computed(() => [
	{ value: "open", label: "ค้าง/รอจ่าย", count: counts.value.open },
	{ value: "all", label: "ทั้งหมด", count: counts.value.all },
]);
const shown = computed(() =>
	rows.value.filter((r) => (tab.value === "all" || is_open(r)) && matches(txt.value, r.worker_name, r.name, r.remark))
);
const submitted = computed(() => rows.value.filter((r) => r.docstatus === 1));
const outstanding = computed(() => submitted.value.reduce((s, r) => s + (r.outstanding_amount || 0), 0));
const owing = computed(() => new Set(submitted.value.filter((r) => r.outstanding_amount > 0).map((r) => r.worker)).size);

const can_act = (r) => (r.docstatus === 0 ? data.value.can_create || data.value.can_submit : data.value.can_cancel && !r.deducted_amount);

async function load() {
	loading.value = true;
	try {
		data.value = await call(API + "get_advances", { project: state.project.name });
	} catch (error) {
		show_error(error);
		data.value ??= { rows: [], workers: [], cash_accounts: [] };
	} finally {
		loading.value = false;
	}
}

function open(row) {
	viewing.value = row;
}

function open_new() {
	Object.assign(form, {
		worker: null,
		amount: null,
		date: today(),
		paid_from_account: data.value?.cash_accounts?.[0]?.value || null,
		remark: "",
	});
	creating.value = true;
}

async function create() {
	busy.value = true;
	try {
		const result = await post(API + "create_advance", { ...form });
		creating.value = false;
		toast(result.docstatus === 1 ? `จ่ายเงินเบิก ${result.name} แล้ว` : `บันทึกร่าง ${result.name} แล้ว`, "success");
		await load();
	} catch (error) {
		show_error(error);
	} finally {
		busy.value = false;
	}
}

async function pay(row) {
	busy.value = true;
	try {
		await post(API + "submit_advance", { name: row.name });
		viewing.value = null;
		toast("จ่ายเงินแล้ว", "success");
		await load();
	} catch (error) {
		show_error(error);
	} finally {
		busy.value = false;
	}
}

async function cancel(row) {
	if (!window.confirm(row.docstatus === 0 ? "ลบร่างใบเบิกนี้?" : "ยกเลิกการจ่าย (ยกเลิก Journal Entry ด้วย)?")) return;
	busy.value = true;
	try {
		await post(API + "cancel_advance", { name: row.name });
		viewing.value = null;
		toast("ยกเลิกแล้ว", "success");
		await load();
	} catch (error) {
		show_error(error);
	} finally {
		busy.value = false;
	}
}

load();
</script>

<style scoped>
.ad-tone {
	--tone: var(--ss-brand);
	--tone-bg: var(--ss-brand-soft);
}
.ad-form {
	display: flex;
	flex-direction: column;
	gap: 12px;
}
.ad-detail {
	display: grid;
	grid-template-columns: auto 1fr;
	gap: 8px 16px;
	margin: 0;
}
.ad-detail dt {
	color: var(--ss-muted);
	font-weight: 400;
}
.ad-detail dd {
	margin: 0;
	text-align: right;
}
</style>
