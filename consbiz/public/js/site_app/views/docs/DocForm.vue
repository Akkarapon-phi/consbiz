<template>
	<!-- สร้าง/แก้ไขร่างเอกสารจัดซื้อ/ขาย (ชุดเดียวทั้ง 6 ชนิด) ข้อมูล/บันทึกผ่าน site_docs.get_form / preview_doc / save_doc
	     ยอดเงินและภาษีคำนวณที่ server (ERPNext) ทุกครั้งที่แก้ (หน่วงเล็กน้อย) ฟอร์มใหม่เก็บร่างใน localStorage -->
	<div class="ss-has-bar">
		<TopBar :title="title" :subtitle="subtitle" :back_to="back_view" :back_params="back_params" />

		<div class="ss-content ss-docform">
			<Skeleton v-if="!form" :rows="3" />
			<template v-else>
				<div v-if="form.source" class="ss-banner tone-blue">
					<Icon name="info" :size="22" />
					<div>
						<div class="ss-banner-title">สร้างจาก {{ source_label }} {{ form.source }}</div>
						<div class="ss-banner-text">
							ดึงรายการที่ยังค้างมาให้แล้ว ลบหรือแก้จำนวนได้ เอกสารจะอ้างถึงต้นทางให้เอง
						</div>
					</div>
				</div>

				<!-- หัวเอกสาร: แท็บเล็ต/จอใหญ่ = ตาราง 3-4 คอลัมน์ -->
				<section class="ss-form ss-docform-head">
					<Picker
						v-if="party_field"
						v-model="form[party_field]"
						class="ss-docform-party"
						:label="config.party"
						:display_value="form.party_label"
						:remote_fn="search_parties"
						required
						@select="(o) => (form.party_label = o.label)"
					/>
					<label v-for="f in fields" :key="f.field" class="ss-field">
						<span class="ss-field-label">{{ f.label }}<em v-if="f.required">*</em></span>
						<input
							v-model="form[f.field]"
							class="ss-input"
							:type="f.type || 'text'"
							:placeholder="f.placeholder"
							@change="f.rows && fill_rows(f.rows, form[f.field])"
						/>
					</label>
					<label v-if="form.tax_templates.length" class="ss-field">
						<span class="ss-field-label">ภาษี</span>
						<select v-model="tax_value" class="ss-input">
							<option v-for="t in tax_options" :key="t.value || 'none'" :value="t.value">
								{{ t.label }}
							</option>
						</select>
					</label>
					<label v-if="has_discount" class="ss-field">
						<span class="ss-field-label">ส่วนลดท้ายบิล (%)</span>
						<input
							v-model.number="form.additional_discount_percentage"
							class="ss-input ss-input--num"
							type="number"
							inputmode="decimal"
							min="0"
							max="100"
							step="any"
							placeholder="0"
						/>
					</label>
				</section>

				<section class="ss-docform-items">
					<h2 class="ss-section-title ss-section-title--first">
						<span
							>รายการ <span class="ss-count">{{ form.items.length }}</span></span
						>
						<span v-if="!is_mr && form.items.length" class="ss-section-total">
							{{ money(lines_total) }}
						</span>
					</h2>
					<Empty
						v-if="!form.items.length && !wide"
						:icon="config.icon"
						title="ยังไม่มีรายการ"
						:text="
							is_mr
								? 'เลือกวัสดุ/สินค้าที่ต้องการขอซื้อ'
								: 'เลือกสินค้า/บริการ แล้วใส่จำนวนและราคา'
						"
					/>
					<LineEditor
						:items="form.items"
						:wide="wide"
						:is_mr="is_mr"
						:date_field="row_date.field"
						:date_label="row_date.label"
						:show_errors="show_errors"
						:search_fn="find_items"
						@add="add_item"
						@remove="remove_row"
						@browse="item_sheet = true"
					/>
				</section>

				<!-- ท้ายเอกสาร: หมายเหตุ (ซ้าย) + สรุปยอด (ขวา) แบบใบเอกสารของระบบเต็ม -->
				<section class="ss-docform-foot">
					<div class="ss-docform-notes">
						<label v-if="remarks_field" class="ss-field">
							<span class="ss-field-label">หมายเหตุ</span>
							<textarea v-model="form[remarks_field]" class="ss-input" rows="3"></textarea>
						</label>
						<p class="ss-muted ss-docform-note">
							<Icon name="info" :size="14" /> หัก ณ ที่จ่าย เงินประกันผลงาน และเงื่อนไขชำระเงิน
							แก้ต่อได้ในระบบเต็มหลังบันทึก
						</p>
					</div>
					<div v-if="!is_mr" class="ss-totals" :class="{ 'is-stale': previewing }">
						<div>
							<span>รวมเป็นเงิน</span><b>{{ money(form.totals.total) }}</b>
						</div>
						<div v-if="form.totals.discount_amount">
							<span>ส่วนลด</span><b>−{{ money(form.totals.discount_amount) }}</b>
						</div>
						<div v-for="t in form.taxes" :key="t.description">
							<span
								>{{ t.description }}<template v-if="t.rate"> {{ t.rate }}%</template></span
							><b>{{ money(t.amount) }}</b>
						</div>
						<div class="is-grand">
							<span
								>ยอดรวมทั้งสิ้น
								<span v-if="previewing" class="ss-spinner ss-spinner--sm"></span></span
							><b>{{ money(grand_total) }}</b>
						</div>
					</div>
				</section>
			</template>
		</div>

		<Teleport to="#ss-layer">
			<Transition name="ss-bar">
				<div v-if="form" class="ss-bottom-bar">
					<span v-if="!is_mr" class="ss-bar-summary">
						<small>ยอดรวม</small> <b>{{ money(grand_total) }}</b>
					</span>
					<span v-else class="ss-bar-summary"
						><b>{{ form.items.length }}</b> รายการ</span
					>
					<button
						type="button"
						class="ss-btn ss-btn--ghost ss-btn--lg"
						:class="{ 'ss-grow': !form.can_submit }"
						:disabled="saving"
						@click="save(0)"
					>
						บันทึกร่าง
					</button>
					<button
						v-if="form.can_submit"
						type="button"
						class="ss-btn ss-btn--primary ss-btn--lg ss-grow"
						:disabled="saving"
						@click="ask_submit"
					>
						<span v-if="saving" class="ss-spinner"></span>
						<template v-else>บันทึกและส่ง</template>
					</button>
				</div>
			</Transition>
		</Teleport>

		<!-- เลือกสินค้า/บริการ (แตะได้หลายรายการ) -->
		<Sheet
			:open="item_sheet"
			title="เพิ่มรายการ"
			:subtitle="`เพิ่มแล้ว ${added} รายการ`"
			full
			@close="item_sheet = false"
		>
			<div class="ss-search">
				<Icon name="search" :size="18" />
				<input
					ref="item_input"
					v-model="item_txt"
					type="search"
					placeholder="ค้นหารหัส ชื่อ หรือกลุ่มสินค้า"
					@input="search_items"
				/>
			</div>
			<div class="ss-options">
				<button
					v-for="it in item_results"
					:key="it.item_code"
					type="button"
					class="ss-option"
					:class="{ 'is-active': in_form.has(it.item_code) }"
					@click="add_item(it)"
				>
					<span class="ss-check-box"
						><Icon v-if="in_form.has(it.item_code)" name="check" :size="14" :stroke="3"
					/></span>
					<span class="ss-option-main">
						<span class="ss-option-label">{{ it.item_name }}</span>
						<span class="ss-option-desc"
							>{{ it.item_code }} · {{ it.item_group }} · {{ it.stock_uom
							}}<template v-if="it.rate && !is_mr"> · {{ money(it.rate) }}</template></span
						>
					</span>
				</button>
				<div v-if="item_loading" class="ss-options-note">กำลังค้นหา…</div>
				<div v-else-if="!item_results.length" class="ss-options-note">ไม่พบรายการ</div>
			</div>
			<template #footer>
				<button
					type="button"
					class="ss-btn ss-btn--primary ss-btn--block"
					@click="item_sheet = false"
				>
					เสร็จ
				</button>
			</template>
		</Sheet>

		<Sheet :open="confirm" :title="`ส่ง${config.label}`" @close="confirm = false">
			<p class="ss-muted">ส่งแล้วแก้ไขไม่ได้ ต้องยกเลิกแล้วแก้ไขในระบบเต็ม</p>
			<div v-if="form" class="ss-facts ss-facts--grid">
				<div v-if="party_field" class="ss-fact">
					<span>{{ config.party }}</span
					><b>{{ form.party_label || form[party_field] }}</b>
				</div>
				<div class="ss-fact">
					<span>รายการ</span><b>{{ form.items.length }}</b>
				</div>
				<div v-if="!is_mr" class="ss-fact">
					<span>ยอดรวม</span><b>{{ money(grand_total) }}</b>
				</div>
			</div>
			<template #footer>
				<button
					type="button"
					class="ss-btn ss-btn--primary ss-btn--block ss-btn--lg"
					:disabled="saving"
					@click="save(1)"
				>
					<span v-if="saving" class="ss-spinner"></span>
					<template v-else>ยืนยันส่ง</template>
				</button>
			</template>
		</Sheet>
	</div>
