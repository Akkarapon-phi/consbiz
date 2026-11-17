<!-- หนังสือรับรองการหักภาษี ณ ที่จ่าย (50 ทวิ, Withholding Tax Cert ของ erpnext_thailand) ที่เราออกให้ผู้ขาย/ผรม.
     ใบใหม่ออกจากหน้าจ่ายชำระเท่านั้น (acc-wht-doc/new/<จ่ายชำระ>) ร่าง = แก้ในหน้านี้ ยืนยัน = Submit แล้ว PDF
     แบบ ภ.ง.ด.3 (บุคคลธรรมดา) / ภ.ง.ด.53 (นิติบุคคล) เติมจากประเภทผู้ขาย API consbiz/accounting_app.py -->
<template>
	<div>
		<TopBar :title="title" :subtitle="doc?.supplier_name" :back_to="back_view" />

		<div class="ss-content">
			<FormHead
				v-if="doc"
				v-model="tab"
				:tabs="TABS"
				:actions="actions"
				:menu="menu"
				:busy="busy"
				:on-print="view.pdf_url ? () => (pdf = true) : null"
			/>

			<Skeleton v-if="!doc" :rows="6" />
			<template v-else>
				<section class="ss-card ss-form">
					<div v-if="doc.name" class="ss-doc-head-top">
						<span class="ss-tag" :class="`tone-${doc.status_tone}`">{{
							doc.status_label
						}}</span>
						<span class="ss-doc-date">{{ doc.name }}</span>
					</div>
					<div class="ss-facts ss-facts--grid">
						<div class="ss-fact">
							<span>ผู้ถูกหัก</span><b>{{ doc.supplier_name || doc.supplier }}</b>
						</div>
						<div class="ss-fact">
							<span>เลขประจำตัวผู้เสียภาษี</span
							><b>{{ doc.supplier_tax_id || "—" }}</b>
						</div>
						<div class="ss-fact">
							<span>ผู้หัก (บริษัท)</span><b>{{ doc.company }}</b>
						</div>
						<div class="ss-fact">
							<span>เลขประจำตัวผู้เสียภาษีบริษัท</span
							><b>{{ doc.company_tax_id || "—" }}</b>
						</div>
						<div v-if="doc.voucher_no" class="ss-fact">
							<span>จ่ายชำระ</span>
							<b
								><a href="#" @click.prevent="open_payment">{{
									doc.voucher_no
								}}</a></b
							>
						</div>
					</div>
					<div class="ss-form-row">
						<label class="ss-field">
							<span class="ss-field-label">แบบ<em>*</em></span>
							<SelectBox
								v-model="doc.income_tax_form"
								:options="options.forms"
								label="แบบ ภ.ง.ด."
								:disabled="!editable"
							/>
						</label>
						<label class="ss-field">
							<span class="ss-field-label">ผู้จ่ายเงิน<em>*</em></span>
							<SelectBox
								v-model="doc.tax_payer"
								:options="options.tax_payers"
								label="ผู้จ่ายเงิน"
								:disabled="!editable"
							/>
						</label>
						<label class="ss-field">
							<span class="ss-field-label">วันที่จ่าย<em>*</em></span>
							<DateInput
								v-model="doc.date"
								label="วันที่จ่าย"
								:disabled="!editable"
							/>
						</label>
					</div>
					<div class="ss-form-row">
						<label class="ss-field">
							<span class="ss-field-label"
								>ที่อยู่บริษัท (สาขาที่ยื่น)<em>*</em></span
							>
							<SelectBox
								v-model="doc.company_address"
								:options="options.company_addresses"
								label="ที่อยู่บริษัท"
								placeholder="เลือกที่อยู่"
								:disabled="!editable"
							/>
						</label>
						<label class="ss-field">
							<span class="ss-field-label">ที่อยู่ผู้ถูกหัก<em>*</em></span>
							<SelectBox
								v-model="doc.supplier_address"
								:options="options.supplier_addresses"
								label="ที่อยู่ผู้ถูกหัก"
								placeholder="เลือกที่อยู่"
								:disabled="!editable"
							/>
						</label>
					</div>
					<p v-if="editable && !options.supplier_addresses.length" class="ss-muted">
						ผู้ขายรายนี้ยังไม่มีที่อยู่ เพิ่มที่อยู่ที่ผู้ขายในระบบเต็มก่อน
					</p>
				</section>

				<section class="ss-card">
					<h2 class="ss-section-title">เงินได้ที่จ่ายและภาษีที่หัก</h2>
					<div class="ss-table-wrap">
						<table class="ss-table ss-table--list">
							<thead>
								<tr>
									<th>ประเภทเงินได้</th>
									<th class="is-num">จำนวนเงินที่จ่าย</th>
									<th class="is-num">อัตรา %</th>
									<th class="is-num">ภาษีที่หัก</th>
								</tr>
							</thead>
							<tbody>
								<tr v-for="(r, i) in doc.items" :key="i" class="is-static">
									<td>
										<SelectBox
											v-if="editable"
											v-model="r.type_of_income"
											:options="options.income_types"
											label="ประเภทเงินได้"
											variant="cell"
											@update:model-value="(v) => set_income(r, v)"
										/>
										<span v-else class="ss-cell-main">{{
											income_label(r.type_of_income)
										}}</span>
										<input
											v-if="editable"
											v-model="r.description"
											class="ss-input"
											placeholder="รายละเอียด"
										/>
										<small
											v-else-if="
												r.description &&
												!income_label(r.type_of_income).endsWith(
													r.description
												)
											"
											>{{ r.description }}</small
										>
									</td>
									<td class="is-num">
										<MoneyInput
											v-if="editable"
											v-model="r.tax_base"
											class="ss-input"
											@update:model-value="recalc(r)"
										/>
										<template v-else>{{ money(r.tax_base) }}</template>
									</td>
									<td class="is-num">
										<input
											v-if="editable"
											v-model.number="r.tax_rate"
											class="ss-input"
											type="number"
											inputmode="decimal"
											min="0"
											step="0.5"
											@input="recalc(r)"
										/>
										<template v-else>{{ num(r.tax_rate) }}</template>
									</td>
									<td class="is-num">
										<MoneyInput
											v-if="editable"
											v-model="r.tax_amount"
											class="ss-input"
										/>
										<b v-else>{{ money(r.tax_amount) }}</b>
									</td>
								</tr>
								<tr class="is-static">
									<td><b>รวม</b></td>
									<td class="is-num">
										<b>{{ money(totals.base) }}</b>
									</td>
									<td></td>
									<td class="is-num">
										<b>{{ money(totals.tax) }}</b>
									</td>
								</tr>
							</tbody>
						</table>
					</div>
					<p v-if="editable" class="ss-muted">
						ภาษีที่หักคำนวณจาก จำนวนเงิน x อัตรา แก้ยอดเองได้
						(ต้องตรงกับยอดที่หักในการจ่ายชำระ)
					</p>
				</section>
			</template>
		</div>

		<Sheet
			:open="confirm_submit"
			title="ยืนยันออกหนังสือรับรอง"
			:subtitle="doc?.name"
			@close="confirm_submit = false"
		>
			<p class="ss-note-line">
				ภาษีที่หัก {{ money(totals.tax) }} ({{ FORM_LABEL[doc?.income_tax_form] }})
				ขึ้นในรายงาน {{ FORM_LABEL[doc?.income_tax_form] }} ของเดือนที่จ่าย
				หลังยืนยันแก้ไขไม่ได้ (ยกเลิกแล้วออกใหม่)
			</p>
			<template #footer>
				<button
					type="button"
					class="ss-btn ss-btn--primary ss-btn--block ss-btn--lg"
					:disabled="busy"
					@click="submit"
				>
					ยืนยัน
				</button>
			</template>
		</Sheet>
		<Sheet
			:open="confirm_cancel"
			title="ยกเลิกหนังสือรับรอง"
			:subtitle="doc?.name"
			@close="confirm_cancel = false"
		>
			<p class="ss-note-line">
				หนังสือนี้หายจากรายงาน ภ.ง.ด. และการจ่ายชำระกลับเป็น "ยังไม่ออกหนังสือ"
				ออกใบใหม่ได้จากหน้าจ่ายชำระ
			</p>
			<template #footer>
				<button
					type="button"
					class="ss-btn ss-btn--danger ss-btn--block ss-btn--lg"
					:disabled="busy"
					@click="cancel"
				>
					ยืนยันยกเลิก
				</button>
			</template>
		</Sheet>
		<DeleteSheet
			:open="deleting"
			label="หนังสือรับรองหัก ณ ที่จ่าย"
			:name="doc?.name"
			:method="`${API}.delete_cert`"
			:args="{ name: doc?.name }"
			@close="deleting = false"
			@deleted="go('acc-wht', {}, { replace: true })"
		/>
		<PdfViewer
			:open="pdf"
			:url="view.pdf_url"
			:name="doc?.name"
			title="หนังสือรับรองหัก ณ ที่จ่าย"
			@close="pdf = false"
		/>
	</div>
