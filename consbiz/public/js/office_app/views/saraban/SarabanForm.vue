<!-- ฟอร์มสร้าง/แก้ร่างเอกสารสารบรรณ (kinds.js) ต้นแบบ = ฟอร์มเอกสารโครงการ (ProjectDocForm.vue): ช่องกรอก + แถบปุ่มล่าง
     ใบนำส่ง: รายการแก้ทีละแถวใน sheet และ "ดึงเอกสาร" จากเอกสารที่ Submit แล้ว (transmittal.get_documents)
     ใบปะหน้า: source = ใบนำส่งต้นทาง (envelope.make_envelope เติมที่อยู่/ผู้ติดต่อของคู่ค้า) -->
<template>
	<div class="ss-has-bar">
		<TopBar
			:title="`${params.name === 'new' ? 'สร้าง' : 'แก้ไข'}${kind.label}`"
			:subtitle="doc.name || 'เอกสารใหม่'"
			:back_to="params.kind"
		/>

		<div class="ss-content">
			<Skeleton v-if="!setup" :rows="4" />
			<div v-else class="ss-split">
				<div class="ss-split-main">
					<div class="ss-form">
						<!-- หนังสือเข้า -->
						<template v-if="params.kind === 'letters-in'">
							<label class="ss-field">
								<span class="ss-field-label">ชื่อเรื่อง<em>*</em></span>
								<input v-model="doc.title" class="ss-input" />
							</label>
							<div class="ss-form-row">
								<label class="ss-field">
									<span class="ss-field-label">เลขที่หนังสือ<em>*</em></span>
									<input
										v-model="doc.document_no"
										class="ss-input"
										placeholder="เลขที่ตามหนังสือ"
									/>
								</label>
								<label class="ss-field">
									<span class="ss-field-label">ลงวันที่<em>*</em></span>
									<DateInput v-model="doc.document_date" label="ลงวันที่" />
								</label>
							</div>
							<div class="ss-form-row">
								<Picker
									v-model="doc.receiver"
									label="ผู้รับ"
									:display_value="labels.receiver"
									:remote_fn="(q) => search('User', q)"
									required
									@select="(o) => (labels.receiver = o?.label)"
								/>
								<label class="ss-field">
									<span class="ss-field-label">ลงรับวันที่<em>*</em></span>
									<DateInput v-model="doc.receive_date" label="ลงรับวันที่" />
								</label>
							</div>
						</template>

						<!-- หนังสือออก -->
						<template v-else-if="params.kind === 'letters-out'">
							<label class="ss-field">
								<span class="ss-field-label">ชื่อเรื่อง<em>*</em></span>
								<input v-model="doc.title" class="ss-input" />
							</label>
							<div class="ss-form-row">
								<label class="ss-field">
									<span class="ss-field-label">ลงวันที่<em>*</em></span>
									<DateInput v-model="doc.document_date" label="ลงวันที่" />
								</label>
								<label class="ss-field">
									<span class="ss-field-label">วันที่ส่ง<em>*</em></span>
									<DateInput v-model="doc.sent_date" label="วันที่ส่ง" />
								</label>
							</div>
							<Picker
								v-model="doc.sender"
								label="ผู้ส่ง"
								:display_value="labels.sender"
								:remote_fn="(q) => search('User', q)"
								required
								@select="(o) => (labels.sender = o?.label)"
							/>
							<div class="ss-form-row">
								<label class="ss-field">
									<span class="ss-field-label">ผู้รับ</span>
									<input
										v-model="doc.receiver"
										class="ss-input"
										placeholder="ชื่อหน่วยงาน / บุคคล"
									/>
								</label>
								<label class="ss-field">
									<span class="ss-field-label">วันที่รับ</span>
									<DateInput
										v-model="doc.receive_date"
										label="วันที่รับ"
										clearable
									/>
								</label>
							</div>
							<div class="ss-field">
								<span class="ss-field-label">สถานะเอกสาร</span>
								<SelectBox
									v-model="doc.document_status"
									label="สถานะเอกสาร"
									:options="LETTER_OUT_STATUS"
								/>
							</div>
						</template>

						<!-- ใบนำส่งเอกสาร -->
						<template v-else-if="params.kind === 'transmittals'">
							<label class="ss-field">
								<span class="ss-field-label">เรื่อง<em>*</em></span>
								<input
									v-model="doc.title"
									class="ss-input"
									placeholder="เช่น ส่งใบแจ้งหนี้งวดที่ 3"
								/>
							</label>
							<div class="ss-form-row">
								<label class="ss-field">
									<span class="ss-field-label">วันที่<em>*</em></span>
									<DateInput v-model="doc.date" label="วันที่" />
								</label>
								<label class="ss-field">
									<span class="ss-field-label">เอกสารถึงวันที่</span>
									<DateInput
										v-model="doc.to_date"
										label="เอกสารถึงวันที่"
										clearable
									/>
								</label>
							</div>
							<div class="ss-field">
								<span class="ss-field-label">ประเภทผู้รับ<em>*</em></span>
								<SelectBox
									v-model="doc.recipient_type"
									label="ประเภทผู้รับ"
									:options="RECIPIENT_TYPES"
									@update:model-value="on_recipient_type"
								/>
							</div>
							<Picker
								v-if="party_type"
								:key="party_type"
								v-model="doc.party"
								:label="
									party_type === 'Customer' ? 'ลูกค้า' : 'ผู้ขาย / ผู้รับเหมา'
								"
								:display_value="labels.party"
								:remote_fn="(q) => search(party_type, q)"
								clearable
								@select="on_party"
							/>
							<div class="ss-form-row">
								<label class="ss-field">
									<span class="ss-field-label">ชื่อผู้รับ</span>
									<input v-model="doc.recipient_name" class="ss-input" />
								</label>
								<label class="ss-field">
									<span class="ss-field-label">เรียน</span>
									<input
										v-model="doc.contact_person"
										class="ss-input"
										placeholder="ชื่อผู้ติดต่อ"
									/>
								</label>
							</div>
						</template>

						<!-- ใบปะหน้าซอง -->
						<template v-else>
							<Picker
								:key="`from-${doc.company}`"
								v-model="doc.from"
								label="ที่อยู่ผู้ส่ง (จาก)"
								:display_value="labels.from"
								:remote_fn="(q) => search('Address', q, { company: doc.company })"
								clearable
								@select="(o) => (labels.from = o?.label)"
							/>
							<Picker
								v-model="doc.to"
								label="ที่อยู่ผู้รับ (ถึง)"
								:display_value="labels.to"
								:remote_fn="(q) => search('Address', q)"
								clearable
								@select="on_to"
							/>
							<Picker
								:key="`receiver-${doc.to}`"
								v-model="doc.receiver"
								label="ผู้รับ (ผู้ติดต่อ)"
								:display_value="labels.receiver"
								:remote_fn="(q) => search('Contact', q, { address: doc.to })"
								clearable
								@select="(o) => (labels.receiver = o?.label)"
							/>
							<div class="ss-form-row">
								<Picker
									v-model="doc.sender"
									label="ผู้ส่ง"
									:display_value="doc.sender_name"
									:remote_fn="(q) => search('User', q)"
									clearable
									@select="on_sender"
								/>
								<label class="ss-field">
									<span class="ss-field-label">วันที่ส่ง</span>
									<DateInput
										v-model="doc.send_date"
										label="วันที่ส่ง"
										clearable
									/>
								</label>
							</div>
							<div class="ss-form-row">
								<label class="ss-field">
									<span class="ss-field-label">ชื่อผู้ส่ง</span>
									<input v-model="doc.sender_name" class="ss-input" />
								</label>
								<label class="ss-field">
									<span class="ss-field-label">เบอร์โทรผู้ส่ง</span>
									<input
										v-model="doc.sender_tel"
										class="ss-input"
										inputmode="tel"
									/>
								</label>
							</div>
							<label class="ss-field">
								<span class="ss-field-label">หมายเหตุ (พิมพ์บนซอง)</span>
								<textarea
									v-model="doc.remark"
									class="ss-input"
									rows="2"
								></textarea>
							</label>
							<div v-if="doc.reference_name" class="ss-fact">
								<span>อ้างอิง</span><b>{{ doc.reference_name }}</b>
							</div>
						</template>

						<!-- ทุกชนิด: บริษัท / โครงการ -->
						<div class="ss-form-row">
							<div class="ss-field">
								<span class="ss-field-label"
									>บริษัท<em v-if="params.kind !== 'envelopes'">*</em></span
								>
								<SelectBox
									v-model="doc.company"
									label="บริษัท"
									:options="companies"
									@update:model-value="on_company"
								/>
							</div>
							<Picker
								v-if="params.kind !== 'envelopes'"
								v-model="doc.project"
								label="โครงการ"
								:display_value="labels.project"
								:remote_fn="(q) => search('Project', q)"
								clearable
								@select="(o) => (labels.project = o?.label)"
							/>
						</div>
					</div>
				</div>

				<!-- ใบนำส่ง: รายการเอกสาร -->
				<aside v-if="params.kind === 'transmittals'" class="ss-split-side">
					<h2 class="ss-section-title">รายการเอกสาร ({{ doc.items.length }})</h2>
					<div class="ss-chips">
						<button
							type="button"
							class="ss-btn ss-btn--soft"
							:disabled="!doc.company"
							@click="open_pull"
						>
							<Icon name="plus" :size="16" /> ดึงเอกสาร
						</button>
						<button type="button" class="ss-btn ss-btn--soft" @click="new_row">
							<Icon name="pen" :size="16" /> พิมพ์รายการเอง
						</button>
					</div>
					<Empty v-if="!doc.items.length" icon="file" title="ยังไม่มีรายการ" />
					<div v-else class="ss-list">
						<button
							v-for="(r, i) in doc.items"
							:key="r._key"
							type="button"
							class="ss-card"
							:style="{ '--i': i }"
							@click="edit_row(r)"
						>
							<div class="ss-card-head">
								<span class="ss-card-main">
									<span class="ss-card-title">{{
										r.description || r.document_no || r.reference_name
									}}</span>
									<span class="ss-card-meta">
										{{
											SOURCE_LABELS[r.reference_doctype] ||
											r.reference_doctype ||
											"พิมพ์เอง"
										}}
										{{ r.document_no ? `· ${r.document_no}` : "" }}
									</span>
								</span>
								<span v-if="r.amount" class="ss-qty"
									><b>{{ money(r.amount) }}</b></span
								>
							</div>
							<div v-if="r.date || r.qty" class="ss-chips">
								<span v-if="r.date" class="ss-chip"
									><Icon name="calendar" :size="12" />
									{{ thai_date(r.date, { year: true }) }}</span
								>
								<span v-if="r.qty" class="ss-chip"
									>{{ num(r.qty) }} {{ r.unit || "" }}</span
								>
							</div>
						</button>
					</div>
				</aside>
			</div>
		</div>

		<Teleport to="#ss-layer">
			<Transition name="ss-bar">
				<div v-if="setup" class="ss-bottom-bar">
					<button
						type="button"
						class="ss-btn ss-btn--lg"
						:class="can_submit ? 'ss-btn--ghost' : 'ss-btn--primary ss-grow'"
						:disabled="saving"
						@click="save(0)"
					>
						<Icon name="save" :size="17" /> บันทึกร่าง
					</button>
					<button
						v-if="can_submit"
						type="button"
						class="ss-btn ss-btn--primary ss-btn--lg ss-grow"
						:disabled="saving"
						@click="save(1)"
					>
						{{ params.kind === "letters-in" ? "บันทึกและลงรับ" : "บันทึกและ Submit" }}
					</button>
				</div>
			</Transition>
		</Teleport>

		<!-- ใบนำส่ง: แก้ / เพิ่มแถว -->
		<Sheet :open="!!row" :title="row?._new ? 'เพิ่มรายการ' : 'แก้รายการ'" @close="row = null">
			<div v-if="row" class="ss-form">
				<div v-if="row.reference_name" class="ss-fact">
					<span>{{ SOURCE_LABELS[row.reference_doctype] || row.reference_doctype }}</span
					><b>{{ row.reference_name }}</b>
				</div>
				<label class="ss-field">
					<span class="ss-field-label">รายละเอียด</span>
					<input v-model="row.description" class="ss-input" />
				</label>
				<div class="ss-form-row">
					<label class="ss-field">
						<span class="ss-field-label">เลขที่เอกสาร</span>
						<input v-model="row.document_no" class="ss-input" />
					</label>
					<label class="ss-field">
						<span class="ss-field-label">วันที่</span>
						<DateInput v-model="row.date" label="วันที่" clearable />
					</label>
				</div>
				<div class="ss-form-row">
					<label class="ss-field">
						<span class="ss-field-label">จำนวน</span>
						<input
							v-model.number="row.qty"
							class="ss-input"
							type="number"
							inputmode="decimal"
							min="0"
						/>
					</label>
					<label class="ss-field">
						<span class="ss-field-label">หน่วย</span>
						<input v-model="row.unit" class="ss-input" placeholder="ฉบับ / ชุด" />
					</label>
				</div>
				<label class="ss-field">
					<span class="ss-field-label">ยอดเงิน</span>
					<MoneyInput v-model="row.amount" class="ss-input" />
				</label>
				<label class="ss-field">
					<span class="ss-field-label">หมายเหตุ</span>
					<input v-model="row.remark" class="ss-input" />
				</label>
			</div>
			<template #footer>
				<div class="ss-sheet-actions">
					<button
						v-if="!row?._new"
						type="button"
						class="ss-btn ss-btn--ghost-danger ss-btn--lg"
						@click="remove_row"
					>
						ลบ
					</button>
					<button
						type="button"
						class="ss-btn ss-btn--primary ss-btn--lg ss-grow"
						@click="save_row"
					>
						ตกลง
					</button>
				</div>
			</template>
		</Sheet>

		<!-- ใบนำส่ง: ดึงเอกสาร -->
		<Sheet
			:open="!!pull"
			title="ดึงเอกสาร"
			subtitle="เอกสารที่ Submit แล้ว ไม่รวมที่เคยนำส่งให้ผู้รับเดียวกัน"
			wide
			@close="pull = null"
		>
			<div v-if="pull" class="ss-form">
				<div class="ss-form-row">
					<div class="ss-field">
						<span class="ss-field-label">ชนิดเอกสาร</span>
						<SelectBox
							v-model="pull.source"
							label="ชนิดเอกสาร"
							:options="source_options"
							@update:model-value="find_documents"
						/>
					</div>
					<label class="ss-field">
						<span class="ss-field-label">ตั้งแต่วันที่</span>
						<DateInput
							v-model="pull.from_date"
							label="ตั้งแต่วันที่"
							clearable
							@update:model-value="find_documents"
						/>
					</label>
					<label class="ss-field">
						<span class="ss-field-label">ถึงวันที่</span>
						<DateInput
							v-model="pull.to_date"
							label="ถึงวันที่"
							clearable
							@update:model-value="find_documents"
						/>
					</label>
				</div>
				<Skeleton v-if="pull.loading" :rows="3" />
				<Empty v-else-if="!pull.rows.length" icon="file" title="ไม่พบเอกสาร" />
				<div v-else class="ss-list">
					<label
						v-for="r in pull.rows"
						:key="r.reference_name"
						class="ss-card ss-checkline"
					>
						<input
							v-model="pull.picked"
							type="checkbox"
							class="ss-check"
							:value="r.reference_name"
							:disabled="in_items(r)"
						/>
						<span class="ss-card-main">
							<span class="ss-card-title"
								>{{ r.document_no || r.reference_name }}
								{{ r.description ? `· ${r.description}` : "" }}</span
							>
							<span class="ss-card-meta">
								{{ r.date ? thai_date(r.date, { year: true }) : "" }}
								{{ r.amount ? `· ${money(r.amount)}` : "" }}
								{{ in_items(r) ? "· อยู่ในรายการแล้ว" : "" }}
							</span>
						</span>
					</label>
				</div>
			</div>
			<template #footer>
				<div class="ss-sheet-actions">
					<button
						type="button"
						class="ss-btn ss-btn--primary ss-btn--block ss-btn--lg"
						:disabled="!pull?.picked.length"
						@click="add_pulled"
					>
						เพิ่ม {{ pull?.picked.length || 0 }} รายการ
					</button>
				</div>
			</template>
		</Sheet>
	</div>