</template>

<script setup>
import { computed, inject, nextTick, onBeforeUnmount, ref, watch } from "vue";
import Icon from "../../components/Icon.vue";
import TopBar from "../../components/TopBar.vue";
import Skeleton from "../../components/Skeleton.vue";
import Empty from "../../components/Empty.vue";
import Picker from "../../components/Picker.vue";
import Sheet from "../../components/Sheet.vue";
import LineEditor from "./LineEditor.vue";
import { DOC_KINDS } from "../../sections.js";
import { call, celebrate, go, money, post, show_error, state, toast } from "../../api.js";

const reload_summary = inject("reload_summary");

// จอกว้าง ≥1000 (แท็บเล็ตแนวนอน/คอมพิวเตอร์): ตารางรายการแก้ไขในช่อง
// แคบกว่านั้น (มือถือ, แท็บเล็ตแนวตั้ง ที่เนื้อหากว้างไม่ถึง ~650px): การ์ด กดง่ายบนจอสัมผัส
const mq_wide = window.matchMedia("(min-width: 1000px)");
const wide = ref(mq_wide.matches);
const on_media = () => (wide.value = mq_wide.matches);
mq_wide.addEventListener("change", on_media);
onBeforeUnmount(() => mq_wide.removeEventListener("change", on_media));
const params = state.route.params;
const kind = DOC_KINDS[params.kind] ? params.kind : "po";
const config = DOC_KINDS[kind];
const is_mr = kind === "mr";
const is_new = !params.name || params.name === "new";

