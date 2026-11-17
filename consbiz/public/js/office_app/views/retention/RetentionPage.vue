<!-- หน้าเอกสารเงินประกันผลงาน 1 หน้า 4 ชนิด (params.type): rr/rp = เงินประกันที่ถูกหัก (ระบบสร้างจากใบแจ้งหนี้ ดู + แก้วันครบกำหนดคืน + ทำใบขอคืน/ใบคืน)
     ri/rl = ใบขอคืน/ใบคืน (ร่าง = แก้ในหน้าเดียวกัน, Submit แล้ว = PDF + บันทึกรับ/จ่ายเงิน = Journal Entry)
     ใช้ทั้งหมวดบัญชี ขาย จัดซื้อ: ชื่อหน้า = `<หน้ารายการ>-doc` (DOC_PAGES ใน kinds.js) API consbiz/retention_app.py -->
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
				:on-print="view.pdf_url ? () => (pdf = true) : null"
			/>

			<Skeleton v-if="!doc" :rows="6" />

			<!-- ---------------- เงินประกันที่ถูกหัก (rr / rp) ---------------- -->
			<template v-else-if="source">
				<section class="ss-card ss-form">
					<div class="ss-doc-head-top">
						<span class="ss-tag" :class="`tone-${doc.status_tone}`">{{
							doc.status_label
						}}</span>
						<span class="ss-doc-date">{{ doc.name }}</span>
					</div>
					<div class="ss-facts ss-facts--grid">
						<div v-for="f in source_facts" :key="f.label" class="ss-fact">
							<span>{{ f.label }}</span
							><b>{{ f.value }}</b>
						</div>
					</div>
					<div class="ss-form-row">
						<label class="ss-field">
							<span class="ss-field-label">วันครบกำหนดคืน</span>
							<DateInput
								v-model="due"
								label="วันครบกำหนดคืน"
								:disabled="!view.can_edit_due || busy"
								clearable
								@change="save_due"
							/>
						</label>
					</div>
					<p v-if="view.can_edit_due" class="ss-muted">
						ใส่วันที่พ้นระยะรับประกันผลงาน ถึงวันนั้นแล้วระบบขึ้นเป็น "ถึงกำหนด{{
							side === "in" ? "ขอคืน" : "คืน"
						}}" ให้
					</p>
				</section>

				<section class="ss-card">
					<h2 class="ss-section-title">ที่มา ({{ text.invoice }})</h2>
					<div class="ss-table-wrap">
						<table class="ss-table ss-table--list">
							<thead>
								<tr>
									<th>ใบแจ้งหนี้</th>
									<th>วันที่</th>
									<th class="is-num">ยอดก่อนภาษี</th>
									<th class="is-num">%</th>
									<th class="is-num">เงินประกัน</th>
								</tr>
							</thead>
							<tbody>
								<tr v-for="(r, i) in doc.items" :key="i" class="is-static">
									<td>
										<span class="ss-cell-main">{{
											r.invoice || r.reference_no || "—"
										}}</span>
										<small v-if="r.description">{{ r.description }}</small>
									</td>
									<td>
										{{
											r.posting_date
												? thai_date(r.posting_date, { year: true })
												: "—"
										}}
									</td>
									<td class="is-num">{{ money(r.base_amount) }}</td>
									<td class="is-num">{{ num(r.retention_percent) }}</td>
									<td class="is-num">
										<b>{{ money(r.amount) }}</b>
									</td>
								</tr>
							</tbody>
						</table>
					</div>
				</section>

				<section class="ss-card">
					<h2 class="ss-section-title">{{ text.claim }}</h2>
					<Empty
						v-if="!view.claims?.length"
						icon="file"
						:title="`ยังไม่มี${text.claim}`"
					/>
					<div v-else class="ss-table-wrap">
						<table class="ss-table ss-table--list">
							<thead>
								<tr>
									<th>เลขที่</th>
									<th>วันที่</th>
									<th class="is-num">ยอด</th>
									<th>สถานะ</th>
								</tr>
							</thead>
							<tbody>
								<tr
									v-for="c in view.claims"
									:key="c.name"
									@click="go(page, { type: c.type, name: c.name })"
								>
									<td>
										<span class="ss-doc-no">{{ c.name }}</span>
									</td>
									<td>
										{{
											c.posting_date
												? thai_date(c.posting_date, { year: true })
												: "—"
										}}
									</td>
									<td class="is-num">
										<b>{{ money(c.amount) }}</b>
									</td>
									<td>
										<span class="ss-tag" :class="`tone-${c.status_tone}`">{{
											c.status_label
										}}</span>
									</td>
								</tr>
							</tbody>
						</table>
					</div>
				</section>
			</template>

			<!-- ---------------- ใบขอคืน / ใบคืน (ri / rl) ---------------- -->
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
								:disabled="!editable || doc.items.length > 0"
							/>
						</label>
						<Picker
							v-model="doc.party"
							:label="text.party"
							:display_value="doc.party_name"
							:remote_fn="(q) => search(text.party_doctype, q)"
							:class="{ 'is-locked': !editable || doc.items.length > 0 }"
							required
							@select="(o) => (doc.party_name = o?.label)"
						/>
						<Picker
							v-model="doc.project"
							label="โครงการ"
							:display_value="doc.project"
							:remote_fn="(q) => search('Project', q)"
							:class="{ 'is-locked': !editable || doc.items.length > 0 }"
							clearable
						/>
					</div>
					<div class="ss-form-row">
						<label class="ss-field">
							<span class="ss-field-label">วันที่<em>*</em></span>
							<DateInput
								v-model="doc.posting_date"
								label="วันที่"
								:disabled="!editable"
							/>
						</label>
						<label class="ss-field">
							<span class="ss-field-label">เครดิต (วัน)</span>
							<input
								v-model.number="doc.credit_day"
								class="ss-input"
								type="number"
								inputmode="numeric"
								min="0"
								:disabled="!editable"
							/>
						</label>
						<label class="ss-field">
							<span class="ss-field-label">{{ text.ref }}</span>
							<input v-model="doc.ref" class="ss-input" :disabled="!editable" />
						</label>
					</div>
					<div class="ss-facts ss-facts--grid">
						<div v-for="f in claim_facts" :key="f.label" class="ss-fact">
							<span>{{ f.label }}</span
							><b>{{ f.value }}</b>
						</div>
					</div>
				</section>

				<section class="ss-card">
					<div class="ss-table-wrap">
						<table class="ss-table ss-table--list">
							<thead>
								<tr>
									<th>เงินประกัน</th>
									<th>ครบกำหนด</th>
									<th class="is-num">เงินประกัน</th>
									<th v-if="editable" class="is-num">คงเหลือ</th>
									<th class="is-num">ยอด{{ text.claim_short }}</th>
									<th v-if="editable"></th>
								</tr>
							</thead>
							<tbody>
								<tr
									v-for="r in doc.items"
									:key="r.retention_reference"
									class="is-static"
								>
									<td>
										<span class="ss-cell-main">{{
											r.retention_reference
										}}</span>
										<small v-if="r.invoice_no">{{ r.invoice_no }}</small>
									</td>
									<td>
										{{
											r.due_date
												? thai_date(r.due_date, { year: true })
												: "—"
										}}
									</td>
									<td class="is-num">{{ money(r.retention_amount) }}</td>
									<td v-if="editable" class="is-num">
										{{ money(r.outstanding_amount) }}
									</td>
									<td class="is-num">
										<MoneyInput
											v-if="editable"
											v-model="r.amount"
											class="ss-input"
										/>
										<b v-else>{{ money(r.amount) }}</b>
									</td>
									<td v-if="editable" class="col-nowrap">
										<button
											type="button"
											class="ss-icon-btn"
											title="ลบแถว"
											aria-label="ลบแถว"
											@click="remove(r)"
										>
											<Icon name="trash" :size="16" />
										</button>
									</td>
								</tr>
								<tr v-if="!doc.items.length">
									<td :colspan="editable ? 6 : 4" class="ss-muted">
										ยังไม่ได้เลือกเงินประกัน
									</td>
								</tr>
							</tbody>
						</table>
					</div>
					<button
						v-if="editable"
						type="button"
						class="ss-btn ss-btn--soft"
						:disabled="!doc.company || !doc.party"
						@click="open_pick"
					>
						<Icon name="plus" :size="16" /> เลือกเงินประกัน
					</button>
					<p v-if="editable" class="ss-muted">
						รวมเงินประกันหลายใบใน{{ text.claim }}ใบเดียวได้ และ{{
							text.claim_short
						}}บางส่วนได้ (ยอดต้องไม่เกินคงเหลือ รวมใบที่ยังเป็นร่าง)
					</p>
				</section>
			</template>
		</div>

		<!-- เลือกเงินประกันที่ยังขอคืน/คืนได้ -->
		<Sheet :open="!!pick" :title="`เลือก${text.source}`" @close="pick = null">
			<div v-if="pick">
				<Skeleton v-if="pick.loading" :rows="3" />
				<Empty
					v-else-if="!pick.rows.length"
					icon="shield"
					:title="`ไม่มีเงินประกันที่${text.claim_short}ได้`"
				/>
				<div v-else class="ss-list">
					<label v-for="r in pick.rows" :key="r.name" class="ss-card ss-checkline">
						<input
							v-model="pick.picked"
							type="checkbox"
							class="ss-check"
							:value="r.name"
							:disabled="in_items(r.name)"
						/>
						<span class="ss-card-main">
							<span class="ss-card-title"
								>{{ r.name }}{{ r.invoice_no ? ` · ${r.invoice_no}` : "" }}</span
							>
							<span class="ss-card-meta">
								คงเหลือ {{ money(r.remaining) }}
								{{ r.project ? `· ${r.project}` : "" }}
								{{
									r.due_date
										? `· ครบกำหนด ${thai_date(r.due_date, { year: true })}`
										: ""
								}}
								{{ in_items(r.name) ? "· อยู่ในรายการแล้ว" : "" }}
							</span>
						</span>
					</label>
				</div>
			</div>
			<template #footer>
				<button
					type="button"
					class="ss-btn ss-btn--primary ss-btn--block ss-btn--lg"
					:disabled="!pick?.picked.length"
					@click="add_picked"
				>
					เพิ่ม {{ pick?.picked.length || "" }} รายการ
				</button>
			</template>
		</Sheet>

		<!-- บันทึกรับ/จ่ายเงิน -->
		<Sheet :open="!!pay" :title="text.pay" :subtitle="doc?.name" @close="pay = null">
			<div v-if="pay" class="ss-form">
				<p v-if="doc.je_status === 0" class="ss-note-line">
					มีร่างรายการ {{ doc.journal_entry }} อยู่แล้ว ยืนยันเพื่อลงบัญชี
				</p>
				<template v-else>
					<label class="ss-field">
						<span class="ss-field-label">บัญชีเงินสด/ธนาคาร<em>*</em></span>
						<SelectBox
							v-model="pay.account"
							:options="pay.accounts"
							label="บัญชีเงินสด/ธนาคาร"
							placeholder="เลือกบัญชี"
						/>
					</label>
					<label class="ss-field">
						<span class="ss-field-label">วิธีชำระเงิน</span>
						<SelectBox
							v-model="pay.mode"
							:options="pay.modes"
							label="วิธีชำระเงิน"
							placeholder="ไม่ระบุ"
						/>
					</label>
				</template>
				<label class="ss-field">
					<span class="ss-field-label"
						>วันที่{{ side === "in" ? "รับ" : "จ่าย" }}เงิน</span
					>
					<DateInput v-model="pay.date" label="วันที่" />
				</label>
				<div class="ss-facts ss-facts--grid">
					<div class="ss-fact">
						<span>ยอด</span><b>{{ money(doc.grand_total) }}</b>
					</div>
				</div>
				<p v-if="!view.can_submit_je" class="ss-muted">
					คุณสร้างร่างรายการได้ ผู้มีสิทธิ์ Submit Journal Entry เป็นผู้ยืนยันลงบัญชี
				</p>
			</div>
			<template #footer>
				<button
					type="button"
					class="ss-btn ss-btn--primary ss-btn--block ss-btn--lg"
					:disabled="busy || (doc?.je_status !== 0 && !pay?.account)"
					@click="record_payment"
				>
					{{ view.can_submit_je ? `ยืนยัน${text.pay}` : "สร้างร่างรายการ" }}
				</button>
			</template>
		</Sheet>

		<Sheet
			:open="confirm_submit"
			:title="`ยืนยัน${text.claim}`"
			:subtitle="doc?.name"
			@close="confirm_submit = false"
		>
			<p class="ss-note-line">
				ยอด {{ money(doc?.grand_total) }} หลังยืนยันแก้ไขไม่ได้ (ยกเลิกแล้วทำใบใหม่) แล้ว{{
					text.pay
				}}เมื่อ{{ side === "in" ? "ได้รับ" : "จ่าย" }}เงินจริง
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
			:title="`ยกเลิก${text.claim}`"
			:subtitle="doc?.name"
			@close="confirm_cancel = false"
		>
			<p class="ss-note-line">
				ยอดเงินประกันที่อ้างถึงกลับมา{{ text.claim_short }}ได้อีกครั้ง
				ร่างรายการรับ/จ่ายเงินที่ยังไม่ลงบัญชีถูกลบด้วย
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
			:label="text.claim"
			:name="doc?.name"
			:method="`${API}.delete_doc`"
			:args="{ type: params.type, name: doc?.name }"
			@close="deleting = false"
			@deleted="go(list_view, {}, { replace: true })"
		/>
		<PdfViewer
			:open="pdf"
			:url="view.pdf_url"
			:name="doc?.name"
			:title="text.claim"
			@close="pdf = false"
		/>
	</div>
