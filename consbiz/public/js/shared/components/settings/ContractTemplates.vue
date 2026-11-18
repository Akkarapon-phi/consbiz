<!-- ตั้งค่าบุคคล > แม่แบบสัญญาจ้าง (ตกลง 2026-11-18, API consbiz/contract_terms.py)
     ซ้าย = รายการแม่แบบ + สร้างใหม่ / กลาง = แก้แม่แบบ (ชื่อ บริษัท ค่าเริ่มต้น เนื้อหา + ตัวแปร) / ขวา = ตัวอย่าง real-time
     ตัวอย่างใช้ค่าตัวอย่าง หรือเลือกพนักงานจริงมาดู สัญญาที่สร้างแล้วไม่เปลี่ยนตามแม่แบบ (คัดลอกตอนสร้าง) -->
<template>
	<div class="ect">
		<nav class="ect-list" aria-label="แม่แบบสัญญา">
			<button
				v-for="t in templates"
				:key="t.name"
				type="button"
				class="ect-item"
				:class="{ 'is-active': form && form.name === t.name, 'is-off': t.disabled }"
				@click="open(t.name)"
			>
				<b>{{ t.title }}</b>
				<small>
					{{ t.company || "ทุกบริษัท" }}
					<span v-if="t.is_default" class="ss-tag tone-blue">เริ่มต้น</span>
					<span v-if="t.disabled" class="ss-tag tone-gray">ปิด</span>
				</small>
			</button>
			<button v-if="can_write" type="button" class="ss-btn ss-btn--soft ect-new" @click="create">
				<Icon name="plus" :size="15" /><span>แม่แบบใหม่</span>
			</button>
		</nav>

		<Skeleton v-if="!form" :rows="4" class="ect-main" />
		<div v-else class="ect-main">
			<header class="ect-head">
				<h2>{{ form.name ? form.title : "แม่แบบใหม่" }}</h2>
				<div class="ect-actions">
					<button v-if="can_write && form.name" type="button" class="ss-btn ss-btn--ghost" :disabled="busy" @click="duplicate">
						<Icon name="copy" :size="14" /><span>ทำสำเนา</span>
					</button>
					<button v-if="can_write && form.name" type="button" class="ss-btn ss-btn--ghost-danger" :disabled="busy" @click="remove">
						<Icon name="trash" :size="14" />
					</button>
					<button v-if="can_write" type="button" class="ss-btn ss-btn--primary" :disabled="busy || !dirty || !form.title" @click="save">
						บันทึก
					</button>
				</div>
			</header>
			<p v-if="!can_write" class="ss-muted ect-note">แก้แม่แบบได้เฉพาะ HR Manager / System Manager</p>
			<div class="ss-form-row">
				<label class="ss-field">
					<span class="ss-field-label">ชื่อแม่แบบ<em>*</em></span>
					<input v-model="form.title" class="ss-input" :disabled="!can_write" placeholder="เช่น สัญญาจ้างพนักงานไซต์งาน" />
				</label>
				<label class="ss-field">
					<span class="ss-field-label">บริษัท</span>
					<SelectBox v-model="form.company" :options="companies" label="บริษัท" :disabled="!can_write" />
				</label>
			</div>
			<div class="ss-form-row">
				<label class="ss-field">
					<span class="ss-field-label">ชื่อเอกสาร</span>
					<input v-model="form.heading" class="ss-input" :disabled="!can_write" placeholder="สัญญาจ้างพนักงาน" />
				</label>
				<label class="ss-field">
					<span class="ss-field-label">ผู้ลงนามฝ่ายนายจ้าง</span>
					<input v-model="form.employer_signer" class="ss-input" :disabled="!can_write" placeholder="ว่าง = เว้นให้เขียน" />
				</label>
			</div>
			<div class="ect-toggles">
				<label v-for="t in TOGGLES" :key="t.key" class="ss-toggle" :class="{ 'is-on': form[t.key], 'is-readonly': !can_write }">
					<input v-model="form[t.key]" type="checkbox" :true-value="1" :false-value="0" :disabled="!can_write" />
					<span class="ss-toggle-track"><span></span></span>
					<span><b>{{ t.label }}</b><small>{{ t.hint }}</small></span>
				</label>
			</div>
			<!-- หน้ากระดาษ: ฟอนต์ ขนาด ระยะบรรทัด ขอบ (มม.) ย่อหน้า (contract_terms.LAYOUT) -->
			<details class="ect-layout" open>
				<summary>หน้ากระดาษและตัวอักษร</summary>
				<div class="ect-grid">
					<label class="ss-field ect-wide">
						<span class="ss-field-label">ฟอนต์</span>
						<SelectBox :model-value="form.layout.font" :options="fonts" label="ฟอนต์" :disabled="!can_write" @update:model-value="set_font" />
					</label>
					<label class="ss-field">
						<span class="ss-field-label">ขนาด (pt)</span>
						<input v-model.number="form.layout.font_size" class="ss-input" type="number" min="8" max="24" step="0.5" :disabled="!can_write" />
					</label>
					<label class="ss-field">
						<span class="ss-field-label">ระยะบรรทัด</span>
						<input v-model.number="form.layout.line_height" class="ss-input" type="number" min="1" max="2.5" step="0.05" :disabled="!can_write" />
					</label>
				</div>
				<div class="ect-grid ect-grid--4">
					<label v-for="m in MARGINS" :key="m.key" class="ss-field">
						<span class="ss-field-label">ขอบ{{ m.label }} (มม.)</span>
						<input v-model.number="form.layout[m.key]" class="ss-input" type="number" min="0" max="60" step="1" :disabled="!can_write" />
					</label>
				</div>
				<div class="ect-grid">
					<label class="ss-field ect-wide">
						<span class="ss-field-label">การย่อหน้า (ปุ่มเยื้องในช่องเนื้อหา)</span>
						<SelectBox v-model="form.layout.indent_style" :options="indents" label="การย่อหน้า" :disabled="!can_write" />
					</label>
					<label class="ss-field">
						<span class="ss-field-label">ระยะต่อระดับ (ซม.)</span>
						<input v-model.number="form.layout.indent_cm" class="ss-input" type="number" min="0" max="5" step="0.25" :disabled="!can_write" />
					</label>
					<button v-if="can_write" type="button" class="ss-link ect-reset" @click="reset_layout">ค่ามาตรฐานหนังสือราชการ</button>
				</div>
				<div class="ect-toggles ect-toggles--2">
					<label v-for="t in PAGE_TOGGLES" :key="t.key" class="ss-toggle" :class="{ 'is-on': form.layout[t.key], 'is-readonly': !can_write }">
						<input v-model="form.layout[t.key]" type="checkbox" :true-value="1" :false-value="0" :disabled="!can_write" />
						<span class="ss-toggle-track"><span></span></span>
						<span><b>{{ t.label }}</b><small>{{ t.hint }}</small></span>
					</label>
				</div>
			</details>
			<TermsEditor v-model="form.terms" :variables="variables" :disabled="!can_write" :indent_style="form.layout.indent_style" />
		</div>

		<aside class="ect-side">
			<div class="ect-side-head">
				<b>ตัวอย่าง</b>
				<Picker
					v-model="sample_employee"
					label=""
					placeholder="ค่าตัวอย่าง"
					:display_value="sample_label"
					:remote_fn="(q) => call('consbiz.hr_docs.search', { doctype: 'Employee', txt: q })"
					clearable
					@select="(o) => (sample_label = o?.label || '')"
				/>
			</div>
			<ContractPreview v-if="form" :data="preview_data" />
		</aside>
	</div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import Icon from "../Icon.vue";
