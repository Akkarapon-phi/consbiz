<!-- เอกสารพนักงาน 1 หน้า (หมวดบุคคล): สัญญาจ้าง (hr-contracts) / 50 ทวิ พนักงาน (hr-wht) params.kind = หน้ารายการ
     ร่าง = แก้ในหน้าเดียวกัน, ยืนยัน (Submit) แล้ว = ดู + PDF (สัญญาจ้างแก้สถานะทดลองงานได้)
     ลอกหน้าตาจากใบงานเพิ่ม ผรม. (VariationPage.vue) API consbiz/hr_docs.py -->
<template>
	<div>
		<TopBar :title="title" :subtitle="doc?.name || 'ใหม่'" :back_to="params.kind" />

		<div class="ss-content">
			<FormHead
				v-if="doc"
				v-model="tab"
				:tabs="[{ value: 'main', label: kind.label }]"
				:actions="actions"
				:menu="menu"
				:busy="busy"
				:on-print="print_one"
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
					<div class="ss-form-row">
						<label v-if="companies.length > 1" class="ss-field">
							<span class="ss-field-label">บริษัท<em>*</em></span>
							<SelectBox
								v-model="doc.company"
								:options="companies"
								label="บริษัท"
								:disabled="!editable"
							/>
						</label>
						<Picker
							v-model="doc.employee"
							label="พนักงาน"
							:display_value="employee_label"
							:remote_fn="(q) => search('Employee', q)"
							:class="{ 'is-locked': !editable }"
							required
							@select="pick_employee"
						/>
					</div>

					<!-- ---------- สัญญาจ้าง ---------- -->
					<template v-if="is_contract">
						<div class="ss-form-row">
							<label class="ss-field">
								<span class="ss-field-label">วันที่ทำสัญญา<em>*</em></span>
								<DateInput
									v-model="doc.date"
									label="วันที่"
									:disabled="!editable"
								/>
							</label>
							<label class="ss-field">
								<span class="ss-field-label">เงินเดือนเริ่มต้น</span>
								<MoneyInput
									v-model="doc.base"
									class="ss-input"
									:disabled="!editable"
								/>
							</label>
						</div>
						<h2 class="ss-section-title">ทดลองงาน</h2>
						<div class="ss-form-row">
							<label class="ss-field">
								<span class="ss-field-label">วันที่เริ่มทดลองงาน</span>
								<DateInput
									v-model="doc.prob_start_date"
									label="วันที่เริ่ม"
									:disabled="!editable"
									clearable
									@change="set_prob_end"
								/>
							</label>
							<label class="ss-field">
								<span class="ss-field-label">จำนวนวันทดลองงาน</span>
								<SelectBox
									v-model="doc.prob_days"
									:options="PROB_DAYS"
									label="จำนวนวัน"
									placeholder="ไม่ระบุ"
									:disabled="!editable"
									@change="set_prob_end"
								/>
							</label>
							<label class="ss-field">
								<span class="ss-field-label">วันสิ้นสุดทดลองงาน</span>
								<DateInput
									v-model="doc.prob_end_date"
									label="วันสิ้นสุด"
									:disabled="!editable"
									clearable
								/>
							</label>
						</div>
						<label class="ss-field">
							<span class="ss-field-label">ผลทดลองงาน</span>
							<SelectBox
								v-model="doc.probation"
								:options="PROBATION"
								label="ผลทดลองงาน"
								placeholder="ยังไม่ประเมิน"
								:disabled="!editable && !view.can_edit_after"
							/>
						</label>
						<p v-if="view.can_edit_after" class="ss-muted">
							สัญญายืนยันแล้ว แก้ได้เฉพาะผลทดลองงาน (พิมพ์แบบประเมินได้จากปุ่มด้านบน)
						</p>
					</template>

					<!-- ---------- 50 ทวิ ---------- -->
					<template v-else>
						<div class="ss-form-row">
							<label class="ss-field">
								<span class="ss-field-label">ชื่อผู้ถูกหักภาษี</span>
								<input
									v-model="doc.full_name"
									class="ss-input"
									:disabled="!editable"
								/>
							</label>
							<label class="ss-field">
								<span class="ss-field-label">เลขประจำตัวผู้เสียภาษี</span>
								<input
									v-model="doc.tax_id"
									class="ss-input"
									inputmode="numeric"
									:disabled="!editable"
								/>
							</label>
						</div>
						<label class="ss-field">
							<span class="ss-field-label">ที่อยู่ผู้ถูกหักภาษี<em>*</em></span>
							<textarea
								v-model="doc.address"
								class="ss-input"
								rows="2"
								:disabled="!editable"
							></textarea>
						</label>
						<label class="ss-field">
							<span class="ss-field-label"
								>ที่อยู่บริษัท (ผู้หักภาษี)<em>*</em></span
							>
							<textarea
								v-model="doc.company_address"
								class="ss-input"
								rows="2"
								:disabled="!editable"
							></textarea>
						</label>
						<div class="ss-form-row">
							<label class="ss-field">
								<span class="ss-field-label">วันที่จ่าย<em>*</em></span>
								<DateInput
									v-model="doc.date"
									label="วันที่จ่าย"
									:disabled="!editable"
								/>
							</label>
							<label class="ss-field">
								<span class="ss-field-label">ยื่นแบบ<em>*</em></span>
								<SelectBox
									v-model="doc.income_tax_form"
									:options="TAX_FORMS"
									label="ยื่นแบบ"
									:disabled="!editable"
								/>
							</label>
							<label class="ss-field">
								<span class="ss-field-label">ผู้จ่ายเงิน<em>*</em></span>
								<SelectBox
									v-model="doc.tax_payer"
									:options="TAX_PAYERS"
									label="ผู้จ่ายเงิน"
									:disabled="!editable"
								/>
							</label>
						</div>
						<label
							class="ss-toggle"
							:class="{ 'is-on': doc.is_agent, 'is-readonly': !editable }"
						>
							<input
								v-model="doc.is_agent"
								type="checkbox"
								:true-value="1"
								:false-value="0"
								:disabled="!editable"
							/>
							<span class="ss-toggle-track"><span></span></span>
							<span>
								<b>หักแทนผู้อื่น</b>
								<small>บริษัทหักภาษีในฐานะตัวแทนของผู้ขาย/ผู้ว่าจ้างรายอื่น</small>
							</span>
						</label>
						<Picker
							v-if="doc.is_agent"
							v-model="doc.withholding_agent_for"
							label="หักแทน"
							:display_value="doc.withholding_agent_for_name"
							:remote_fn="(q) => search('Supplier', q)"
							:class="{ 'is-locked': !editable }"
							@select="(o) => (doc.withholding_agent_for_name = o?.label)"
						/>
					</template>
				</section>

				<!-- รายการเงินได้ของ 50 ทวิ -->
				<section v-if="!is_contract" class="ss-card">
					<div class="ss-table-wrap">
						<table class="ss-table ss-table--list">
							<thead>
								<tr>
									<th>ประเภทเงินได้</th>
									<th>คำอธิบาย</th>
									<th class="is-num">จำนวนเงินที่จ่าย</th>
									<th class="is-num">อัตรา %</th>
									<th class="is-num">ภาษีที่หัก</th>
									<th v-if="editable"></th>
								</tr>
							</thead>
							<tbody>
								<tr v-for="r in doc.items" :key="r._key" class="is-static">
									<td class="col-nowrap">
										<SelectBox
											v-if="editable"
											v-model="r.type_of_income"
											:options="income_options"
											label="ประเภทเงินได้"
											@change="pick_income(r)"
										/>
										<b v-else>{{ r.type_of_income }}</b>
									</td>
									<td>
										<input
											v-if="editable"
											v-model="r.description"
											class="ss-input"
										/>
										<template v-else>{{ r.description }}</template>
									</td>
									<td class="is-num">
										<MoneyInput
											v-if="editable"
											v-model="r.tax_base"
											class="ss-input"
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
										/>
										<template v-else>{{ num(r.tax_rate) }}</template>
									</td>
									<td class="is-num">
										<b>{{ money(tax_of(r)) }}</b>
									</td>
									<td v-if="editable" class="col-nowrap">
										<button
											type="button"
											class="ss-icon-btn"
											title="ลบแถว"
											aria-label="ลบแถว"
											@click="doc.items = doc.items.filter((x) => x !== r)"
										>
											<Icon name="trash" :size="16" />
										</button>
									</td>
								</tr>
								<tr v-if="!doc.items.length">
									<td :colspan="editable ? 6 : 5" class="ss-muted">
										ยังไม่มีรายการเงินได้
									</td>
								</tr>
							</tbody>
						</table>
					</div>
					<button
						v-if="editable"
						type="button"
						class="ss-btn ss-btn--soft"
						@click="add_item"
					>
						<Icon name="plus" :size="16" /> เพิ่มรายการเงินได้
					</button>
					<div class="ss-facts ss-facts--grid">
						<div class="ss-fact">
							<span>รวมเงินที่จ่าย</span><b>{{ money(total_base) }}</b>
						</div>
						<div class="ss-fact">
							<span>รวมภาษีที่หัก</span><b>{{ money(total_tax) }}</b>
						</div>
					</div>
				</section>
			</template>
		</div>

		<Sheet
			:open="confirm_submit"
			:title="`ยืนยัน${kind.label}`"
			:subtitle="doc?.name"
			@close="confirm_submit = false"
		>
			<p class="ss-note-line">
				หลังยืนยันแก้ไขไม่ได้<template v-if="is_contract"> (ยกเว้นผลทดลองงาน)</template>
				ถ้าผิดให้ยกเลิกแล้วทำใบใหม่
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
			:title="`ยกเลิก${kind.label}`"
			:subtitle="doc?.name"
			@close="confirm_cancel = false"
		>
			<p class="ss-note-line">ยกเลิกแล้วเอกสารนี้ใช้ไม่ได้ ทำใบใหม่แทน</p>
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
			:label="kind.label"
			:name="doc?.name"
			:method="`${API}.delete_doc`"
			:args="{ kind: params.kind, name: doc?.name }"
			@close="deleting = false"
			@deleted="go(params.kind, {}, { replace: true })"
		/>
		<PdfViewer
			:open="!!pdf"
			:url="pdf?.url"
			:name="doc?.name"
			:title="pdf?.label"
			@close="pdf = null"
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
import Picker from "../../../shared/components/Picker.vue";
import SelectBox from "../../../shared/components/SelectBox.vue";
import Sheet from "../../../shared/components/Sheet.vue";
import Skeleton from "../../../shared/components/Skeleton.vue";
import TopBar from "../../../shared/components/TopBar.vue";
import FormHead from "../../../shared/components/FormHead.vue";
import { LABELS, can_duplicate, doc_menu, duplicate_doc, step_actions } from "../../../shared/form_actions.js";
import {
	back,
	boot,
	call,
	celebrate,
	desk_url,
	go,
	money,
	num,
	post,
	scope_args,
	show_error,
	state,
	today,
} from "../../../shared/api.js";
import { API, HR_DOC_KINDS } from "./kinds.js";