</template>

<script setup>
import { computed, inject, ref } from "vue";
import DateInput from "../../../shared/components/DateInput.vue";
import DeleteSheet from "../../../shared/components/DeleteSheet.vue";
import Empty from "../../../shared/components/Empty.vue";
import Icon from "../../../shared/components/Icon.vue";
import MoneyInput from "../../../shared/components/MoneyInput.vue";
import PdfViewer from "../../../shared/components/PdfViewer.vue";
import Picker from "../../../shared/components/Picker.vue";
import SelectBox from "../../../shared/components/SelectBox.vue";
import Sheet from "../../../shared/components/Sheet.vue";
import Skeleton from "../../../shared/components/Skeleton.vue";
import TopBar from "../../../shared/components/TopBar.vue";
import FormHead from "../../../shared/components/FormHead.vue";
import { LABELS, doc_menu, step_actions } from "../../../shared/form_actions.js";
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
	thai_date,
	today,
} from "../../../shared/api.js";
import { API, DOC_PAGES, SIDE_OF_TYPE, SIDE_TEXT, is_source } from "./kinds.js";

const reload_summary = inject("reload_summary");
const params = state.route.params;
const page = state.route.view;
const list_view = DOC_PAGES[page];
const side = SIDE_OF_TYPE[params.type] || "in";
const text = SIDE_TEXT[side];
const source = is_source(params.type);
const TABS = [{ value: "detail", label: source ? text.source : text.claim }];
const companies = (boot.companies || []).map((c) => ({ value: c.name, label: c.name }));