</template>

<script setup>
import { computed, inject, ref } from "vue";
import DateInput from "../../../shared/components/DateInput.vue";
import DeleteSheet from "../../../shared/components/DeleteSheet.vue";
import Icon from "../../../shared/components/Icon.vue";
import MoneyInput from "../../../shared/components/MoneyInput.vue";
import PdfViewer from "../../../shared/components/PdfViewer.vue";
import SelectBox from "../../../shared/components/SelectBox.vue";
import Sheet from "../../../shared/components/Sheet.vue";
import Skeleton from "../../../shared/components/Skeleton.vue";
import TopBar from "../../../shared/components/TopBar.vue";
import FormHead from "../../../shared/components/FormHead.vue";
import { LABELS, can_duplicate, doc_menu, duplicate_doc, step_actions } from "../../../shared/form_actions.js";
import {
	back,
	call,
	celebrate,
	desk_url,
	go,
	money,
	num,
	post,
	show_error,
	state,
} from "../../../shared/api.js";
import { API, FORM_LABEL } from "./kinds.js";

const reload_summary = inject("reload_summary");
const params = state.route.params;
const is_new = !params.name || params.name === "new";
// ใบใหม่ย้อนกลับไปหน้าจ่ายชำระต้นทาง
const back_view = is_new ? "acc-payments" : "acc-wht";
const TABS = [{ value: "detail", label: "หนังสือรับรอง" }];

