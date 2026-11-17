<!-- ใบเบิกงวด ผรม. 1 หน้า: ร่าง = กรอกปริมาณงวดนี้ (ตามปริมาณ) หรือเลือกงวด (ตามงวด) ยอดคำนวณจาก server ทันที (preview_claim)
     Submit = อนุมัติ แล้วกดสร้างใบแจ้งหนี้ซื้อ (PI) % งานจริงมาจากแผนงาน เบิกเกินแสดงสีเตือน API consbiz/subcontract_app.py -->
<template>
	<div>
		<TopBar :title="title" :subtitle="doc?.supplier_name" back_to="claims" />

		<div class="ss-content">
			<FormHead v-if="doc" v-model="tab" :tabs="TABS" :actions="actions" :menu="menu" :busy="busy" />

			<Skeleton v-if="!doc" :rows="6" />
			<template v-else>
				<section class="ss-card ss-form">
					<div v-if="!editable" class="ss-doc-head-top">
						<span class="ss-tag" :class="`tone-${doc.status_tone}`">{{
							doc.status_label
						}}</span>
						<span class="ss-doc-date">{{ doc.name }}</span>
					</div>
					<Picker
						v-model="doc.subcontract_agreement"
						label="สัญญา"
						:display_value="agreement_label"
						:remote_fn="
							(q) =>
								call(`${API}.search`, { doctype: 'Subcontract Agreement', txt: q })
						"
						:class="{ 'is-locked': !!doc.name }"
						required
						@select="change_agreement"
					/>
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
						<span class="ss-field-label"
							>งวดงานที่เบิก<em v-if="!ctx.appendix">*</em></span
						>
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
					<label v-if="agreement?.penalty_per_day" class="ss-field">
						<span class="ss-field-label"
							>จำนวนวันที่ปรับ ({{ money(agreement.penalty_per_day) }} / วัน)</span
						>
						<input
							v-model.number="doc.penalty_days"
							class="ss-input"
							type="number"
							inputmode="numeric"
							min="0"
							:disabled="!editable"
							@change="refresh"
						/>
					</label>
					<label class="ss-field">
						<span class="ss-field-label">หมายเหตุ</span>
						<textarea
							v-model="doc.remarks"
							class="ss-input"
							rows="2"
							:disabled="!editable"
						></textarea>
					</label>
				</section>

				<div v-if="doc.from_contractor && doc.docstatus === 0" class="ss-banner" :class="`tone-${view.contractor_busy ? 'gray' : 'amber'}`">
					<Icon name="user" :size="22" />
					<div>
						<div class="ss-banner-title">
							{{
								view.contractor_busy
									? `${doc.prepared_by_name || "ผู้รับเหมา"} กำลังร่าง/แก้ใบเบิกนี้ในแอปผู้รับเหมา`
									: `${doc.prepared_by_name || "ผู้รับเหมา"} ส่งใบเบิกนี้ให้ตรวจ`
							}}
						</div>
						<div class="ss-banner-text">
							<template v-if="view.contractor_busy && doc.return_reason"
								>ส่งกลับแก้แล้ว: {{ doc.return_reason }}</template
							>
							<template v-else-if="view.contractor_busy"
								>แก้หรืออนุมัติได้เมื่อผู้รับเหมาส่งให้ตรวจ</template
							>
							<template v-else
								>ตรวจและแก้ปริมาณได้ แล้วอนุมัติ หรือส่งกลับให้ผู้รับเหมาแก้ (ต้องระบุเหตุผล)
								ไฟล์แนบดูได้ในระบบเต็ม</template
							>
						</div>
					</div>
				</div>
				<div v-if="error" class="ss-banner tone-rose">
					<Icon name="alert" :size="22" />
					<div class="ss-banner-text">{{ error }}</div>
				</div>
				<div v-else-if="over.length" class="ss-banner tone-amber">
					<Icon name="alert" :size="22" />
					<div>
						<div class="ss-banner-title">เบิกเกินความคืบหน้าจริงในแผนงาน</div>
						<div class="ss-banner-text">{{ over.join(", ") }}</div>
					</div>
				</div>

				<section v-if="tab === 'items'" class="ss-card">
					<div class="ss-table-wrap">
						<table class="ss-table ss-table--list">
							<thead>
								<tr>
									<th>รายการ</th>
									<th class="is-num">ตามสัญญา</th>
									<th class="is-num">สะสมก่อนหน้า</th>
									<th class="is-num">งวดนี้</th>
									<th class="is-num">สะสมถึงงวดนี้</th>
									<th class="is-num">คงเหลือ</th>
									<th class="is-num">มูลค่างวดนี้</th>
									<th class="is-num">% เบิก / % งานจริง</th>
								</tr>
							</thead>
							<tbody>
								<template v-for="g in groups" :key="g.key">
									<tr v-if="g.label" class="is-static">
										<td colspan="8">
											<b>{{ g.label }}</b>
										</td>
									</tr>
									<tr
										v-for="r in g.rows"
										:key="r.agreement_item"
										class="is-static"
									>
										<td>
											<span class="ss-cell-main">{{ r.item_name }}</span>
											<small>{{
												[r.wbs, r.uom].filter(Boolean).join(" · ")
											}}</small>
										</td>
										<td class="is-num">{{ num(r.contract_qty) }}</td>
										<td class="is-num">{{ num(r.previous_qty) }}</td>
										<td class="is-num">
											<input
												v-if="row_edit(r)"
												v-model.number="r.qty"
												class="ss-input"
												type="number"
												inputmode="decimal"
												min="0"
												:max="
													(r.contract_qty || 0) - (r.previous_qty || 0)
												"
												@change="refresh"
											/>
											<b v-else>{{ num(r.qty) }}</b>
										</td>
										<td class="is-num">{{ num(r.cumulative_qty) }}</td>
										<td class="is-num">{{ num(r.remaining_qty) }}</td>
										<td class="is-num">
											<b>{{ money(r.amount) }}</b>
										</td>
										<td
											class="is-num col-nowrap"
											:class="{ 'tone-amber': is_over(r) }"
										>
											{{ num(r.claimed_progress) }}% /
											{{
												r.actual_progress === null ||
												r.actual_progress === undefined
													? "—"
													: `${num(r.actual_progress)}%`
											}}
										</td>
									</tr>
								</template>
							</tbody>
						</table>
					</div>
					<p v-if="editable && doc.items.some(row_edit)" class="ss-muted">
						กรอกปริมาณที่ทำได้ในงวดนี้ ระบบรวมยอดสะสมและคงเหลือให้
						(เกินปริมาณตามสัญญาต้องทำใบงานเพิ่มก่อน)
						<template v-if="agreement?.billing_method === 'Milestone'"
							>งานหลักเบิกตาม % ของงวด งานเพิ่มแนบท้ายเบิกตามปริมาณจริง</template
						>
					</p>
				</section>

				<section v-else class="ss-card">
					<div class="ss-facts ss-facts--grid">
						<div v-for="f in amounts" :key="f.label" class="ss-fact">
							<span>{{ f.label }}</span
							><b>{{ f.value }}</b>
						</div>
					</div>
					<p class="ss-muted">
						ยอดก่อน VAT · เงินประกันและหัก ณ ที่จ่ายลงในใบแจ้งหนี้ซื้อตามระบบเดิม
						เงินล่วงหน้าหักจากรายการจ่ายล่วงหน้าที่อ้าง PO
					</p>
				</section>
			</template>
		</div>

		<Sheet
			:open="confirm_submit"
			title="อนุมัติใบเบิก"
			:subtitle="doc?.name"
			@close="confirm_submit = false"
		>
			<p class="ss-note-line">
				อนุมัติแล้วแก้ไม่ได้ จากนั้นกด "สร้างใบแจ้งหนี้ (PI)" ให้ฝ่ายบัญชีตรวจและตั้งหนี้
			</p>
			<div v-if="doc" class="ss-facts ss-facts--grid">
				<div class="ss-fact">
					<span>มูลค่างวดนี้</span><b>{{ money(doc.gross_amount) }}</b>
				</div>
				<div class="ss-fact">
					<span>ยอดจ่ายสุทธิ (ก่อน VAT)</span><b>{{ money(doc.net_amount) }}</b>
				</div>
			</div>
			<template #footer>
				<button
					type="button"
					class="ss-btn ss-btn--primary ss-btn--block ss-btn--lg"
					:disabled="busy"
					@click="submit"
				>
					ยืนยันอนุมัติ
				</button>
			</template>
		</Sheet>
		<Sheet
			:open="confirm_cancel"
			title="ยกเลิกใบเบิก"
			:subtitle="doc?.name"
			@close="confirm_cancel = false"
		>
			<p class="ss-note-line">
				ร่างใบแจ้งหนี้ของใบเบิกนี้จะถูกลบ (ใบแจ้งหนี้ที่ Submit แล้วต้องยกเลิกก่อน)
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
		<Sheet
			:open="returning"
			title="ส่งกลับให้ผู้รับเหมาแก้"
			:subtitle="doc?.name"
			@close="returning = false"
		>
			<label class="ss-field">
				<span class="ss-field-label">เหตุผล / สิ่งที่ต้องแก้<em>*</em></span>
				<textarea v-model="return_reason" class="ss-input" rows="3"></textarea>
			</label>
			<template #footer>
				<button
					type="button"
					class="ss-btn ss-btn--danger ss-btn--block ss-btn--lg"
					:disabled="busy || !return_reason.trim()"
					@click="send_back"
				>
					ส่งกลับ
				</button>
			</template>
		</Sheet>
		<DeleteSheet
			:open="deleting"
			label="ใบเบิก"
			:name="doc?.name"
			:method="`${API}.delete_doc`"
			:args="{ kind: 'claims', name: doc?.name }"
			@close="deleting = false"
			@deleted="go('claims', {}, { replace: true })"
		/>
	</div>