const tab = ref("detail");
const view = ref({});
const doc = ref(null);
const saved = ref("");
const busy = ref(false);
const due = ref(null);
const pick = ref(null);
const pay = ref(null);
const pdf = ref(false);
const deleting = ref(false);
const confirm_submit = ref(false);
const confirm_cancel = ref(false);

const editable = computed(() => !source && !!view.value.can_edit);
const title = computed(() =>
	doc.value?.name
		? `${source ? text.source : text.claim} ${doc.value.name}`
		: `${text.claim}ใหม่`
);
const total = computed(() =>
	(doc.value?.items || []).reduce((sum, r) => sum + (Number(r.amount) || 0), 0)
);
const can_save = computed(
	() => !!doc.value?.company && !!doc.value?.party && doc.value.items.length > 0
);

const source_facts = computed(() =>
	[
		[text.party, doc.value.party_name],
		["โครงการ", doc.value.project || "—"],
		[
			"วันที่ถูกหัก",
			doc.value.posting_date ? thai_date(doc.value.posting_date, { year: true }) : "—",
		],
		["เงินประกัน", money(doc.value.grand_total)],
		[`ทำใบ${text.claim_short}แล้ว`, money(doc.value.billed_amount)],
		[text.paid, money(doc.value.paid_amount)],
		["คงเหลือ", money(doc.value.outstanding_amount)],
		...(doc.value.ref ? [[text.ref, doc.value.ref]] : []),
	].map(([label, value]) => ({ label, value }))
);
const claim_facts = computed(() =>
	[
		[`ยอด${text.claim_short}รวม`, money(editable.value ? total.value : doc.value.grand_total)],
		...(doc.value.due_date && !editable.value
			? [["ครบกำหนด", thai_date(doc.value.due_date, { year: true })]]
			: []),
		...(doc.value.bank
			? [["บัญชีรับเงิน", `${doc.value.bank} ${doc.value.bank_account_no || ""}`]]
			: []),
		...(doc.value.journal_entry
			? [
					[
						doc.value.je_status === 1 ? text.paid : "ร่างรายการ",
						`${doc.value.journal_entry}${
							doc.value.account ? ` · ${doc.value.account}` : ""
						}`,
					],
			  ]
			: []),
	].map(([label, value]) => ({ label, value }))
);