const PROB_DAYS = ["30", "60", "90", "119"].map((d) => ({ value: d, label: `${d} วัน` }));
const PROBATION = [
	{ value: "", label: "ยังไม่ประเมิน" },
	{ value: "ผ่าน", label: "ผ่าน" },
	{ value: "ไม่ผ่าน", label: "ไม่ผ่าน" },
];
const TAX_FORMS = [
	{ value: "PND3", label: "ภ.ง.ด.3" },
	{ value: "PND53", label: "ภ.ง.ด.53" },
];
const TAX_PAYERS = [
	{ value: "Withholding", label: "หัก ณ ที่จ่าย" },
	{ value: "Paid One Time", label: "ออกให้ครั้งเดียว" },
];
// คำอธิบายตั้งต้นตามประเภทเงินได้ (ตรงกับตารางในฟอร์ม Withholding Tax Items ของ erpnext_thailand)
const INCOME_TEXT = {
	1: "เงินเดือน ค่าจ้าง ฯลฯ 40(1)",
	2: "ค่าธรรมเนียม ค่านายหน้า ฯลฯ 40(2)",
	3: "ค่าแห่งลิขสิทธิ์ ฯลฯ 40(3)",
	4: "ดอกเบี้ย ฯลฯ 40(4)ก",
	5: "ค่าจ้างทำของ ค่าบริการ ค่าเช่า ค่าขนส่ง ฯลฯ 3 เตรส",
	6: "อื่นๆ (ระบุ)",
};
const CONTRACT_INPUT = [
	"company",
	"employee",
	"date",
	"base",
	"prob_start_date",
	"prob_days",
	"prob_end_date",
	"probation",
];
const WHT_INPUT = [
	"company",
	"employee",
	"full_name",
	"tax_id",
	"address",
	"company_address",
	"is_agent",
	"withholding_agent_for",
	"income_tax_form",
	"tax_payer",
	"date",
];

