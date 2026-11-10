<!-- ดูเอกสารโครงการ 4 ชนิด (kinds.js): ร่าง = แก้/ส่ง, ส่งแล้ว = บันทึกผลอนุมัติ/ผลตรวจ, ปิดรายการ Punch List, แก้ปริมาณจริงของงานลด-เพิ่ม
     ยกเลิก/แก้ฉบับ (amend) และไฟล์แนบใช้ระบบเต็ม -->
<template>
	<div class="ss-has-bar">
		<TopBar :title="kind.label" :subtitle="params.name" :back_to="kind.list" :back_params="kind.list_params">
			<template #actions>
				<a class="ss-icon-btn" :href="desk_url(kind.doctype, params.name)" aria-label="เปิดในระบบเต็ม" title="เปิดในระบบเต็ม"><Icon name="external" :size="19" /></a>
			</template>
		</TopBar>

		<div class="ss-content">
			<Skeleton v-if="!view" :rows="4" />
			<div v-else class="ss-split">
				<div class="ss-split-main">
					<div class="ss-doc-head">
						<div class="ss-doc-head-top">
							<span class="ss-tag" :class="`tone-${doc.status_tone}`">{{ doc.status_label }}</span>
							<span class="ss-doc-date">{{ doc.name }}</span>
						</div>
						<h2 class="ss-section-title">{{ doc.title }}</h2>
						<div class="ss-facts ss-facts--grid">
							<div v-for="f in facts" :key="f.label" class="ss-fact">
								<span>{{ f.label }}</span><b>{{ f.value }}</b>
							</div>
						</div>
					</div>
					<div v-for="b in notes" :key="b.label">
						<h2 class="ss-section-title">{{ b.label }}</h2>
						<p class="ss-note-line">{{ b.text }}</p>
					</div>
					<div v-if="view.reinspection" class="ss-banner tone-amber">
						<Icon name="alert" :size="22" />
						<div>
							<div class="ss-banner-title">มีใบขอตรวจซ้ำแล้ว</div>
							<button type="button" class="ss-link" @click="go(kind.view, { kind: params.kind, name: view.reinspection })">{{ view.reinspection }}</button>
						</div>
					</div>
				</div>

				<aside v-if="doc.items" class="ss-split-side">
					<h2 class="ss-section-title">รายการ ({{ doc.items.length }})</h2>
					<div class="ss-list">
						<component :is="row_editable ? 'button' : 'div'" v-for="(row, i) in doc.items" :key="row.name" :type="row_editable ? 'button' : undefined" class="ss-card" :style="{ '--i': i }" @click="row_editable && open_row(row)">
							<div class="ss-card-head">
								<span v-if="params.kind === 'vo'" class="ss-tag" :class="row.variation_type === 'Omission' ? 'tone-rose' : 'tone-green'">{{ row.variation_type === "Omission" ? "ลด" : "เพิ่ม" }}</span>
								<span class="ss-card-main">
									<span class="ss-card-title">{{ row.item_name || row.description }}</span>
									<span class="ss-card-meta"><i v-if="row.wbs || row.variation_wbs" class="ss-wbs">{{ row.variation_wbs || row.wbs }}</i> {{ row.location || row.responsible || "" }}</span>
								</span>
								<span v-if="params.kind === 'vo'" class="ss-qty"><b>{{ num(row.qty) }}</b><small>{{ row.uom }}</small></span>
								<span v-else class="ss-tag" :class="row.status === 'Closed' ? 'tone-green' : 'tone-amber'">{{ row.status === "Closed" ? "ปิดแล้ว" : "ยังไม่แก้" }}</span>
							</div>
							<div v-if="params.kind === 'vo' && row.amount !== undefined" class="ss-chips">
								<span class="ss-chip">ราคา {{ money(row.rate) }}</span>
								<span class="ss-chip">มูลค่า {{ money(row.amount) }}</span>
							</div>
							<div v-if="params.kind === 'punch'" class="ss-chips">
								<span v-if="row.responsible" class="ss-chip"><Icon name="user" :size="12" /> {{ row.responsible }}</span>
								<span v-if="row.due_date" class="ss-chip"><Icon name="calendar" :size="12" /> กำหนด {{ thai_date(row.due_date) }}</span>
								<span v-if="row.closed_on" class="ss-chip"><Icon name="search-check" :size="12" /> ปิด {{ thai_date(row.closed_on) }}</span>
							</div>
							<div v-if="row.photo || row.photo_after" class="ss-photos">
								<div v-if="row.photo" class="ss-photo"><img :src="row.photo" alt="รูปก่อนแก้" /></div>
								<div v-if="row.photo_after" class="ss-photo"><img :src="row.photo_after" alt="รูปหลังแก้" /></div>
							</div>
						</component>
					</div>
				</aside>
			</div>
		</div>

		<Teleport to="#ss-layer">
			<Transition name="ss-bar">
				<div v-if="actions.length" class="ss-bottom-bar">
					<button v-for="a in actions" :key="a.label" type="button" class="ss-btn ss-btn--lg" :class="a.primary ? 'ss-btn--primary ss-grow' : a.danger ? 'ss-btn--ghost-danger' : 'ss-btn--ghost'" :disabled="busy" @click="a.run">{{ a.label }}</button>
				</div>
			</Transition>
		</Teleport>

		<DeleteSheet
			:open="deleting"
			:label="kind.label"
			:name="params.name"
			:method="`${API}.delete_doc`"
			:args="{ kind: params.kind, name: params.name }"
			@close="deleting = false"
			@deleted="after_delete"
		/>

		<!-- ยืนยันการส่ง งานลด-เพิ่ม/EOT มีผลกับแผนงาน -->
		<Sheet :open="confirming" title="ยืนยันการส่ง" @close="confirming = false">
			<p class="ss-note-line">{{ params.kind === "vo" ? "งานเพิ่มจะเป็นแถวใหม่ในแผน และงานลดจะลดปริมาณงานเดิมทันที" : "ยื่นขอขยายเวลา วันจบสัญญาจะเลื่อนเมื่อบันทึกผลว่าอนุมัติ" }} หลังส่งแก้ได้เฉพาะช่องที่ระบบอนุญาต</p>
			<template #footer>
				<div class="ss-sheet-actions">
					<button type="button" class="ss-btn ss-btn--primary ss-btn--block ss-btn--lg" :disabled="busy" @click="submit">ยืนยันส่ง</button>
				</div>
			</template>
		</Sheet>

		<!-- ผลอนุมัติ / ผลตรวจ -->
		<Sheet :open="!!result" :title="params.kind === 'inspection' ? 'บันทึกผลตรวจ' : 'บันทึกผลอนุมัติ'" @close="result = null">
			<div v-if="result" class="ss-form">
				<template v-if="params.kind === 'inspection'">
					<div class="ss-field">
						<span class="ss-field-label">ผลตรวจ<em>*</em></span>
						<SelectBox v-model="result.result" label="ผลตรวจ" :options="RESULTS" />
					</div>
					<label class="ss-field">
						<span class="ss-field-label">วันที่ตรวจ</span>
						<DateInput v-model="result.inspected_on" label="วันที่ตรวจ" clearable />
					</label>
					<label class="ss-field">
						<span class="ss-field-label">ความเห็นผู้ตรวจ</span>
						<textarea v-model="result.comments" class="ss-input" rows="3"></textarea>
					</label>
				</template>
				<template v-else>
					<div class="ss-field">
						<span class="ss-field-label">ผลอนุมัติ<em>*</em></span>
						<SelectBox v-model="result.employer_status" label="ผลอนุมัติ" :options="EMPLOYER_STATUS" />
					</div>
					<label class="ss-field">
						<span class="ss-field-label">วันที่อนุมัติ</span>
						<DateInput v-model="result.employer_approved_on" label="วันที่อนุมัติ" clearable />
					</label>
					<label v-if="params.kind === 'eot' && result.employer_status === 'Approved'" class="ss-field">
						<span class="ss-field-label">จำนวนวันที่อนุมัติ</span>
						<input v-model.number="result.approved_days" class="ss-input" type="number" inputmode="numeric" min="0" />
					</label>
					<label v-if="params.kind === 'eot'" class="ss-field">
						<span class="ss-field-label">เลขที่หนังสืออนุมัติ</span>
						<input v-model="result.approval_reference" class="ss-input" />
					</label>
					<label v-if="params.kind === 'vo'" class="ss-field">
						<span class="ss-field-label">เลขที่อ้างอิง</span>
						<input v-model="result.reference_no" class="ss-input" />
					</label>
					<label v-if="params.kind === 'vo'" class="ss-field">
						<span class="ss-field-label">ขอขยายเวลา (วัน)</span>
						<input v-model.number="result.extension_days" class="ss-input" type="number" inputmode="numeric" min="0" />
					</label>
				</template>
			</div>
			<template #footer>
				<div class="ss-sheet-actions">
					<button type="button" class="ss-btn ss-btn--primary ss-btn--block ss-btn--lg" :disabled="busy" @click="save_result">บันทึก</button>
				</div>
			</template>
		</Sheet>

		<!-- แก้แถวหลังส่ง -->
		<Sheet :open="!!editing" :title="params.kind === 'punch' ? 'ปิดรายการ' : 'แก้ปริมาณจริง'" @close="editing = null">
			<div v-if="editing" class="ss-form">
				<template v-if="params.kind === 'punch'">
					<Segmented v-model="editing.status" :options="ROW_STATUS" />
					<div class="ss-field">
						<span class="ss-field-label">รูปหลังแก้</span>
						<PhotoInput v-model="editing._photos" :max="1" />
					</div>
				</template>
				<template v-else>
					<div class="ss-form-row">
						<label class="ss-field">
							<span class="ss-field-label">ปริมาณ</span>
							<input v-model.number="editing.qty" class="ss-input" type="number" inputmode="decimal" min="0" />
						</label>
						<label class="ss-field">
							<span class="ss-field-label">ราคาต่อหน่วย</span>
							<MoneyInput class="ss-input" v-model="editing.rate" :disabled="editing.variation_type === 'Omission'" />
						</label>
					</div>
					<label class="ss-field">
						<span class="ss-field-label">มูลค่า (งานเหมา)</span>
						<MoneyInput class="ss-input" v-model="editing.amount" :disabled="Number(editing.qty) > 0 || editing.variation_type === 'Omission'" />
					</label>
				</template>
			</div>
			<template #footer>
				<div class="ss-sheet-actions">
					<button type="button" class="ss-btn ss-btn--primary ss-btn--block ss-btn--lg" :disabled="busy || editing?._photos?.some((p) => p.uploading)" @click="save_row">บันทึก</button>
				</div>
			</template>
		</Sheet>
	</div>