const INPUT = [
	"name",
	"modified",
	"company",
	"party",
	"project",
	"posting_date",
	"credit_day",
	"ref",
];
const payload = () =>
	JSON.stringify({
		...Object.fromEntries(INPUT.map((f) => [f, doc.value[f] ?? null])),
		items: doc.value.items.map((r) => ({
			retention_reference: r.retention_reference,
			amount: Number(r.amount) || 0,
			description: r.description || null,
		})),
	});
const dirty = computed(
	() => !!doc.value && !source && (!doc.value.name || payload() !== saved.value)
);
const search = (doctype, txt) => call(`${API}.search`, { doctype, txt });
const in_items = (name) => doc.value.items.some((r) => r.retention_reference === name);

function apply(result) {
	view.value = result;
	doc.value = { ...result.doc, items: (result.doc.items || []).map((r) => ({ ...r })) };
	if (!source && !doc.value.posting_date) doc.value.posting_date = today();
	due.value = doc.value.due_date || null;
	saved.value = source ? "" : payload();
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

// ---- เงินประกันที่ถูกหัก
async function save_due() {
	if ((due.value || null) === (doc.value.due_date || null)) return;
	const result = await run(() =>
		post(`${API}.set_due_date`, {
			type: params.type,
			name: doc.value.name,
			due_date: due.value,
		})
	);
	if (result) apply(result);
	else due.value = doc.value.due_date || null;
}
function make_claim() {
	go(page, { type: text.claim_type, name: "new", source: doc.value.name });
}

// ---- ใบขอคืน / ใบคืน
async function open_pick() {
	pick.value = { loading: true, rows: [], picked: [] };
	try {
		const rows = await call(`${API}.open_sources`, {
			type: params.type,
			company: doc.value.company,
			party: doc.value.party,
			project: doc.value.project,
			exclude: doc.value.name,
		});
		if (pick.value) pick.value = { ...pick.value, loading: false, rows };
	} catch (e) {
		show_error(e);
		pick.value = null;
	}
}
function add_picked() {
	for (const name of pick.value.picked) {
		const r = pick.value.rows.find((x) => x.name === name);
		if (!r || in_items(name)) continue;
		doc.value.items.push({
			retention_reference: r.name,
			invoice_no: r.invoice_no,
			due_date: r.due_date,
			retention_amount: r.grand_total,
			outstanding_amount: r.remaining,
			amount: r.remaining,
		});
		if (!doc.value.project && r.project) doc.value.project = r.project;
	}
	pick.value = null;
}
function remove(r) {
	doc.value.items = doc.value.items.filter((x) => x !== r);
}
async function save() {
	const is_new = !doc.value.name;
	const result = await run(
		() => post(`${API}.save_claim`, { type: params.type, data: payload() }),
		"บันทึกแล้ว"
	);
	if (!result) return;
	apply(result);
	if (is_new) go(page, { type: params.type, name: result.doc.name }, { replace: true });
}
async function submit() {
	const result = await run(
		() => post(`${API}.submit_doc`, { type: params.type, name: doc.value.name }),
		"ยืนยันแล้ว"
	);
	if (result) apply(result);
	confirm_submit.value = false;
}
async function cancel() {
	const result = await run(
		() => post(`${API}.cancel_doc`, { type: params.type, name: doc.value.name }),
		"ยกเลิกแล้ว"
	);
	if (result) apply(result);
	confirm_cancel.value = false;
}
async function open_pay() {
	pay.value = { accounts: [], modes: [], account: null, mode: null, date: today() };
	if (doc.value.je_status === 0) return;
	try {
		const options = await call(`${API}.payment_options`, { company: doc.value.company });
		if (!pay.value) return;
		pay.value.accounts = options.accounts.map((a) => ({
			value: a.value,
			label: a.label,
			description: a.account_type === "Bank" ? "ธนาคาร" : "เงินสด",
		}));
		pay.value.modes = [
			{ value: null, label: "ไม่ระบุ" },
			...options.modes.map((m) => ({ value: m, label: m })),
		];
		if (pay.value.accounts.length === 1) pay.value.account = pay.value.accounts[0].value;
	} catch (e) {
		show_error(e);
	}
}
async function record_payment() {
	const result = await run(
		() =>
			post(`${API}.record_payment`, {
				type: params.type,
				name: doc.value.name,
				account: pay.value.account,
				mode_of_payment: pay.value.mode,
				posting_date: pay.value.date,
				submit: view.value.can_submit_je ? 1 : 0,
			}),
		view.value.can_submit_je ? `${text.paid}` : "สร้างร่างรายการแล้ว"
	);
	if (!result) return;
	apply(result.view);
	pay.value = null;
}

async function load() {
	try {
		const name = params.name && params.name !== "new" ? params.name : undefined;
		const { company, project } = scope_args();
		const result = await call(`${API}.get_doc`, {
			type: params.type,
			name,
			source: name ? undefined : params.source,
			company,
			project,
		});
		apply(result);
	} catch (e) {
		show_error(e);
		back(list_view);
	}
}
// หัวฟอร์ม เงินประกันที่ถูกหัก: ทำใบขอคืน/ใบคืน, ใบขอคืน/ใบคืน: ร่าง → บันทึก → ยืนยัน → บันทึกรับ/จ่ายเงิน
const actions = computed(() => {
	const d = doc.value;
	const v = view.value;
	const claim = v.can_claim && { label: `ทำ${text.claim}`, icon: "plus", run: make_claim };
	if (source) return step_actions({ stage: "done", next: [claim] });
	return step_actions({
		stage: editable.value ? "draft" : "done",
		is_new: !d.name,
		dirty: dirty.value,
		save: editable.value && { run: save, disabled: !can_save.value },
		submit: v.can_submit && { label: LABELS.confirm, run: () => (confirm_submit.value = true) },
		cancel: v.can_cancel && (() => (confirm_cancel.value = true)),
		next: [v.can_pay && { label: text.pay, icon: "receive", run: open_pay }, claim],
	});
});
const menu = computed(() => {
	const d = doc.value;
	const v = view.value;
	return doc_menu({
		refresh: d.name && load,
		desk: [d.doctype, d.name],
		remove: !source && editable.value && v.can_delete && (() => (deleting.value = true)),
	});
});

load();
</script>