import Picker from "../Picker.vue";
import SelectBox from "../SelectBox.vue";
import Skeleton from "../Skeleton.vue";
import TermsEditor from "../contract/TermsEditor.vue";
import ContractPreview from "../contract/ContractPreview.vue";
import { boot, call, post, show_error, toast } from "../../api.js";

const API = "consbiz.contract_terms.";
const TOGGLES = [
	{ key: "is_default", label: "แม่แบบเริ่มต้น", hint: "สัญญาใหม่ของบริษัทนี้ใช้แม่แบบนี้ก่อน" },
	{ key: "witnesses", label: "มีช่องพยาน 2 คน", hint: "ท้ายสัญญา" },
	{ key: "disabled", label: "ปิดใช้งาน", hint: "ไม่ให้เลือกในสัญญาใหม่" },
];
const PAGE_TOGGLES = [
	{ key: "letterhead", label: "หัวกระดาษบริษัท", hint: "โลโก้ ชื่อ ที่อยู่ เลขผู้เสียภาษี โทร อีเมล ทุกหน้า (ข้อมูลบริษัท)" },
	{ key: "footer_sign", label: "ลงชื่อท้ายกระดาษ", hint: "ลูกจ้างทุกหน้า นายจ้าง/พยานเฉพาะหน้าสุดท้าย (ปิด = ทุกคนลงชื่อท้ายเนื้อหา)" },
];
const FIELDS = ["name", "modified", "title", "company", "is_default", "disabled", "heading", "employer_signer", "witnesses", "description", "terms", "layout"];
const MARGINS = [
	{ key: "margin_top", label: "บน" },
	{ key: "margin_bottom", label: "ล่าง" },
	{ key: "margin_left", label: "ซ้าย" },
	{ key: "margin_right", label: "ขวา" },
];
const companies = [{ value: "", label: "ทุกบริษัท" }, ...(boot.companies || []).map((c) => ({ value: c.name, label: c.name }))];

