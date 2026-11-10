<!-- ฟอร์มสร้าง/แก้ร่างของเอกสารโครงการ 4 ชนิด (kinds.js) รายการ (งานลด-เพิ่ม/Punch List) แก้ทีละแถวใน sheet
     Submit งานลด-เพิ่ม/EOT ทำจากหน้าดู (มีผลกับแผนงาน ต้องยืนยัน) ขอตรวจงาน/Punch List ส่งจากฟอร์มได้เลย -->
<template>
	<div class="ss-has-bar">
		<TopBar :title="`${params.name === 'new' ? 'สร้าง' : 'แก้ไข'} ${kind.label}`" :subtitle="doc.name || 'เอกสารใหม่'" :back_to="kind.list" :back_params="kind.list_params" />

		<div class="ss-content">
			<Skeleton v-if="!setup" :rows="4" />
			<div v-else class="ss-split">
				<div class="ss-split-main">
					<div class="ss-form">
						<div v-if="doc.reinspection_of" class="ss-banner tone-amber">
							<Icon name="alert" :size="22" />
							<div>
								<div class="ss-banner-title">ขอตรวจซ้ำ</div>
								<div class="ss-banner-text">อ้างใบ {{ doc.reinspection_of }} ที่ตรวจไม่ผ่าน</div>
							</div>
						</div>
						<label class="ss-field">
							<span class="ss-field-label">เรื่อง<em>*</em></span>
							<input v-model="doc.title" class="ss-input" />
						</label>

						<!-- งานลด-เพิ่ม -->
						<template v-if="params.kind === 'vo'">
							<div class="ss-form-row">
								<label class="ss-field">
									<span class="ss-field-label">วันที่<em>*</em></span>
									<DateInput v-model="doc.date" label="วันที่" />
								</label>
								<label class="ss-field">
									<span class="ss-field-label">เลขที่อ้างอิง</span>
									<input v-model="doc.reference_no" class="ss-input" />
								</label>
							</div>
							<label class="ss-field">
								<span class="ss-field-label">ขอขยายเวลา (วัน)</span>
								<input v-model.number="doc.extension_days" class="ss-input" type="number" inputmode="numeric" min="0" />
							</label>
							<label class="ss-toggle" :class="{ 'is-on': doc.is_provisional }">
								<input v-model="doc.is_provisional" type="checkbox" :true-value="1" :false-value="0" />
								<span class="ss-toggle-track"><span></span></span>
								<span><b>ปริมาณประมาณการ</b><small>แก้ปริมาณและราคาจริงได้หลังส่ง</small></span>
							</label>
						</template>

						<!-- EOT -->
						<template v-else-if="params.kind === 'eot'">
							<div class="ss-field">
								<span class="ss-field-label">สาเหตุ<em>*</em></span>
								<SelectBox v-model="doc.cause" label="สาเหตุ" :options="CAUSES" />
							</div>
							<Picker v-if="doc.cause === 'Variation Order'" v-model="doc.variation_order" label="งานลด-เพิ่มที่อ้าง" :options="order_options" required @select="on_order" />
							<div class="ss-form-row">
								<label class="ss-field">
									<span class="ss-field-label">วันที่แจ้ง<em>*</em></span>
									<DateInput v-model="doc.date" label="วันที่แจ้ง" />
								</label>
								<label class="ss-field">
									<span class="ss-field-label">เลขที่หนังสือแจ้ง</span>
									<input v-model="doc.reference_no" class="ss-input" />
								</label>
							</div>
							<div class="ss-form-row">
								<label class="ss-field">
									<span class="ss-field-label">เริ่มเกิดเหตุ<em>*</em></span>
									<DateInput v-model="doc.event_start" label="เริ่มเกิดเหตุ" />
								</label>
								<label class="ss-field">
									<span class="ss-field-label">เหตุสิ้นสุด</span>
									<DateInput v-model="doc.event_end" label="เหตุสิ้นสุด" clearable />
								</label>
							</div>
							<label class="ss-field">
								<span class="ss-field-label">จำนวนวันที่ขอ<em>*</em></span>
								<input v-model.number="doc.requested_days" class="ss-input" type="number" inputmode="numeric" min="1" />
							</label>
							<div v-if="late_notice" class="ss-banner tone-amber">
								<Icon name="alert" :size="22" />
								<div>
									<div class="ss-banner-title">แจ้งหลังกำหนด</div>
									<div class="ss-banner-text">ต้องแจ้งภายใน 15 วันนับจากเหตุสิ้นสุด ผู้ว่าจ้างอาจไม่พิจารณา</div>
								</div>
							</div>
						</template>

						<!-- ขอตรวจงาน -->
						<template v-else-if="params.kind === 'inspection'">
							<Picker v-model="doc.wbs" label="งาน (WBS)" :options="setup.wbs" required />
							<label class="ss-field">
								<span class="ss-field-label">ตำแหน่ง</span>
								<input v-model="doc.location" class="ss-input" placeholder="เช่น ฐานราก F3" />
							</label>
							<div class="ss-form-row">
								<label class="ss-field">
									<span class="ss-field-label">วันที่ขอ<em>*</em></span>
									<DateInput v-model="doc.request_date" label="วันที่ขอ" />
								</label>
								<label class="ss-field">
									<span class="ss-field-label">วันที่นัดตรวจ</span>
									<DateInput v-model="doc.inspection_date" label="วันที่นัดตรวจ" clearable />
								</label>
							</div>
							<label class="ss-field">
								<span class="ss-field-label">ผู้ตรวจ</span>
								<input v-model="doc.inspector" class="ss-input" />
							</label>
						</template>

						<!-- Punch List -->
						<template v-else>
							<label class="ss-field">
								<span class="ss-field-label">วันที่<em>*</em></span>
								<DateInput v-model="doc.date" label="วันที่" />
							</label>
							<Picker v-model="doc.inspection_request" label="อ้างใบขอตรวจงาน" :options="inspection_options" clearable />
						</template>

						<label v-if="params.kind === 'vo' || params.kind === 'eot'" class="ss-field">
							<span class="ss-field-label">เหตุผล</span>
							<textarea v-model="doc.reason" class="ss-input" rows="2"></textarea>
						</label>
						<label v-if="params.kind !== 'punch'" class="ss-field">
							<span class="ss-field-label">หมายเหตุ</span>
							<textarea v-model="doc.remarks" class="ss-input" rows="2"></textarea>
						</label>
					</div>
				</div>

				<aside v-if="has_items" class="ss-split-side">
					<h2 class="ss-section-title">
						รายการ ({{ doc.items.length }})
						<span v-if="params.kind === 'vo'" class="ss-section-total">สุทธิ {{ money(net_total) }}</span>
					</h2>
					<TransitionGroup tag="div" class="ss-list" name="ss-list">
						<button v-for="(row, i) in doc.items" :key="row._key" type="button" class="ss-card ss-card--row" :style="{ '--i': i }" @click="edit_row(row)">
							<span v-if="params.kind === 'vo'" class="ss-tag" :class="row.variation_type === 'Omission' ? 'tone-rose' : 'tone-green'">{{ row.variation_type === "Omission" ? "ลด" : "เพิ่ม" }}</span>
							<span class="ss-card-main">
								<span class="ss-card-title">{{ row.item_name || row.description }}</span>
								<span class="ss-card-meta">
									<i v-if="row.wbs" class="ss-wbs">{{ row.wbs }}</i>
									{{ params.kind === "vo" ? `${num(row.qty)} ${row.uom || ""}` : row.location || row.responsible || "" }}
								</span>
							</span>
							<span v-if="params.kind === 'vo'" class="ss-qty"><b>{{ money(row_amount(row)) }}</b></span>
						</button>
					</TransitionGroup>
					<button type="button" class="ss-add-row" @click="new_row"><Icon name="plus" :size="20" :stroke="2.6" /> เพิ่มรายการ</button>
				</aside>
			</div>
		</div>

		<Teleport to="#ss-layer">
			<Transition name="ss-bar">
				<div v-if="setup" class="ss-bottom-bar">
					<button v-if="quick_submit" type="button" class="ss-btn ss-btn--ghost ss-btn--lg" :disabled="saving" @click="save(0)">บันทึกร่าง</button>
					<button type="button" class="ss-btn ss-btn--primary ss-btn--lg ss-grow" :disabled="saving" @click="save(quick_submit ? 1 : 0)">
						<span v-if="saving" class="ss-spinner"></span>
						<template v-else>{{ quick_submit ? "ส่ง" : "บันทึก" }}</template>
					</button>
				</div>
			</Transition>
		</Teleport>

		<Sheet :open="!!row" :title="row?._new ? 'เพิ่มรายการ' : 'แก้รายการ'" @close="row = null">
			<div v-if="row" class="ss-form">
				<template v-if="params.kind === 'vo'">
					<Segmented v-model="row.variation_type" :options="VARIATION_TYPES" />
					<Picker v-model="row.wbs" :label="row.variation_type === 'Omission' ? 'งานเดิม (WBS)' : 'งานเดิม (ถ้าเพิ่มปริมาณงานเดิม)'" :options="task_options" :required="row.variation_type === 'Omission'" :clearable="row.variation_type !== 'Omission'" @select="on_task" />
					<p v-if="row_task" class="ss-note-line is-muted">ตามสัญญา {{ num(row_task.contract_quantity) }} {{ row_task.uom || "" }} · ทำแล้ว {{ num(row_task.done_qty) }}</p>
					<label class="ss-field">
						<span class="ss-field-label">ชื่องาน<em v-if="row.variation_type === 'Addition'">*</em></span>
						<input v-model="row.item_name" class="ss-input" :disabled="row.variation_type === 'Omission'" />
					</label>
					<div class="ss-form-row">
						<label class="ss-field">
							<span class="ss-field-label">ปริมาณ</span>
							<input v-model.number="row.qty" class="ss-input" type="number" inputmode="decimal" min="0" />
						</label>
						<Picker v-model="row.uom" label="หน่วย" remote="UOM" :display_value="row.uom" />
					</div>
					<div class="ss-form-row">
						<label class="ss-field">
							<span class="ss-field-label">ราคาต่อหน่วย</span>
							<MoneyInput class="ss-input" v-model="row.rate" :disabled="row.variation_type === 'Omission'" />
						</label>
						<label class="ss-field">
							<span class="ss-field-label">มูลค่า (งานเหมา)</span>
							<MoneyInput class="ss-input" v-model="row.amount" :disabled="Number(row.qty) > 0 || row.variation_type === 'Omission'" />
						</label>
					</div>
				</template>
				<template v-else>
					<label class="ss-field">
						<span class="ss-field-label">รายละเอียด<em>*</em></span>
						<textarea v-model="row.description" class="ss-input" rows="3"></textarea>
					</label>
					<div class="ss-form-row">
						<label class="ss-field">
							<span class="ss-field-label">ตำแหน่ง</span>
							<input v-model="row.location" class="ss-input" />
						</label>
						<label class="ss-field">
							<span class="ss-field-label">ผู้รับผิดชอบ</span>
							<input v-model="row.responsible" class="ss-input" />
						</label>
					</div>
					<Picker v-model="row.wbs" label="งาน (WBS)" :options="setup.wbs" clearable />
					<label class="ss-field">
						<span class="ss-field-label">กำหนดแก้</span>
						<DateInput v-model="row.due_date" label="กำหนดแก้" clearable />
					</label>
					<div class="ss-field">
						<span class="ss-field-label">รูปก่อนแก้</span>
						<PhotoInput v-model="row._photos" :max="1" />
					</div>
				</template>
			</div>
			<template #footer>
				<div class="ss-sheet-actions">
					<button v-if="!row?._new" type="button" class="ss-btn ss-btn--ghost-danger" aria-label="ลบรายการ" @click="remove_row"><Icon name="trash" :size="18" /></button>
					<button type="button" class="ss-btn ss-btn--primary ss-btn--block ss-btn--lg" :disabled="row?._photos?.some((p) => p.uploading)" @click="save_row">{{ row?._new ? "เพิ่ม" : "บันทึก" }}</button>
				</div>
			</template>
		</Sheet>
	</div>
