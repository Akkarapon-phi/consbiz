<template>
	<div>
		<TopBar :title="doc?.account_name || 'บัญชีธนาคาร'" back_to="acc-bank-accounts" />
		<div class="ss-content">
			<Empty v-if="failed" title="โหลดข้อมูลบัญชีไม่สำเร็จ" icon="alert" />
			<Skeleton v-else-if="!doc" />
			<template v-else>
				<section class="ss-card ss-form">
					<div class="ss-card-head">
						<div class="ss-card-main">
							<b class="ss-card-title">{{ doc.account_name }}</b>
							<span class="ss-card-meta">{{ doc.bank }} · {{ doc.company }}</span>
						</div>
						<span v-if="doc.disabled" class="ss-tag tone-gray">ปิดใช้งาน</span>
						<span v-if="doc.is_default" class="ss-tag tone-green">บัญชีเริ่มต้น</span>
						<button
							v-if="data.can_write"
							type="button"
							class="ss-btn ss-btn--soft ss-list-create"
							@click="form = true"
						>
							<Icon name="pen" :size="16" /> แก้ไข
						</button>
					</div>
					<div class="ss-facts ss-facts--grid">
						<div class="ss-fact">
							<span>เลขที่บัญชี</span><b>{{ doc.bank_account_no || "—" }}</b>
						</div>
						<div class="ss-fact">
							<span>ผังบัญชี</span><b>{{ doc.account || "—" }}</b>
						</div>
						<div v-if="doc.branch_code" class="ss-fact">
							<span>รหัสสาขา</span><b>{{ doc.branch_code }}</b>
						</div>
						<div v-if="doc.iban" class="ss-fact">
							<span>IBAN</span><b>{{ doc.iban }}</b>
						</div>
						<div v-if="data.can_gl" class="ss-fact">
							<span>ยอดคงเหลือ ณ วันนี้</span
							><b>{{ money(data.balance) }} {{ data.currency }}</b>
						</div>
					</div>
				</section>
				<template v-if="data.can_gl">
					<ListHead>
						<template #lead><b class="ss-section-title">รายการเคลื่อนไหว</b></template>
						<template #tools>
							<ProjectFilter />
							<DateInput
								v-model="month"
								picker="month"
								variant="tool"
								label="เลือกเดือน"
								placeholder="3 เดือนล่าสุด"
								:max="today_month"
								clearable
							/>
						</template>
					</ListHead>
					<ListCard :on="wide">
						<div v-if="wide" class="ss-table-wrap">
							<table class="ss-table ss-table--list">
								<thead>
									<tr>
										<th>วันที่</th>
										<th>เอกสาร</th>
										<th class="bank-party-column">คู่ค้า / หมายเหตุ</th>
										<th class="is-num">ฝาก</th>
										<th class="is-num">ถอน</th>
										<th class="is-num">คงเหลือ</th>
									<th class="col-modified"></th>
									</tr>
								</thead>
								<tbody>
									<tr class="is-static">
										<td colspan="5">ยอดยกมา · {{ date(data.from_date) }}</td>
										<td class="is-num">
											<b>{{ money(data.opening) }}</b>
										</td>
										<td class="col-modified"></td>
									</tr>
									<tr v-for="r in data.rows" :key="r.name" class="is-static">
										<td class="col-nowrap">{{ date(r.posting_date) }}</td>
										<td class="col-nowrap">
											<button
												v-if="r.payment_view"
												class="ss-link"
												type="button"
												@click="payment(r)"
											>
												{{ r.voucher_no }}
											</button>
											<b v-else>{{ r.voucher_no }}</b
											><small>{{ r.voucher_type }}</small>
										</td>
										<td>
											<div v-if="r.party">{{ r.party }}</div>
											<small v-if="r.remarks" class="bank-remarks" :title="r.remarks">{{ r.remarks }}</small>
										</td>
										<td class="is-num">{{ money(r.debit) }}</td>
										<td class="is-num">{{ money(r.credit) }}</td>
										<td class="is-num">
											<b>{{ money(r.balance) }}</b>
										</td>
										<ModifiedCell :value="r.modified" :row="r" />
									</tr>
									<tr v-if="!data.rows.length">
										<td colspan="7">ไม่มีรายการเคลื่อนไหวในช่วงนี้</td>
									</tr>
								</tbody>
							</table>
						</div>
						<div v-else class="ss-list">
							<div class="ss-card">
								<div class="ss-card-head">
									<b>ยอดยกมา · {{ date(data.from_date) }}</b
									><b>{{ money(data.opening) }}</b>
								</div>
							</div>
							<Empty
								v-if="!data.rows.length"
								icon="list"
								title="ไม่มีรายการเคลื่อนไหวในช่วงนี้"
							/>
							<div v-for="r in data.rows" :key="r.name" class="ss-card">
								<div class="ss-card-head">
									<span class="ss-card-main">
										<button
											v-if="r.payment_view"
											type="button"
											class="ss-link bank-voucher"
											@click="payment(r)"
										>
											{{ r.voucher_no }}
										</button>
										<b v-else class="bank-voucher">{{ r.voucher_no }}</b>
										<span class="ss-card-meta"
											>{{ r.voucher_type }} · {{ date(r.posting_date) }}</span
										> </span
									><b>{{ money(r.balance) }}</b>
								</div>
								<div class="ss-chips">
									<span class="ss-chip">ฝาก {{ money(r.debit) }}</span
									><span class="ss-chip">ถอน {{ money(r.credit) }}</span>
								</div>
								<div v-if="r.party" class="ss-card-meta">{{ r.party }}</div>
								<div v-if="r.remarks" class="ss-card-meta bank-remarks" :title="r.remarks">{{ r.remarks }}</div>
							</div>
						</div>
						<footer class="ss-list-foot">
							<span>ยอดปลายงวด · {{ date(data.to_date) }}</span>
							<span class="ss-toolbar-gap"></span
							><b>{{ money(data.closing) }} {{ data.currency }}</b>
						</footer>
					</ListCard>
				</template>
			</template>
		</div>
		<BankForm v-if="form" :doc="doc" @close="form = false" @saved="saved" />
	</div>
