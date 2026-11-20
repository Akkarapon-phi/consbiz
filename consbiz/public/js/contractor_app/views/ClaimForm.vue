<!-- ใบเบิกงวดของผู้รับเหมา: ร่าง/ส่งกลับแก้ = กรอกปริมาณงวดนี้ (หรือเลือกงวดงาน) + แนบรูป/ไฟล์ แล้ว "ส่งให้ตรวจ"
     รอตรวจ = ดู + ถอนกลับมาแก้ได้ อนุมัติแล้ว = ดูอย่างเดียว ยอดคำนวณจาก server ทันที (contractor_app.preview_claim)
     ค่าปรับเจ้าหน้าที่ใส่ตอนตรวจ ผรม. ไม่กรอก -->
<template>
	<div>
		<TopBar :title="title" :subtitle="agreement?.title" back_to="contractor-claims" no_project />

		<div class="ss-content">
			<FormHead
				v-if="doc"
				model-value="main"
				:tabs="[{ value: 'main', label: 'ใบเบิกงวด' }]"
				:actions="actions"
				:menu="menu"
				:busy="busy"
			>
				<template #summary><b>{{ money(doc.gross_amount) }}</b> บาท</template>
			</FormHead>
			<Skeleton v-if="!doc" :rows="6" />
			<template v-else>
				<div v-if="doc.status === 'Returned'" class="ss-banner tone-rose">
					<Icon name="alert" :size="22" />
					<div>
						<div class="ss-banner-title">ส่งกลับให้แก้</div>
						<div class="ss-banner-text">{{ doc.return_reason }}</div>
					</div>
				</div>
				<div v-else-if="doc.status === 'Pending Review'" class="ss-banner tone-amber">
					<Icon name="clock" :size="22" />
					<div>
						<div class="ss-banner-title">ส่งให้ตรวจแล้ว รอเจ้าหน้าที่ตรวจ</div>
						<div class="ss-banner-text">
							เจ้าหน้าที่อาจปรับปริมาณตามที่ตรวจจริง ต้องการแก้เองให้กด "ดึงกลับ"
						</div>
					</div>
				</div>

				<section class="ss-card ss-form">
					<div v-if="doc.name" class="ss-doc-head-top">
						<span class="ss-tag" :class="`tone-${doc.status_tone}`">{{ doc.status_label }}</span>
						<span class="ss-doc-date">{{ doc.name }}</span>
					</div>
					<div class="ss-form-row">
						<label class="ss-field">
							<span class="ss-field-label">วันที่เบิก<em>*</em></span>
							<DateInput
								v-model="doc.posting_date"
								label="วันที่เบิก"
								:disabled="!editable"
							/>
						</label>
						<label class="ss-field">
							<span class="ss-field-label">งานตั้งแต่</span>
							<DateInput
								v-model="doc.period_from"
								label="งานตั้งแต่"
								clearable
								:disabled="!editable"
							/>
						</label>
						<label class="ss-field">
							<span class="ss-field-label">ถึง</span>
							<DateInput
								v-model="doc.period_to"
								label="ถึง"
								clearable
								:disabled="!editable"
							/>
						</label>
					</div>
					<div v-if="agreement?.billing_method === 'Milestone'" class="ss-field">
						<span class="ss-field-label">งวดงานที่เบิก</span>
						<SelectBox
							v-if="editable"
							v-model="doc.milestone"
							label="งวดงาน"
							:options="milestone_options"
							@update:model-value="refresh"
						/>
						<b v-else-if="doc.milestone"
							>{{ doc.milestone_description }} ({{ num(doc.milestone_percent) }}%)</b
						>
						<b v-else>ไม่เบิกงวด (เฉพาะงานเพิ่ม)</b>
					</div>
					<label class="ss-field">
						<span class="ss-field-label">หมายเหตุถึงเจ้าหน้าที่</span>
						<textarea
							v-model="doc.remarks"
							class="ss-input"
							rows="2"
							:disabled="!editable"
						></textarea>
					</label>
				</section>

				<div v-if="error" class="ss-banner tone-rose">
					<Icon name="alert" :size="22" />
					<div class="ss-banner-text">{{ error }}</div>
				</div>

				<h2 class="ss-section-title">ผลงานงวดนี้</h2>
				<p v-if="editable && doc.items.some(row_edit)" class="ss-muted">
					กรอกปริมาณที่ทำได้ในงวดนี้ ระบบรวมยอดสะสมและคงเหลือให้ (เกินปริมาณตามสัญญาเบิกไม่ได้
					ต้องให้บริษัททำใบงานเพิ่มก่อน)
				</p>
				<template v-for="g in groups" :key="g.key">
					<h2 v-if="g.label" class="ss-section-title">{{ g.label }}</h2>
					<div class="ss-list">
						<div v-for="r in g.rows" :key="r.agreement_item" class="ss-card">
							<div class="ss-card-title">{{ r.item_name }}</div>
							<div class="ss-card-meta">
								ตามสัญญา {{ num(r.contract_qty) }} {{ r.uom || "" }} · เบิกแล้ว
								{{ num(r.previous_qty) }} · คงเหลือหลังงวดนี้ {{ num(r.remaining_qty) }}
							</div>
							<div class="ss-claim-row">
								<Stepper
									v-if="row_edit(r)"
									v-model="r.qty"
									:min="0"
									:max="(r.contract_qty || 0) - (r.previous_qty || 0)"
									@update:model-value="refresh"
								/>
								<b v-else>งวดนี้ {{ num(r.qty) }} {{ r.uom || "" }}</b>
								<span class="ss-qty"
									><b>{{ money(r.amount) }}</b
									><small>สะสม {{ num(r.claimed_progress) }}%</small></span
								>
							</div>
						</div>
					</div>
				</template>

				<h2 class="ss-section-title">รูป / ไฟล์ผลงาน</h2>
				<div class="ss-photos">
					<a
						v-for="f in view.files"
						:key="f.name"
						class="ss-photo"
						:href="file_url(f)"
						target="_blank"
						:title="f.file_name"
					>
						<img v-if="f.is_image" :src="file_url(f)" alt="" loading="lazy" />
						<span v-else class="ss-photo-doc"
							><Icon name="file" :size="24" /><small>{{ f.file_name }}</small></span
						>
						<button
							v-if="f.can_remove"
							type="button"
							class="ss-photo-remove"
							aria-label="ลบไฟล์"
							@click.prevent="remove_file(f)"
						>
							<Icon name="x" :size="14" :stroke="3" />
						</button>
					</a>
					<div v-for="p in uploading" :key="p.key" class="ss-photo">
						<img v-if="p.preview" :src="p.preview" alt="" />
						<div class="ss-photo-progress"><span class="ss-spinner"></span></div>
					</div>
					<label v-if="editable && (!doc.name || view.can_upload)" class="ss-photo-add">
						<input type="file" accept="image/*,application/pdf" multiple @change="add_files" />
						<Icon name="camera" :size="24" />
						<span>แนบรูป/ไฟล์</span>
					</label>
				</div>
				<p v-if="!view.files?.length && !editable" class="ss-muted">ไม่มีไฟล์แนบ</p>

				<h2 class="ss-section-title">ยอดเงิน (ก่อน VAT)</h2>
				<section class="ss-card">
					<div class="ss-facts">
						<div v-for="f in amounts" :key="f.label" class="ss-fact">
							<span>{{ f.label }}</span><b>{{ f.value }}</b>
						</div>
					</div>
				</section>

			</template>
		</div>


		<Sheet
			:open="confirm_send"
			title="ส่งใบเบิกให้ตรวจ"
			:subtitle="agreement?.title"
			@close="confirm_send = false"
		>
			<p class="ss-note-line">
				ส่งแล้วแก้ไม่ได้ จนกว่าเจ้าหน้าที่ส่งกลับ หรือคุณดึงกลับมาแก้ก่อนเจ้าหน้าที่ตรวจ
			</p>
			<div v-if="doc" class="ss-facts">
				<div class="ss-fact"><span>มูลค่างวดนี้</span><b>{{ money(doc.gross_amount) }}</b></div>
				<div class="ss-fact">
					<span>ยอดสุทธิโดยประมาณ (ก่อน VAT)</span><b>{{ money(doc.net_amount) }}</b>
				</div>
				<div class="ss-fact"><span>ไฟล์แนบ</span><b>{{ view.files?.length || 0 }} ไฟล์</b></div>
			</div>
			<template #footer>
				<button
					type="button"
					class="ss-btn ss-btn--primary ss-btn--block ss-btn--lg"
					:disabled="busy"
					@click="save(true)"
				>
					ยืนยันส่ง
				</button>
			</template>
		</Sheet>
		<Sheet :open="deleting" title="ลบใบเบิก" :subtitle="doc?.name" @close="deleting = false">
			<p class="ss-note-line">ลบใบเบิกและไฟล์แนบทั้งหมด กู้คืนไม่ได้</p>
			<template #footer>
				<button
					type="button"
					class="ss-btn ss-btn--danger ss-btn--block ss-btn--lg"
					:disabled="busy"
					@click="remove"
				>
					ยืนยันลบ
				</button>
			</template>
		</Sheet>
	</div>
