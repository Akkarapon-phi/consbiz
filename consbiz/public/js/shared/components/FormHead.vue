<!-- หัวฟอร์มกลางของทุกหน้าเอกสาร (ตกลง 2026-11-17) แก้ที่นี่ที่เดียวมีผลทุกหน้า
     แถว = แท็บหัวข้อของฟอร์ม (tabs + v-model) → [พิมพ์] → [⋯ เมนู] → ปุ่มตามขั้นตอน (ปุ่มหลักขวาสุด)
     ปุ่มตามขั้นตอน (actions) แสดงเฉพาะขั้นที่ทำได้ตอนนี้ ไม่ขึ้นพร้อมกัน: ใช้ step_actions() ใน shared/form_actions.js
       [{ key, label, icon?, tone: "primary" | "soft" | "danger", onClick | href, disabled?, title? }]
     เมนู ⋯ (menu) = คำสั่งที่ไม่ใช่ขั้นตอน (ทำซ้ำ โหลดใหม่ เปิดในระบบเต็ม ลบ): ใช้ doc_menu()
       [{ key, label, icon?, danger?, onClick | href }] รายการ danger แยกกลุ่มไว้ท้ายเมนู
     มือถือ (< 768): ปุ่มย้ายลงแถบล่าง (พิมพ์ซ้ายสุด ปุ่มหลักขวาสุด) หัวเหลือแท็บ
     slot summary = ข้อความสรุปข้างปุ่ม (เช่น รับ 3 รายการ)
     slot lead = แทนแท็บ (เช่น ชื่อขั้นของฟอร์มทีละขั้น), slot tools = ปุ่มพิเศษของหน้าก่อนปุ่มพิมพ์ (จอ ≥ 768) -->
<template>
	<div class="ss-list-head ss-form-head" :class="{ 'ss-list-head--many': many, 'is-empty': head_empty }">
		<StatusTabs
			v-if="tabs && tabs.length"
			:model-value="modelValue"
			:options="tabs"
			@update:model-value="$emit('update:modelValue', $event)"
		/>
		<slot name="lead" />
		<div v-if="wide && has_tools" class="ss-list-tools">
			<slot name="tools" />
			<span v-if="$slots.summary" class="ss-bar-summary"><slot name="summary" /></span>
			<button
				v-if="onPrint"
				type="button"
				class="ss-icon-btn"
				title="PDF / พิมพ์ / แชร์"
				aria-label="พิมพ์"
				@click="onPrint"
			>
				<Icon name="printer" :size="17" />
			</button>
			<button
				v-if="menu_items.length"
				ref="more_wide"
				type="button"
				class="ss-icon-btn ss-form-more"
				:class="{ 'is-on': menu_open }"
				aria-label="คำสั่งอื่น"
				title="คำสั่งอื่น"
				aria-haspopup="menu"
				:aria-expanded="menu_open"
				@click="toggle_menu"
			>
				<Icon name="more" :size="18" :stroke="2.6" />
			</button>
			<FormAction v-for="a in shown" :key="a.key" :action="a" :busy="busy" />
		</div>
		<slot />

		<Teleport v-if="!wide && has_bar" to="#ss-layer">
			<Transition name="ss-bar" appear>
				<div class="ss-bottom-bar ss-docview-bar ss-form-bar">
					<button
						v-if="onPrint"
						type="button"
						class="ss-btn ss-btn--ghost ss-btn--lg ss-docview-print"
						title="PDF / พิมพ์ / แชร์"
						@click="onPrint"
					>
						<Icon name="printer" :size="17" />
						<span class="ss-docview-print-label">พิมพ์</span>
					</button>
					<button
						v-if="menu_items.length"
						ref="more_bar"
						type="button"
						class="ss-btn ss-btn--ghost ss-btn--lg ss-form-more"
						:class="{ 'ss-docview-print': !onPrint }"
						aria-label="คำสั่งอื่น"
						aria-haspopup="menu"
						:aria-expanded="menu_open"
						@click="toggle_menu"
					>
						<Icon name="more" :size="18" :stroke="2.6" />
					</button>
					<div v-if="$slots.summary" class="ss-bar-summary"><slot name="summary" /></div>
					<FormAction
						v-for="(a, i) in shown"
						:key="a.key"
						:action="a"
						:busy="busy"
						large
						:class="{ 'ss-grow': i === shown.length - 1 }"
					/>
				</div>
			</Transition>
		</Teleport>

		<!-- เมนูอยู่ชั้นบนสุด: หัวฟอร์มติดจอ (sticky + backdrop-filter) ทำให้ position: fixed เพี้ยน -->
		<Teleport to="#ss-layer">
			<DockMenu
				:open="menu_open"
				:anchor="wide ? more_wide : more_bar"
				:groups="menu_groups"
				:placement="wide ? 'below' : 'above'"
				@close="menu_open = false"
			/>
		</Teleport>
	</div>
</template>

<script setup>
import { computed, defineComponent, h, ref, useSlots } from "vue";
import Icon from "./Icon.vue";
import StatusTabs from "./StatusTabs.vue";
import DockMenu from "./DockMenu.vue";
import { use_wide } from "../table.js";

const props = defineProps({
	modelValue: [String, Number],
	tabs: Array,
	many: Boolean,
	actions: { type: Array, default: () => [] },
	menu: { type: Array, default: () => [] },
	busy: Boolean,
	onPrint: Function,
});
defineEmits(["update:modelValue"]);

const slots = useSlots();
const wide = use_wide();
const more_wide = ref(null);
const more_bar = ref(null);
const menu_open = ref(false);

const shown = computed(() => props.actions.filter(Boolean));
const menu_items = computed(() => props.menu.filter(Boolean));
const has_tools = computed(
	() => !!(slots.tools || props.onPrint || menu_items.value.length || shown.value.length)
);
const head_empty = computed(
	() => !props.tabs?.length && !slots.lead && !slots.default && !(wide.value && has_tools.value)
);
const has_bar = computed(() => !!(props.onPrint || menu_items.value.length || shown.value.length));

const menu_groups = computed(() => {
	const item = (m) => ({
		key: m.key,
		label: m.label,
		icon: m.icon,
		href: m.href,
		danger: m.danger,
		onclick: m.onClick,
	});
	const normal = menu_items.value.filter((m) => !m.danger).map(item);
	const danger = menu_items.value.filter((m) => m.danger).map(item);
	return [normal, danger].filter((g) => g.length).map((items) => ({ items }));
});

function toggle_menu() {
	menu_open.value = !menu_open.value;
}

// ปุ่ม 1 ปุ่มของขั้นตอน (ปุ่มหรือลิงก์)
const FormAction = defineComponent({
	props: { action: Object, busy: Boolean, large: Boolean },
	setup(p) {
		return () => {
			const a = p.action;
			const cls = [
				"ss-btn",
				{
					primary: "ss-btn--primary",
					soft: "ss-btn--soft",
					danger: "ss-btn--ghost-danger",
				}[a.tone || "soft"],
				p.large ? "ss-btn--lg" : "ss-list-create",
			];
			const inner = [
				a.icon ? h(Icon, { name: a.icon, size: a.tone === "primary" ? 18 : 17 }) : null,
				h("span", a.label),
			];
			if (a.href) {
				return h("a", { class: cls, href: a.href, target: a.target || "_blank", title: a.title }, inner);
			}
			return h(
				"button",
				{
					type: "button",
					class: cls,
					disabled: a.disabled || (p.busy && !a.ignore_busy),
					title: a.title,
					onClick: a.onClick,
				},
				inner
			);
		};
	},
});
</script>