</template>

<script setup>
import ModifiedCell from "../../../shared/components/ModifiedCell.vue";
import { computed, ref, watch } from "vue";
import { call, go, iso_date, money, scope_args, show_error, state, thai_date } from "../../../shared/api.js";
import { use_wide } from "../../../shared/table.js";
import DateInput from "../../../shared/components/DateInput.vue";
import Empty from "../../../shared/components/Empty.vue";
import Icon from "../../../shared/components/Icon.vue";
import ListHead from "../../../shared/components/ListHead.vue";
import ListCard from "../../../shared/components/ListCard.vue";
import Skeleton from "../../../shared/components/Skeleton.vue";
import TopBar from "../../../shared/components/TopBar.vue";
import ProjectFilter from "../../../shared/docs/ProjectFilter.vue";
import BankForm from "./BankForm.vue";

const name = state.route.params.name;
const wide = use_wide();
const today_month = iso_date(new Date()).slice(0, 7);
const data = ref(null);
const failed = ref(false);
const doc = computed(() => data.value?.doc);
const month = ref(null);
const form = ref(false);
const date = (d) => thai_date(d, { year: true });
function payment(r) {
	go("acc-payment", { kind: r.payment_view, name: r.voucher_no });
}
function saved() {
	form.value = false;
	load();
}
let job = 0;
async function load() {
	const id = ++job;
	failed.value = false;
	try {
		const result = await call("consbiz.bank_app.get_account", {
			name,
			month: month.value || undefined,
			company: scope_args().company,
			project: scope_args().project,
		});
		if (id === job) data.value = result;
	} catch (e) {
		if (id === job) {
			failed.value = true;
			show_error(e);
		}
	}
}
watch([month, () => scope_args().project], load, { immediate: true });
</script>

<style scoped>
.bank-party-column {
	width: 100%;
}
.bank-voucher,
.bank-remarks {
	white-space: nowrap;
}
.bank-remarks {
	display: block;
	overflow: hidden;
	text-overflow: ellipsis;
}
td .bank-remarks {
	/* Let the table size the column without measuring the full remark. */
	width: 0;
	min-width: 100%;
}
</style>
