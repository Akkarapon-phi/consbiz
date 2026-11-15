<!-- ใบงานเพิ่ม ผรม. 1 หน้า: รายการแนบท้ายสัญญา แยกจากงานหลัก (งานหลัก/% งวดไม่เปลี่ยน) เบิกตามปริมาณจริง
     ยอด/การตรวจแผนงานจาก server ทันที (preview_variation) อนุมัติ (Submit) = เพิ่มแถวแนบท้ายในสัญญา + PO เดิมเลขที่เดิม
     (ระบบทำแทน เก็บ PDF ฉบับก่อนแก้ไว้ที่ po_snapshot แล้วแจ้งฝ่ายจัดซื้อส่งผู้รับเหมา) API consbiz/subcontract_app.py -->
<template>
	<div>
		<TopBar :title="title" :subtitle="doc?.supplier_name" back_to="variations" />

		<div class="ss-content">
			<div v-if="doc" class="ss-list-head">
				<StatusTabs v-model="tab" :options="TABS" />
				<div class="ss-list-tools">
					<a
						v-if="doc.name"
						class="ss-icon-btn"
						:href="desk_url('Subcontract Variation', doc.name)"
						title="เปิดในระบบเต็ม"
						aria-label="เปิดในระบบเต็ม"
						><Icon name="external" :size="17"
					/></a>
					<template v-if="editable">
						<button
							v-if="view.can_delete && doc.name"
							type="button"
							class="ss-btn ss-btn--ghost-danger ss-list-create"
							:disabled="busy"
							@click="deleting = true"
						>
							ลบ
						</button>
						<button
							v-if="view.can_submit && doc.name"
							type="button"
							class="ss-btn ss-btn--soft ss-list-create"
							:disabled="busy || dirty || !!error"
							:title="dirty ? 'บันทึกก่อนอนุมัติ' : ''"
							@click="confirm_submit = true"
						>
							อนุมัติ
						</button>
						<button
							type="button"
							class="ss-btn ss-btn--primary ss-list-create"
							:disabled="busy || !dirty || !doc.subcontract_agreement"
							@click="save"
						>
							<Icon name="save" :size="18" /> <span>บันทึก</span>
						</button>
					</template>
					<template v-else>
						<button
							v-if="view.can_cancel"
							type="button"
							class="ss-btn ss-btn--ghost-danger ss-list-create"
							:disabled="busy"
							@click="confirm_cancel = true"
						>
							ยกเลิก
						</button>
						<a
							v-if="doc.po_snapshot"
							class="ss-btn ss-btn--soft ss-list-create"
							:href="doc.po_snapshot"
							target="_blank"
							>PO ฉบับเดิม (Rev.{{ (doc.revision_no || 1) - 1 }})</a
						>
						<a
							v-if="doc.purchase_order"
							class="ss-btn ss-btn--soft ss-list-create"
							:href="desk_url('Purchase Order', doc.purchase_order)"
							target="_blank"
							>{{ doc.purchase_order }}</a
						>
					</template>
				</div>
			</div>

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
								call(`${API}.search`, {
									doctype: 'Subcontract Agreement',
									txt: q,
									status: 'variation',
								})
						"
						:class="{ 'is-locked': !!doc.name }"
						required
						@select="change_agreement"
					/>
					<div class="ss-form-row">
						<label class="ss-field">
							<span class="ss-field-label">วันที่<em>*</em></span>
							<DateInput
								v-model="doc.posting_date"
								label="วันที่"
								:disabled="!editable"
							/>
						</label>
						<Picker
							v-model="doc.variation_order"
							label="อ้างงานเพิ่ม-ลด ผู้ว่าจ้าง (VO)"
							:display_value="doc.variation_order"
							:remote_fn="(q) => search('Variation Order', q)"
							:class="{ 'is-locked': !editable }"
							clearable
							@select="refresh"
						/>
					</div>
					<label class="ss-field">
						<span class="ss-field-label">เหตุผล<em>*</em></span>
						<textarea
							v-model="doc.reason"
							class="ss-input"
							rows="2"
							placeholder="เช่น ผู้ว่าจ้างสั่งเพิ่มพื้นที่ปูกระเบื้องชั้น 2"
							:disabled="!editable"
						></textarea>
					</label>
					<div class="ss-facts ss-facts--grid">
						<div v-for="f in facts" :key="f.label" class="ss-fact">
							<span>{{ f.label }}</span
							><b>{{ f.value }}</b>
						</div>
					</div>
				</section>

				<div v-if="error" class="ss-banner tone-rose">
					<Icon name="alert" :size="22" />
					<div class="ss-banner-text">{{ error }}</div>
				</div>

				<section class="ss-card">
					<div class="ss-table-wrap">
						<table class="ss-table ss-table--list">
							<thead>
								<tr>
									<th>รายการ</th>
									<th class="is-num">ปริมาณ</th>
									<th>หน่วย</th>
									<th class="is-num">ราคา/หน่วย</th>
									<th class="is-num">มูลค่า</th>
									<th v-if="editable"></th>
								</tr>
							</thead>
							<tbody>
								<tr v-for="r in doc.items" :key="r._key" class="is-static">
									<td>
										<span class="ss-cell-main">{{ r.item_name }}</span>
										<small v-if="r.wbs">{{ r.wbs }}</small>
									</td>
									<td class="is-num">
										<input
											v-if="editable"
											v-model.number="r.qty"
											class="ss-input"
											type="number"
											inputmode="decimal"
											min="0"
											@change="refresh"
										/>
										<b v-else>{{ num(r.qty) }}</b>
									</td>
									<td>{{ r.uom || "" }}</td>
									<td class="is-num">{{ money(r.rate) }}</td>
									<td class="is-num">
										<b>{{ money(r.amount) }}</b>
									</td>
									<td v-if="editable" class="col-nowrap">
										<button
											type="button"
											class="ss-icon-btn"
											title="แก้รายการ"
											aria-label="แก้รายการ"
											@click="edit_new(r)"
										>
											<Icon name="pen" :size="16" />
										</button>
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
									<td :colspan="editable ? 6 : 5" class="ss-muted">
										ยังไม่มีรายการ
									</td>
								</tr>
							</tbody>
						</table>
					</div>
					<button
						v-if="editable && doc.subcontract_agreement"
						type="button"
						class="ss-btn ss-btn--soft"
						@click="edit_new()"
					>
						<Icon name="plus" :size="16" /> เพิ่มรายการ
					</button>
					<p v-if="editable" class="ss-muted">
						งานเพิ่มเป็นรายการแนบท้ายสัญญา แยกจากงานหลัก (งานหลักและ % งวดไม่เปลี่ยน)
						เบิกตามปริมาณจริง ปริมาณจ้างรวมต้องไม่เกินแผนงาน (เกินต้องทำ VO
						ฝั่งผู้ว่าจ้างก่อน)
					</p>
				</section>
			</template>
		</div>

		<!-- รายการใหม่ -->
		<Sheet :open="!!row" :title="row?._new ? 'เพิ่มรายการ' : 'แก้รายการ'" @close="row = null">
			<div v-if="row" class="ss-form">
				<Picker
					v-model="row.wbs"
					label="งานในแผน (WBS)"
					:options="wbs"
					clearable
					empty_text="โครงการนี้ยังไม่มีแผนงาน"
					@select="pick_wbs"
				/>
				<label class="ss-field">
					<span class="ss-field-label">รายการ<em>*</em></span>
					<input v-model="row.item_name" class="ss-input" />
				</label>
				<div class="ss-form-row">
					<label class="ss-field">
						<span class="ss-field-label">ปริมาณ<em>*</em></span>
						<input
							v-model.number="row.qty"
							class="ss-input"
							type="number"
							inputmode="decimal"
							min="0"
						/>
					</label>
					<Picker
						v-model="row.uom"
						label="หน่วย"
						:display_value="row.uom"
						:remote_fn="(q) => search('UOM', q)"
						clearable
					/>
				</div>
				<label class="ss-field">
					<span class="ss-field-label">ราคาต่อหน่วย<em>*</em></span>
					<MoneyInput v-model="row.rate" class="ss-input" />
				</label>
			</div>
			<template #footer>
				<button
					type="button"
					class="ss-btn ss-btn--primary ss-btn--block ss-btn--lg"
					@click="save_new"
				>
					ตกลง
				</button>
			</template>
		</Sheet>

		<Sheet
			:open="confirm_submit"
			title="อนุมัติใบงานเพิ่ม"
			:subtitle="doc?.name"
			@close="confirm_submit = false"
		>
			<p class="ss-note-line">
				ปริมาณและมูลค่าในสัญญาเพิ่มตามใบนี้
				<template v-if="agreement?.purchase_order">
					และใบสั่งซื้อ {{ agreement.purchase_order }} อัปเดตเป็น Rev.{{
						doc?.revision_no
					}}
					(เลขที่เดิม) ระบบเก็บ PDF ฉบับก่อนแก้ไว้ให้ ส่งใบใหม่ให้ผู้รับเหมาอีกครั้ง
				</template>
			</p>
			<div v-if="doc" class="ss-facts ss-facts--grid">
				<div class="ss-fact">
					<span>มูลค่างานเพิ่ม</span><b>{{ money(doc.addition_amount) }}</b>
				</div>
				<div class="ss-fact">
					<span>มูลค่าสัญญาหลังแก้</span><b>{{ money(doc.revised_amount) }}</b>
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
			title="ยกเลิกใบงานเพิ่ม"
			:subtitle="doc?.name"
			@close="confirm_cancel = false"
		>
			<p class="ss-note-line">
				ปริมาณในสัญญาและใบสั่งซื้อลดกลับเป็นฉบับก่อนหน้า ยกเลิกได้เฉพาะใบล่าสุด
				และต้องยังไม่ได้เบิกปริมาณที่เพิ่ม
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
			label="ใบงานเพิ่ม"
			:name="doc?.name"
			:method="`${API}.delete_doc`"
			:args="{ kind: 'variations', name: doc?.name }"
			@close="deleting = false"
			@deleted="go('variations', {}, { replace: true })"
		/>
	</div>
