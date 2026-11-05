<template>
	<!-- ช่องเลือกของแอป (แทน <select> ของเบราว์เซอร์ที่หน้าตาไม่เข้ากับแอป)
	     variant: field = ช่องในฟอร์ม, cell = ช่องในตาราง (ไม่มีกรอบจนชี้/โฟกัส), tool = ปุ่มในแถบเครื่องมือ
	     คีย์บอร์ด: Enter/Space/↓ เปิด, ↑↓ เลื่อน, Enter เลือก, Esc ปิด, พิมพ์ตัวอักษรกระโดดไปรายการที่ขึ้นต้นด้วยตัวนั้น -->
	<button
		ref="trigger"
		type="button"
		class="ss-select"
		:class="[`ss-select--${variant}`, { 'is-open': open, 'is-empty': !current }]"
		:disabled="disabled"
		aria-haspopup="listbox"
		:aria-expanded="open"
		:aria-label="label"
		@click="toggle"
		@keydown="on_trigger_key"
	>
		<slot name="prefix"></slot>
		<span class="ss-select-value">{{ current ? current.label : placeholder }}</span>
		<Icon name="chevron-down" :size="variant === 'cell' ? 14 : 16" class="ss-select-arrow" />
	</button>
	<Teleport to="body">
		<Transition name="ss-pop-menu">
			<ul
				v-if="open"
				ref="menu"
				class="ss-select-menu"
				role="listbox"
				:style="menu_style"
				:aria-label="label"
				@keydown="on_menu_key"
			>
				<li
					v-for="(o, i) in options"
					:key="String(o.value)"
					role="option"
					:aria-selected="o.value === modelValue"
					:class="{ 'is-active': i === active, 'is-selected': o.value === modelValue }"
					@mousedown.prevent="choose(o)"
					@mouseenter="active = i"
				>
					<span class="ss-select-text">
						<span>{{ o.label }}</span>
						<small v-if="o.description">{{ o.description }}</small>
					</span>
					<Icon v-if="o.value === modelValue" name="check" :size="15" :stroke="2.6" />
				</li>
				<li v-if="!options.length" class="is-note">ไม่มีตัวเลือก</li>
			</ul>
		</Transition>
	</Teleport>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, ref } from "vue";
import Icon from "./Icon.vue";

const props = defineProps({
	modelValue: { type: [String, Number, Boolean], default: null },
	options: { type: Array, default: () => [] },
	placeholder: { type: String, default: "เลือก" },
	variant: { type: String, default: "field" },
	label: String,
	disabled: Boolean,
});
const emit = defineEmits(["update:modelValue", "change"]);

const trigger = ref(null);
const menu = ref(null);
const open = ref(false);
const active = ref(0);
const menu_style = ref({});

const current = computed(() => props.options.find((o) => o.value === props.modelValue));

// วางเมนูใต้ช่อง (ไม่พอ = เปิดขึ้นบน) กว้างอย่างน้อยเท่าช่อง
function place() {
	const box = trigger.value?.getBoundingClientRect();
	if (!box) return;
	const height = Math.min(320, props.options.length * 40 + 12);
	const below = window.innerHeight - box.bottom;
	const up = below < height + 12 && box.top > below;
	const width = Math.max(box.width, 180);
	const left = Math.min(box.left, window.innerWidth - width - 8);
	menu_style.value = {
		left: `${Math.max(8, left)}px`,
		minWidth: `${width}px`,
		maxWidth: `${Math.max(width, 360)}px`,
		...(up ? { bottom: `${window.innerHeight - box.top + 4}px` } : { top: `${box.bottom + 4}px` }),
	};
}

async function show() {
	if (props.disabled) return;
	active.value = Math.max(
		0,
		props.options.findIndex((o) => o.value === props.modelValue)
	);
	place();
	open.value = true;
	await nextTick();
	menu.value?.querySelector(".is-active")?.scrollIntoView({ block: "nearest" });
	window.addEventListener("pointerdown", outside, true);
	window.addEventListener("scroll", place, true);
	window.addEventListener("resize", place);
}

function hide(focus = true) {
	open.value = false;
	window.removeEventListener("pointerdown", outside, true);
	window.removeEventListener("scroll", place, true);
	window.removeEventListener("resize", place);
	if (focus) trigger.value?.focus();
}

const toggle = () => (open.value ? hide() : show());

function outside(event) {
	if (!menu.value?.contains(event.target) && !trigger.value?.contains(event.target)) hide(false);
}

function choose(option) {
	if (option.value !== props.modelValue) {
		emit("update:modelValue", option.value);
		emit("change", option.value);
	}
	hide();
}

function move(delta) {
	if (!props.options.length) return;
	active.value = (active.value + delta + props.options.length) % props.options.length;
	nextTick(() => menu.value?.querySelector(".is-active")?.scrollIntoView({ block: "nearest" }));
}

function jump(key) {
	const k = key.toLowerCase();
	const start = active.value + 1;
	const list = props.options;
	for (let n = 0; n < list.length; n++) {
		const i = (start + n) % list.length;
		if (String(list[i].label).toLowerCase().startsWith(k)) {
			active.value = i;
			return move(0);
		}
	}
}

function on_trigger_key(event) {
	if (!open.value && ["Enter", " ", "ArrowDown", "ArrowUp"].includes(event.key)) {
		event.preventDefault();
		return show();
	}
	if (open.value) on_menu_key(event);
}

function on_menu_key(event) {
	if (event.key === "ArrowDown") move(1);
	else if (event.key === "ArrowUp") move(-1);
	else if (event.key === "Enter" || event.key === " ")
		props.options[active.value] && choose(props.options[active.value]);
	else if (event.key === "Escape" || event.key === "Tab") return hide(event.key === "Escape");
	else if (event.key.length === 1) jump(event.key);
	else return;
	event.preventDefault();
}

onBeforeUnmount(() => hide(false));
</script>
