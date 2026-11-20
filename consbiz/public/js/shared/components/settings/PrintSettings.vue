<!-- ตั้งค่าแบบฟอร์มพิมพ์ของหมวด (ตกลง 2026-11-18, หมวดจัดซื้อ เมนู ⋯ > ตั้งค่า) API consbiz/print_settings.py
     แถวละ 1 เอกสาร: ชื่อเอกสาร + แบบที่ใช้อยู่ (ซ้าย) / ตัวเลือกแบบฟอร์ม (ขวา) แบบเดียวกับหน้าตั้งค่าบุคคล
     ใช้กับปุ่มพิมพ์ในแอปเท่านั้น ไม่เปลี่ยนแบบเริ่มต้นของระบบเต็ม แก้ได้เฉพาะ Purchase Manager / System Manager -->
<template>
	<div class="ss-settings-form">
		<div class="ss-settings-form-inner prs">
			<header class="prs-head">
				<h2>แบบฟอร์มพิมพ์</h2>
				<p>เลือกแบบฟอร์มที่ใช้ตอนกดพิมพ์/PDF ของแต่ละเอกสารในแอป (ไม่เปลี่ยนแบบเริ่มต้นของระบบเต็ม)</p>
			</header>
			<Skeleton v-if="!data" :rows="3" />
			<template v-else>
				<p v-if="!data.can_edit" class="prs-note">แก้ได้เฉพาะ Purchase Manager / System Manager</p>
				<div v-for="d in data.docs" :key="d.doctype" class="prs-row">
					<div class="prs-label">
						<b>{{ d.label }}</b>
						<small>
							ใช้อยู่: {{ label_of(d, d.current) }}
							<span v-if="kind_of(d, d.current)" class="ss-tag">{{ kind_of(d, d.current) }}</span>
							<template v-if="!d.chosen"> (ค่าเริ่มต้น)</template>
						</small>
					</div>
					<div class="prs-control">
						<SelectBox
							:model-value="d.chosen || ''"
							:label="`แบบฟอร์ม${d.label}`"
							:options="options_of(d)"
							:disabled="!data.can_edit || busy === d.doctype"
							@update:model-value="(v) => save(d, v)"
						/>
					</div>
				</div>
				<p class="prs-note prs-foot">
					รูปแบบ HTML: ตัวอย่างก่อนพิมพ์คมชัดและแบ่งหน้าตรงกับ PDF, พิมพ์ต้นฉบับ/สำเนาได้ · Print Designer: แก้หน้าตาเองในระบบเต็ม
				</p>
			</template>
		</div>
	</div>
</template>

<script setup>
import { ref } from "vue";
import Skeleton from "../Skeleton.vue";
import SelectBox from "../SelectBox.vue";
import { call, post, show_error, toast } from "../../api.js";

const props = defineProps({ section: { type: String, default: "buy" } });

const data = ref(null);
const busy = ref(null);

const find = (d, name) => d.formats.find((f) => f.value === name);
const label_of = (d, name) => (name ? find(d, name)?.label || name : "ไม่มีแบบฟอร์ม");
const kind_of = (d, name) => (name ? find(d, name)?.kind || "" : "");
const options_of = (d) => [
	{ value: "", label: d.default ? `ค่าเริ่มต้น (${d.default})` : "ค่าเริ่มต้น (แบบชื่อเดียวกับเอกสาร)" },
	...d.formats.map((f) => ({ value: f.value, label: f.label, description: f.kind })),
];

async function load() {
	try {
		data.value = await call("consbiz.print_settings.get_settings", { section: props.section });
	} catch (error) {
		show_error(error);
	}
}

async function save(d, value) {
	if ((d.chosen || "") === (value || "")) return;
	busy.value = d.doctype;
	try {
		data.value = await post("consbiz.print_settings.set_format", {
			section: props.section,
			doctype: d.doctype,
			print_format: value || null,
		});
		toast(`บันทึกแบบฟอร์ม${d.label}แล้ว`, "success");
	} catch (error) {
		show_error(error);
	} finally {
		busy.value = null;
	}
}

load();
</script>

<style scoped>
.prs-head h2 { margin: 0; font-size: var(--ss-fs-xl); font-weight: 650; }
.prs-head p { margin: 4px 0 12px; color: var(--ss-muted); font-size: var(--ss-fs); }
.prs-note { margin: 0 0 8px; color: var(--ss-muted); font-size: var(--ss-fs-sm); }
.prs-foot { margin-top: 14px; }
.prs-row {
	display: flex;
	align-items: center;
	gap: 14px;
	padding: 14px 0;
	border-bottom: 1px solid var(--ss-border);
}
.prs-label { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 3px; }
.prs-label b { font-weight: 600; }
.prs-label small { color: var(--ss-muted); font-size: var(--ss-fs-sm); line-height: 1.6; }
.prs-label .ss-tag { margin-left: 4px; }
.prs-control { flex: none; width: 300px; }
@media (max-width: 640px) {
	.prs-row { flex-direction: column; align-items: stretch; }
	.prs-control { width: auto; }
}
</style>