</template>

<script setup>
import { computed, inject, ref } from "vue";
import DateInput from "../../../shared/components/DateInput.vue";
import DeleteSheet from "../../../shared/components/DeleteSheet.vue";
import Icon from "../../../shared/components/Icon.vue";
import Picker from "../../../shared/components/Picker.vue";
import SelectBox from "../../../shared/components/SelectBox.vue";
import Sheet from "../../../shared/components/Sheet.vue";
import Skeleton from "../../../shared/components/Skeleton.vue";
import TopBar from "../../../shared/components/TopBar.vue";
import FormHead from "../../../shared/components/FormHead.vue";
import { LABELS, doc_menu, step_actions } from "../../../shared/form_actions.js";
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
	today,
} from "../../../shared/api.js";
import { API } from "./kinds.js";

const TABS = [
	{ value: "items", label: "รายการ" },
	{ value: "amounts", label: "ยอดเงิน" },
];
const reload_summary = inject("reload_summary");
const params = state.route.params;
const view = ref({});
const ctx = ref({});
const doc = ref(null);
const saved = ref("");
const error = ref(null);
const tab = ref("items");
const busy = ref(false);
const deleting = ref(false);
const confirm_submit = ref(false);
const confirm_cancel = ref(false);
const returning = ref(false);
const return_reason = ref("");

