<template>
	<div class="ss-picker-wrap">
		<button
			type="button"
			class="ss-field ss-picker"
			:class="{ 'is-empty': !modelValue }"
			@click="open = true"
		>
			<span class="ss-field-label">{{ label }}<em v-if="required">*</em></span>
			<span class="ss-picker-value">
				<span>{{ display || placeholder || "เลือก" }}</span>
				<Icon name="chevron-down" :size="18" />
			</span>
		</button>

		<Sheet :open="open" :title="label" full @close="open = false">
			<div class="ss-search">
				<Icon name="search" :size="18" />
				<input
					ref="input"
					v-model="txt"
					type="search"
					:placeholder="`ค้นหา${label}`"
					@input="search_remote"
				/>
			</div>
			<div class="ss-options">
				<button
					v-for="option in shown"
					:key="option.value"
					type="button"
					class="ss-option"
					:class="{ 'is-active': option.value === modelValue }"
					@click="choose(option)"
				>
					<span class="ss-option-main">
						<span class="ss-option-label">{{ option.label }}</span>
						<span v-if="option.description" class="ss-option-desc">{{ option.description }}</span>
					</span>
					<Icon v-if="option.value === modelValue" name="check" :size="18" />
				</button>
				<button
					v-if="allow_text && txt.trim()"
					type="button"
					class="ss-option"
					@click="choose({ value: txt.trim(), label: txt.trim() })"
				>
					<span class="ss-option-main">
						<span class="ss-option-label">ใช้ “{{ txt.trim() }}”</span>
					</span>
				</button>
				<div v-if="loading" class="ss-options-note">กำลังค้นหา…</div>
				<div v-else-if="!shown.length && !allow_text" class="ss-options-note">ไม่พบรายการ</div>
			</div>
			<template v-if="modelValue && clearable" #footer>
				<button
					type="button"
					class="ss-btn ss-btn--ghost ss-btn--block"
					@click="choose({ value: null, label: '' })"
				>
					ล้างค่า
				</button>
			</template>
		</Sheet>
	</div>
</template>

<script setup>
// ช่องเลือกแบบเปิด sheet ค้นหา: options คงที่ หรือ remote = ชื่อ DocType (store_app.search)
import { computed, nextTick, ref, watch } from "vue";
import Icon from "./Icon.vue";
import Sheet from "./Sheet.vue";
import { call } from "../api.js";

const props = defineProps({
	modelValue: { type: [String, Number], default: null },
	label: { type: String, default: "" },
	placeholder: String,
	options: { type: Array, default: () => [] },
	remote: String,
	display_value: String,
	required: Boolean,
	clearable: Boolean,
	allow_text: Boolean,
});
const emit = defineEmits(["update:modelValue", "select"]);

const open = ref(false);
const txt = ref("");
const loading = ref(false);
const results = ref([]);
const input = ref(null);
const chosen = ref(null);

const source = computed(() => (props.remote ? results.value : props.options));
const shown = computed(() => {
	if (props.remote) return results.value;
	const q = txt.value.trim().toLowerCase();
	const list = q
		? props.options.filter((o) =>
				`${o.label} ${o.value} ${o.description || ""}`.toLowerCase().includes(q)
		  )
		: props.options;
	return list.slice(0, 200);
});
const display = computed(() => {
	if (!props.modelValue) return "";
	if (props.display_value) return props.display_value;
	const found = source.value.find((o) => o.value === props.modelValue) || chosen.value;
	return found?.label || props.modelValue;
});

let timer = null;
function search_remote() {
	if (!props.remote) return;
	clearTimeout(timer);
	timer = setTimeout(async () => {
		loading.value = true;
		try {
			results.value = await call("search", { doctype: props.remote, txt: txt.value });
		} finally {
			loading.value = false;
		}
	}, 220);
}

watch(open, async (value) => {
	if (!value) return;
	txt.value = "";
	if (props.remote) search_remote();
	await nextTick();
	// มือถือ: โฟกัสหลัง sheet เลื่อนขึ้นเสร็จ ไม่งั้นคีย์บอร์ดดันหน้ากระตุก
	setTimeout(() => input.value?.focus(), 320);
});

function choose(option) {
	chosen.value = option;
	emit("update:modelValue", option.value);
	emit("select", option);
	open.value = false;
}
</script>
