<!-- เมนูของหมวดเป็นแท็บบนแถบบน (จอ ≥768): ใน TopBar แทนชื่อหน้า (หน้าเมนูหลัก)
     ข้อมูลเมนู/ตัวเลข/เมนูที่เลือกจาก AppShell (provide "section_nav") มือถือใช้แถบเมนูล่างของ AppShell แทน
     ที่ไม่พอ (2026-11-16): เมนูที่ล้นซ่อนแล้วรวมไว้ที่ปุ่ม "…" ท้ายแถบ (DockMenu below) เมนูที่เลือกอยู่แสดงเสมอ
     กรอบนอก .ss-sectabs-wrap กินที่ว่างของแถบบน (วัดที่ว่างจากตัวนี้) ส่วน nav กว้างเท่าเมนูที่แสดง
     วัดความกว้างจริงของแต่ละเมนูจากแถวเงา .ss-sectabs-measure (class เดียวกัน มองไม่เห็น)
     ช่องของกลุ่มเมนู (tab.group, ตกลง 2026-11-18) = dropdown รายการเมนูในกลุ่ม (DockMenu below-start) มือถือใช้ bottom sheet ของ AppShell -->
<template>
	<div v-if="nav && nav.tabs.value.length > 1" ref="wrap" class="ss-sectabs-wrap">
		<nav class="ss-sectabs" :class="`ss-sectabs--${variant}`" aria-label="เมนูของหมวด">
			<button
				v-for="tab in shown"
				:key="tab.view"
				type="button"
				class="ss-sectab"
				:class="{ 'is-active': tab.view === active }"
				:aria-current="tab.view === active ? 'page' : undefined"
				:aria-haspopup="is_group(tab) ? 'menu' : undefined"
				:aria-expanded="is_group(tab) ? group_menu?.group === tab.group : undefined"
				:title="tab.label"
				@click="click_tab(tab, $event)"
			>
				<Icon :name="tab.icon" :size="16" :stroke="tab.view === active ? 2.4 : 2" />
				<span class="ss-sectab-label">{{ tab.label }}</span>
				<span v-if="tab.badge" class="ss-sectab-badge" :class="tab.badge_tone">{{ tab.badge }}</span>
				<Icon v-if="is_group(tab)" class="ss-sectab-caret" name="chevron-down" :size="14" :stroke="2.4" />
			</button>
			<button
				v-if="hidden.length"
				ref="more"
				type="button"
				class="ss-sectab ss-sectab--more"
				:class="{ 'is-open': menu }"
				aria-label="เมนูอื่น"
				title="เมนูอื่น"
				aria-haspopup="menu"
				:aria-expanded="menu"
				@click="menu = !menu"
			>
				<Icon name="more" :size="18" :stroke="2.6" />
				<span v-if="hidden.some((t) => t.badge)" class="ss-sectab-more-dot"></span>
			</button>
		</nav>
		<div ref="measure" class="ss-sectabs ss-sectabs-measure" aria-hidden="true">
			<span
				v-for="tab in tabs"
				:key="tab.view"
				class="ss-sectab"
				:class="{ 'is-active': tab.view === active }"
			>
				<Icon :name="tab.icon" :size="16" />
				<span class="ss-sectab-label">{{ tab.label }}</span>
				<span v-if="tab.badge" class="ss-sectab-badge">{{ tab.badge }}</span>
				<Icon v-if="is_group(tab)" class="ss-sectab-caret" name="chevron-down" :size="14" />
			</span>
			<span class="ss-sectab ss-sectab--more"><Icon name="more" :size="18" /></span>
		</div>
		<DockMenu :open="menu" :anchor="more" :groups="menu_groups" placement="below" @close="menu = false" />
		<DockMenu
			:open="!!group_menu"
			:anchor="group_menu?.anchor"
			:groups="group_menu?.groups || []"
			placement="below-start"
			@close="group_menu = null"
		/>
	</div>
</template>

<script setup>
import { computed, inject, nextTick, onBeforeUnmount, ref, watch } from "vue";
import Icon from "./Icon.vue";
import DockMenu from "./DockMenu.vue";

defineProps({ variant: { type: String, default: "bar" } });
const nav = inject("section_nav", null);

const wrap = ref(null);
const measure = ref(null);
const more = ref(null);
const menu = ref(false);
const fit = ref(Infinity);

const tabs = computed(() => nav?.tabs.value || []);
const active = computed(() => nav?.active_view.value);
const shown = computed(() => {
	if (fit.value >= tabs.value.length) return tabs.value;
	const out = tabs.value.slice(0, fit.value);
	const current = tabs.value.find((t) => t.view === active.value);
	if (current && !out.includes(current)) out.splice(Math.max(fit.value - 1, 0), 1, current);
	return out;
});
const hidden = computed(() => tabs.value.filter((t) => !shown.value.includes(t)));
const is_group = (tab) => !!tab.group && (nav.group_members?.(tab.group).length || 0) > 1;
const item_of = (t) => ({
	key: t.view,
	label: t.badge ? `${t.label} (${t.badge})` : t.label,
	icon: t.icon,
	selected: t.view === active.value,
	onclick: () => nav.open_tab(t.view),
});
// เมนูที่ล้น: เมนูเดี่ยวรวมกลุ่มเดียว กลุ่มเมนูแยกเป็นหัวข้อ
const menu_groups = computed(() => {
	const single = hidden.value.filter((t) => !is_group(t));
	return [
		...(single.length ? [{ items: single.map(item_of) }] : []),
		...hidden.value
			.filter(is_group)
			.map((t) => ({ label: nav.group_label(t.group), items: nav.group_members(t.group).map(item_of) })),
	];
});
const group_menu = ref(null);
function click_tab(tab, event) {
	if (!is_group(tab)) {
		nav.open_tab(tab.view);
		return;
	}
	if (group_menu.value?.group === tab.group) {
		group_menu.value = null;
		return;
	}
	group_menu.value = {
		group: tab.group,
		anchor: event.currentTarget,
		groups: [{ items: nav.group_members(tab.group).map(item_of) }],
	};
}

function relayout() {
	const box = wrap.value;
	const row = measure.value;
	if (!box || !row) return;
	const style = getComputedStyle(row);
	const gap = parseFloat(style.columnGap) || 0;
	const pad = parseFloat(style.paddingLeft) + parseFloat(style.paddingRight);
	const room = box.clientWidth - pad;
	const widths = [...row.children].map((c) => c.getBoundingClientRect().width);
	const more_w = widths.pop();
	const total = widths.reduce((a, w) => a + w, 0) + gap * Math.max(widths.length - 1, 0);
	if (total <= room + 0.5) {
		fit.value = Infinity;
		return;
	}
	const current = tabs.value.findIndex((t) => t.view === active.value);
	const width_of = (n) => {
		const list = widths.slice(0, n);
		if (current >= n && n > 0) list[n - 1] = widths[current];
		return list.reduce((a, w) => a + w + gap, more_w);
	};
	let n = 0;
	while (n < widths.length && width_of(n + 1) <= room) n++;
	fit.value = Math.max(n, 1);
}

let observer = null;
watch(
	wrap,
	(el) => {
		observer?.disconnect();
		if (!el) return;
		observer = new ResizeObserver(() => relayout());
		observer.observe(el);
		relayout();
		document.fonts?.ready.then(relayout);
	},
	{ flush: "post" }
);
onBeforeUnmount(() => observer?.disconnect());
watch(
	() => [tabs.value.map((t) => `${t.view}|${t.label}|${t.badge}`).join(","), active.value],
	() => nextTick(relayout)
);
</script>
