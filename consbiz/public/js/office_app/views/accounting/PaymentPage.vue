<!-- หน้ารับชำระ / จ่ายชำระ (Payment Entry) ของหมวดบัญชี: ใบแจ้งหนี้ที่ตัดหนี้ รายการหัก ภาษีที่ล้าง ใบกำกับภาษี หนังสือรับรองหัก ณ ที่จ่าย
     ร่าง = ยืนยัน/ลบ, ยืนยันแล้ว = ยกเลิก (ยกเลิกหนังสือรับรอง/ใบกำกับภาษีที่อ้างใบนี้ด้วย) + ออกหนังสือรับรอง (จ่ายชำระที่มีหัก ณ ที่จ่าย)
     URL: acc-payment/<หน้ารายการ>/<เลขที่> API consbiz/accounting_app.py -->
<template>
	<div>
		<TopBar :title="title" :subtitle="doc?.party_name" :back_to="list_view" />

		<div class="ss-content">
			<FormHead
				v-if="doc"
				v-model="tab"
				:tabs="TABS"
				:actions="actions"
				:menu="menu"
				:busy="busy"
				:on-print="() => (pdf = true)"
			/>

			<Skeleton v-if="!doc" :rows="6" />
			<template v-else>
				<section class="ss-card ss-form">
					<div class="ss-doc-head-top">
						<span class="ss-tag" :class="`tone-${doc.status_tone}`">{{
							doc.status_label
						}}</span>
						<span class="ss-doc-date">{{ doc.name }}</span>
					</div>
					<div class="ss-facts ss-facts--grid">
						<div v-for="f in facts" :key="f.label" class="ss-fact">
							<span>{{ f.label }}</span
							><b>{{ f.value }}</b>
						</div>
					</div>
					<p v-if="doc.docstatus === 0 && !view.can_submit" class="ss-muted">
						ร่างนี้รอผู้มีสิทธิ์ยืนยันลงบัญชี
					</p>
				</section>

				<section v-if="view.received_certificate" class="ss-card ss-card-head">
					<a v-if="view.received_certificate.url" class="ss-tag tone-green" :href="view.received_certificate.url" target="_blank" rel="noopener">ได้รับหนังสือแล้ว</a>
					<span v-else class="ss-tag tone-amber">ยังไม่ได้รับหนังสือ 50 ทวิ</span>
					<button v-if="view.received_certificate.can_attach" class="ss-btn ss-btn--soft" :disabled="busy" @click="cert_input.click()">แนบหนังสือ 50 ทวิ</button>
					<input ref="cert_input" type="file" hidden accept="application/pdf,image/*" @change="attach_certificate" />
				</section>
				<!-- หนังสือรับรองหัก ณ ที่จ่าย: ยังไม่ออก -->
				<div
					v-if="
						view.has_wht &&
						doc.docstatus === 1 &&
						!view.certs.some((c) => c.docstatus < 2)
					"
					class="ss-banner tone-amber"
				>
					<Icon name="alert" :size="22" />
					<div class="ss-grow">
						<div class="ss-banner-title">ยังไม่ได้ออกหนังสือรับรองหัก ณ ที่จ่าย</div>
						<div class="ss-banner-text">
							หัก ณ ที่จ่าย {{ money(wht_total) }} ออกหนังสือรับรอง (50 ทวิ)
							ให้ผู้ถูกหัก แล้วยื่น ภ.ง.ด.3 / 53 ตามเดือนที่จ่าย
						</div>
					</div>
				</div>

				<section class="ss-card">
					<h2 class="ss-section-title">ใบแจ้งหนี้ที่ตัดหนี้</h2>
					<div class="ss-table-wrap">
						<table class="ss-table ss-table--list">
							<thead>
								<tr>
									<th>เอกสาร</th>
									<th class="is-num">ยอดใบแจ้งหนี้</th>
									<th class="is-num">ค้างก่อนรายการนี้</th>
									<th class="is-num">ตัดหนี้</th>
									<th class="col-modified"></th>
								</tr>
							</thead>
							<tbody>
								<tr
									v-for="r in doc.references"
									:key="r.doctype + r.name"
									:class="{ 'is-static': !r.kind }"
									@click="r.kind && open_doc(r.kind, r.name)"
								>
									<td>
										<span class="ss-doc-no">{{ r.name }}</span>
										<small>{{ DOCTYPE_LABEL[r.doctype] || r.doctype }}</small>
									</td>
									<td class="is-num">{{ money(r.total_amount) }}</td>
									<td class="is-num">{{ money(r.outstanding_amount) }}</td>
									<td class="is-num">
										<b>{{ money(r.allocated_amount) }}</b>
									</td>
									<ModifiedCell :value="r.modified" :row="r" />
								</tr>
							</tbody>
						</table>
					</div>
				</section>

				<section v-if="doc.deductions.length" class="ss-card">
					<h2 class="ss-section-title">รายการหัก</h2>
					<div class="ss-table-wrap">
						<table class="ss-table ss-table--list">
							<thead>
								<tr>
									<th>รายการ</th>
									<th>บัญชี</th>
									<th class="is-num">ฐานภาษี</th>
									<th class="is-num">ยอด</th>
								</tr>
							</thead>
							<tbody>
								<tr v-for="(d, i) in doc.deductions" :key="i" class="is-static">
									<td>
										<span class="ss-cell-main">{{
											d.description || "—"
										}}</span>
										<small v-if="d.wht_type">{{ d.wht_type }}</small>
									</td>
									<td>{{ d.account }}</td>
									<td class="is-num">
										{{ d.wht_base ? money(d.wht_base) : "—" }}
									</td>
									<td class="is-num">
										<b>{{ money(d.amount) }}</b>
									</td>
								</tr>
							</tbody>
						</table>
					</div>
				</section>

				<section
					v-if="view.tax_invoices.length || view.certs.length || doc.taxes.length"
					class="ss-card"
				>
					<h2 class="ss-section-title">ภาษี</h2>
					<p v-if="doc.taxes.length" class="ss-muted">
						ล้างภาษี{{ is_receive ? "ขาย" : "ซื้อ" }}ที่ยังไม่ถึงกำหนด
						{{ money(undue_cleared) }} เป็นภาษีถึงกำหนดในเดือนที่{{ word }}
					</p>
					<div class="ss-flow">
						<button
							v-for="t in view.tax_invoices"
							:key="t.name"
							type="button"
							class="ss-flow-item"
							@click="
								go('acc-tax-doc', {
									kind:
										t.type === 'sales' ? 'acc-sales-tax' : 'acc-purchase-tax',
									name: t.name,
								})
							"
						>
							<Icon name="chevron-right" :size="16" />
							<span class="ss-flow-main">
								<small
									>ใบกำกับภาษี{{ t.type === "sales" ? "ขาย" : "ซื้อ" }} · ภาษี
									{{ money(t.tax_amount) }}</small
								>
								<b>{{ t.number || t.name }}</b>
							</span>
							<span class="ss-tag" :class="`tone-${t.status_tone}`">{{
								t.status_label
							}}</span>
						</button>
						<button
							v-for="c in view.certs"
							:key="c.name"
							type="button"
							class="ss-flow-item"
							@click="go('acc-wht-doc', { name: c.name })"
						>
							<Icon name="chevron-right" :size="16" />
							<span class="ss-flow-main">
								<small
									>หนังสือรับรองหัก ณ ที่จ่าย ·
									{{ FORM_LABEL[c.income_tax_form] }}</small
								>
								<b>{{ c.name }}</b>
							</span>
							<span class="ss-tag" :class="`tone-${c.status_tone}`">{{
								c.status_label
							}}</span>
						</button>
					</div>
				</section>

				<section v-if="doc.remarks" class="ss-card">
					<h2 class="ss-section-title">หมายเหตุ</h2>
					<p class="ss-pre">{{ doc.remarks }}</p>
				</section>
			</template>
		</div>

		<Sheet
			:open="confirm_submit"
			:title="`ยืนยัน${word}`"
			:subtitle="doc?.name"
			@close="confirm_submit = false"
		>
			<p class="ss-note-line">
				ยอด{{ word }} {{ money(doc?.paid_amount) }} ลงบัญชีและตัดหนี้ใบแจ้งหนี้
				หลังยืนยันแก้ไขไม่ได้ (ยกเลิกแล้วทำใหม่)
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
			:title="`ยกเลิก${word}`"
			:subtitle="doc?.name"
			@close="confirm_cancel = false"
		>
			<p class="ss-note-line">
				ยอดค้างของใบแจ้งหนี้กลับมาเท่าเดิม
				<template v-if="linked_count">
					และยกเลิก{{ linked_text }}ที่อ้างรายการนี้ด้วย
				</template>
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
		<Sheet :open="clearance_open" :title="clearance_label" :subtitle="doc?.name" form @close="clearance_open = false">
			<label v-if="!doc?.clearance_date" class="ss-field">
				<span>วันที่เช็คผ่าน</span>
				<DateInput v-model="clearance_date" :min="earliest_clearance" label="วันที่เช็คผ่าน" />
			</label>
			<p v-else class="ss-note-line">วันที่เช็คผ่าน {{ thai_date(doc.clearance_date, { year: true }) }}</p>
			<template #footer>
				<button type="button" class="ss-btn ss-btn--primary" :disabled="busy || (!doc?.clearance_date && clearance_date < earliest_clearance)" @click="save_clearance">
					{{ clearance_label }}
				</button>
			</template>
		</Sheet>
		<DeleteSheet
			:open="deleting"
			:label="word"
			:name="doc?.name"
			:method="`${API}.delete_payment`"
			:args="{ name: doc?.name }"
			@close="deleting = false"
			@deleted="go(list_view, {}, { replace: true })"
		/>
		<PdfViewer
			:open="pdf"
			:url="view.pdf_url"
			:name="doc?.name"
			:title="word"
			@close="pdf = false"
		/>
	</div>
