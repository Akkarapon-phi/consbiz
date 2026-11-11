<!-- เบิกเงิน (API consbiz/self_advance.py): เบิกเงินเดือนล่วงหน้า (วงเงิน 50% เกิน = ผู้บริหารอนุมัติ, หักคืน 1-6 งวด)
     เงินสำรองจ่าย (จ่ายแล้วเคลียร์ภายใน 15 วัน) และเบิกค่าใช้จ่ายคืน (สำรองจ่ายเอง) ทุกรายการค่าใช้จ่ายต้องมีรูปบิล
     ผู้อนุมัติ = Role Expense Approver (โมดูลอนุมัติ หน้า approve) จ่ายเงิน/รับเงินคืน ฝ่ายบัญชีทำในระบบเต็ม -->
<template>
	<div>
		<TopBar title="เบิกเงิน" no_project>
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
			<Skeleton v-if="data === null" :rows="3" />
			<template v-else>
				<div class="ss-stats ss-stats--3">
					<div class="ss-stat tone-green" style="--i: 0">
						<span class="ss-stat-icon"><Icon name="calculator" :size="20" /></span>
						<span class="ss-stat-value">{{ money(data.salary.available, { short: true }) }}</span>
						<span class="ss-stat-label">วงเงินเบิกล่วงหน้าคงเหลือ</span>
					</div>
					<div class="ss-stat tone-green" style="--i: 1">
						<span class="ss-stat-icon"><Icon name="receive" :size="20" /></span>
						<span class="ss-stat-value">{{ money(to_clear, { short: true }) }}</span>
						<span class="ss-stat-label">เงินสำรองจ่ายรอเคลียร์</span>
						<span v-if="overdue_count" class="ss-stat-alert">เลยกำหนด {{ overdue_count }}</span>
					</div>
					<div class="ss-stat tone-green" style="--i: 2">
						<span class="ss-stat-icon"><Icon name="clock" :size="20" /></span>
						<span class="ss-stat-value">{{ pending_count }}</span>
						<span class="ss-stat-label">รออนุมัติ</span>
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
							@click="load"
						>
							<Icon name="refresh" :size="17" />
						</button>
						<button type="button" class="ss-btn ss-btn--primary ss-list-create" @click="open_request()">
							<Icon name="plus" :size="18" :stroke="2.6" />
							<span>ขอเบิก</span>
						</button>
					</div>
				</div>
				<div v-else class="ss-tabs">
					<button
						v-for="t in tabs"
						:key="t.value"
						type="button"
						class="ss-tab"
						:class="{ 'is-active': tab === t.value }"
						@click="tab = t.value"
					>
						{{ t.label }} <span class="ss-tab-count">{{ t.count }}</span>
					</button>
				</div>

				<template v-if="tab === 'advances'">
					<Empty
						v-if="!data.advances.length"
						icon="calculator"
						title="ยังไม่มีใบเบิก"
						text="กดปุ่ม ขอเบิก เพื่อเบิกเงินเดือนล่วงหน้าหรือเงินสำรองจ่าย"
					/>
					<div v-else class="ss-list">
						<button
							v-for="(row, i) in data.advances"
							:key="row.name"
							type="button"
							class="ss-card ss-card--row"
							:style="{ '--i': i }"
							@click="viewing = row"
						>
							<span class="ss-avatar tone-green"><Icon :name="row.advance_type === 'Salary Advance' ? 'calculator' : 'receive'" :size="18" /></span>
							<span class="ss-card-main">
								<span class="ss-card-title">{{ TYPE[row.advance_type] }}</span>
								<span class="ss-card-meta">{{ thai_date(row.posting_date, { year: true }) }} · {{ row.purpose }}</span>
							</span>
							<span class="ss-leave-side">
								<b class="ss-money">{{ money(row.advance_amount) }}</b>
								<span class="ss-tag" :class="`tone-${advance_status(row).tone}`">{{ advance_status(row).label }}</span>
							</span>
						</button>
					</div>
				</template>
				<template v-else>
					<Empty
						v-if="!data.claims.length"
						icon="file"
						title="ยังไม่มีใบเคลียร์/เบิกคืน"
						text="เคลียร์เงินสำรองจ่ายจากใบเบิก หรือกด ขอเบิก → เบิกค่าใช้จ่ายคืน"
					/>
					<div v-else class="ss-list">
						<button
							v-for="(row, i) in data.claims"
							:key="row.name"
							type="button"
							class="ss-card ss-card--row"
							:style="{ '--i': i }"
							@click="open_claim(row)"
						>
							<span class="ss-avatar tone-teal"><Icon name="file" :size="18" /></span>
							<span class="ss-card-main">
								<span class="ss-card-title">{{ row.total_advance_amount ? "เคลียร์เงินสำรองจ่าย" : "เบิกค่าใช้จ่ายคืน" }}</span>
								<span class="ss-card-meta">{{ thai_date(row.posting_date, { year: true }) }} · {{ row.name }}</span>
							</span>
							<span class="ss-leave-side">
								<b class="ss-money">{{ money(row.total_claimed_amount) }}</b>
								<span class="ss-tag" :class="`tone-${claim_status(row).tone}`">{{ claim_status(row).label }}</span>
							</span>
						</button>
					</div>
				</template>
			</template>
		</div>

		<Teleport to="#ss-layer">
			<Transition name="ss-pop">
				<button v-if="data && !wide" type="button" class="ss-fab" @click="open_request()">
					<Icon name="plus" :size="26" :stroke="2.6" />
					<span>ขอเบิก</span>
				</button>
			</Transition>
		</Teleport>

		<!-- ขอเบิก -->
		<Sheet :open="request_open" title="ขอเบิก" subtitle="ส่งให้ผู้อนุมัติ (Expense Approver)" @close="request_open = false">
			<Segmented v-model="form.type" :options="REQUEST_TYPES" />
			<template v-if="form.type !== 'reimburse'">
				<div class="ss-field">
					<span class="ss-field-label">จำนวนเงิน (บาท)<em>*</em></span>
					<MoneyInput v-model="form.amount" />
				</div>
				<template v-if="form.type === 'Salary Advance'">
					<div class="ss-facts">
						<div class="ss-fact"><span>เงินเดือน</span><b>{{ money(data.salary.base) }}</b></div>
						<div class="ss-fact">
							<span>วงเงิน {{ num(data.salary.percent) }}%</span><b>{{ money(data.salary.limit) }}</b>
						</div>
						<div class="ss-fact"><span>ยังหักคืนไม่ครบ</span><b>{{ money(data.salary.used) }}</b></div>
						<div class="ss-fact"><span>คงเหลือ</span><b>{{ money(data.salary.available) }}</b></div>
					</div>
					<p v-if="over_limit" class="ss-note ss-note--warn">
						เกินวงเงิน {{ money(Number(form.amount) - data.salary.available) }} บาท ต้องให้ผู้บริหารอนุมัติเพิ่ม
					</p>
					<div class="ss-field">
						<span class="ss-field-label">หักคืนจากเงินเดือน</span>
						<SelectBox v-model="form.installments" :options="installment_options" />
					</div>
				</template>
				<div v-else class="ss-field">
					<span class="ss-field-label">วันที่ต้องการรับเงิน</span>
					<DateInput v-model="form.required_date" :min="today()" clearable />
				</div>
				<label class="ss-field">
					<span class="ss-field-label">วัตถุประสงค์<em>*</em></span>
					<textarea
						v-model="form.purpose"
						class="ss-input"
						rows="2"
						:placeholder="form.type === 'Salary Advance' ? 'เช่น ค่าเทอมลูก' : 'เช่น ซื้อวัสดุเร่งด่วนหน้างาน'"
					></textarea>
				</label>
			</template>
			<p v-else class="ss-note">
				สำรองจ่ายเงินตัวเองไปแล้ว ส่งบิลเบิกคืน กด ต่อไป เพื่อเพิ่มรายการค่าใช้จ่ายพร้อมรูปบิล
			</p>
			<template #footer>
				<button
					type="button"
					class="ss-btn ss-btn--primary ss-btn--block ss-btn--lg"
					:disabled="busy || !can_request"
					@click="send_request"
				>
					<span v-if="busy" class="ss-spinner"></span>
					<span>{{ form.type === "reimburse" ? "ต่อไป" : "ส่งขอเบิก" }}</span>
				</button>
			</template>
		</Sheet>

		<!-- รายละเอียดใบเบิก -->
		<Sheet :open="!!viewing" :title="viewing && TYPE[viewing.advance_type]" :subtitle="viewing?.name" @close="viewing = null">
			<div v-if="viewing" class="ss-facts">
				<div class="ss-fact">
					<span>สถานะ</span>
					<b><span class="ss-tag" :class="`tone-${advance_status(viewing).tone}`">{{ advance_status(viewing).label }}</span></b>
				</div>
				<div class="ss-fact"><span>จำนวนเงิน</span><b>{{ money(viewing.advance_amount) }} บาท</b></div>
				<div class="ss-fact"><span>วัตถุประสงค์</span><b>{{ viewing.purpose }}</b></div>
				<div v-if="viewing.advance_type === 'Salary Advance'" class="ss-fact">
					<span>หักคืน</span><b>{{ viewing.installments || 1 }} งวด</b>
				</div>
				<div v-if="viewing.over_limit" class="ss-fact"><span>วงเงิน</span><b>เกินวงเงิน (ผู้บริหารอนุมัติ)</b></div>
				<div v-if="viewing.paid_amount" class="ss-fact"><span>จ่ายแล้ว</span><b>{{ money(viewing.paid_amount) }}</b></div>
				<template v-if="viewing.advance_type === 'Expense Advance' && viewing.docstatus === 1">
					<div class="ss-fact"><span>เคลียร์แล้ว</span><b>{{ money(viewing.claimed_amount) }}</b></div>
					<div v-if="viewing.return_amount" class="ss-fact"><span>คืนเงินแล้ว</span><b>{{ money(viewing.return_amount) }}</b></div>
					<div class="ss-fact"><span>คงค้าง</span><b>{{ money(viewing.unclaimed) }}</b></div>
					<div v-if="viewing.clear_due_date" class="ss-fact">
						<span>กำหนดเคลียร์</span>
						<b :class="{ 'ss-text-danger': viewing.overdue }">{{ thai_date(viewing.clear_due_date, { year: true }) }}</b>
					</div>
				</template>
				<div v-if="viewing.reject_reason" class="ss-fact"><span>เหตุผลที่ไม่อนุมัติ</span><b>{{ viewing.reject_reason }}</b></div>
			</div>
			<template v-if="viewing && (viewing.can_clear || viewing.can_delete)" #footer>
				<button
					v-if="viewing.can_clear"
					type="button"
					class="ss-btn ss-btn--primary ss-btn--block ss-btn--lg"
					@click="open_clear(viewing)"
				>
					<Icon name="file" :size="18" />
					<span>เคลียร์ค่าใช้จ่าย</span>
				</button>
				<button
					v-else
					type="button"
					class="ss-btn ss-btn--ghost-danger ss-btn--block ss-btn--lg"
					:disabled="busy"
					@click="withdraw_advance(viewing)"
				>
					<Icon name="trash" :size="18" />
					<span>ถอนใบเบิก</span>
				</button>
			</template>
		</Sheet>

		<!-- ใบเคลียร์ / เบิกคืน -->
		<Sheet
			:open="!!claim"
			full
			:title="claim?.advance ? 'เคลียร์เงินสำรองจ่าย' : 'เบิกค่าใช้จ่ายคืน'"
			:subtitle="claim?.advance ? `${claim.advance.name} · คงค้าง ${money(claim.advance.unclaimed)} บาท` : 'ทุกรายการต้องแนบรูปบิล/ใบเสร็จ'"
			@close="close_claim"
		>
			<template v-if="claim">
				<section v-for="(row, i) in claim.rows" :key="row.key" class="ss-card ss-claim-row">
					<div class="ss-dayoff-head">
						<b>รายการที่ {{ i + 1 }}</b>
						<button
							v-if="claim.rows.length > 1"
							type="button"
							class="ss-icon-btn"
							aria-label="ลบรายการ"
							@click="claim.rows.splice(i, 1)"
						>
							<Icon name="trash" :size="16" />
						</button>
					</div>
					<div class="ss-leave-dates">
						<div class="ss-field">
							<span class="ss-field-label">ประเภท<em>*</em></span>
							<SelectBox v-model="row.expense_type" :options="type_options" placeholder="เลือก" />
						</div>
						<div class="ss-field">
							<span class="ss-field-label">วันที่</span>
							<DateInput v-model="row.expense_date" />
						</div>
					</div>
					<label class="ss-field">
						<span class="ss-field-label">รายละเอียด</span>
						<input v-model="row.description" class="ss-input" placeholder="เช่น ค่าน้ำมันรถไปไซต์" />
					</label>
					<div class="ss-field">
						<span class="ss-field-label">จำนวนเงิน (บาท)<em>*</em></span>
						<MoneyInput v-model="row.amount" />
					</div>
					<div class="ss-field">
						<span class="ss-field-label">รูปบิล/ใบเสร็จ<em>*</em></span>
						<PhotoInput v-model="row.photos" :max="1" label="ถ่ายรูปบิล" />
					</div>
				</section>
				<button type="button" class="ss-btn ss-btn--soft ss-btn--block" @click="add_row">
					<Icon name="plus" :size="18" /><span>เพิ่มรายการ</span>
				</button>
				<label class="ss-field">
					<span class="ss-field-label">หมายเหตุ</span>
					<textarea v-model="claim.remark" class="ss-input" rows="2"></textarea>
				</label>
				<div class="ss-facts">
					<div class="ss-fact"><span>รวมค่าใช้จ่าย</span><b>{{ money(claim_total) }} บาท</b></div>
					<template v-if="claim.advance">
						<div class="ss-fact"><span>ตัดจากเงินสำรองจ่าย</span><b>{{ money(Math.min(claim_total, claim.advance.unclaimed)) }}</b></div>
						<div v-if="claim_total < claim.advance.unclaimed" class="ss-fact">
							<span>ต้องคืนเงินให้บริษัท</span><b class="ss-text-danger">{{ money(claim.advance.unclaimed - claim_total) }}</b>
						</div>
						<div v-else-if="claim_total > claim.advance.unclaimed" class="ss-fact">
							<span>บริษัทจ่ายเพิ่ม</span><b>{{ money(claim_total - claim.advance.unclaimed) }}</b>
						</div>
					</template>
				</div>
			</template>
			<template #footer>
				<button
					type="button"
					class="ss-btn ss-btn--primary ss-btn--block ss-btn--lg"
					:disabled="busy || !can_send_claim"
					@click="send_claim"
				>
					<span v-if="busy" class="ss-spinner"></span>
					<span>ส่งให้ผู้อนุมัติ</span>
				</button>
			</template>
		</Sheet>

		<!-- ดูใบเคลียร์ -->
		<Sheet :open="!!claim_view" :title="claim_view?.name" :subtitle="claim_view && claim_status(claim_view).label" @close="claim_view = null">
			<Skeleton v-if="claim_view && !claim_view.expenses" :rows="2" />
			<template v-else-if="claim_view">
				<div class="ss-list">
					<div v-for="(r, i) in claim_view.expenses" :key="i" class="ss-card ss-card--row">
						<a v-if="r.receipt" :href="r.receipt" target="_blank" class="ss-thumb"><img :src="r.receipt" alt="" loading="lazy" /></a>
						<span v-else class="ss-thumb"><Icon name="file" :size="20" /></span>
						<span class="ss-card-main">
							<span class="ss-card-title">{{ r.expense_type }}</span>
							<span class="ss-card-meta">{{ thai_date(r.expense_date, { year: true }) }} · {{ r.description }}</span>
						</span>
						<b class="ss-money">{{ money(r.amount) }}</b>
					</div>
				</div>
				<div class="ss-facts">
					<div class="ss-fact"><span>รวม</span><b>{{ money(claim_view.total_claimed_amount) }} บาท</b></div>
					<div v-if="claim_view.total_advance_amount" class="ss-fact">
						<span>ตัดเงินสำรองจ่าย</span><b>{{ money(claim_view.total_advance_amount) }}</b>
					</div>
					<div v-if="claim_view.reject_reason" class="ss-fact"><span>เหตุผลที่ไม่อนุมัติ</span><b>{{ claim_view.reject_reason }}</b></div>
				</div>
			</template>
			<template v-if="claim_view?.can_delete" #footer>
				<button type="button" class="ss-btn ss-btn--ghost-danger ss-btn--block ss-btn--lg" :disabled="busy" @click="withdraw_claim(claim_view)">
					<Icon name="trash" :size="18" /><span>ถอนใบ</span>
				</button>
			</template>
		</Sheet>
	</div>