</template>

<script setup>
import { computed, inject, ref } from "vue";
import DateInput from "../../shared/components/DateInput.vue";
import Icon from "../../shared/components/Icon.vue";
import FormHead from "../../shared/components/FormHead.vue";
import { LABELS, doc_menu, step_actions } from "../../shared/form_actions.js";
import SelectBox from "../../shared/components/SelectBox.vue";
import Sheet from "../../shared/components/Sheet.vue";
import Skeleton from "../../shared/components/Skeleton.vue";
import Stepper from "../../shared/components/Stepper.vue";
import TopBar from "../../shared/components/TopBar.vue";
import { back, celebrate, go, money, num, show_error, state, today } from "../../shared/api.js";
import { capi, cpost, file_url as claim_file_url, upload_claim_file } from "../api.js";

const reload_summary = inject("reload_summary");
const params = state.route.params;
const view = ref({});
const doc = ref(null);
const saved = ref("");
const error = ref(null);
const busy = ref(false);
const confirm_send = ref(false);
const deleting = ref(false);
const uploading = ref([]);
let upload_seq = 0;

const agreement = computed(() => view.value.agreement);
const editable = computed(() => !!view.value.can_edit);
// กรอกปริมาณได้: สัญญาตามปริมาณทุกแถว / สัญญาตามงวดเฉพาะงานเพิ่มแนบท้าย
const row_edit = (r) =>
	editable.value && (agreement.value?.billing_method === "Measured" || !!r.variation);