const tab = ref("detail");
const view = ref({});
const doc = ref(null);
const options = ref({
	forms: [],
	tax_payers: [],
	company_addresses: [],
	supplier_addresses: [],
	income_types: [],
});
const saved = ref("");
const busy = ref(false);
const pdf = ref(false);
const deleting = ref(false);
const confirm_submit = ref(false);
const confirm_cancel = ref(false);

const editable = computed(() => !!view.value.can_edit);
const title = computed(() =>
	doc.value?.name
		? `หนังสือรับรองหัก ณ ที่จ่าย ${doc.value.name}`
		: "ออกหนังสือรับรองหัก ณ ที่จ่าย"
);
const totals = computed(() => ({
	base: (doc.value?.items || []).reduce((s, r) => s + (Number(r.tax_base) || 0), 0),
	tax: (doc.value?.items || []).reduce((s, r) => s + (Number(r.tax_amount) || 0), 0),
}));
const can_save = computed(
	() =>
		!!doc.value?.income_tax_form &&
		!!doc.value?.company_address &&
		!!doc.value?.supplier_address &&
		doc.value.items.length > 0 &&
		doc.value.items.every((r) => r.type_of_income)
);

const INPUT = [
	"name",
	"modified",
	"voucher_no",
	"income_tax_form",
	"tax_payer",
	"date",
	"company_address",
	"supplier_address",
];
const payload = () =>
	JSON.stringify({
		...Object.fromEntries(INPUT.map((f) => [f, doc.value[f] ?? null])),
		items: doc.value.items.map((r) => ({
			type_of_income: r.type_of_income,
			description: r.description || null,
			tax_base: Number(r.tax_base) || 0,
			tax_rate: Number(r.tax_rate) || 0,
			tax_amount: Number(r.tax_amount) || 0,
		})),
	});