</template>

<script setup>
import { computed, inject, reactive, ref } from "vue";
import DateInput from "../../../shared/components/DateInput.vue";
import Empty from "../../../shared/components/Empty.vue";
import Icon from "../../../shared/components/Icon.vue";
import MoneyInput from "../../../shared/components/MoneyInput.vue";
import Picker from "../../../shared/components/Picker.vue";
import SelectBox from "../../../shared/components/SelectBox.vue";
import Sheet from "../../../shared/components/Sheet.vue";
import Skeleton from "../../../shared/components/Skeleton.vue";
import TopBar from "../../../shared/components/TopBar.vue";
import {
	back,
	boot,
	call,
	celebrate,
	go,
	money,
	num,
	post,
	scope_args,
	show_error,
	state,
	thai_date,
} from "../../../shared/api.js";
import {
	API,
	LETTER_OUT_STATUS,
	PARTY_TYPES,
	RECIPIENT_TYPES,
	SARABAN_KINDS,
	SOURCE_LABELS,
} from "./kinds.js";

const reload_summary = inject("reload_summary");
const params = state.route.params;
const kind = SARABAN_KINDS[params.kind];

// ช่องบังคับ (ตรงกับ reqd ของ DocType) ตรวจก่อนส่ง ให้ข้อความเป็นภาษาไทย
const REQUIRED = {
	"letters-in": ["document_no", "title", "document_date", "company", "receiver", "receive_date"],
	"letters-out": ["title", "document_date", "company", "sender", "sent_date"],
	transmittals: ["company", "title", "date", "recipient_type"],
	envelopes: [],
};

