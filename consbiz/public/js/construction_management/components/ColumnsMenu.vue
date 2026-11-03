<script setup>
// เมนูคอลัมน์ (ปุ่มไอคอนบนแถบเครื่องมือ): ติ๊กเพื่อแสดง/ซ่อน ลากที่จับเพื่อเรียงลำดับ
// WBS ตรึงซ้ายสุดเสมอ (ลากไม่ได้ และวางเหนือ WBS ไม่ได้) รายการ (item_name) ซ่อนไม่ได้
// settings เป็น reactive ของ App แก้ตรงได้ (App.pin_wbs คุมให้ WBS อยู่หน้าสุดอีกชั้น)
import { computed, ref } from "vue";

const props = defineProps({
	settings: Object,
	columns: Array, // COLUMNS ทั้งหมด
});
const emit = defineEmits(["fit-columns"]);

const by_key = computed(() => new Map(props.columns.map((c) => [c.key, c])));
const chosen = computed(() => props.settings.columns.map((key) => by_key.value.get(key)).filter(Boolean));
const others = computed(() => props.columns.filter((c) => !props.settings.columns.includes(c.key)));

function toggle(key) {
	if (key === "item_name") return;
	const keys = props.settings.columns;
	props.settings.columns = keys.includes(key) ? keys.filter((k) => k !== key) : [...keys, key];
}

// ---------- ลากเรียงลำดับ ----------
const dragging = ref(null);
const target = ref(null); // { key, after }

function on_dragstart(event, key) {
	dragging.value = key;
	event.dataTransfer.effectAllowed = "move";
	event.dataTransfer.setData("text/plain", key);
}

function on_dragover(event, key) {
	if (!dragging.value || key === dragging.value) return;
	const rect = event.currentTarget.getBoundingClientRect();
	const after = event.clientY > rect.top + rect.height / 2;
	// วางเหนือ WBS ไม่ได้
	if (key === "wbs" && !after) return;
	event.preventDefault();
	target.value = { key, after };
}

function on_drop() {
	const from = dragging.value;
	const to = target.value;
	dragging.value = target.value = null;
	if (!from || !to) return;
	const keys = props.settings.columns.filter((k) => k !== from);
	keys.splice(keys.indexOf(to.key) + (to.after ? 1 : 0), 0, from);
	props.settings.columns = keys;
}

function on_dragend() {
	dragging.value = target.value = null;
}

const icon = (name, size = "sm") => frappe.utils.icon(name, size);
</script>

<template>
	<div class="cs-cols" @click.stop>
		<div class="cs-cols-head">
			<span>{{ __("ลากเพื่อเรียงลำดับ") }}</span>
			<button type="button" class="btn btn-default btn-xs" @click="emit('fit-columns')">
				{{ __("พอดีคอลัมน์") }}
			</button>
		</div>
		<div
			v-for="column in chosen"
			:key="column.key"
			class="cs-cols-row"
			:class="{
				'cs-cols-dragging': dragging === column.key,
				'cs-cols-before': target?.key === column.key && !target.after,
				'cs-cols-after': target?.key === column.key && target.after,
			}"
			:draggable="column.key !== 'wbs'"
			@dragstart="on_dragstart($event, column.key)"
			@dragover="on_dragover($event, column.key)"
			@drop.prevent="on_drop"
			@dragend="on_dragend"
		>
			<span
				class="cs-cols-handle"
				:class="{ 'cs-cols-pinned': column.key === 'wbs' }"
				:title="column.key === 'wbs' ? __('ซ้ายสุดเสมอ') : __('ลากเพื่อเรียงลำดับ')"
				v-html="icon(column.key === 'wbs' ? 'pin' : 'grip-vertical')"
			/>
			<label class="cs-cols-check">
				<input
					type="checkbox"
					checked
					:disabled="column.key === 'item_name'"
					@change="toggle(column.key)"
				/>
				{{ column.label }}
			</label>
		</div>
		<div v-if="others.length" class="cs-cols-divider">{{ __("ยังไม่แสดง") }}</div>
		<div v-for="column in others" :key="column.key" class="cs-cols-row cs-cols-off">
			<span class="cs-cols-handle" />
			<label class="cs-cols-check">
				<input type="checkbox" @change="toggle(column.key)" />
				{{ column.label }}
			</label>
		</div>
	</div>
</template>

<style scoped>
.cs-cols {
	width: 260px;
	max-height: 70vh;
	overflow-y: auto;
	padding: 4px 8px 8px;
}
.cs-cols-head {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 8px;
	padding: 4px 4px 8px;
	color: var(--text-muted);
	font-size: var(--text-xs);
}
.cs-cols-row {
	display: flex;
	align-items: center;
	gap: 6px;
	padding: 3px 4px;
	border-radius: var(--radius-sm);
	box-shadow: 0 0 0 transparent;
}
.cs-cols-row[draggable="true"] {
	cursor: grab;
}
.cs-cols-row:hover {
	background: var(--fg-hover-color);
}
.cs-cols-dragging {
	opacity: 0.4;
}
/* เส้นบอกตำแหน่งที่จะวาง */
.cs-cols-before {
	box-shadow: inset 0 2px 0 var(--primary);
}
.cs-cols-after {
	box-shadow: inset 0 -2px 0 var(--primary);
}
.cs-cols-handle {
	display: grid;
	flex: none;
	place-items: center;
	width: 18px;
	color: var(--text-muted);
}
.cs-cols-handle :deep(svg) {
	stroke: currentColor;
}
.cs-cols-pinned {
	color: var(--primary);
}
.cs-cols-check {
	display: flex;
	flex: 1;
	align-items: center;
	gap: 8px;
	margin: 0;
	font-size: var(--text-sm);
	font-weight: 400;
	cursor: pointer;
}
.cs-cols-check input {
	margin: 0;
}
.cs-cols-off {
	color: var(--text-muted);
}
.cs-cols-divider {
	margin: 8px 4px 2px;
	color: var(--text-muted);
	font-size: var(--text-xs);
	font-weight: 600;
}
</style>