</template>

<script setup>
import { computed, inject, reactive, ref } from "vue";
import DateInput from "../../../shared/components/DateInput.vue";
import Icon from "../../../shared/components/Icon.vue";
import MoneyInput from "../../../shared/components/MoneyInput.vue";
import PhotoInput from "../../../shared/components/PhotoInput.vue";
import Picker from "../../../shared/components/Picker.vue";
import Segmented from "../../../shared/components/Segmented.vue";
import SelectBox from "../../../shared/components/SelectBox.vue";
import Sheet from "../../../shared/components/Sheet.vue";
import Skeleton from "../../../shared/components/Skeleton.vue";
import TopBar from "../../../shared/components/TopBar.vue";
import { back, call, celebrate, go, money, num, post, show_error, state, today } from "../../../shared/api.js";
import { CAUSES, PROJECT_KINDS, VARIATION_TYPES } from "./kinds.js";

const reload_summary = inject("reload_summary");
const params = state.route.params;
const kind = PROJECT_KINDS[params.kind];
const API = "consbiz.project_docs";
const DATE_DEFAULT = { vo: "date", eot: "date", inspection: "request_date", punch: "date" };

let key = 0;
const setup = ref(null);
const saving = ref(false);
const row = ref(null);
const can_submit = ref(false);
const doc = reactive({ name: null, title: "", items: [] });
const has_items = params.kind === "vo" || params.kind === "punch";
const quick_submit = computed(() => kind.quick && can_submit.value);