const reload_summary = inject("reload_summary");
const params = state.route.params;
const kind = HR_DOC_KINDS[params.kind] || HR_DOC_KINDS["hr-contracts"];
const is_contract = params.kind === "hr-contracts";
const DOCTYPE = is_contract ? "Employment Contract" : "WHT Employee";
const INPUT = is_contract ? CONTRACT_INPUT : WHT_INPUT;
const companies = (boot.companies || []).map((c) => ({ value: c.name, label: c.name }));

let key = 0;
const tab = ref("main");
const view = ref({});
const doc = ref(null);
const saved = ref("");
const busy = ref(false);
const pdf = ref(null);
const deleting = ref(false);
const confirm_submit = ref(false);
const confirm_cancel = ref(false);
const incomes = ref([]);

const editable = computed(() => !!view.value.can_edit);
const title = computed(() =>
	doc.value?.full_name ? `${kind.label} · ${doc.value.full_name}` : `${kind.label}ใหม่`
);
const employee_label = computed(() =>
	doc.value?.full_name ? `${doc.value.full_name} (${doc.value.employee})` : doc.value?.employee
);
const income_options = computed(() => incomes.value.map((v) => ({ value: v, label: v })));
const tax_of = (r) => Math.round((Number(r.tax_base) || 0) * (Number(r.tax_rate) || 0)) / 100;
const total_base = computed(() =>
	(doc.value?.items || []).reduce((s, r) => s + (Number(r.tax_base) || 0), 0)
);
const total_tax = computed(() => (doc.value?.items || []).reduce((s, r) => s + tax_of(r), 0));
const ready = computed(() => {
	const d = doc.value;
	if (!d?.company || !d.employee) return false;
	if (is_contract) return !!d.date;
	return !!(d.date && d.income_tax_form && d.tax_payer && d.address && d.items.length);
});