const groups = computed(() => {
	const out = [{ key: "main", label: null, rows: [] }];
	for (const r of doc.value?.items || []) {
		if (!r.variation) out[0].rows.push(r);
		else {
			let g = out.find((x) => x.key === r.variation);
			if (!g) out.push((g = { key: r.variation, label: `งานเพิ่ม ${r.variation}`, rows: [] }));
			g.rows.push(r);
		}
	}
	if (out.length > 1 && out[0].rows.length) out[0].label = "งานหลักตามสัญญา";
	return out.filter((g) => g.rows.length);
});
const milestone_options = computed(() => [
	...(view.value.appendix ? [{ value: "", label: "ไม่เบิกงวด (เฉพาะงานเพิ่ม)" }] : []),
	...(view.value.milestones || []),
]);
const title = computed(() =>
	doc.value?.name ? `ใบเบิกงวดที่ ${doc.value.claim_no || ""}` : "ใบเบิกงวดใหม่"
);
const amounts = computed(() => {
	const d = doc.value;
	const a = agreement.value || {};
	const rows = [
		["มูลค่างวดนี้", money(d.gross_amount)],
		[`หักคืนเงินล่วงหน้า (${num(a.advance_recovery_percent)}%)`, money(d.advance_recovery)],
		[`หักเงินประกันผลงาน (${num(a.retention_percent)}%)`, money(d.retention_amount)],
		[`หัก ณ ที่จ่าย (${num(a.wht_percent)}%)`, money(d.wht_amount)],
	];
	if (Number(d.penalty_amount)) rows.push([`ค่าปรับ (${d.penalty_days} วัน)`, money(d.penalty_amount)]);
	rows.push(["ยอดสุทธิ (ก่อน VAT)", money(d.net_amount)]);
	return rows.map(([label, value]) => ({ label, value }));
});

const INPUT = ["name", "modified", "subcontract_agreement", "posting_date", "period_from", "period_to", "milestone", "remarks"];
const payload = () =>
	JSON.stringify({
		...Object.fromEntries(INPUT.map((f) => [f, doc.value[f] ?? null])),
		items: doc.value.items.map((r) => ({ agreement_item: r.agreement_item, qty: r.qty })),
	});
const dirty = computed(() => !!doc.value && payload() !== saved.value);
const file_url = (f) => claim_file_url(doc.value.name, f.name);

