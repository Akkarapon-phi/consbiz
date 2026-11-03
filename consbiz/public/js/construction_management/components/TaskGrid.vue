<script setup>
// ตาราง WBS ฝั่งซ้าย: แถวสูงเท่ากับ timeline และเลื่อนแนวตั้งตาม timeline (App ตั้ง scrollTop ให้)
// ล้อเมาส์แนวตั้งส่งต่อให้ App เลื่อน timeline แทน เพื่อให้มี scrollbar แนวตั้งอันเดียว
// คลิกช่องที่แก้ได้จะเปิด Frappe control ในช่องนั้น, ลากหัวคอลัมน์เพื่อสลับตำแหน่ง
// คีย์บอร์ดแบบ Excel: ลูกศรเลื่อนช่อง, Enter / F2 แก้ช่อง, ระหว่างแก้ Enter = บันทึกแล้วลงแถวถัดไป,
// Tab / Shift+Tab = บันทึกแล้วไปช่องที่แก้ได้ถัดไป / ก่อนหน้า, Esc = ยกเลิก
// คลิกช่องใดก็ได้ส่ง select ให้ App (คลิก WBS/ชื่องาน = เปิดแผงคน/เครื่องจักร/วัสดุของงานด้านขวา)
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from "vue";
import FrappeControl from "./FrappeControl.vue";
import { can_edit, cell_text, cell_tone, cell_value } from "../columns";

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
	selected: String,
});
const emit = defineEmits([
	"update",
	"toggle",
	"resize-column",
	"move-column",
	"hover",
	"scroll-y",
	"reveal-row",
	"select",
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

// จอสัมผัส: ปัดขึ้น-ลงบนตารางเลื่อน timeline เหมือนล้อเมาส์ (ปัดซ้าย-ขวาเลื่อนตารางตามปกติ)
let touch = null;
function on_touchstart(event) {
	const t = event.touches[0];
	touch = event.touches.length === 1 ? { x: t.clientX, y: t.clientY, axis: null } : null;
}
function on_touchmove(event) {
	if (!touch) return;
	const t = event.touches[0];
	const dx = touch.x - t.clientX;
	const dy = touch.y - t.clientY;
	touch.axis ??= Math.abs(dy) > Math.abs(dx) ? "y" : "x";
	if (touch.axis !== "y") return;
	event.preventDefault();
	emit("scroll-y", dy);
	Object.assign(touch, { x: t.clientX, y: t.clientY });
}
function on_touchend() {
	touch = null;
}

// ---------- แก้ค่าในช่อง ----------

const editing = ref(null); // { task, column, value }
const editor = ref(null);

function start_edit(task, column) {
	active.value = { name: task.name, key: column.key };
	emit("select", task, column.key);
	if (!props.canWrite || !can_edit(task, column)) {
		focus_body();
		return;
	}
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

// ---------- คีย์บอร์ด ----------

const active = ref(null); // ช่องที่เลือกอยู่ { name, key }

function is_active(task, column) {
	return active.value?.name === task.name && active.value.key === column.key;
}

function focus_body() {
	nextTick(() => body.value?.focus({ preventScroll: true }));
}

function position() {
	if (!active.value) return null;
	const row = props.tasks.findIndex((t) => t.name === active.value.name);
	const col = props.columns.findIndex((c) => c.key === active.value.key);
	return row < 0 || col < 0 ? null : { row, col };
}

function set_active(row, col) {
	const task = props.tasks[row];
	const column = props.columns[col];
	if (!task || !column) return false;
	active.value = { name: task.name, key: column.key };
	emit("reveal-row", row);
	reveal_column(col);
	return true;
}

// เลื่อนตารางแนวนอนให้เห็นคอลัมน์ที่เลือก
function reveal_column(col) {
	const el = body.value;
	if (!el) return;
	const left = props.columns.slice(0, col).reduce((sum, c) => sum + c.width, 0);
	const right = left + props.columns[col].width;
	if (left < el.scrollLeft) el.scrollLeft = left;
	else if (right > el.scrollLeft + el.clientWidth) el.scrollLeft = right - el.clientWidth;
}

// ไปช่องที่แก้ได้ถัดไป: แนวตั้ง (Enter) คอลัมน์เดิม, แนวนอน (Tab) ไล่ต่อแถวถัดไป
function next_editable(step, vertical) {
	const pos = position();
	if (!pos) return;
	const cols = props.columns.length;
	let { row, col } = pos;
	for (let i = 0; i < props.tasks.length * cols; i++) {
		if (vertical) row += step;
		else {
			col += step;
			if (col >= cols) [row, col] = [row + 1, 0];
			if (col < 0) [row, col] = [row - 1, cols - 1];
		}
		const task = props.tasks[row];
		if (!task) return;
		if (props.canWrite && can_edit(task, props.columns[col])) {
			set_active(row, col);
			return;
		}
	}
}

function edit_active() {
	const pos = position();
	if (pos) start_edit(props.tasks[pos.row], props.columns[pos.col]);
}

// ระหว่างแก้: ยืนยันค่าที่พิมพ์ (ให้ control ส่ง change) แล้วย้ายช่อง
function finish_edit(move) {
	const control = editor.value?.[0]?.get_control?.() || editor.value?.get_control?.();
	control?.$input?.trigger("change");
	nextTick(() => {
		editing.value = null;
		move?.();
		focus_body();
	});
}

function on_keydown(event) {
	const date = editing.value?.column.editor === "Date";
	if (event.key === "Escape") {
		event.preventDefault();
		editing.value = null;
		focus_body();
	} else if (event.key === "Enter") {
		event.preventDefault();
		finish_edit(() => next_editable(event.shiftKey ? -1 : 1, true));
	} else if (event.key === "Tab") {
		event.preventDefault();
		finish_edit(() => next_editable(event.shiftKey ? -1 : 1, false));
	} else if (!date && (event.key === "ArrowUp" || event.key === "ArrowDown")) {
		// ช่องวันที่ใช้ลูกศรใน date picker
		event.preventDefault();
		finish_edit(() => next_editable(event.key === "ArrowUp" ? -1 : 1, true));
	}
}

// ไม่ได้แก้ช่องอยู่ (โฟกัสที่ตาราง)
function on_grid_keydown(event) {
	if (editing.value || event.ctrlKey || event.metaKey || event.altKey) return;
	const pos = position();
	if (!pos) {
		if (event.key.startsWith("Arrow") && props.tasks.length) {
			event.preventDefault();
			set_active(0, 0);
		}
		return;
	}
	const moves = { ArrowUp: [-1, 0], ArrowDown: [1, 0], ArrowLeft: [0, -1], ArrowRight: [0, 1] };
	if (moves[event.key]) {
		event.preventDefault();
		const [dr, dc] = moves[event.key];
		set_active(pos.row + dr, pos.col + dc);
	} else if (event.key === "Enter" || event.key === "F2") {
		event.preventDefault();
		edit_active();
	} else if (event.key === "Tab") {
		event.preventDefault();
		next_editable(event.shiftKey ? -1 : 1, false);
	} else if (event.key === "Escape") {
		active.value = null;
	}
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
		<div
			ref="body"
			class="cs-grid-body"
			tabindex="0"
			@wheel="on_wheel"
			@touchstart.passive="on_touchstart"
			@touchmove="on_touchmove"
			@touchend="on_touchend"
			@keydown="on_grid_keydown"
		>
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
						:class="{
							'cs-group': task.is_group,
							'cs-hover': hovered === task.name,
							'cs-selected': selected === task.name,
						}"
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
								'cs-active': is_active(task, column),
							}"
							:style="{ width: column.width + 'px' }"
							@click="start_edit(task, column)"
						>
							<span
								v-if="column.key === 'item_name'"
								class="cs-name"
								:style="{ paddingLeft: task.indent * 16 + 'px' }"
								:title="
									task.is_group
										? task.item_name
										: `${task.item_name}\n${__('คลิกเพื่อกำหนดคน/เครื่องจักร/วัสดุ')}`
								"
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
							<span
								v-else-if="cell_tone(task, column.key, metrics)"
								class="indicator-pill no-indicator-dot cs-pill"
								:class="cell_tone(task, column.key, metrics)"
							>
								{{ cell_text(task, column.key, metrics) }}
							</span>
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
	background: var(--card-bg);
	border-bottom: 1px solid color-mix(in srgb, var(--border-color) 70%, transparent);
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
	border-bottom: 1px solid color-mix(in srgb, var(--border-color) 45%, transparent);
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
.cs-row.cs-selected {
	background: var(--consbiz-gantt-row-selected);
}
.cs-pill {
	height: 20px;
	padding: 0 8px;
	font-size: var(--text-xs);
}
.cs-cell {
	display: flex;
	align-items: center;
	flex: 0 0 auto;
	padding: 0 8px;
	overflow: hidden;
	white-space: nowrap;
	border-right: 1px solid color-mix(in srgb, var(--border-color) 45%, transparent);
	box-sizing: border-box;
	font-variant-numeric: tabular-nums;
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
.cs-grid-body:focus {
	outline: none;
}
/* ช่องที่เลือกด้วยคีย์บอร์ด (แสดงเฉพาะตอนตารางมีโฟกัส หรือกำลังแก้) */
.cs-grid-body:focus .cs-cell.cs-active,
.cs-cell.cs-active.cs-editing {
	box-shadow: inset 0 0 0 2px var(--consbiz-gantt-plan);
	border-radius: 4px;
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