</template>

<script setup>
import ModifiedCell from "../../../shared/components/ModifiedCell.vue";
import { computed, inject, ref } from "vue";
import DateInput from "../../../shared/components/DateInput.vue";
import DeleteSheet from "../../../shared/components/DeleteSheet.vue";
import Icon from "../../../shared/components/Icon.vue";
import PdfViewer from "../../../shared/components/PdfViewer.vue";
import Sheet from "../../../shared/components/Sheet.vue";
import Skeleton from "../../../shared/components/Skeleton.vue";
import TopBar from "../../../shared/components/TopBar.vue";
import FormHead from "../../../shared/components/FormHead.vue";
import { LABELS, can_duplicate, doc_menu, duplicate_doc, step_actions } from "../../../shared/form_actions.js";
import { open_doc } from "../../../shared/docs/kinds.js";
import {
	back,
	call,
	celebrate,
	iso_date,
	go,
	money,
	post,
	upload,
	show_error,
	state,
	thai_date,
} from "../../../shared/api.js";
import { API, FORM_LABEL } from "./kinds.js";

const DOCTYPE_LABEL = {
	"Sales Invoice": "ใบแจ้งหนี้ขาย",
	"Purchase Invoice": "ใบแจ้งหนี้ซื้อ",
	"Purchase Order": "ใบสั่งซื้อ (เงินล่วงหน้า)",
	"Sales Order": "ใบสั่งขาย (เงินล่วงหน้า)",
	"Employee Advance": "เงินเบิกพนักงาน",
};