// ช่องหัวเอกสาร (ตรงกับ FORM ใน site_docs.py) rows = ช่องของแถวที่ตามค่านี้เมื่อแก้
const PARTY = { po: "supplier", pi: "supplier", qtn: "party_name", so: "customer", si: "customer" };
const FIELDS = {
	mr: [
		{ field: "transaction_date", label: "วันที่", type: "date", required: true },
		{
			field: "schedule_date",
			label: "ต้องการภายใน",
			type: "date",
			required: true,
			rows: "schedule_date",
		},
	],
	po: [
		{ field: "transaction_date", label: "วันที่", type: "date", required: true },
		{ field: "schedule_date", label: "กำหนดส่ง", type: "date", required: true, rows: "schedule_date" },
	],
	pi: [
		{ field: "posting_date", label: "วันที่", type: "date", required: true },
		{ field: "due_date", label: "ครบกำหนดจ่าย", type: "date" },
		{ field: "bill_no", label: "เลขที่บิลผู้ขาย", placeholder: "เลขที่ใบแจ้งหนี้ของผู้ขาย" },
		{ field: "tax_invoice_number", label: "เลขที่ใบกำกับภาษี", placeholder: "เมื่อมีภาษีซื้อ" },
	],
	qtn: [
		{ field: "transaction_date", label: "วันที่", type: "date", required: true },
		{ field: "valid_till", label: "ยืนราคาถึง", type: "date" },
	],
	so: [
		{ field: "transaction_date", label: "วันที่", type: "date", required: true },
		{ field: "delivery_date", label: "กำหนดส่งมอบ", type: "date", required: true, rows: "delivery_date" },
	],
	si: [
		{ field: "posting_date", label: "วันที่", type: "date", required: true },
		{ field: "due_date", label: "ครบกำหนดรับ", type: "date" },
	],
};
const REMARKS = { mr: "custom_remark", pi: "remarks", si: "remarks" };
const SOURCE_KIND = { po: "mr", pi: "po", so: "qtn", si: "so" };

const party_field = PARTY[kind];
const remarks_field = REMARKS[kind];
const form = ref(null);
const show_errors = ref(false);
const saving = ref(false);
const confirm = ref(false);
const previewing = ref(false);
let uid = 0;

