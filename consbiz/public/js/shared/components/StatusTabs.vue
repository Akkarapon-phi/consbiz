<!-- แท็บสถานะของหัวรายการ (.ss-list-head แท็บเล็ต/จอใหญ่) หน้าตาเดียวกับแท็บของหน้าแก้แผนงาน (.pl-tabs)
     แท็บไม่พอกับความกว้างแถบ: แท็บที่ล้นซ่อน แล้วรวมไว้ที่ปุ่ม "…" ท้ายแถว (เมนูลง DockMenu placement below)
     แท็บที่เลือกอยู่แสดงเสมอ (แทนที่แท็บท้ายสุดที่พอ) วัดความกว้างจากแถวเงา .ss-list-tabs-measure ที่มองไม่เห็น -->
<template>
	<div ref="root" class="ss-list-tabs" role="tablist" aria-label="สถานะ">
		<button
			v-for="o in shown"
			:key="o.value"
			type="button"
			role="tab"
			class="ss-list-tab"
			:class="{ 'is-active': o.value === modelValue }"
			:aria-selected="o.value === modelValue"
			@click="$emit('update:modelValue', o.value)"
		>
			{{ o.label }}
			<span v-if="o.count != null" class="ss-tab-count">{{ o.count }}</span>
			<span v-if="o.alert" class="ss-tab-dot" :title="o.alert === true ? '' : o.alert"></span>
		</button>
		<button
			v-if="hidden.length"
			ref="more"
			type="button"
			class="ss-list-tab ss-list-tab--more"
			:class="{ 'is-open': menu }"
			aria-label="แท็บอื่น"
			title="แท็บอื่น"
			aria-haspopup="menu"
			:aria-expanded="menu"
			@click="menu = !menu"
		>
			<Icon name="more" :size="18" :stroke="2.6" />
			<span v-if="hidden.some((o) => o.alert || o.count)" class="ss-tab-dot"></span>
		</button>
		<div ref="measure" class="ss-list-tabs-measure" aria-hidden="true">
			<span v-for="o in options" :key="o.value" class="ss-list-tab">
				{{ o.label }}
				<span v-if="o.count != null" class="ss-tab-count">{{ o.count }}</span>
				<span v-if="o.alert" class="ss-tab-dot"></span>
			</span>
			<span class="ss-list-tab ss-list-tab--more"><Icon name="more" :size="18" /></span>
		</div>
		<DockMenu :open="menu" :anchor="more" :groups="menu_groups" placement="below" @close="menu = false" />
	</div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import Icon from "./Icon.vue";
import DockMenu from "./DockMenu.vue";

const props = defineProps({
	modelValue: String,
	options: { type: Array, required: true }, // [{value, label, count?, alert? (จุดแดง: true หรือข้อความ tooltip)}]
});
const emit = defineEmits(["update:modelValue"]);

const root = ref(null);
const measure = ref(null);
const more = ref(null);
const menu = ref(false);
const fit = ref(Infinity); // จำนวนแท็บที่แสดงได้ (Infinity = ทั้งหมด)

const shown = computed(() => {
	if (fit.value >= props.options.length) return props.options;
	const out = props.options.slice(0, fit.value);
	const active = props.options.find((o) => o.value === props.modelValue);
	if (active && !out.includes(active)) out.splice(Math.max(fit.value - 1, 0), 1, active);
	return out;
});
const hidden = computed(() => props.options.filter((o) => !shown.value.includes(o)));
const menu_groups = computed(() => [
	{
		items: hidden.value.map((o) => ({
			key: o.value,
			label: o.count ? `${o.label} (${o.count})` : o.label,
			onclick: () => emit("update:modelValue", o.value),
		})),
	},
]);

function relayout() {
	const el = root.value;
	const row = measure.value;
	if (!el || !row) return;
	const style = getComputedStyle(el);
	const gap = parseFloat(style.columnGap) || 0;
	const room = el.clientWidth - parseFloat(style.paddingLeft) - parseFloat(style.paddingRight);
	const widths = [...row.children].map((c) => c.getBoundingClientRect().width);
	const more_w = widths.pop();
	const total = widths.reduce((a, w) => a + w, 0) + gap * Math.max(widths.length - 1, 0);
	if (total <= room + 0.5) {
		fit.value = Infinity;
		return;
	}
	// เหลือที่ให้ปุ่ม "…" แล้วนับแท็บที่พอ แท็บที่เลือกอยู่ในส่วนที่ล้น = แทนที่แท็บท้ายสุด ต้องพอด้วย
	const active = props.options.findIndex((o) => o.value === props.modelValue);
	const width_of = (n) => {
		const list = widths.slice(0, n);
		if (active >= n && n > 0) list[n - 1] = widths[active];
		return list.reduce((a, w) => a + w + gap, more_w);
	};
	let n = 0;
	while (n < widths.length && width_of(n + 1) <= room) n++;
	fit.value = Math.max(n, 1);
}

let observer;
onMounted(() => {
	relayout();
	observer = new ResizeObserver(() => relayout());
	observer.observe(root.value);
	document.fonts?.ready.then(relayout);
});
onBeforeUnmount(() => observer?.disconnect());
watch(
	() => [props.options.map((o) => `${o.label}|${o.count}|${o.alert}`).join(","), props.modelValue],
	() => nextTick(relayout)
);
</script>
