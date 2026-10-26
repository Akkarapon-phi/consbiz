<script setup>
// ตาราง WBS ฝั่งซ้าย: แถวสูงเท่ากับ timeline และเลื่อนแนวตั้งตาม timeline (App ตั้ง scrollTop ให้)
// ล้อเมาส์แนวตั้งส่งต่อให้ App เลื่อน timeline แทน เพื่อให้มี scrollbar แนวตั้งอันเดียว
// คลิกช่องที่แก้ได้จะเปิด Frappe control ในช่องนั้น, ลากหัวคอลัมน์เพื่อสลับตำแหน่ง
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from "vue";
import FrappeControl from "./FrappeControl.vue";
import { can_edit, cell_text, cell_value } from "../columns";

const props = defineProps({
	tasks: Array,
	columns: Array,
	metrics: Map,
	collapsed: Object,
	canWrite: Boolean,
	rowHeight: Number,
	headerHeight: Number,
	bodyHeight: Number,
	summaryRows: Array,
	summaryRowHeight: Number,
	hovered: String,
});
const emit = defineEmits([
	"update",
	"toggle",
	"resize-column",
	"move-column",
	"hover",
	"scroll-y",
]);

const body = ref(null);
// App ยกเลิกค่าที่พิมพ์ค้างก่อน Undo/Redo ด้วยคีย์ลัด
function cancel_edit() {
	editing.value = null;
}
defineExpose({ body, cancel_edit });

const total_width = computed(() => props.columns.reduce((sum, c) => sum + c.width, 0));

function on_wheel(event) {
	if (Math.abs(event.deltaY) <= Math.abs(event.deltaX)) return;
	event.preventDefault();
	emit("scroll-y", event.deltaY);
}

// ---------- แก้ค่าในช่อง ----------

const editing = ref(null); // { task, column, value }
const editor = ref(null);

function start_edit(task, column) {
	if (!props.canWrite || !can_edit(task, column)) return;
	editing.value = { task, column, value: cell_value(task, column.key, props.metrics) };
}

function commit(value) {
	// ถูกยกเลิกไปแล้ว (Escape / คีย์ลัด Undo) แต่ช่องกรอกยังส่ง change ตามมาตอนหลุดโฟกัส
	if (!editing.value) return;
	const { task, column } = editing.value;
	editing.value = null;
	emit("update", task, column.key, value);
}

function is_editing(task, column) {
	return editing.value?.task === task && editing.value.column.key === column.key;
}

// คลิกนอกช่อง: ยืนยันค่าที่พิมพ์ค้างไว้แล้วปิด (ยกเว้นคลิกใน date picker ของ Frappe)
function on_document_mousedown(event) {
	if (!editing.value) return;
	if (event.target.closest(".cs-editing, .datepicker")) return;
	const control = editor.value?.[0]?.get_control?.() || editor.value?.get_control?.();
	control?.$input?.trigger("change");
	nextTick(() => (editing.value = null));
}

function on_keydown(event) {
	if (event.key === "Escape") editing.value = null;
}

onMounted(() => document.addEventListener("mousedown", on_document_mousedown, true));
onBeforeUnmount(() => document.removeEventListener("mousedown", on_document_mousedown, true));

// ---------- ปรับความกว้างและสลับคอลัมน์ ----------

function start_resize(column, event) {
	const start_x = event.clientX;
	const move = (e) => emit("resize-column", column.key, column.width + e.clientX - start_x);
	const up = () => {
		document.removeEventListener("mousemove", move);
		document.removeEventListener("mouseup", up);
		document.body.classList.remove("cs-resizing");
	};
	document.addEventListener("mousemove", move);
	document.addEventListener("mouseup", up);
	document.body.classList.add("cs-resizing");
}

const dragging = ref(null);
const drop_target = ref(null);

function on_drop(column) {
	if (dragging.value && dragging.value !== column.key) {
		emit("move-column", dragging.value, column.key);
	}
	dragging.value = drop_target.value = null;
}
</script>