const agreement = computed(() => ctx.value.agreement);
const editable = computed(() => !!doc.value && (!doc.value.name || view.value.can_edit));
// กรอกปริมาณงวดนี้ได้: สัญญาตามปริมาณทุกแถว / สัญญาตามงวดเฉพาะงานเพิ่มแนบท้าย
const row_edit = (r) =>
	editable.value && (agreement.value?.billing_method === "Measured" || !!r.variation);
// งานหลักก่อน แล้วงานเพิ่มแนบท้ายแยกตามใบงานเพิ่ม
const groups = computed(() => {
	const out = [{ key: "main", label: null, rows: [] }];
	for (const r of doc.value?.items || []) {
		if (!r.variation) out[0].rows.push(r);
		else {
			let g = out.find((x) => x.key === r.variation);
			if (!g)
				out.push((g = { key: r.variation, label: `งานเพิ่ม ${r.variation}`, rows: [] }));
			g.rows.push(r);
		}
	}
	if (out.length > 1 && out[0].rows.length) out[0].label = "งานหลักตามสัญญา";
	return out.filter((g) => g.rows.length);
});
const milestone_options = computed(() => [
	...(ctx.value.appendix ? [{ value: "", label: "ไม่เบิกงวด (เฉพาะงานเพิ่ม)" }] : []),
	...(ctx.value.milestones || []),
]);
const title = computed(() =>
	doc.value?.name ? `ใบเบิกงวดที่ ${doc.value.claim_no || ""}` : "ใบเบิกงวดใหม่"
);
const agreement_label = computed(() =>
	agreement.value
		? `${agreement.value.supplier_name} · ${agreement.value.title}`
		: doc.value?.subcontract_agreement
);
const is_over = (r) =>
	r.actual_progress !== null &&
	r.actual_progress !== undefined &&
	Number(r.claimed_progress) > Number(r.actual_progress) + 0.01;