// หัวฟอร์ม: ร่าง/ส่งกลับแก้ → บันทึก → ส่งอนุมัติ (ส่งให้ตรวจ) → รอตรวจ: ดึงกลับ
const actions = computed(() => {
	const d = doc.value;
	return step_actions({
		stage: editable.value ? "draft" : view.value.can_withdraw ? "pending" : "done",
		is_new: !d.name,
		dirty: dirty.value,
		save: editable.value && (() => save(false)),
		submit: editable.value && {
			label: LABELS.send,
			icon: "send",
			disabled: !!error.value || uploading.value.length > 0,
			run: () => (confirm_send.value = true),
		},
		withdraw: view.value.can_withdraw && { icon: "undo", run: withdraw },
	});
});
const menu = computed(() =>
	doc_menu({
		refresh: doc.value.name && load,
		remove: view.value.can_delete && (() => (deleting.value = true)),
	})
);

function apply(result, keep_saved = false) {
	view.value = result;
	doc.value = result.doc;
	if (!doc.value.posting_date) doc.value.posting_date = today();
	if (!keep_saved) saved.value = payload();
}

let seq = 0;
// คำนวณยอดจาก server ทุกครั้งที่ค่าเปลี่ยน (ไม่บันทึก) ผลล่าสุดเท่านั้นที่ใช้
async function refresh() {
	if (!editable.value) return;
	const mine = ++seq;
	try {
		const result = await cpost("preview_claim", { data: payload() });
		if (mine !== seq) return;
		error.value = result.error;
		if (result.error) return;
		const keep = { name: doc.value.name, modified: doc.value.modified, docstatus: doc.value.docstatus };
		doc.value = {
			...result.doc,
			...keep,
			status_label: doc.value.status_label,
			status_tone: doc.value.status_tone,
		};
	} catch (e) {
		show_error(e);
	}
}

async function run(task, message) {
	busy.value = true;
	try {
		const result = await task();
		reload_summary?.();
		if (message) await celebrate(message, result?.doc?.name || doc.value?.name || "");
		return result;
	} catch (e) {
		show_error(e);
	} finally {
		busy.value = false;
	}
}

async function save(send) {
	const is_new = !doc.value.name;
	const result = await run(
		() => cpost("save_claim", { data: payload(), send: send ? 1 : 0 }),
		send ? "ส่งให้ตรวจแล้ว" : "บันทึกแล้ว"
	);
	confirm_send.value = false;
	if (!result) return;
	apply(result);
	error.value = null;
	if (is_new) go("contractor-claim", { name: result.doc.name }, { replace: true });
}

async function withdraw() {
	const result = await run(() => cpost("withdraw_claim", { name: doc.value.name }), "ดึงกลับมาแก้แล้ว");
	if (result) apply(result);
}

async function remove() {
	const result = await run(() => cpost("delete_claim", { name: doc.value.name }).then(() => true));
	deleting.value = false;
	if (result) go("contractor-claims", {}, { replace: true });
}

// แนบไฟล์: ใบใหม่ต้องบันทึกก่อน แล้วอัปโหลดทีละไฟล์ (contractor_app.upload_file ผูกกับใบเบิกเลย)
async function add_files(event) {
	const files = [...event.target.files];
	event.target.value = "";
	if (!files.length) return;
	if (!doc.value.name || dirty.value) {
		const is_new = !doc.value.name;
		const result = await run(() => cpost("save_claim", { data: payload() }));
		if (!result) return;
		apply(result);
		if (is_new) go("contractor-claim", { name: result.doc.name }, { replace: true });
	}
	// เทียบด้วย key (ของใน ref เป็น Proxy เทียบกับ object เดิมไม่ได้)
	const pending = files.map((file) => ({
		key: ++upload_seq,
		file,
		preview: file.type.startsWith("image/") ? URL.createObjectURL(file) : "",
	}));
	const keys = pending.map((p) => p.key);
	uploading.value = [...uploading.value, ...pending];
	for (const p of pending) {
		try {
			const result = await upload_claim_file(doc.value.name, p.file);
			view.value = { ...view.value, files: result.files, can_upload: result.can_upload };
		} catch (e) {
			show_error(e);
		}
	}
	uploading.value = uploading.value.filter((p) => !keys.includes(p.key));
}

async function remove_file(f) {
	try {
		const result = await cpost("remove_file", { name: doc.value.name, file: f.name });
		view.value = { ...view.value, files: result.files };
	} catch (e) {
		show_error(e);
	}
}

async function load() {
	try {
		const name = params.name && params.name !== "new" ? params.name : undefined;
		apply(await capi("get_claim", { name, agreement: params.agreement }), !name);
	} catch (e) {
		show_error(e);
		back("contractor-claims");
	}
}
load();
</script>