// ช่องที่ server ไม่มี (เช่น ไม่ได้ติดตั้ง erpnext_thailand) ไม่แสดง
const fields = computed(() =>
	FIELDS[kind].filter((f) => !form.value?.fields || form.value.fields.includes(f.field))
);
const title = computed(() => (is_new ? `${config.label}ใหม่` : `แก้ไข${config.label}`));
const subtitle = computed(() => (is_new ? state.project?.project_name || "" : params.name));
const source_label = computed(() => DOC_KINDS[SOURCE_KIND[kind]]?.label || "");
const back_view = computed(() => (is_new && !params.source ? kind : `${config.section}-doc`));
const back_params = computed(() =>
	is_new && !params.source
		? {}
		: { kind: is_new ? SOURCE_KIND[kind] : kind, name: is_new ? params.source : params.name }
);
const grand_total = computed(() => form.value?.totals.rounded_total || form.value?.totals.grand_total || 0);
const tax_options = computed(() => [
	...form.value.tax_templates.map((t) => ({ value: t.name, label: t.title || t.name })),
	{ value: "", label: "ไม่มีภาษี" },
]);
// ภาษี: select ใช้ "" แทน "ไม่มีภาษี"
const tax_value = computed({
	get: () => form.value?.taxes_and_charges || "",
	set: (value) => (form.value.taxes_and_charges = value || null),
});
const has_discount = computed(() => !!form.value?.fields?.includes("additional_discount_percentage"));
// วันที่รายแถว (แก้ต่างจากหัวเอกสารได้)
const row_date = computed(
	() =>
		({
			mr: { field: "schedule_date", label: "ต้องการภายใน" },
			po: { field: "schedule_date", label: "กำหนดส่ง" },
			so: { field: "delivery_date", label: "กำหนดส่งมอบ" },
		}[kind] || {})
);
const lines_total = computed(() =>
	(form.value?.items || []).reduce((s, r) => s + (Number(r.qty) || 0) * (Number(r.rate) || 0), 0)
);
const find_items = (txt) =>
	call("consbiz.site_docs.search_items", { kind, txt, project: state.project?.name || null });

const in_form = computed(() => new Set(form.value?.items.map((r) => r.item_code)));

// ---------------------------------------------------------------- โหลด / ร่างในเครื่อง

const draft_key = `consbiz.site.docform.${kind}.${params.source || "new"}.${state.project?.name || ""}`;

function with_uid(items) {
	return items.map((row) => ({ ...row, uid: ++uid }));
}

async function load() {
	try {
		const data = await call("consbiz.site_docs.get_form", {
			kind,
			name: is_new ? null : params.name,
			source: params.source || null,
			project: state.project?.name || null,
		});
		data.items = with_uid(data.items);
		if (is_new) restore_draft(data);
		form.value = data;
	} catch (error) {
		show_error(error);
	}
}

function restore_draft(data) {
	try {
		const saved = JSON.parse(localStorage.getItem(draft_key) || "null");
		if (!saved) return;
		Object.assign(data, saved, { items: with_uid(saved.items || []) });
		toast("กู้ข้อมูลที่กรอกค้างไว้แล้ว", "info");
	} catch {
		/* ร่างเสียหรือเข้าถึงไม่ได้: เริ่มใหม่ */
	}
}

// ค่าที่ส่งให้ server (ช่องที่กรอกได้เท่านั้น)
function payload() {
	const f = form.value;
	const out = { name: f.name, source: f.source, project: state.project?.name || null };
	for (const field of [
		...fields.value.map((x) => x.field),
		party_field,
		remarks_field,
		"taxes_and_charges",
		has_discount.value && "additional_discount_percentage",
	]) {
		if (field) out[field] = f[field] ?? null;
	}
	out.items = f.items.map((row) => ({
		key: row.key,
		item_code: row.item_code,
		qty: Number(row.qty) || 0,
		uom: row.uom,
		...(is_mr ? {} : { rate: Number(row.rate) || 0 }),
		...(row.schedule_date ? { schedule_date: row.schedule_date } : {}),
		...(row.delivery_date ? { delivery_date: row.delivery_date } : {}),
	}));
	return out;
}