const over = computed(() =>
	(doc.value?.items || []).filter((r) => Number(r.qty) > 0 && is_over(r)).map((r) => r.item_name)
);

const INPUT = [
	"name",
	"modified",
	"subcontract_agreement",
	"posting_date",
	"period_from",
	"period_to",
	"milestone",
	"penalty_days",
	"remarks",
];
const payload = () =>
	JSON.stringify({
		...Object.fromEntries(INPUT.map((f) => [f, doc.value[f] ?? null])),
		items: doc.value.items.map((r) => ({
			agreement_item: r.agreement_item,
			qty: r.qty,
		})),
	});
const dirty = computed(() => !!doc.value && payload() !== saved.value);

const amounts = computed(() => {
	const d = doc.value;
	const a = agreement.value || {};
	return [
		["มูลค่างวดนี้", money(d.gross_amount)],
		[`หักคืนเงินล่วงหน้า (${num(a.advance_recovery_percent)}%)`, money(d.advance_recovery)],
		[
			`หักเงินประกันผลงาน (${num(a.retention_percent)}%${
				a.retention_cap_percent ? ` เพดาน ${num(a.retention_cap_percent)}%` : ""
			})`,
			money(d.retention_amount),
		],
		[`หัก ณ ที่จ่าย (${num(a.wht_percent)}%)`, money(d.wht_amount)],
		[`ค่าปรับ (${d.penalty_days || 0} วัน)`, money(d.penalty_amount)],
		["ยอดจ่ายสุทธิ (ก่อน VAT)", money(d.net_amount)],
		["มูลค่าสัญญา", money(a.total_amount)],
		[
			"เบิกแล้วก่อนงวดนี้",
			money(
				d.docstatus === 1
					? (a.claimed_amount || 0) - (d.gross_amount || 0)
					: a.claimed_amount
			),
		],
	].map(([label, value]) => ({ label, value }));
});

function apply(result, keep_saved = false) {
	view.value = result;
	if (result.agreement)
		ctx.value = {
			agreement: result.agreement,
			milestones: result.milestones,
			appendix: result.appendix,
		};
	doc.value = result.doc;
	if (!doc.value.posting_date) doc.value.posting_date = today();
	if (!keep_saved) saved.value = payload();
}