const task_options = computed(() =>
	(setup.value?.tasks || []).map((t) => ({ value: t.wbs, label: `${t.wbs} ${t.item_name}`, description: t.group_path, task: t }))
);
const order_options = computed(() =>
	(setup.value?.orders || []).map((o) => ({ value: o.name, label: o.title, description: o.name, days: o.extension_days }))
);
const inspection_options = computed(() =>
	(setup.value?.inspections || []).map((o) => ({ value: o.name, label: o.title, description: o.name }))
);
const row_task = computed(() => setup.value?.tasks?.find((t) => t.wbs === row.value?.wbs));

const row_amount = (r) => (Number(r.qty) > 0 ? Number(r.qty) * Number(r.rate || 0) : Number(r.amount) || 0);
const net_total = computed(() =>
	doc.items.reduce((sum, r) => sum + (r.variation_type === "Omission" ? -1 : 1) * row_amount(r), 0)
);
// 15 วัน ตรงกับ NOTICE_DAYS ใน extension_of_time.py
const late_notice = computed(() => {
	if (params.kind !== "eot" || !doc.date || !doc.event_end) return false;
	const deadline = new Date(`${doc.event_end}T00:00:00`);
	deadline.setDate(deadline.getDate() + 15);
	return new Date(`${doc.date}T00:00:00`) > deadline;
});