</template>

<script setup>
import { computed, inject, ref } from "vue";
import DateInput from "../../../shared/components/DateInput.vue";
import DeleteSheet from "../../../shared/components/DeleteSheet.vue";
import Icon from "../../../shared/components/Icon.vue";
import MoneyInput from "../../../shared/components/MoneyInput.vue";
import Picker from "../../../shared/components/Picker.vue";
import Sheet from "../../../shared/components/Sheet.vue";
import Skeleton from "../../../shared/components/Skeleton.vue";
import StatusTabs from "../../../shared/components/StatusTabs.vue";
import TopBar from "../../../shared/components/TopBar.vue";
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

const TABS = [{ value: "items", label: "รายการงานเพิ่ม" }];
const reload_summary = inject("reload_summary");
const params = state.route.params;
let key = 0;
const view = ref({});
const ctx = ref({});
const doc = ref(null);
const saved = ref("");
const error = ref(null);
const tab = ref("items");
const busy = ref(false);
const row = ref(null);
const wbs = ref([]);
const deleting = ref(false);
const confirm_submit = ref(false);
const confirm_cancel = ref(false);

const agreement = computed(() => ctx.value.agreement);
const editable = computed(() => !!doc.value && (!doc.value.name || view.value.can_edit));
const title = computed(() =>
	doc.value?.revision_no ? `ใบงานเพิ่ม ครั้งที่ ${doc.value.revision_no}` : "ใบงานเพิ่มใหม่"
);
const agreement_label = computed(() =>
	agreement.value
		? `${agreement.value.supplier_name} · ${agreement.value.title}`
		: doc.value?.subcontract_agreement
);
// สถานะ PO หลังอนุมัติ: ฝ่ายจัดซื้อส่งฉบับแก้ไขให้ผู้รับเหมาแล้วหรือยัง
const po_status = computed(() => {
	const po = ctx.value.po_revision;
	const name = doc.value?.purchase_order || agreement.value?.purchase_order;
	if (!name) return null;
	if (!po || doc.value.docstatus !== 1) return name;
	return po.pending
		? `${name} Rev.${po.revision} · รอฝ่ายจัดซื้อส่งผู้รับเหมา`
		: `${name} Rev.${po.revision} · ส่งแล้ว${po.sent_by_name ? ` (${po.sent_by_name})` : ""}`;
});
const facts = computed(() =>
	[
		["มูลค่าสัญญาก่อนแก้", money(doc.value.previous_amount)],
		["มูลค่างานเพิ่ม", money(doc.value.addition_amount)],
		["มูลค่าสัญญาหลังแก้", money(doc.value.revised_amount)],
		...(po_status.value ? [["ใบสั่งซื้อ", po_status.value]] : []),
	].map(([label, value]) => ({ label, value }))
);