let seq = 0;
// คำนวณยอดจาก server ทุกครั้งที่ค่าเปลี่ยน (ไม่บันทึก) ผลล่าสุดเท่านั้นที่ใช้
async function refresh() {
	if (!doc.value?.subcontract_agreement) return;
	const mine = ++seq;
	try {
		const result = await post(`${API}.preview_claim`, { data: payload() });
		if (mine !== seq) return;
		error.value = result.error;
		// ตรวจไม่ผ่าน (เช่น เกินคงเหลือ) server หยุดกลางรายการ: คงรายการที่กรอกไว้ แสดงแค่ข้อความ
		if (result.error) return;
		const keep = {
			name: doc.value.name,
			modified: doc.value.modified,
			docstatus: doc.value.docstatus,
		};
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

async function change_agreement(option) {
	if (!option || doc.value.name) return;
	const result = await call(`${API}.get_claim`, { agreement: option.value }).catch(show_error);
	if (!result) return;
	apply(result, true);
	error.value = null;
}

async function run(task, message) {
	busy.value = true;
	try {
		const result = await task();
		reload_summary();
		if (message) await celebrate(message, result?.doc?.name || doc.value.name);
		return result;
	} catch (e) {
		show_error(e);
	} finally {
		busy.value = false;
	}
}
async function save() {
	const result = await run(() => post(`${API}.save_claim`, { data: payload() }), "บันทึกแล้ว");
	if (!result) return;
	const is_new = !doc.value.name;
	apply(result);
	error.value = null;
	if (is_new) go("claim", { name: result.doc.name }, { replace: true });
}
async function submit() {
	const result = await run(
		() => post(`${API}.submit_doc`, { kind: "claims", name: doc.value.name }),
		"อนุมัติแล้ว"
	);
	if (result) apply(result);
	confirm_submit.value = false;
}
async function cancel() {
	const result = await run(
		() => post(`${API}.cancel_doc`, { kind: "claims", name: doc.value.name }),
		"ยกเลิกแล้ว"
	);
	if (result) apply(result);
	confirm_cancel.value = false;
}
async function send_back() {
	const result = await run(
		() => post(`${API}.return_claim`, { name: doc.value.name, reason: return_reason.value }),
		"ส่งกลับแล้ว"
	);
	if (result) apply(result);
	returning.value = false;
	return_reason.value = "";
}
async function make_invoice() {
	const result = await run(() =>
		post(`${API}.run_action`, {
			kind: "claims",
			name: doc.value.name,
			action: "purchase_invoice",
		})
	);
	if (!result) return;
	apply(result.view);
	await celebrate(`สร้าง ${result.name} แล้ว (ร่าง)`, "ฝ่ายบัญชีตรวจ ใส่ภาษีซื้อ แล้ว Submit");
	window.open(desk_url(result.doctype, result.name), "_blank");
}

async function load() {
	try {
		const name = params.name && params.name !== "new" ? params.name : undefined;
		if (!name && !params.agreement) {
			// ใบใหม่ที่ยังไม่เลือกสัญญา: ฟอร์มว่าง เลือกสัญญาแล้วโหลดรายการ
			apply({ doc: { subcontract_agreement: null, items: [], posting_date: today() } });
			return;
		}
		apply(await call(`${API}.get_claim`, { name, agreement: params.agreement }), !name);
	} catch (e) {
		show_error(e);
		back("claims");
	}
}
// หัวฟอร์ม: ร่าง → บันทึก → อนุมัติ (หรือส่งกลับแก้) → สร้างใบแจ้งหนี้ (PI)
const actions = computed(() => {
	const d = doc.value;
	const v = view.value;
	return step_actions({
		stage: editable.value ? "draft" : "done",
		is_new: !d.name,
		dirty: dirty.value,
		save: editable.value && { run: () => save(), disabled: !d.subcontract_agreement },
		submit: v.can_submit && d.name && {
			label: LABELS.approve,
			disabled: !!error.value,
			run: () => (confirm_submit.value = true),
		},
		reject: v.can_return && { label: "ส่งกลับแก้", run: () => (returning.value = true) },
		cancel: v.can_cancel && (() => (confirm_cancel.value = true)),
		next: [v.can_make_pi && { label: "สร้างใบแจ้งหนี้ (PI)", icon: "plus", run: make_invoice }],
	});
});
const menu = computed(() => {
	const d = doc.value;
	const v = view.value;
	return doc_menu({
		items: [
			d.purchase_invoice && v.pi_status !== 2 && {
				label: `ใบแจ้งหนี้ ${d.purchase_invoice}`,
				icon: "file",
				href: desk_url("Purchase Invoice", d.purchase_invoice),
			},
		],
		refresh: d.name && load,
		desk: ["Subcontract Claim", d.name],
		remove: editable.value && v.can_delete && d.name && (() => (deleting.value = true)),
	});
});

load();
</script>