</template>

<script setup>
import { computed, inject, ref } from "vue";
import DateInput from "../../../shared/components/DateInput.vue";
import Icon from "../../../shared/components/Icon.vue";
import MoneyInput from "../../../shared/components/MoneyInput.vue";
import PhotoInput from "../../../shared/components/PhotoInput.vue";
import Segmented from "../../../shared/components/Segmented.vue";
import SelectBox from "../../../shared/components/SelectBox.vue";
import Sheet from "../../../shared/components/Sheet.vue";
import Skeleton from "../../../shared/components/Skeleton.vue";
import DeleteSheet from "../../../shared/components/DeleteSheet.vue";
import TopBar from "../../../shared/components/TopBar.vue";
import { back, call, celebrate, desk_url, go, money, num, post, show_error, state, thai_date } from "../../../shared/api.js";
import { EMPLOYER_STATUS, PROJECT_KINDS, RESULTS, cause_label } from "./kinds.js";

const ROW_STATUS = [
	{ value: "Open", label: "ยังไม่แก้" },
	{ value: "Closed", label: "แก้แล้ว" },
];
const API = "consbiz.project_docs";
const reload_summary = inject("reload_summary");
const params = state.route.params;
const kind = PROJECT_KINDS[params.kind];

const view = ref(null);
const doc = computed(() => view.value?.doc);
const busy = ref(false);
const confirming = ref(false);
const result = ref(null);
const editing = ref(null);

