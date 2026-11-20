<!-- เนื้อหาสัญญาจ้าง (แม่แบบ / เฉพาะฉบับ, ตกลง 2026-11-18): RichEditor + ปุ่มเยื้อง + เมนู "แทรกข้อมูล" ตัวแปร {{ key }}
     ตัวแปรแทนค่าตอนพิมพ์/ตัวอย่างที่ server (consbiz/contract_terms.py VARIABLES) ข้อย่อย 1.1 ใช้ปุ่มเยื้อง (ql-indent-1) -->
<template>
	<div class="ec-editor" :class="`ec-editor--${indent_style}`">
		<RichEditor
			ref="editor"
			:model-value="modelValue"
			label="เนื้อหาสัญญา"
			placeholder="พิมพ์เนื้อหาสัญญา"
			doc_tools
			:disabled="disabled"
			@update:model-value="$emit('update:modelValue', $event)"
		>
			<template #tools>
				<button
					v-if="!disabled"
					ref="menu_btn"
					type="button"
					class="ss-rich-tool ec-insert"
					title="แทรกข้อมูลของสัญญา (แทนค่าตอนพิมพ์)"
					@mousedown.prevent="menu = !menu"
				>
					<Icon name="plus" :size="14" /><span>แทรกข้อมูล</span>
				</button>
			</template>
		</RichEditor>
		<DockMenu :open="menu" :anchor="menu_btn" :groups="groups" placement="below-start" @close="menu = false" />
	</div>
</template>

<script setup>
import { computed, ref } from "vue";
import Icon from "../Icon.vue";
import DockMenu from "../DockMenu.vue";
import RichEditor from "../RichEditor.vue";

const props = defineProps({
	modelValue: { type: String, default: "" },
	variables: { type: Array, default: () => [] },
	disabled: Boolean,
	// รูปแบบย่อหน้าของแม่แบบ (layout.indent_style) ช่องแก้แสดงแบบเดียวกับเอกสาร
	indent_style: { type: String, default: "first_line" },
});
defineEmits(["update:modelValue"]);

const editor = ref(null);
const menu_btn = ref(null);
const menu = ref(false);
const groups = computed(() => [
	{
		label: "แทรกตรงเคอร์เซอร์ (แทนค่าตอนพิมพ์)",
		items: props.variables.map((v) => ({
			key: v.key,
			label: v.label,
			sub: `{{ ${v.key} }}`,
			onclick: () => editor.value?.insert(`{{ ${v.key} }}`),
		})),
	},
]);
</script>
