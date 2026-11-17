<!-- หัวรายการกลางของทุกหน้า (.ss-list-head) แก้ที่นี่ที่เดียวมีผลทุกหน้า (ตกลง 2026-11-17)
     แถว 1: แท็บสถานะ (tabs + v-model) หรือ slot lead (เช่น เลือกเดือน) → slot tools (ปุ่มของหน้า) → โหลดใหม่ → ปุ่มสร้าง (ขวาสุด)
     แถว 2 (แถวตัวกรอง): ค้นหา (v-model:search, มีปุ่ม X) → slot filters (ตัวกรองแบบเลือก) → ปุ่มตัวกรองรวม (ขวาสุด)
       มีปุ่มตัวกรองรวม (@filters) = ตัวกรองเรียงแถวเดียว ที่ไม่พอซ่อน (ไปตั้งในหน้าตัวกรองรวมของหน้านั้น)
       ไม่มี = ตัวกรองตกบรรทัดได้
     slot default = แถวเพิ่มท้ายหัวรายการ (เช่น สรุปยอด)
     ปุ่ม/ช่องที่ไม่ส่ง = ไม่แสดง: @refresh = ปุ่มโหลดใหม่ (loading = หมุน), create + @create = ปุ่มสร้าง
     หัวรายการแสดงทุกขนาดจอ หน้าที่ใช้แบบอื่นบนมือถือใส่ v-if="wide" เอง -->
<template>
	<div class="ss-list-head" :class="{ 'ss-list-head--many': many }">
		<StatusTabs
			v-if="tabs"
			:model-value="modelValue"
			:options="tabs"
			@update:model-value="$emit('update:modelValue', $event)"
		/>
		<slot name="lead" />
		<div v-if="show_tools" class="ss-list-tools">
			<slot name="tools" />
			<button
				v-if="onRefresh"
				type="button"
				class="ss-icon-btn"
				:class="{ 'is-spinning': loading }"
				aria-label="โหลดใหม่"
				title="โหลดใหม่"
				@click="onRefresh"
			>
				<Icon name="refresh" :size="17" />
			</button>
			<button
				v-if="create && onCreate"
				type="button"
				class="ss-btn ss-btn--primary ss-list-create"
				:aria-label="create"
				:title="create_title"
				:disabled="create_disabled"
				@click="onCreate"
			>
				<Icon :name="create_icon" :size="18" :stroke="2.6" />
				<span>{{ create }}</span>
			</button>
		</div>
		<div
			v-if="show_filterbar"
			class="ss-list-filterbar"
			:class="{ 'ss-list-filterbar--doc': onFilters }"
		>
			<ListSearch
				v-if="search !== undefined"
				ref="search_box"
				:model-value="search"
				:placeholder="search_placeholder"
				@update:model-value="$emit('update:search', $event)"
			/>
			<div v-if="$slots.filters" ref="filters_box" class="ss-list-filters">
				<slot name="filters" />
			</div>
			<button
				v-if="onFilters"
				type="button"
				class="ss-tool ss-tool--filter"
				:class="{ 'is-active': filter_count }"
				aria-label="ตัวกรองทั้งหมด"
				title="ตัวกรองทั้งหมด"
				@click="onFilters"
			>
				<Icon name="sliders" :size="17" />
				<span v-if="filter_count" class="ss-tab-count">{{ filter_count }}</span>
			</button>
		</div>
		<slot />
	</div>
</template>

<script setup>
import { computed, onUpdated, ref, useSlots } from "vue";
import Icon from "./Icon.vue";
import StatusTabs from "./StatusTabs.vue";
import ListSearch from "./ListSearch.vue";
import { use_overflow_row } from "../table.js";

// on* = ตัวจัดการ event (@refresh/@create/@filters) ประกาศเป็น prop เพื่อรู้ว่าหน้าส่งมาไหม (ไม่ส่ง = ไม่มีปุ่ม)
const props = defineProps({
	modelValue: [String, Number],
	tabs: Array,
	// แท็บเยอะ: แท็บเลื่อนแนวนอนได้ เครื่องมือไม่บีบแท็บ
	many: Boolean,
	search: { type: String, default: undefined },
	search_placeholder: { type: String, default: "ค้นหา" },
	loading: Boolean,
	create: String,
	create_icon: { type: String, default: "plus" },
	create_disabled: Boolean,
	create_title: String,
	filter_count: Number,
	onRefresh: Function,
	onCreate: Function,
	onFilters: Function,
});
defineEmits(["update:modelValue", "update:search"]);

const slots = useSlots();
const show_tools = computed(() => !!(slots.tools || props.onRefresh || (props.create && props.onCreate)));
const show_filterbar = computed(
	() => props.search !== undefined || !!slots.filters || !!props.onFilters
);

const search_box = ref(null);
const filters_box = ref(null);
// แถวเดียว: ตัวกรองที่ไม่พอซ่อน (มีปุ่มตัวกรองรวมให้ตั้งค่าที่ซ่อนอยู่)
// ไม่มีปุ่มตัวกรองรวม = ไม่วัด (ตัวกรองตกบรรทัดได้ ไม่ซ่อน)
const overflow = use_overflow_row(
	computed(() => (props.onFilters ? filters_box.value : null)),
	[() => props.onFilters]
);
onUpdated(() => props.onFilters && overflow.measure());

defineExpose({ focus: () => search_box.value?.focus() });
</script>