</template>

<script setup>
import { computed, inject, reactive, ref } from "vue";
import Icon from "../../shared/components/Icon.vue";
import TopBar from "../../shared/components/TopBar.vue";
import Skeleton from "../../shared/components/Skeleton.vue";
import Empty from "../../shared/components/Empty.vue";
import Sheet from "../../shared/components/Sheet.vue";
import Segmented from "../../shared/components/Segmented.vue";
import SelectBox from "../../shared/components/SelectBox.vue";
import DateInput from "../../shared/components/DateInput.vue";
import MoneyInput from "../../shared/components/MoneyInput.vue";
import PhotoInput from "../../shared/components/PhotoInput.vue";
import StatusTabs from "../../shared/components/StatusTabs.vue";
import { use_wide } from "../../shared/table.js";
import { call, celebrate, money, num, post, show_error, thai_date, toast, today } from "../../shared/api.js";
import { advance_status, claim_status, TYPE } from "../../shared/approvals/status.js";

const API = "consbiz.self_advance.";
const REQUEST_TYPES = [
	{ value: "Salary Advance", label: "เงินเดือนล่วงหน้า" },
	{ value: "Expense Advance", label: "เงินสำรองจ่าย" },
	{ value: "reimburse", label: "เบิกคืน" },
];
const reload_summary = inject("reload_summary");