<template>
	<div class="cs-grid">
		<div ref="body" class="cs-grid-body" @wheel="on_wheel">
			<div :style="{ width: total_width + 'px' }">
				<div class="cs-grid-header" :style="{ height: headerHeight + 'px' }">
					<div
						v-for="column in columns"
						:key="column.key"
						class="cs-cell"
						:class="{
							'text-right': column.align === 'right',
							'cs-drop-target': drop_target === column.key,
						}"
						:style="{ width: column.width + 'px' }"
						:title="__('ลากเพื่อสลับตำแหน่งคอลัมน์')"
						draggable="true"
						@dragstart="dragging = column.key"
						@dragover.prevent="drop_target = column.key"
						@dragleave="drop_target = null"
						@drop.prevent="on_drop(column)"
						@dragend="dragging = drop_target = null"
					>
						<span class="cs-header-label">{{ column.label }}</span>
						<span
							class="cs-resize"
							@mousedown.prevent.stop="start_resize(column, $event)"
						/>
					</div>
				</div>

				<div :style="{ minHeight: bodyHeight + 'px' }">
					<div
						v-for="task in tasks"
						:key="task.name"
						class="cs-row"
						:class="{ 'cs-group': task.is_group, 'cs-hover': hovered === task.name }"
						:style="{ height: rowHeight + 'px' }"
						@mouseenter="emit('hover', task.name)"
						@mouseleave="emit('hover', null)"
					>
						<div
							v-for="column in columns"
							:key="column.key"
							class="cs-cell"
							:class="{
								'text-right': column.align === 'right',
								'cs-editable': canWrite && can_edit(task, column),
								'cs-editing': is_editing(task, column),
							}"
							:style="{ width: column.width + 'px' }"
							@click="start_edit(task, column)"
						>
							<span
								v-if="column.key === 'item_name'"
								class="cs-name"
								:style="{ paddingLeft: task.indent * 16 + 'px' }"
								:title="task.item_name"
							>
								<button
									v-if="task.is_group"
									type="button"
									class="cs-toggle btn btn-xs btn-link"
									@click.stop="emit('toggle', task)"
								>
									<svg class="icon icon-xs">
										<use
											:href="
												collapsed.has(task.name)
													? '#icon-right'
													: '#icon-down'
											"
										/>
									</svg>
								</button>
								<span v-else class="cs-toggle" />
								<span class="ellipsis">{{ task.item_name }}</span>
							</span>
							<FrappeControl
								v-else-if="is_editing(task, column)"
								ref="editor"
								class="cs-editor"
								:df="{ fieldtype: column.editor }"
								:model-value="editing.value"
								autofocus
								@update:model-value="commit"
								@keydown="on_keydown"
							/>
							<template v-else>{{ cell_text(task, column.key, metrics) }}</template>
						</div>
					</div>
				</div>

				<div
					v-if="summaryRows.length"
					class="cs-summary-labels"
					:style="{ height: summaryRows.length * summaryRowHeight + 1 + 'px' }"
				>
					<div
						v-for="row in summaryRows"
						:key="row.key"
						class="cs-summary-label"
						:class="{ 'cs-group-start': row.group_start }"
						:style="{ height: summaryRowHeight + 'px' }"
					>
						<span class="cs-summary-text">
							<span class="cs-dot" :style="{ background: row.color }" />
							{{ row.label }}
						</span>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<style scoped>
.cs-grid {
	flex: 0 0 auto;
	min-width: 0;
	overflow: hidden;
}
.cs-grid-body {
	height: 100%;
	/* scrollbar แนวนอนแสดงตลอดเหมือน timeline เพื่อให้ความสูงที่เลื่อนได้เท่ากัน */
	overflow-x: scroll;
	overflow-y: hidden;
}
.cs-grid-header {
	position: sticky;
	top: 0;
	z-index: 2;
	display: flex;
	background: var(--subtle-fg);
	border-bottom: 1px solid var(--border-color);
	font-size: var(--text-sm);
	font-weight: 600;
	color: var(--text-muted);
}
.cs-grid-header .cs-cell {
	position: relative;
	align-items: flex-end;
	padding-bottom: 6px;
	cursor: grab;
}
.cs-header-label {
	white-space: normal;
	line-height: 1.2;
}
.cs-drop-target {
	box-shadow: inset 3px 0 0 var(--primary);
}
.cs-resize {
	position: absolute;
	top: 0;
	right: 0;
	width: 6px;
	height: 100%;
	cursor: col-resize;
}
.cs-resize:hover {
	background: var(--border-color);
}
.cs-row {
	display: flex;
	border-bottom: 1px solid var(--border-color);
	font-size: var(--text-sm);
	box-sizing: border-box;
}
.cs-row.cs-group {
	font-weight: 600;
	color: var(--heading-color);
}
.cs-row.cs-hover {
	background: var(--consbiz-gantt-row-hover);
}
.cs-cell {
	display: flex;
	align-items: center;
	flex: 0 0 auto;
	padding: 0 8px;
	overflow: hidden;
	white-space: nowrap;
	border-right: 1px solid var(--border-color);
	box-sizing: border-box;
}
.cs-cell.text-right {
	justify-content: flex-end;
}
.cs-cell.cs-editable {
	cursor: text;
}
.cs-cell.cs-editable:hover {
	box-shadow: inset 0 0 0 1px var(--gray-400);
}
.cs-cell.cs-editing {
	padding: 0 2px;
	overflow: visible;
}
.cs-editor {
	width: 100%;
}
.cs-name {
	display: flex;
	align-items: center;
	min-width: 0;
}
.cs-toggle {
	flex: 0 0 20px;
	width: 20px;
	padding: 0;
	margin-right: 2px;
}
.cs-summary-labels {
	position: sticky;
	bottom: 0;
	z-index: 2;
	box-sizing: border-box;
	background: var(--subtle-fg);
	border-top: 1px solid var(--border-color);
}
.cs-summary-label {
	display: flex;
	align-items: center;
	gap: 6px;
	padding: 0 8px;
	font-size: var(--text-xs);
	font-weight: 600;
	color: var(--text-muted);
	border-bottom: 1px solid var(--border-color);
	box-sizing: border-box;
}
/* เส้นแบ่งกลุ่ม Baseline / แผน / จริง (ไม่เพิ่มความสูงแถว) */
.cs-group-start {
	box-shadow: inset 0 1px 0 var(--gray-500);
}
/* ป้ายติดซ้ายเมื่อเลื่อนตารางแนวนอน */
.cs-summary-text {
	position: sticky;
	left: 8px;
	display: flex;
	align-items: center;
	gap: 6px;
}
.cs-dot {
	width: 8px;
	height: 8px;
	border-radius: 50%;
}
</style>