const templates = ref([]);
const variables = ref([]);
const fonts = ref([]);
const indents = ref([]);
const layout_default = ref({});
const parse_layout = (v) => ({ ...layout_default.value, ...(typeof v === "string" ? JSON.parse(v || "{}") : v || {}) });
const can_write = ref(false);
const form = ref(null);
const saved = ref("");
const busy = ref(false);
const sample_employee = ref(null);
const sample_label = ref("");

const snapshot = () => JSON.stringify(Object.fromEntries(FIELDS.map((f) => [f, form.value?.[f] ?? null])));
const dirty = computed(() => !!form.value && snapshot() !== saved.value);
const preview_data = computed(() => ({
	sample: true,
	employee: sample_employee.value || null,
	company: form.value?.company || null,
	heading: form.value?.heading,
	employer_signer: form.value?.employer_signer,
	witnesses: form.value?.witnesses,
	terms: form.value?.terms,
	layout: form.value?.layout,
}));
// เปลี่ยนฟอนต์ = ขนาด/ระยะบรรทัดตั้งต้นของฟอนต์นั้น (Sarabun 16pt, Noto Sans Thai 11pt)
function set_font(value) {
	const f = fonts.value.find((x) => x.value === value);
	Object.assign(form.value.layout, { font: value, ...(f ? { font_size: f.size, line_height: f.line } : {}) });
}
// ระเบียบงานสารบรรณ: Sarabun 16pt ขอบบน 2.5 ซม. ซ้าย 3 ซม. ขวา/ล่าง 2 ซม. ย่อหน้าบรรทัดแรก
const reset_layout = () => (form.value.layout = { ...layout_default.value });

async function load(select = null) {
	try {
		const res = await call(`${API}get_templates`);
		templates.value = res.templates;
		variables.value = res.variables;
		can_write.value = res.can_write;
		fonts.value = res.fonts;
		indents.value = res.indents;
		layout_default.value = res.layout_default;
		const name = select || form.value?.name || res.templates[0]?.name;
		if (name) await open(name, true);
		else create();
	} catch (e) {
		show_error(e);
	}
}

function confirm_leave() {
	return !dirty.value || window.confirm("ยังไม่ได้บันทึกแม่แบบนี้ ทิ้งที่แก้ไว้?");
}

async function open(name, force = false) {
	if (!force && (form.value?.name === name || !confirm_leave())) return;
	try {
		const t = await call(`${API}get_template`, { name });
		form.value = Object.fromEntries(FIELDS.map((f) => [f, t[f] ?? (f === "company" ? "" : null)]));
		form.value.layout = parse_layout(t.layout);
		form.value.modified = String(t.modified);
		saved.value = snapshot();
	} catch (e) {
		show_error(e);
	}
}

function create(base = null) {
	if (!base && !confirm_leave()) return;
	form.value = {
		name: null,
		modified: null,
		title: base ? `${base.title} (สำเนา)` : "",
		company: base?.company || "",
		is_default: 0,
		disabled: 0,
		heading: base?.heading || "สัญญาจ้างพนักงาน",
		employer_signer: base?.employer_signer || "",
		witnesses: base?.witnesses || 0,
		description: base?.description || "",
		terms: base?.terms || "",
		layout: parse_layout(base?.layout),
	};
	saved.value = "";
}
const duplicate = () => create({ ...form.value });

