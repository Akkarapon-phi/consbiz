<!-- ช่องค้นหาของหน้ารายการ หน้าใส่ไว้ใน slot search ของ TopBar
     หน้าตาใหม่ (NEW_LOOK): ถ้าหน้านั้นมีหัวรายการ (.ss-list-head) ย้ายตัวเองไปเป็นแถวตัวกรอง (.ss-list-filterbar) ท้ายหัวรายการ
     (ทุกหน้าไม่ต้องแก้เอง หัวรายการที่โผล่ทีหลัง เช่น หลังโหลดข้อมูล ก็ตามไป) หน้าที่มี .ss-list-filterbar ของตัวเองแล้ว = เข้าไปอยู่ในแถวนั้น
     ไม่มีหัวรายการ / หน้าตาเดิม: บนแถบบน จอ < 1180 เป็นปุ่มแว่นขยาย กดแล้วกางทับแถบบน ออกจากช่องแล้วพับ (มีคำค้นอยู่ = ปุ่มมีจุด) -->
<template>
	<span ref="anchor" class="ss-header-search-anchor">
		<Teleport v-if="host" :to="host">
			<div v-if="own_bar" class="ss-list-filterbar ss-list-filterbar--auto">
				<ListSearch
					ref="list"
					:model-value="modelValue"
					:placeholder="placeholder"
					@update:model-value="$emit('update:modelValue', $event)"
				/>
			</div>
			<ListSearch
				v-else
				ref="list"
				:model-value="modelValue"
				:placeholder="placeholder"
				@update:model-value="$emit('update:modelValue', $event)"
			/>
		</Teleport>
		<div v-else class="ss-header-search" :class="{ 'is-open': open, 'has-value': modelValue }">
			<button
				type="button"
				class="ss-icon-btn ss-header-search-toggle"
				aria-label="ค้นหา"
				title="ค้นหา"
				@mousedown.prevent
				@click="toggle"
			>
				<Icon name="search" :size="20" />
			</button>
			<label class="ss-toolbar-search ss-header-search-box">
				<Icon name="search" :size="17" />
				<input
					ref="input"
					:value="modelValue"
					type="search"
					:placeholder="placeholder"
					@input="$emit('update:modelValue', $event.target.value)"
					@blur="open = false"
					@keydown.esc="input.blur()"
				/>
			</label>
		</div>
	</span>
</template>

<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref } from "vue";
import Icon from "./Icon.vue";
import ListSearch from "./ListSearch.vue";
import { state } from "../api.js";
import { NEW_LOOK } from "../modules.js";

defineProps({
	modelValue: String,
	placeholder: String,
});
defineEmits(["update:modelValue"]);

const open = ref(false);
const input = ref(null);
const list = ref(null);
const anchor = ref(null);
// ที่วางในหัวรายการ: แถวตัวกรองของหน้า (ถ้ามี) หรือตัวหัวรายการ (สร้างแถวเอง)
const host = ref(null);
const own_bar = ref(false);

function find_host() {
	if (!NEW_LOOK.has(state.section)) return;
	const view = anchor.value?.closest(".ss-view");
	const head = view?.querySelector(".ss-list-head");
	if (!head) {
		host.value = null;
		return;
	}
	const bar = head.querySelector(":scope > .ss-list-filterbar:not(.ss-list-filterbar--auto)");
	const next = bar || head;
	if (host.value !== next) {
		own_bar.value = !bar;
		host.value = next;
	}
}

let observer = null;
onMounted(() => {
	nextTick(find_host);
	const view = anchor.value?.closest(".ss-view");
	if (!view || !NEW_LOOK.has(state.section)) return;
	// หัวรายการมาทีหลัง (โหลดข้อมูล) หรือหายไป (เปลี่ยนแท็บ) = หาที่วางใหม่
	observer = new MutationObserver(() => {
		if (host.value && view.contains(host.value)) return;
		find_host();
	});
	observer.observe(view, { childList: true, subtree: true });
});
onBeforeUnmount(() => observer?.disconnect());

async function focus() {
	if (host.value) {
		list.value?.focus();
		return;
	}
	open.value = true;
	await nextTick();
	input.value?.focus();
}

function toggle() {
	if (open.value) input.value?.blur();
	else focus();
}

defineExpose({ focus });
</script>