const dirty = computed(() => !!doc.value && (!doc.value.name || payload() !== saved.value));

const income_label = (value) =>
	options.value.income_types.find((o) => o.value === value)?.label || value || "—";
function set_income(r, value) {
	// รายละเอียดเดิมเป็นคำอธิบายของประเภทเดิม = เปลี่ยนตาม
	const old = options.value.income_types.find(
		(o) => r.description && o.label.endsWith(r.description)
	);
	const next = options.value.income_types.find((o) => o.value === value);
	if ((!r.description || old) && next) r.description = next.label.replace(/^[\d.]+\.\s*/, "");
}
function recalc(r) {
	r.tax_amount = Math.round((Number(r.tax_base) || 0) * (Number(r.tax_rate) || 0)) / 100;
}

function apply(result) {
	view.value = result;
	options.value = result.options;
	doc.value = { ...result.doc, items: (result.doc.items || []).map((r) => ({ ...r })) };
	saved.value = payload();
}

async function run(task, message) {
	busy.value = true;
	try {
		const result = await task();
		reload_summary();
		if (message) await celebrate(message, result?.doc?.name || doc.value?.name || "");
		return result;
	} catch (e) {
		show_error(e);
	} finally {
		busy.value = false;
	}
}

function open_payment() {
	go("acc-payment", { kind: "acc-payments", name: doc.value.voucher_no });
}
async function save() {
	const result = await run(() => post(`${API}.save_cert`, { data: payload() }), "บันทึกแล้ว");
	if (!result) return;
	apply(result);
	if (is_new) go("acc-wht-doc", { name: result.doc.name }, { replace: true });
}
async function submit() {
	const result = await run(
		() => post(`${API}.submit_cert`, { name: doc.value.name }),
		"ออกหนังสือรับรองแล้ว"
	);
	if (result) apply(result);
	confirm_submit.value = false;
}
async function cancel() {
	const result = await run(
		() => post(`${API}.cancel_cert`, { name: doc.value.name }),
		"ยกเลิกแล้ว"
	);
	if (result) apply(result);
	confirm_cancel.value = false;
}

async function load() {
	try {
		apply(
			await call(
				`${API}.get_cert`,
				is_new ? { source: params.source } : { name: params.name }
			)
		);
	} catch (e) {
		show_error(e);
		back(back_view);
	}
}
// หัวฟอร์ม: ร่าง → บันทึก → ยืนยันออกหนังสือ → ยกเลิก
const actions = computed(() => {
	const v = view.value;
	return step_actions({
		stage: editable.value ? "draft" : "done",
		is_new: !doc.value.name,
		dirty: dirty.value,
		save: editable.value && { run: save, disabled: !can_save.value },
		submit: v.can_submit && { label: "ยืนยันออกหนังสือ", run: () => (confirm_submit.value = true) },
		cancel: v.can_cancel && (() => (confirm_cancel.value = true)),
	});
});
const menu = computed(() =>
	doc_menu({
		refresh: doc.value.name && load,
		desk: [doc.value.doctype, doc.value.name],
		remove: editable.value && view.value.can_delete && (() => (deleting.value = true)),
	})
);

load();
</script>