let draft_timer = null;
let preview_timer = null;
let preview_id = 0;
watch(
	() => form.value && JSON.stringify(payload()),
	(value, old) => {
		if (!value || !old) return;
		if (is_new) {
			clearTimeout(draft_timer);
			draft_timer = setTimeout(() => {
				try {
					const { items, ...rest } = payload();
					localStorage.setItem(
						draft_key,
						JSON.stringify({
							...rest,
							party_label: form.value.party_label,
							items: form.value.items,
						})
					);
				} catch {
					/* พื้นที่เต็ม/โหมดส่วนตัว: ไม่เก็บร่าง */
				}
			}, 600);
		}
		if (!is_mr) {
			clearTimeout(preview_timer);
			preview_timer = setTimeout(preview, 450);
		}
	}
);

// ยอดรวม/ภาษีจาก ERPNext (ข้อมูลยังไม่ครบ เช่น ยังไม่เลือกผู้ขาย = คงยอดเดิมไว้)
async function preview() {
	const id = ++preview_id;
	previewing.value = true;
	try {
		const result = await post("consbiz.site_docs.preview_doc", { kind, data: payload() });
		if (id !== preview_id) return;
		form.value.totals = result.totals;
		form.value.taxes = result.taxes;
	} catch {
		/* แสดงข้อผิดพลาดตอนบันทึก */
	} finally {
		if (id === preview_id) previewing.value = false;
	}
}

// ---------------------------------------------------------------- รายการ

const item_sheet = ref(false);
const item_txt = ref("");
const item_results = ref([]);
const item_loading = ref(false);
const item_input = ref(null);
const added = ref(0);
let search_timer = null;

function search_items() {
	clearTimeout(search_timer);
	search_timer = setTimeout(async () => {
		item_loading.value = true;
		try {
			item_results.value = await call("consbiz.site_docs.search_items", {
				kind,
				txt: item_txt.value,
				project: state.project?.name || null,
			});
		} catch (error) {
			show_error(error);
		} finally {
			item_loading.value = false;
		}
	}, 220);
}

watch(item_sheet, async (open) => {
	if (!open) return;
	added.value = 0;
	item_txt.value = "";
	search_items();
	await nextTick();
	setTimeout(() => item_input.value?.focus(), 320);
});

function add_item(it) {
	const date_field = { mr: "schedule_date", po: "schedule_date", so: "delivery_date" }[kind];
	form.value.items.push({
		uid: ++uid,
		key: null,
		item_code: it.item_code,
		item_name: it.item_name,
		qty: 1,
		uom: it.stock_uom,
		uoms: it.uoms,
		rate: it.rate || 0,
		...(date_field ? { [date_field]: form.value[date_field] } : {}),
	});
	added.value++;
}

function remove_row(row) {
	form.value.items = form.value.items.filter((r) => r !== row);
}

function fill_rows(field, value) {
	if (value) form.value.items.forEach((row) => (row[field] = value));
}

function row_error(row) {
	if (!(Number(row.qty) > 0)) return "ใส่จำนวนมากกว่า 0";
	return "";
}

async function search_parties(txt) {
	return call("consbiz.site_docs.search_parties", { kind, txt, company: form.value.company });
}

// ---------------------------------------------------------------- บันทึก

function form_error() {
	if (party_field && !form.value[party_field]) return `เลือก${config.party}`;
	const missing = fields.value.find((f) => f.required && !form.value[f.field]);
	if (missing) return `ใส่${missing.label}`;
	if (!form.value.items.length) return "เพิ่มรายการอย่างน้อย 1 รายการ";
	const bad = form.value.items.find(row_error);
	if (bad) return `${bad.item_name || bad.item_code}: ${row_error(bad)}`;
	return "";
}

function ask_submit() {
	const error = form_error();
	if (error) {
		show_errors.value = true;
		return toast(error, "error");
	}
	confirm.value = true;
}

async function save(submit) {
	const error = form_error();
	if (error) {
		show_errors.value = true;
		return toast(error, "error");
	}
	saving.value = true;
	try {
		const result = await post("consbiz.site_docs.save_doc", { kind, data: payload(), submit });
		try {
			localStorage.removeItem(draft_key);
		} catch {
			/* ไม่มีร่าง */
		}
		confirm.value = false;
		reload_summary();
		await celebrate(submit ? `ส่ง${config.label}แล้ว` : "บันทึกร่างแล้ว", result.name);
		go(`${config.section}-doc`, { kind, name: result.name }, { replace: true });
	} catch (err) {
		show_error(err);
	} finally {
		saving.value = false;
	}
}

load();
</script>