function on_order(option) {
	if (option?.days) doc.requested_days = option.days;
}
function on_task(option) {
	const task = option?.task;
	if (!task) return;
	Object.assign(row.value, { item_name: task.item_name, uom: task.uom, rate: task.rate });
}

function new_row() {
	row.value =
		params.kind === "vo"
			? { _new: true, _key: ++key, variation_type: "Addition", wbs: null, item_name: "", uom: null, qty: null, rate: null, amount: null }
			: { _new: true, _key: ++key, description: "", location: "", wbs: null, responsible: "", due_date: null, _photos: [] };
}
function edit_row(r) {
	row.value = { ...r, _new: false, _photos: [...(r._photos || [])] };
}
function save_row() {
	const r = row.value;
	if (params.kind === "punch" && !r.description?.trim()) return show_error(new Error("กรอกรายละเอียด"));
	if (params.kind === "vo" && r.variation_type === "Omission" && !r.wbs) return show_error(new Error("งานลดต้องเลือกงานเดิม"));
	if (params.kind === "vo" && r.variation_type === "Addition" && !r.item_name?.trim()) return show_error(new Error("กรอกชื่องาน"));
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

const REQUIRED = {
	vo: ["title", "date"],
	eot: ["title", "cause", "date", "event_start", "requested_days"],
	inspection: ["title", "wbs", "request_date"],
	punch: ["title", "date"],
};

async function save(submit) {
	if (REQUIRED[params.kind].some((f) => !doc[f])) return show_error(new Error("กรอกช่องที่มีเครื่องหมาย * ให้ครบ"));
	if (has_items && !doc.items.length) return show_error(new Error("เพิ่มรายการอย่างน้อย 1 แถว"));
	saving.value = true;
	try {
		const items = doc.items.map(({ _key, _new, _photos, ...r }) => ({ ...r, ...(_photos ? { photo: _photos[0]?.file_url || "" } : {}) }));
		const files = doc.items.flatMap((r) => (r._photos || []).map((p) => p.name)).filter(Boolean);
		const result = await post(`${API}.save_doc`, {
			kind: params.kind,
			project: state.project.name,
			submit,
			data: { ...doc, items, files },
		});
		reload_summary();
		if (submit) await celebrate("ส่งแล้ว", result.name);
		go(kind.view, { kind: params.kind, name: result.name }, { replace: true });
	} catch (error) {
		show_error(error);
	} finally {
		saving.value = false;
	}
}

async function load() {
	try {
		const form = await call(`${API}.get_form`, {
			kind: params.kind,
			project: state.project.name,
			name: params.name === "new" ? undefined : params.name,
			source: params.source,
		});
		Object.assign(doc, form.doc, {
			items: (form.doc.items || []).map((r) => ({ ...r, _key: ++key, ...(params.kind === "punch" ? { _photos: r.photo ? [{ file_url: r.photo }] : [] } : {}) })),
		});
		const field = DATE_DEFAULT[params.kind];
		doc[field] = doc[field] || today();
		can_submit.value = form.can_submit;
		setup.value = form.setup;
	} catch (error) {
		show_error(error);
		back(kind.list, kind.list_params);
	}
}
load();
</script>