const date = (value) => (value ? thai_date(value, { year: true }) : "–");
const days = (value) => `${value || 0} วัน`;

const facts = computed(() => {
	const d = doc.value;
	const list = {
		vo: [
			["วันที่", date(d.date)],
			["เลขที่อ้างอิง", d.reference_no || "–"],
			["วันที่อนุมัติ", date(d.employer_approved_on)],
			["ขอขยายเวลา", days(d.extension_days)],
			...(d.is_provisional ? [["ปริมาณ", "ประมาณการ"]] : []),
			...(d.net_amount === undefined
				? []
				: [
						["งานเพิ่ม", money(d.addition_amount)],
						["งานลด", money(d.omission_amount)],
						["สุทธิ", money(d.net_amount)],
						["มูลค่าสัญญาปรับปรุง", money(d.revised_amount)],
				  ]),
		],
		eot: [
			["สาเหตุ", cause_label(d.cause)],
			...(d.variation_order ? [["งานลด-เพิ่มที่อ้าง", d.variation_order]] : []),
			["วันที่แจ้ง", date(d.date)],
			["ช่วงเกิดเหตุ", `${date(d.event_start)} ถึง ${date(d.event_end)}`],
			["ต้องแจ้งภายใน", date(d.notice_deadline)],
			["วันที่ขอ", days(d.requested_days)],
			["วันที่อนุมัติ", days(d.approved_days)],
			["เลขที่หนังสืออนุมัติ", d.approval_reference || "–"],
			["วันจบสัญญาเดิม", date(d.contract_finish_date)],
			["วันจบใหม่", date(d.revised_finish_date)],
		],
		inspection: [
			["งาน", `${d.wbs} ${d.item_name || ""}`],
			["ตำแหน่ง", d.location || "–"],
			["วันที่ขอ", date(d.request_date)],
			["วันที่นัดตรวจ", date(d.inspection_date)],
			["ผู้ตรวจ", d.inspector || "–"],
			["วันที่ตรวจ", date(d.inspected_on)],
			...(d.reinspection_of ? [["ขอตรวจซ้ำจาก", d.reinspection_of]] : []),
		],
		punch: [
			["วันที่", date(d.date)],
			["รายการค้าง", d.open_items ?? "–"],
			...(d.inspection_request ? [["ใบขอตรวจงาน", d.inspection_request]] : []),
		],
	};
	return list[params.kind].map(([label, value]) => ({ label, value }));
});
const notes = computed(() => {
	const d = doc.value;
	return [
		{ label: "เหตุผล", text: d.reason },
		{ label: "ความเห็นผู้ตรวจ", text: d.comments },
		{ label: "หมายเหตุ", text: d.remarks },
	].filter((b) => b.text);
});