const reload_summary = inject("reload_summary");
const params = state.route.params;
const list_view = ["acc-cheques-in", "acc-cheques-out", "acc-receipts", "acc-wht-received"].includes(params.kind) ? params.kind : "acc-payments";

const tab = ref("detail");
const view = ref({ tax_invoices: [], certs: [] });
const doc = ref(null);
const busy = ref(false);
const pdf = ref(false);
const deleting = ref(false);
const confirm_submit = ref(false);
const confirm_cancel = ref(false);

const is_receive = computed(() => (doc.value?.payment_type || "") === "Receive");
const word = computed(() => (is_receive.value ? "รับชำระ" : "จ่ายชำระ"));
const title = computed(() => `${word.value} ${params.name}`);
const TABS = computed(() => [{ value: "detail", label: word.value }]);
const wht_total = computed(() =>
	(doc.value?.deductions || [])
		.filter(
			(d) =>
				d.wht_type ||
				/หัก ณ ที่จ่าย/.test(d.description || "") ||
				/หัก ณ ที่จ่าย/.test(d.account || "")
		)
		.reduce((s, d) => s + d.amount, 0)
);
const undue_cleared = computed(() =>
	Math.max(0, ...(doc.value?.taxes || []).map((t) => Math.abs(t.amount)))
);
const linked = computed(() => [
	...view.value.certs.filter((c) => c.docstatus === 1).map(() => "หนังสือรับรองหัก ณ ที่จ่าย"),
	...view.value.tax_invoices.filter((t) => t.docstatus === 1).map(() => "ใบกำกับภาษี"),
]);
const linked_count = computed(() => linked.value.length);
const linked_text = computed(() => [...new Set(linked.value)].join(" และ"));