async function save() {
	busy.value = true;
	try {
		const t = await post(`${API}save_template`, { data: JSON.stringify(form.value) });
		toast("บันทึกแม่แบบแล้ว", "success");
		await load(t.name);
	} catch (e) {
		show_error(e);
	} finally {
		busy.value = false;
	}
}

async function remove() {
	if (!window.confirm(`ลบแม่แบบ ${form.value.title}?`)) return;
	busy.value = true;
	try {
		await post(`${API}delete_template`, { name: form.value.name });
		form.value = null;
		await load();
	} catch (e) {
		show_error(e);
	} finally {
		busy.value = false;
	}
}

onMounted(() => load());
</script>

<style scoped>
.ect {
	display: grid;
	grid-template-columns: 200px minmax(0, 1fr) minmax(360px, 42%);
	flex: 1;
	min-width: 0;
	min-height: 0;
}
.ect-list {
	display: flex;
	flex-direction: column;
	gap: 4px;
	padding: 12px 8px;
	border-right: 1px solid var(--ss-border);
	overflow-y: auto;
}
.ect-item {
	display: flex;
	flex-direction: column;
	gap: 3px;
	padding: 8px 10px;
	border: 0;
	border-radius: 10px;
	background: transparent;
	text-align: left;
	cursor: pointer;
}
.ect-item b { font-weight: 600; font-size: var(--ss-fs); }
.ect-item small { display: flex; flex-wrap: wrap; align-items: center; gap: 4px; color: var(--ss-muted); font-size: var(--ss-fs-sm); }
.ect-item.is-active { background: var(--ss-brand-soft); }
.ect-item.is-off b { color: var(--ss-muted); }
.ect-new { margin-top: 6px; justify-content: center; }
.ect-main {
	display: flex;
	flex-direction: column;
	gap: 12px;
	min-width: 0;
	padding: 14px 18px 18px;
	overflow-y: auto;
}
.ect-head { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.ect-head h2 { margin: 0; font-size: var(--ss-fs-xl); font-weight: 650; }
.ect-actions { display: flex; gap: 6px; }
.ect-note { margin: 0; font-size: var(--ss-fs-sm); }
.ect-layout { border: 1px solid var(--ss-border); border-radius: 12px; padding: 8px 12px 12px; }
.ect-layout summary { cursor: pointer; font-weight: 600; padding: 4px 0; }
.ect-grid { display: grid; grid-template-columns: 2fr 1fr 1fr; gap: 10px; align-items: end; margin-top: 8px; }
.ect-grid--4 { grid-template-columns: repeat(4, minmax(0, 1fr)); }
.ect-reset { grid-column: 1 / -1; justify-self: start; font-size: var(--ss-fs-sm); }
.ect-toggles--2 { grid-template-columns: repeat(2, minmax(0, 1fr)) !important; margin-top: 10px; }
.ect-toggles { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; }
.ect-side {
	display: flex;
	flex-direction: column;
	gap: 8px;
	min-height: 0;
	padding: 12px;
	border-left: 1px solid var(--ss-border);
	background: var(--ss-surface-2);
}
.ect-side-head { display: flex; align-items: center; gap: 10px; }
.ect-side-head :deep(.ss-picker-wrap) { flex: 1; }
.ect-side .ec-preview { flex: 1; }
@media (max-width: 1100px) {
	.ect { grid-template-columns: 180px minmax(0, 1fr); }
	.ect-side { grid-column: 1 / -1; border-left: 0; border-top: 1px solid var(--ss-border); min-height: 70dvh; }
	.ect-toggles { grid-template-columns: minmax(0, 1fr); }
}
@media (max-width: 767px) {
	.ect { display: flex; flex-direction: column; overflow-y: auto; }
	.ect-list { flex-direction: row; overflow-x: auto; border-right: 0; border-bottom: 1px solid var(--ss-border); }
	.ect-item { flex: none; }
	.ect-main { overflow: visible; }
}
</style>
