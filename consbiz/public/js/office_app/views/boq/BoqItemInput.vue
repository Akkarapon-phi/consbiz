<!-- ช่องชื่อรายการของ BOQ: พิมพ์แล้วค้นหา BOQ Item (เลือก = @pick) ไม่เลือกก็ใช้ข้อความที่พิมพ์เป็นชื่อรายการได้
     คีย์บอร์ด: ↑↓ เลื่อน, Enter เลือก (ยังไม่ได้เลื่อน = ใช้ข้อความที่พิมพ์), Esc ปิด -->
<template>
	<input
		ref="input"
		class="ss-boq-input"
		:value="modelValue"
		:disabled="disabled"
		placeholder="พิมพ์ค้นหา หรือกรอกชื่อรายการ"
		role="combobox"
		aria-label="รายการ"
		aria-autocomplete="list"
		:aria-expanded="open"
		autocomplete="off"
		@input="on_input"
		@keydown="on_key"
		@blur="hide"
	/>
	<Teleport to="body">
		<Transition name="ss-pop-menu">
			<ul
				v-if="open"
				ref="menu"
				class="ss-select-menu ss-boq-combo"
				role="listbox"
				aria-label="BOQ Item"
				:style="menu_style"
			>
				<li
					v-for="(o, i) in options"
					:key="o.value"
					role="option"
					:aria-selected="i === active"
					:class="{ 'is-active': i === active }"
					@mousedown.prevent="choose(o)"
					@mouseenter="active = i"
				>
					<span class="ss-select-text">
						<span>{{ o.label }}</span>
						<small>{{ o.value }}<template v-if="o.uom"> · {{ o.uom }}</template></small>
						<RichText :html="o.description" :lines="2" class="ss-boq-desc" />
					</span>
				</li>
			</ul>
		</Transition>
	</Teleport>
</template>

<script setup>
import { nextTick, onBeforeUnmount, ref } from "vue";
import RichText from "../../../shared/components/RichText.vue";
import { show_error } from "../../../shared/api.js";

const props = defineProps({
	modelValue: { type: String, default: "" },
	search: { type: Function, required: true },
	disabled: Boolean,
});
const emit = defineEmits(["update:modelValue", "pick"]);

const DELAY = 180;
const input = ref(null);
const menu = ref(null);
const open = ref(false);
const options = ref([]);
const active = ref(-1);
const menu_style = ref({});
let timer = null;
let request = 0;

function place() {
	const box = input.value?.getBoundingClientRect();
	if (!box) return;
	const height = 320;
	const below = window.innerHeight - box.bottom;
	const up = below < height + 12 && box.top > below;
	const width = Math.max(box.width, 360);
	menu_style.value = {
		left: `${Math.max(8, Math.min(box.left, window.innerWidth - width - 8))}px`,
		width: `${width}px`,
		...(up ? { bottom: `${window.innerHeight - box.top + 4}px` } : { top: `${box.bottom + 4}px` }),
	};
}

function listen(on) {
	const method = on ? "addEventListener" : "removeEventListener";
	window[method]("scroll", place, true);
	window[method]("resize", place);
}

function show() {
	place();
	if (!open.value) listen(true);
	open.value = true;
}

// เพิ่มเลข request ด้วย คำตอบที่มาช้าจะได้ไม่เปิดเมนูอีกหลังปิดแล้ว
function hide() {
	clearTimeout(timer);
	request++;
	if (open.value) listen(false);
	open.value = false;
}

async function find(text) {
	const mine = ++request;
	let found;
	try {
		found = await props.search(text);
	} catch (error) {
		show_error(error);
		return;
	}
	if (mine !== request) return;
	options.value = found;
	active.value = -1;
	if (found.length) show();
	else hide();
}

function on_input(event) {
	const text = event.target.value;
	emit("update:modelValue", text);
	clearTimeout(timer);
	if (!text.trim()) return hide();
	timer = setTimeout(() => find(text.trim()), DELAY);
}

function choose(option) {
	emit("pick", option);
	hide();
}

function move(step) {
	const count = options.value.length;
	active.value = (active.value + step + count) % count;
	nextTick(() => menu.value?.querySelector(".is-active")?.scrollIntoView({ block: "nearest" }));
}

function on_key(event) {
	if (!open.value) return;
	if (event.key === "ArrowDown") move(1);
	else if (event.key === "ArrowUp") move(active.value < 0 ? 0 : -1);
	else if (event.key === "Enter") {
		if (active.value >= 0) choose(options.value[active.value]);
		else hide();
	} else if (event.key === "Escape") hide();
	else {
		if (event.key === "Tab") hide();
		return;
	}
	event.preventDefault();
}

onBeforeUnmount(hide);
</script>