const payload = () =>
	JSON.stringify({
		name: doc.value.name,
		modified: doc.value.modified,
		...Object.fromEntries(INPUT.map((f) => [f, doc.value[f] ?? null])),
		...(is_contract
			? {}
			: {
					items: doc.value.items.map((r) => ({
						type_of_income: r.type_of_income,
						description: r.description,
						tax_base: Number(r.tax_base) || 0,
						tax_rate: Number(r.tax_rate) || 0,
					})),
			  }),
	});
const dirty = computed(() => !!doc.value && (!doc.value.name || payload() !== saved.value));
const search = (doctype, txt) =>
	call(`${API}.search`, { doctype, txt, company: doc.value?.company });

function apply(result) {
	view.value = result;
	doc.value = {
		...result.doc,
		probation: result.doc.probation || "",
		items: (result.doc.items || []).map((r) => ({ ...r, _key: ++key })),
	};
	saved.value = payload();
}

async function pick_employee(option) {
	if (!option) return;
	try {
		const info = await call(`${API}.employee_info`, { employee: option.value });
		const d = doc.value;
		d.full_name = info.employee_name;
		if (info.company) d.company = info.company;
		if (is_contract) {
			if (!d.base && info.base) d.base = info.base;
			if (!d.prob_start_date && info.date_of_joining) {
				d.prob_start_date = info.date_of_joining;
				set_prob_end();
			}
		} else {
			d.tax_id = info.custom_id_card || d.tax_id;
			d.address = info.permanent_address || d.address;
		}
	} catch (e) {
		show_error(e);
	}
}
// วันสิ้นสุดทดลองงาน = วันเริ่ม + จำนวนวัน - 1 (เช่น เริ่ม 1 ม.ค. 119 วัน = 29 เม.ย.)
function set_prob_end() {
	const d = doc.value;
	if (!d.prob_start_date || !d.prob_days) return;
	const end = new Date(`${d.prob_start_date}T00:00:00`);
	end.setDate(end.getDate() + Number(d.prob_days) - 1);
	const pad = (n) => String(n).padStart(2, "0");
	d.prob_end_date = `${end.getFullYear()}-${pad(end.getMonth() + 1)}-${pad(end.getDate())}`;
}
function add_item() {
	const last = doc.value.items.at(-1);
	doc.value.items.push({
		_key: ++key,
		type_of_income: last?.type_of_income || "1",
		description: last?.description || INCOME_TEXT[1],
		tax_base: null,
		tax_rate: last?.tax_rate ?? 3,
	});
}
function pick_income(r) {
	const text =
		INCOME_TEXT[r.type_of_income] ||
		(String(r.type_of_income).startsWith("4.") ? "เงินปันผล เงินส่วนแบ่งกำไร ฯลฯ 40(4)ข" : "");
	if (text) r.description = text;
}