const row_editable = computed(() => !!view.value?.can_update && (params.kind === "punch" || params.kind === "vo"));

const deleting = ref(false);
function after_delete() {
	reload_summary();
	go(kind.list, kind.list_params, { replace: true });
}

const actions = computed(() => {
	const v = view.value;
	if (!v) return [];
	const list = [];
	if (v.can_delete) list.push({ label: "ลบ", danger: true, run: () => (deleting.value = true) });
	if (v.can_edit) list.push({ label: "แก้ไข", primary: !v.can_submit, run: () => go(kind.form, { kind: params.kind, name: params.name }) });
	if (v.can_submit) list.push({ label: "ส่ง", primary: true, run: () => (kind.quick ? submit() : (confirming.value = true)) });
	if (v.can_update && params.kind !== "punch")
		list.push({ label: params.kind === "inspection" ? "บันทึกผลตรวจ" : "บันทึกผลอนุมัติ", primary: true, run: open_result });
	if (v.can_reinspect && !v.reinspection)
		list.push({ label: "ขอตรวจซ้ำ", run: () => go(kind.form, { kind: params.kind, name: "new", source: params.name }) });
	return list;
});

function open_result() {
	const fields = {
		vo: ["employer_status", "employer_approved_on", "reference_no", "extension_days"],
		eot: ["employer_status", "employer_approved_on", "approved_days", "approval_reference"],
		inspection: ["result", "inspected_on", "comments"],
	}[params.kind];
	result.value = Object.fromEntries(fields.map((f) => [f, doc.value[f]]));
}
function open_row(row) {
	editing.value = { ...row, _photos: row.photo_after ? [{ file_url: row.photo_after }] : [] };
}

async function run(task, message) {
	busy.value = true;
	try {
		const updated = await task();
		if (updated) view.value = updated;
		else await load();
		reload_summary();
		result.value = null;
		editing.value = null;
		confirming.value = false;
		await celebrate(message, params.name);
	} catch (error) {
		show_error(error);
	} finally {
		busy.value = false;
	}
}
const update = (data) => () => post(`${API}.update_submitted`, { kind: params.kind, name: params.name, data });

function submit() {
	run(() => post(`${API}.submit_doc`, { kind: params.kind, name: params.name }), "ส่งแล้ว");
}
function save_result() {
	run(update(result.value), "บันทึกแล้ว");
}
function save_row() {
	const { name, status, qty, rate, amount, _photos } = editing.value;
	const row =
		params.kind === "punch"
			? { name, status, photo_after: _photos[0]?.file_url || "" }
			: { name, qty, rate, amount };
	const files = (_photos || []).map((p) => p.name).filter(Boolean);
	run(update({ items: [row], files }), "บันทึกแล้ว");
}

async function load() {
	try {
		view.value = await call(`${API}.get_view`, { kind: params.kind, name: params.name });
	} catch (error) {
		show_error(error);
		back(kind.list, kind.list_params);
	}
}
load();
</script>
