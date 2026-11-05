<!-- แก้ข้อความแบบ Text Editor (ตัวหนา/เอียง/ขีดเส้นใต้/ลำดับเลข/หัวข้อย่อย) ให้ข้อความจากระบบเต็มไม่เสียรูปแบบ
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
		</div>
		<div
			ref="area"
			class="ss-rich ss-rich-area"
			contenteditable="true"
			role="textbox"
			aria-multiline="true"
			:aria-label="label"
			:data-placeholder="placeholder"
			@input="emit_value"
			@focus="focused = true"
			@blur="on_blur"
			@paste="on_paste"
		></div>
	</div>
</template>

<script setup>
import { onMounted, ref, watch } from "vue";
import Icon from "./Icon.vue";
import { sanitize_html } from "../api.js";

const props = defineProps({
	modelValue: { type: String, default: "" },
	label: String,
	placeholder: { type: String, default: "" },
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