async function run(task, message) {
	busy.value = true;
	try {
		const result = await task();
		reload_summary();
		if (message) await celebrate(message, result?.doc?.name || "");
		return result;
	} catch (e) {
		show_error(e);
	} finally {
		busy.value = false;
	}
}
async function save() {
	const is_new = !doc.value.name;
	const result = await run(
		() => post(`${API}.save_doc`, { kind: params.kind, data: payload() }),
		"บันทึกแล้ว"
	);
	if (!result) return;
	apply(result);
	if (is_new) go("hr-doc", { kind: params.kind, name: result.doc.name }, { replace: true });
}
async function submit() {
	const result = await run(
		() => post(`${API}.submit_doc`, { kind: params.kind, name: doc.value.name }),
		"ยืนยันแล้ว"
	);
	if (result) apply(result);
	confirm_submit.value = false;
}
async function cancel() {
	const result = await run(
		() => post(`${API}.cancel_doc`, { kind: params.kind, name: doc.value.name }),
		"ยกเลิกแล้ว"
	);
	if (result) apply(result);
	confirm_cancel.value = false;
}

async function load() {
	try {
		const name = params.name && params.name !== "new" ? params.name : undefined;
		const [result, types] = await Promise.all([
			call(`${API}.get_doc`, { kind: params.kind, name, company: scope_args().company }),
			is_contract ? [] : call(`${API}.income_types`),
		]);
		incomes.value = types;
		apply(result);
		if (!name) {
			doc.value.date ??= today();
			if (!is_contract && !doc.value.items.length) add_item();
		}
	} catch (e) {
		show_error(e);
		back(params.kind);
	}
}
// หัวฟอร์ม: ร่าง → บันทึก → ยืนยัน → ยกเลิก (ยืนยันแล้วแก้ได้เฉพาะบางช่อง เช่น ผลทดลองงาน = บันทึก)
const actions = computed(() => {
	const v = view.value;
	return step_actions({
		stage: editable.value ? "draft" : "done",
		is_new: !doc.value.name,
		dirty: dirty.value,
		save: editable.value && { run: save, disabled: !ready.value },
		save_after: v.can_edit_after && { run: save, disabled: !ready.value },
		submit: v.can_submit && { label: LABELS.confirm, run: () => (confirm_submit.value = true) },
		cancel: v.can_cancel && (() => (confirm_cancel.value = true)),
	});
});
// PDF ใบเดียว = ปุ่มพิมพ์ หลายแบบ = เลือกในเมนู ⋯ (ต้องบันทึกก่อนพิมพ์)
const print_one = computed(() =>
	(view.value.pdfs || []).length === 1 && !dirty.value ? () => (pdf.value = view.value.pdfs[0]) : null
);
const menu = computed(() => {
	const pdfs = view.value.pdfs || [];
	return doc_menu({
		items:
			pdfs.length > 1 && !dirty.value
				? pdfs.map((p) => ({ key: p.url, label: `พิมพ์${p.label}`, icon: "printer", run: () => (pdf.value = p) }))
				: [],
		duplicate:
			doc.value.name &&
			can_duplicate(DOCTYPE) &&
			(() => duplicate_doc(DOCTYPE, doc.value.name, "hr-doc", { kind: params.kind })),
		refresh: doc.value.name && load,
		desk: [DOCTYPE, doc.value.name],
		remove: editable.value && view.value.can_delete && (() => (deleting.value = true)),
	});
});

load();
</script>