const INPUT = [
	"name",
	"modified",
	"subcontract_agreement",
	"posting_date",
	"variation_order",
	"reason",
];
const ITEM = ["wbs", "item_name", "uom", "qty", "rate"];
const payload = () =>
	JSON.stringify({
		...Object.fromEntries(INPUT.map((f) => [f, doc.value[f] ?? null])),
		items: doc.value.items.map((r) => Object.fromEntries(ITEM.map((f) => [f, r[f] ?? null]))),
	});
const dirty = computed(() => !!doc.value && payload() !== saved.value);
const search = (doctype, txt) => call(`${API}.search`, { doctype, txt });

const keyed = (items) => (items || []).map((r) => ({ ...r, _key: ++key }));

function apply(result, keep_saved = false) {
	view.value = result;
	if (result.agreement)
		ctx.value = { agreement: result.agreement, po_revision: result.po_revision };
	doc.value = { ...result.doc, items: keyed(result.doc.items) };
	if (!doc.value.posting_date) doc.value.posting_date = today();
	if (!keep_saved) saved.value = payload();
	load_wbs();
}

let seq = 0;
// คำนวณยอด + ตรวจแผนงานจาก server ทุกครั้งที่ค่าเปลี่ยน (ไม่บันทึก) ผลล่าสุดเท่านั้นที่ใช้
async function refresh() {
	if (!doc.value?.subcontract_agreement || !doc.value.items.length) {
		error.value = null;
		return;
	}
	const mine = ++seq;
	try {
		const result = await post(`${API}.preview_variation`, { data: payload() });
		if (mine !== seq) return;
		error.value = result.error;
		// ตรวจไม่ผ่าน (เช่น เกินแผนงาน) server หยุดกลางรายการ: คงรายการที่กรอกไว้ แสดงแค่ข้อความ
		if (result.error) return;
		const keep = Object.fromEntries(
			["name", "modified", "docstatus", "status_label", "status_tone"].map((f) => [
				f,
				doc.value[f],
			])
		);
		doc.value = { ...result.doc, ...keep, items: keyed(result.doc.items) };
	} catch (e) {
		show_error(e);
	}
}

