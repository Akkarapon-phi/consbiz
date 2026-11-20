<!-- ช่องเลือกแบบพิมพ์ค้นหาในช่อง (combobox, ตกลง 2026-11-18) ใช้แทน Picker (เปิด sheet) ในฟอร์มเอกสาร
     โฟกัส = แสดงรายการทันที พิมพ์ = ค้นหาทันที (ไม่ต้องกด Enter, รองรับคีย์บอร์ดไทยที่ยังไม่ยืนยันตัวอักษร)
     ↑↓ เลื่อน Enter เลือก Esc ปิด ออกจากช่องโดยไม่เลือก = คงค่าเดิม
     options คงที่ [{ value, label, description }] หรือ remote_fn(txt) => Promise<options> -->
<template>
	<div class="ss-field ss-combo" :class="{ 'is-open': open }">
		<span v-if="label" class="ss-field-label">{{ label }}<em v-if="required">*</em></span>
		<span class="ss-combo-box">
			<input
				ref="input"
				class="ss-input ss-combo-input"
				type="text"
				role="combobox"
				autocomplete="off"
				:aria-label="label"
				:aria-expanded="open"
				:placeholder="placeholder || 'พิมพ์เพื่อค้นหา'"
				:value="open ? txt : display"
				@focus="start"
				@input="on_input"
				@blur="close_soon"
				@keydown.down.prevent="move(1)"
				@keydown.up.prevent="move(-1)"
				@keydown.enter.prevent="choose(shown[active])"
				@keydown.esc.prevent="close"
			/>
			<button
				v-if="clearable && modelValue && !open"
				type="button"
				class="ss-combo-clear"
				aria-label="ล้างค่า"
				@mousedown.prevent="clear"
			>
				<Icon name="x" :size="13" :stroke="2.6" />
			</button>
			<Icon name="chevron-down" :size="15" class="ss-combo-caret" />
		</span>
		<Teleport to="#ss-layer">
			<ul
				v-if="open"
				ref="list"
				class="ss-typeahead-list ss-typeahead-list--fixed ss-combo-list"
				role="listbox"
				:style="list_style"
			>
				<li v-if="loading && !shown.length" class="is-note">กำลังค้นหา…</li>
				<li v-else-if="!shown.length" class="is-note">{{ empty_text || "ไม่พบรายการ" }}</li>
				<li
					v-for="(o, i) in shown"
					:key="o.value"
					role="option"
					:aria-selected="o.value === modelValue"
					:class="{ 'is-active': i === active, 'is-chosen': o.value === modelValue }"
					@mousedown.prevent="choose(o)"
					@mouseenter="active = i"
				>
					<span>
						<b>{{ o.label }}</b>
						<small v-if="o.description">{{ o.description }}</small>
					</span>
					<Icon v-if="o.value === modelValue" name="check" :size="15" :stroke="2.6" />
				</li>
			</ul>
		</Teleport>
	</div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from "vue";
import Icon from "./Icon.vue";

const props = defineProps({
	modelValue: { type: [String, Number], default: null },
	label: String,
	placeholder: String,
	options: { type: Array, default: () => [] },
	remote_fn: Function,
	display_value: String,
	required: Boolean,
	clearable: Boolean,
	empty_text: String,
});
const emit = defineEmits(["update:modelValue", "select"]);

const input = ref(null);
const list = ref(null);
const open = ref(false);
const txt = ref("");
const results = ref([]);
const loading = ref(false);
const active = ref(0);
const list_style = ref({});
const chosen = ref(null);

const shown = computed(() => {
	if (props.remote_fn) return results.value;
	const q = txt.value.trim().toLowerCase();
	const all = props.options;
	return (q ? all.filter((o) => `${o.label} ${o.value} ${o.description || ""}`.toLowerCase().includes(q)) : all).slice(0, 200);
});
const display = computed(() => {
	if (!props.modelValue) return "";
	if (props.display_value) return props.display_value;
	const found = props.options.find((o) => o.value === props.modelValue) || chosen.value;
	return found?.label || String(props.modelValue);
});

function place() {
	const r = input.value?.getBoundingClientRect();
	if (!r) return;
	const below = window.innerHeight - r.bottom;
	const up = below < 240 && r.top > below;
	list_style.value = {
		left: `${r.left}px`,
		width: `${Math.max(r.width, 260)}px`,
		...(up ? { bottom: `${window.innerHeight - r.top + 4}px`, top: "auto" } : { top: `${r.bottom + 4}px` }),
	};
}

let timer = null;
let request = 0;
function search() {
	if (!props.remote_fn) return;
	clearTimeout(timer);
	timer = setTimeout(async () => {
		const id = ++request;
		loading.value = true;
		try {
			const rows = await props.remote_fn(txt.value);
			if (id === request) results.value = rows || [];
		} finally {
			if (id === request) loading.value = false;
		}
	}, 180);
}

function start() {
	txt.value = "";
	active.value = 0;
	place();
	open.value = true;
	search();
	nextTick(() => input.value?.select());
}
// อ่านค่าจากช่องตรงๆ (v-model รอจนคีย์บอร์ดภาษาไทย/IME ยืนยันตัวอักษร ทำให้ไม่ค้นหาจนกด Enter)
function on_input(event) {
	txt.value = event.target.value;
	active.value = 0;
	if (!open.value) {
		place();
		open.value = true;
	}
	search();
}
function move(delta) {
	if (!open.value) return start();
	const n = shown.value.length;
	if (n) active.value = (active.value + delta + n) % n;
}
function choose(option) {
	if (!option) return;
	chosen.value = option;
	emit("update:modelValue", option.value);
	emit("select", option);
	close();
}
function clear() {
	chosen.value = null;
	emit("update:modelValue", null);
	emit("select", null);
}
function close() {
	open.value = false;
	txt.value = "";
}
function close_soon() {
	setTimeout(close, 150);
}

// เลื่อนหน้า (รวม iOS เลื่อนให้ช่องพ้นคีย์บอร์ด) = ย้ายรายการตามช่อง ยกเว้นเลื่อนในรายการเอง
const on_scroll = (e) => {
	if (open.value && !list.value?.contains(e.target)) place();
};
onMounted(() => window.addEventListener("scroll", on_scroll, true));
onBeforeUnmount(() => window.removeEventListener("scroll", on_scroll, true));
</script>