const data = ref(null);
const loading = ref(false);
const busy = ref(false);
const wide = use_wide();
const tab = ref("advances");
const viewing = ref(null);

const tabs = computed(() => [
	{ value: "advances", label: "ใบเบิก", count: data.value?.advances.length || 0 },
	{ value: "claims", label: "เคลียร์/เบิกคืน", count: data.value?.claims.length || 0 },
]);
const to_clear = computed(() =>
	(data.value?.advances || []).filter((a) => a.can_clear).reduce((s, a) => s + a.unclaimed, 0)
);
const overdue_count = computed(() => (data.value?.advances || []).filter((a) => a.overdue).length);
const pending_count = computed(
	() =>
		(data.value?.advances || []).filter((a) => a.docstatus === 0 && a.approval !== "Rejected").length +
		(data.value?.claims || []).filter((c) => c.docstatus === 0 && !c.reject_reason).length
);

async function load() {
	loading.value = true;
	try {
		data.value = await call(`${API}get_advance_data`);
	} catch (error) {
		show_error(error);
		data.value ??= { advances: [], claims: [], salary: {}, expense_types: [], max_installments: 1 };
	} finally {
		loading.value = false;
	}
}
load();

// ---------------------------------------------------------------- ขอเบิก

const request_open = ref(false);
const form = reactive({});
const installment_options = computed(() =>
	Array.from({ length: data.value?.max_installments || 1 }, (_, i) => ({
		value: i + 1,
		label: i ? `ผ่อน ${i + 1} งวด (เดือน)` : "หักครั้งเดียวงวดถัดไป",
	}))
);
const over_limit = computed(
	() => form.type === "Salary Advance" && Number(form.amount) > (data.value?.salary.available || 0)
);
const can_request = computed(
	() => form.type === "reimburse" || (Number(form.amount) > 0 && form.purpose?.trim())
);

