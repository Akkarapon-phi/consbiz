<!-- แก้ข้อความแบบ Text Editor (ตัวหนา/เอียง/ขีดเส้นใต้/ลำดับเลข/หัวข้อย่อย) ให้ข้อความจากระบบเต็มไม่เสียรูปแบบ
     doc_tools = เพิ่มปุ่มเยื้อง/ลดเยื้อง (class ql-indent-N แบบ Quill) + slot tools ต่อท้ายแถบ (เช่น แทรกตัวแปรของสัญญาจ้าง)
     ref.insert(text) = แทรกข้อความตรงเคอร์เซอร์ล่าสุดในช่อง (ไม่มี = ท้ายข้อความ)
     ค่า = HTML ที่ผ่าน sanitize_html แล้ว ระบบเต็ม (Quill) เปิดต่อได้ปกติ -->
<template>
	<div class="ss-rich-editor" :class="{ 'is-focus': focused }">
		<div class="ss-rich-tools" role="toolbar" :aria-label="`จัดรูปแบบ ${label || ''}`">
			<button
				v-for="t in TOOLS"
				:key="t.cmd"
				type="button"
				class="ss-rich-tool"
				:title="t.title"
				:aria-label="t.title"
				@mousedown.prevent="run(t.cmd)"
			>
				<b v-if="t.text" :style="t.style">{{ t.text }}</b>
				<Icon v-else :name="t.icon" :size="16" />
			</button>
			<template v-if="doc_tools">
				<button type="button" class="ss-rich-tool" title="ลดการเยื้อง" aria-label="ลดการเยื้อง" @mousedown.prevent="indent(-1)">
					<Icon name="outdent" :size="16" />
				</button>
				<button type="button" class="ss-rich-tool" title="เยื้องเข้า (ข้อย่อย)" aria-label="เยื้องเข้า" @mousedown.prevent="indent(1)">
					<Icon name="indent" :size="16" />
				</button>
			</template>
			<slot name="tools" />
		</div>
		<div
			ref="area"
			class="ss-rich ss-rich-area"
			role="textbox"
			aria-multiline="true"
			:aria-label="label"
			:data-placeholder="placeholder"
			:contenteditable="disabled ? 'false' : 'true'"
			@input="emit_value"
			@focus="focused = true"
			@blur="on_blur"
			@paste="on_paste"
		></div>
	</div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from "vue";
import Icon from "./Icon.vue";
import { sanitize_html } from "../api.js";

const props = defineProps({
	modelValue: { type: String, default: "" },
	label: String,
	placeholder: { type: String, default: "" },
	doc_tools: Boolean,
	disabled: Boolean,
});
const emit = defineEmits(["update:modelValue"]);

const TOOLS = [
	{ cmd: "bold", title: "ตัวหนา", text: "B" },
	{ cmd: "italic", title: "ตัวเอียง", text: "I", style: "font-style: italic" },
	{ cmd: "underline", title: "ขีดเส้นใต้", text: "U", style: "text-decoration: underline" },
	{ cmd: "insertOrderedList", title: "ลำดับเลข", icon: "list-ordered" },
	{ cmd: "insertUnorderedList", title: "หัวข้อย่อย", icon: "list" },
];

const area = ref(null);
const focused = ref(false);
let last = null;

function load(html) {
	const clean = sanitize_html(html);
	if (area.value && clean !== last) {
		area.value.innerHTML = clean;
		last = clean;
	}
}

function emit_value() {
	last = sanitize_html(area.value.innerHTML);
	emit("update:modelValue", last);
}

function run(cmd) {
	area.value.focus();
	document.execCommand(cmd, false, null);
	emit_value();
}

// วางจากที่อื่น: เก็บเฉพาะแท็กที่ปลอดภัย
function on_paste(event) {
	const html = event.clipboardData?.getData("text/html");
	const text = event.clipboardData?.getData("text/plain");
	event.preventDefault();
	document.execCommand("insertHTML", false, html ? sanitize_html(html) : sanitize_html(text || ""));
	emit_value();
}

// ตำแหน่งเคอร์เซอร์ล่าสุดในช่อง (ปุ่ม/เมนูนอกช่องทำให้เสียโฟกัส แทรกตรงที่เดิม)
let range = null;
function remember() {
	const sel = window.getSelection();
	if (sel?.rangeCount && area.value?.contains(sel.anchorNode)) range = sel.getRangeAt(0).cloneRange();
}
document.addEventListener("selectionchange", remember);
onBeforeUnmount(() => document.removeEventListener("selectionchange", remember));

function restore() {
	area.value.focus();
	const sel = window.getSelection();
	sel.removeAllRanges();
	if (range && area.value.contains(range.startContainer)) sel.addRange(range);
	else {
		const end = document.createRange();
		end.selectNodeContents(area.value);
		end.collapse(false);
		sel.addRange(end);
	}
}

function insert(text) {
	if (props.disabled) return;
	restore();
	document.execCommand("insertText", false, text);
	emit_value();
}

// เยื้องย่อหน้าที่เคอร์เซอร์อยู่ (ql-indent-1..3)
function indent(step) {
	restore();
	let node = window.getSelection().anchorNode;
	while (node && node !== area.value && !(node.nodeType === 1 && /^(P|LI|DIV|H[1-4])$/.test(node.tagName))) node = node.parentNode;
	if (!node || node === area.value) {
		document.execCommand("formatBlock", false, "p");
		node = window.getSelection().anchorNode;
		while (node && node.nodeType !== 1) node = node.parentNode;
		if (!node || node === area.value) return;
	}
	const now = Number((node.className.match(/ql-indent-(\d)/) || [])[1] || 0);
	const next = Math.max(0, Math.min(3, now + step));
	node.classList.remove(`ql-indent-${now}`);
	if (next) node.classList.add(`ql-indent-${next}`);
	if (!node.className) node.removeAttribute("class");
	emit_value();
}

defineExpose({ insert });

function on_blur() {
	focused.value = false;
	emit_value();
}

onMounted(() => load(props.modelValue));
watch(
	() => props.modelValue,
	(value) => {
		if (!focused.value) load(value);
	}
);
</script>