async function load_wbs() {
	const project = agreement.value?.project;
	wbs.value = project ? await call(`${API}.wbs_options`, { project }).catch(() => []) : [];
}

async function change_agreement(option) {
	if (!option || doc.value.name) return;
	const result = await call(`${API}.get_variation`, { agreement: option.value }).catch(
		show_error
	);
	if (!result) return;
	apply(result, true);
	error.value = null;
}

function edit_new(r) {
	row.value = r
		? { ...r, _new: false }
		: { _key: ++key, _new: true, wbs: null, item_name: "", uom: null, qty: null, rate: null };
}
function pick_wbs(option) {
	if (!option) return;
	if (!row.value.item_name) row.value.item_name = option.label.replace(/^\S+\s/, "");
	if (!row.value.uom && option.uom) row.value.uom = option.uom;
}
function save_new() {
	const r = row.value;
	if (!r.item_name?.trim() || !(Number(r.qty) > 0))
		return show_error(new Error("กรอกรายการและปริมาณ"));
	const { _new, ...clean } = r;
	const index = doc.value.items.findIndex((x) => x._key === r._key);
	if (index >= 0) doc.value.items.splice(index, 1, clean);
	else doc.value.items.push(clean);
	row.value = null;
	refresh();
}
function remove(r) {
	doc.value.items = doc.value.items.filter((x) => x._key !== r._key);
	refresh();
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
	const result = await run(
		() => post(`${API}.save_variation`, { data: payload() }),
		"บันทึกแล้ว"
	);
	if (!result) return;
	const is_new = !doc.value.name;
	apply(result);
	error.value = null;
	if (is_new) go("variation", { name: result.doc.name }, { replace: true });
}
async function submit() {
	const result = await run(
		() => post(`${API}.submit_doc`, { kind: "variations", name: doc.value.name }),
		"อนุมัติแล้ว"
	);
	if (result) apply(result);
	confirm_submit.value = false;
}
async function cancel() {
	const result = await run(
		() => post(`${API}.cancel_doc`, { kind: "variations", name: doc.value.name }),
		"ยกเลิกแล้ว"
	);
	if (result) apply(result);
	confirm_cancel.value = false;
}

async function load() {
	try {
		const name = params.name && params.name !== "new" ? params.name : undefined;
		if (!name && !params.agreement) {
			// ใบใหม่ที่ยังไม่เลือกสัญญา: ฟอร์มว่าง
			apply({ doc: { subcontract_agreement: null, items: [], posting_date: today() } });
			return;
		}
		apply(await call(`${API}.get_variation`, { name, agreement: params.agreement }), !name);
	} catch (e) {
		show_error(e);
		back("variations");
	}
}
load();
</script>
