<!-- ค่าที่แก้ได้ทีละช่อง (เช่น ช่อง Allow on Submit ของเอกสารที่ส่งแล้ว): ค่า + ดินสอเล็ก
     แก้ตรงที่เดิมทุกจอ (✓ / ✕, Enter บันทึก, Esc ยกเลิก) ไม่มี popup (ตกลง 2026-11-18 เดิมจอสัมผัสเปิด sheet)
     ค่าว่าง = ปุ่ม "+ เพิ่ม" save(value, apply) คืน Promise ปิดตัวแก้เมื่อสำเร็จ -->
<template>
	<span class="ss-ie" :class="{ 'is-block': multiline, 'is-editing': editing && inline }">
		<template v-if="!(editing && inline)">
			<button v-if="editable && empty" type="button" class="ss-ie-add" @click="start">
				<Icon name="plus" :size="13" :stroke="2.6" /> เพิ่ม{{ add_label ?? label }}
			</button>
			<template v-else>
				<span class="ss-ie-value"
					><slot>{{ display }}</slot></span
				><button
					v-if="editable"
					type="button"
					class="ss-ie-pen"
					:aria-label="`แก้ไข${label}`"
					:title="`แก้ไข${label}`"
					@click="start"
				>
					<Icon name="pen" :size="13" :stroke="2.2" />
				</button>
			</template>
		</template>

		<span v-else class="ss-ie-form" @keydown="on_key">
			<DateInput
				v-if="fieldtype === 'Date'"
				v-model="draft"
				variant="cell"
				:label="label"
				:min="min"
				:clearable="!required"
			/>
			<textarea
				v-else-if="multiline"
				ref="input"
				v-model="draft"
				class="ss-input"
				rows="3"
				:aria-label="label"
			></textarea>
			<input v-else ref="input" v-model="draft" class="ss-input" type="text" :aria-label="label" />
			<label v-if="apply_label" class="ss-ie-apply">
				<input v-model="apply" type="checkbox" class="ss-check" /> {{ apply_label }}
			</label>
			<span class="ss-ie-actions">
				<button
					type="button"
					class="ss-icon-btn ss-icon-btn--sm is-ok"
					aria-label="บันทึก"
					title="บันทึก (Enter)"
					:disabled="busy"
					@click="commit"
				>
					<span v-if="busy" class="ss-spinner ss-spinner--sm"></span>
					<Icon v-else name="check" :size="16" :stroke="2.6" />
				</button>
				<button
					type="button"
					class="ss-icon-btn ss-icon-btn--sm"
					aria-label="ยกเลิก"
					title="ยกเลิก (Esc)"
					:disabled="busy"
					@click="cancel"
				>
					<Icon name="x" :size="16" :stroke="2.4" />
				</button>
			</span>
		</span>

	</span>
</template>

<script setup>
import { computed, nextTick, ref } from "vue";
import Icon from "./Icon.vue";
import DateInput from "./DateInput.vue";

const props = defineProps({
	modelValue: { type: [String, Number], default: null },
	label: { type: String, required: true },
	// ข้อความปุ่มตอนค่าว่าง (ค่าเริ่มต้น = label)
	add_label: String,
	subtitle: String,
	display: String,
	fieldtype: { type: String, default: "Data" },
	editable: Boolean,
	required: Boolean,
	multiline: Boolean,
	min: String,
	// ถามว่าใช้ค่านี้กับทุกรายการด้วยไหม (วันที่หัวเอกสาร) ค่าเริ่มต้นติ๊ก
	apply_label: String,
	save: { type: Function, required: true },
});

const editing = ref(false);
const draft = ref(null);
const apply = ref(true);
const busy = ref(false);
const input = ref(null);

const empty = computed(
	() => props.modelValue === null || props.modelValue === undefined || props.modelValue === ""
);

// แก้ตรงที่เดิมทุกจอ (ตกลง 2026-11-18)
const inline = true;

async function start() {
	draft.value = props.modelValue ?? (props.fieldtype === "Date" ? null : "");
	apply.value = true;
	editing.value = true;
	await nextTick();
	input.value?.focus();
	input.value?.select?.();
}

function cancel() {
	if (busy.value) return;
	editing.value = false;
}

async function commit() {
	if (busy.value) return;
	const value = typeof draft.value === "string" ? draft.value.trim() : draft.value;
	if ((value || null) === (props.modelValue || null)) {
		editing.value = false;
		return;
	}
	busy.value = true;
	try {
		await props.save(value || null, !!props.apply_label && apply.value);
		editing.value = false;
	} catch {
		// save แสดงข้อผิดพลาดเอง: คงตัวแก้ไว้ให้แก้ต่อ
	} finally {
		busy.value = false;
	}
}

function on_key(event) {
	// Esc/Enter ของปฏิทินที่เปิดอยู่ (DateInput จัดการเองแล้ว) ไม่นับ
	if (event.defaultPrevented || document.querySelector(".ss-cal-pop")) return;
	if (event.key === "Escape") {
		event.preventDefault();
		cancel();
	} else if (event.key === "Enter" && (!props.multiline || event.ctrlKey || event.metaKey)) {
		if (event.target.closest?.(".ss-date")) return;
		event.preventDefault();
		commit();
	}
}
</script>