function open_request() {
	Object.assign(form, { type: "Salary Advance", amount: null, purpose: "", installments: 1, required_date: null });
	request_open.value = true;
}

async function send_request() {
	if (form.type === "reimburse") {
		request_open.value = false;
		open_clear(null);
		return;
	}
	busy.value = true;
	try {
		await post(`${API}request_advance`, {
			advance_type: form.type,
			amount: form.amount,
			purpose: form.purpose,
			installments: form.installments,
			required_date: form.required_date || undefined,
		});
		request_open.value = false;
		celebrate("ส่งขอเบิกแล้ว", over_limit.value ? "รอผู้อนุมัติ และผู้บริหาร (เกินวงเงิน)" : "รอผู้อนุมัติ");
		tab.value = "advances";
		await load();
		reload_summary?.("self");
	} catch (error) {
		show_error(error);
	} finally {
		busy.value = false;
	}
}

async function withdraw_advance(row) {
	busy.value = true;
	try {
		await post(`${API}delete_advance`, { name: row.name });
		viewing.value = null;
		toast("ถอนใบเบิกแล้ว", "success");
		await load();
	} catch (error) {
		show_error(error);
	} finally {
		busy.value = false;
	}
}

// ---------------------------------------------------------------- เคลียร์ / เบิกคืน