let key = 0;
const setup = ref(null);
const saving = ref(false);
const can_submit = ref(false);
const doc = reactive({ name: null, items: [] });
const labels = reactive({});
const row = ref(null);
const pull = ref(null);

const companies = computed(() =>
	(boot.companies || []).map((c) => ({ value: c.name, label: c.name }))
);
const party_type = computed(() => PARTY_TYPES[doc.recipient_type]);
const source_options = computed(() =>
	(setup.value?.sources || []).map((s) => ({ value: s, label: SOURCE_LABELS[s] || s }))
);

const search = (doctype, txt, extra = {}) => call(`${API}.search`, { doctype, txt, ...extra });

function on_company() {
	if (params.kind === "envelopes") {
		doc.from = null;
		labels.from = null;
	}
}
function on_recipient_type() {
	doc.party = null;
	labels.party = null;
}
function on_party(option) {
	labels.party = option?.label;
	if (option?.label) doc.recipient_name = option.label;
}
function on_to(option) {
	labels.to = option?.label;
	doc.receiver = null;
	labels.receiver = null;
}
async function on_sender(option) {
	if (!option) return;
	try {
		Object.assign(doc, await call(`${API}.user_contact`, { user: option.value }));
	} catch (error) {
		show_error(error);
	}
}

// ---------------------------------------------------------------- รายการของใบนำส่ง
function new_row() {
	row.value = {
		_new: true,
		_key: ++key,
		description: "",
		document_no: "",
		date: null,
		qty: null,
		unit: "",
		amount: null,
		remark: "",
	};
}
function edit_row(r) {
	row.value = { ...r, _new: false };
}
function save_row() {
	const r = row.value;
	if (!r.description?.trim() && !r.document_no?.trim() && !r.reference_name)
		return show_error(new Error("กรอกรายละเอียดหรือเลขที่เอกสาร"));
	const clean = { ...r, _new: false };
	const index = doc.items.findIndex((x) => x._key === r._key);
	if (index >= 0) doc.items.splice(index, 1, clean);
	else doc.items.push(clean);
	row.value = null;
}
function remove_row() {
	doc.items = doc.items.filter((x) => x._key !== row.value._key);
	row.value = null;
}

