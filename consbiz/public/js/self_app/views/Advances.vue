<!-- เบิกเงิน (API consbiz/self_advance.py, ฟอร์มขอเบิก/เคลียร์ = shared/components/AdvanceForms.vue ชุดเดียวกับที่ HR บันทึกแทน): เบิกเงินเดือนล่วงหน้า (วงเงิน 50% เกิน = ผู้บริหารอนุมัติ, หักคืน 1-6 งวด)
     เงินทดรองจ่าย (จ่ายแล้วเคลียร์ภายใน 15 วัน) และเบิกสำรองจ่าย (สำรองจ่ายเอง) ทุกรายการค่าใช้จ่ายต้องมีรูปบิล
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
						<span class="ss-stat-label">เงินทดรองจ่ายรอเคลียร์</span>
						<span v-if="overdue_count" class="ss-stat-alert">เลยกำหนด {{ overdue_count }}</span>
					</div>
					<div class="ss-stat tone-green" style="--i: 2">
						<span class="ss-stat-icon"><Icon name="clock" :size="20" /></span>
						<span class="ss-stat-value">{{ pending_count }}</span>
						<span class="ss-stat-label">รออนุมัติ</span>
					</div>
				</div>

				<ListHead
					v-if="wide"
					v-model="tab"
					:tabs="tabs"
					:loading="loading"
					@refresh="load"
					create="ขอเบิก"
					@create="open_request()"
				/>
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
						text="กดปุ่ม ขอเบิก เพื่อเบิกเงินเดือนล่วงหน้าหรือเงินทดรองจ่าย"
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
						title="ยังไม่มีใบเคลียร์/สำรองจ่าย"
						text="เคลียร์เงินทดรองจ่ายจากใบเบิก หรือกด ขอเบิก → เบิกสำรองจ่าย"
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
								<span class="ss-card-title">{{ row.total_advance_amount ? "เคลียร์เงินทดรองจ่าย" : "เบิกสำรองจ่าย" }}</span>
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

		<AdvanceForms ref="forms" :data="data" @done="on_done" />

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
					<span>หักคืน</span><b>{{ viewing.docstatus === 1 ? `${viewing.installments || 1} งวด` : "ผู้อนุมัติกำหนด" }}</b>
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
						<span>ตัดเงินทดรองจ่าย</span><b>{{ money(claim_view.total_advance_amount) }}</b>
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
import { computed, inject, ref } from "vue";
import Icon from "../../shared/components/Icon.vue";
import TopBar from "../../shared/components/TopBar.vue";
import Skeleton from "../../shared/components/Skeleton.vue";
import Empty from "../../shared/components/Empty.vue";
import Sheet from "../../shared/components/Sheet.vue";
import AdvanceForms from "../../shared/components/AdvanceForms.vue";
import ListHead from "../../shared/components/ListHead.vue";
import { use_wide } from "../../shared/table.js";
import { call, celebrate, money, post, replace_params, show_error, state, thai_date, toast } from "../../shared/api.js";
import { advance_status, claim_status, TYPE } from "../../shared/approvals/status.js";

const API = "consbiz.self_advance.";
const reload_summary = inject("reload_summary");

const data = ref(null);
const loading = ref(false);
const busy = ref(false);
const wide = use_wide();
const tab = ref("advances");
const viewing = ref(null);

const tabs = computed(() => [
	{ value: "advances", label: "ใบเบิก", count: data.value?.advances.length || 0 },
	{ value: "claims", label: "เคลียร์/สำรองจ่าย", count: data.value?.claims.length || 0 },
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
// ทางลัดจากหน้าแรก: /advances/<Salary Advance|Expense Advance|reimburse> = เปิดฟอร์มขอเบิกชนิดนั้นทันที
const start_action = state.route.params.action;
load().then(() => {
	if (!start_action) return;
	replace_params("advances", {});
	open_request(start_action);
});

// ---------------------------------------------------------------- ขอเบิก / เคลียร์ (shared/components/AdvanceForms.vue)

const forms = ref(null);
const open_request = (type = null) => forms.value?.open_request(type);
function open_clear(advance) {
	viewing.value = null;
	forms.value?.open_clear(advance);
}
async function on_done({ kind, over_limit }) {
	if (kind === "advance") celebrate("ส่งขอเบิกแล้ว", over_limit ? "รอผู้อนุมัติ และผู้บริหาร (เกินวงเงิน)" : "รอผู้อนุมัติ");
	else celebrate("ส่งให้ผู้อนุมัติแล้ว");
	tab.value = kind === "advance" ? "advances" : "claims";
	await load();
	reload_summary?.("self");
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