const claim = ref(null);
let row_key = 0;
const new_row = () => ({ key: ++row_key, expense_type: null, expense_date: today(), description: "", amount: null, photos: [] });
const type_options = computed(() => (data.value?.expense_types || []).map((t) => ({ value: t, label: t })));
const claim_total = computed(() => (claim.value?.rows || []).reduce((s, r) => s + (Number(r.amount) || 0), 0));
const can_send_claim = computed(
	() =>
		claim.value?.rows.length &&
		claim.value.rows.every((r) => r.expense_type && Number(r.amount) > 0 && r.photos[0]?.name && !r.photos[0]?.uploading)
);

function open_clear(advance) {
	viewing.value = null;
	claim.value = { advance, rows: [new_row()], remark: "" };
}
function add_row() {
	claim.value.rows.push(new_row());
}
function close_claim() {
	if (!busy.value) claim.value = null;
}

async function send_claim() {
	busy.value = true;
	try {
		await post(`${API}submit_claim`, {
			rows: claim.value.rows.map((r) => ({
				expense_type: r.expense_type,
				expense_date: r.expense_date,
				description: r.description,
				amount: r.amount,
				receipt: r.photos[0].name,
			})),
			remark: claim.value.remark,
			advance: claim.value.advance?.name,
		});
		claim.value = null;
		celebrate("ส่งให้ผู้อนุมัติแล้ว");
		tab.value = "claims";
		await load();
		reload_summary?.("self");
	} catch (error) {
		show_error(error);
	} finally {
		busy.value = false;
	}
}

const claim_view = ref(null);
async function open_claim(row) {
	claim_view.value = { ...row };
	try {
		const detail = await call(`${API}get_claim`, { name: row.name });
		if (claim_view.value?.name === row.name) claim_view.value = { ...detail, can_delete: row.can_delete };
	} catch (error) {
		show_error(error);
		claim_view.value = null;
	}
}

async function withdraw_claim(row) {
	busy.value = true;
	try {
		await post(`${API}delete_claim`, { name: row.name });
		claim_view.value = null;
		toast("ถอนใบแล้ว", "success");
		await load();
	} catch (error) {
		show_error(error);
	} finally {
		busy.value = false;
	}
}
</script>