const in_items = (r) =>
	doc.items.some(
		(x) => x.reference_doctype === r.reference_doctype && x.reference_name === r.reference_name
	);

function open_pull() {
	pull.value = {
		source: pull.value?.source || setup.value.sources[0],
		from_date: null,
		to_date: doc.to_date || null,
		rows: [],
		picked: [],
		loading: false,
	};
	find_documents();
}
async function find_documents() {
	const p = pull.value;
	if (!p?.source) return;
	p.loading = true;
	p.picked = [];
	try {
		p.rows = await call(`${API}.transmittal_documents`, {
			source: p.source,
			company: doc.company,
			recipient_type: doc.recipient_type,
			party: doc.party,
			from_date: p.from_date,
			to_date: p.to_date,
			project: doc.project,
			exclude: doc.name,
		});
	} catch (error) {
		show_error(error);
		p.rows = [];
	} finally {
		p.loading = false;
	}
}
function add_pulled() {
	const picked = new Set(pull.value.picked);
	for (const r of pull.value.rows) {
		if (picked.has(r.reference_name) && !in_items(r)) doc.items.push({ ...r, _key: ++key });
	}
	pull.value = null;
}

// ---------------------------------------------------------------- บันทึก
async function save(submit) {
	if (REQUIRED[params.kind].some((f) => !doc[f]))
		return show_error(new Error("กรอกช่องที่มีเครื่องหมาย * ให้ครบ"));
	saving.value = true;
	try {
		const items = doc.items.map(({ _key, _new, ...r }) => r);
		const result = await post(`${API}.save_doc`, {
			kind: params.kind,
			submit,
			data: { ...doc, items },
		});
		reload_summary();
		if (submit) await celebrate("บันทึกแล้ว", result.name);
		go("saraban-doc", { kind: params.kind, name: result.name }, { replace: true });
	} catch (error) {
		show_error(error);
	} finally {
		saving.value = false;
	}
}

async function load() {
	try {
		const { company, project } = scope_args();
		const form = await call(`${API}.get_form`, {
			kind: params.kind,
			name: params.name === "new" ? undefined : params.name,
			source: params.source,
			company: company || boot.default_company || boot.companies?.[0]?.name,
			project,
		});
		const { items, labels: names, ...rest } = form.doc;
		Object.assign(doc, rest, { items: (items || []).map((r) => ({ ...r, _key: ++key })) });
		Object.assign(labels, names || {}, {
			receiver: (names || {}).receiver || rest.receiver_name,
			sender: rest.sender_name,
		});
		can_submit.value = form.can_submit;
		setup.value = form.setup;
	} catch (error) {
		show_error(error);
		back(params.kind);
	}
}
load();
</script>