const clearance_open = ref(false);
const clearance_date = ref("");
const clearance_label = computed(() => doc.value?.clearance_date ? "ล้างวันที่เช็คผ่าน" : "บันทึกเช็คผ่าน");
const earliest_clearance = computed(() => [doc.value?.posting_date, doc.value?.reference_date].filter(Boolean).sort().at(-1));
function open_clearance() {
	clearance_date.value = [iso_date(new Date()), earliest_clearance.value].sort().at(-1);
	clearance_open.value = true;
}
async function save_clearance() {
	const result = await run(() => post(`${API}.set_cheque_clearance`, {
		name: doc.value.name,
		clearance_date: doc.value.clearance_date ? "" : clearance_date.value,
		previous_date: doc.value.clearance_date || "",
	}));
	if (result) {
		apply(result);
		clearance_open.value = false;
	}
}
const facts = computed(() => {
	const d = doc.value;
	return [
		[is_receive.value ? "ลูกค้า" : "ผู้ขาย / ผรม.", d.party_name || d.party],
		[`วันที่${word.value}`, d.posting_date ? thai_date(d.posting_date, { year: true }) : "—"],
		["ตัดหนี้", money(d.total_allocated)],
		["รายการหัก", money(d.total_deductions)],
		[`ยอด${is_receive.value ? "รับ" : "จ่าย"}จริง`, money(d.paid_amount)],
		["บัญชี", d.account_name || d.account || "—"],
		...(d.mode_of_payment ? [["วิธีชำระ", d.mode_of_payment]] : []),
		...(d.is_cheque ? [
			["เลขที่เช็ค", d.reference_no || "—"],
			["วันที่หน้าเช็ค", d.reference_date ? thai_date(d.reference_date, { year: true }) : "—"],
			["วันที่เช็คผ่าน", d.clearance_date ? thai_date(d.clearance_date, { year: true }) : "—"],
		] : []),
		...(!d.is_cheque && d.reference_no && d.reference_no !== "-"
			? [
					[
						"เลขที่อ้างอิง",
						`${d.reference_no}${
							d.reference_date
								? ` · ${thai_date(d.reference_date, { year: true })}`
								: ""
						}`,
					],
			  ]
			: []),
		...(d.tax_invoice_number
			? [
					[
						"ใบกำกับภาษี",
						`${d.tax_invoice_number}${
							d.tax_invoice_date
								? ` · ${thai_date(d.tax_invoice_date, { year: true })}`
								: ""
						}`,
					],
			  ]
			: []),
		...(d.unallocated ? [["ยังไม่ตัดหนี้", money(d.unallocated)]] : []),
		...(d.project ? [["โครงการ", d.project]] : []),
	].map(([label, value]) => ({ label, value }));
});

function apply(result) {
	view.value = result;
	doc.value = result.doc;
}

async function run(task, message) {
	busy.value = true;
	try {
		const result = await task();
		reload_summary();
		if (message) await celebrate(message, doc.value?.name || "");
		return result;
	} catch (e) {
		show_error(e);
	} finally {
		busy.value = false;
	}
}

async function submit() {
	const result = await run(
		() => post(`${API}.submit_payment`, { name: doc.value.name }),
		`ยืนยัน${word.value}แล้ว`
	);
	if (result) apply(result);
	confirm_submit.value = false;
}
async function cancel() {
	const result = await run(
		() => post(`${API}.cancel_payment`, { name: doc.value.name }),
		"ยกเลิกแล้ว"
	);
	if (result) apply(result);
	confirm_cancel.value = false;
}

const cert_input = ref(null);
async function attach_certificate(event) {
	const file = event.target.files[0];
	if (!file) return;
	busy.value = true;
	try {
		await upload(new File([file], "50 ทวิ - " + file.name, { type: file.type }), { doctype: "Payment Entry", docname: doc.value.name });
		await load();
	} catch (error) {
		show_error(error);
	} finally {
		busy.value = false;
		event.target.value = "";
	}
}

async function load() {
	try {
		apply(await call(`${API}.get_payment`, { name: params.name }));
	} catch (e) {
		show_error(e);
		back(list_view);
	}
}
// หัวฟอร์ม: ร่าง (ไม่มีสิทธิ์ยืนยันตอนสร้าง) → ยืนยัน → ออกหนังสือรับรองหัก ณ ที่จ่าย
const actions = computed(() => {
	const v = view.value;
	return step_actions({
		stage: v.can_submit ? "draft" : "done",
		submit: v.can_submit && { label: `${LABELS.confirm}${word.value}`, run: () => (confirm_submit.value = true) },
		cancel: v.can_cancel && (() => (confirm_cancel.value = true)),
		next: [
			v.can_clear && { label: clearance_label.value, icon: "calendar", run: open_clearance },
			v.can_cert && {
				label: "ออกหนังสือรับรองหัก ณ ที่จ่าย",
				icon: "file",
				run: () => go("acc-wht-doc", { name: "new", source: doc.value.name }),
			},
		],
	});
});
const menu = computed(() =>
	doc_menu({
		refresh: load,
		desk: ["Payment Entry", doc.value.name],
		remove: view.value.can_delete && (() => (deleting.value = true)),
	})
);

load();
</script>
