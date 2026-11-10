<!-- ตารางแบบรายการเอกสารจัดซื้อ สำหรับข้อมูลที่โหลดมาครบแล้ว (เรียง/แบ่งหน้าในเครื่อง)
     columns: [{key, label, class?, sort?}] sort = true (เรียงตาม row[key]) หรือฟังก์ชันคืนค่าที่ใช้เรียง
     ช่องที่ต้องจัดรูปแบบใช้ slot ชื่อเดียวกับ key (ได้ { row }) class ใช้ชุดเดียวกับ DocTable (col-wide = ซ่อนเมื่อจอ < 1180)
     selectable + v-model:selected (Set ของ row_key) = มีช่องติ๊ก ติ๊กหัวตาราง = ทุกแถวของ rows (รวมหน้าอื่น) -->
<template>
	<div class="ss-data-table">
		<div class="ss-table-wrap">
			<table class="ss-table ss-table--list">
				<thead>
					<tr>
						<th v-if="selectable" class="col-check">
							<input
								type="checkbox"
								class="ss-check"
								aria-label="เลือกทั้งหมด"
								:checked="all_checked"
								:indeterminate.prop="some_checked && !all_checked"
								@change="toggle_all"
							/>
						</th>
						<th
							v-for="c in columns"
							:key="c.key"
							:class="c.class"
							:aria-sort="aria_sort(c)"
						>
							<button
								v-if="c.sort"
								type="button"
								class="ss-th-sort"
								@click="set_sort(c)"
							>
								{{ c.label }}
								<Icon
									:name="
										sort_key === c.key
											? order === 'asc'
												? 'chevron-up'
												: 'chevron-down'
											: 'arrow-up-down'
									"
									:size="13"
									:stroke="2.4"
									:class="{ 'is-idle': sort_key !== c.key }"
								/>
							</button>
							<template v-else>{{ c.label }}</template>
						</th>
					</tr>
				</thead>
				<tbody>
					<tr
						v-for="(row, i) in page_rows"
						:key="row[row_key]"
						:class="{
							'is-late': late?.(row),
							'is-static': !clickable,
							'is-selected': selectable && selected.has(row[row_key]),
						}"
						:style="{ '--i': Math.min(i, 20) }"
						:tabindex="clickable ? 0 : undefined"
						@click="clickable && $emit('open', row)"
						@keydown.enter="clickable && $emit('open', row)"
						@keydown.down.prevent="step($event, 1)"
						@keydown.up.prevent="step($event, -1)"
						@keydown.j.exact="app.shortcuts && step($event, 1)"
						@keydown.k.exact="app.shortcuts && step($event, -1)"
					>
						<td v-if="selectable" class="col-check" @click.stop>
							<input
								type="checkbox"
								class="ss-check"
								:aria-label="`เลือก ${row[row_key]}`"
								:checked="selected.has(row[row_key])"
								@change="toggle(row[row_key])"
							/>
						</td>
						<td v-for="c in columns" :key="c.key" :class="c.class">
							<slot :name="c.key" :row="row">{{ row[c.key] }}</slot>
						</td>
					</tr>
				</tbody>
			</table>
		</div>
		<footer class="ss-list-foot">
			<span class="ss-list-range">
				แสดง <b>{{ start + 1 }}–{{ start + page_rows.length }}</b> จาก
				<b>{{ rows.length }}</b>
			</span>
			<span class="ss-toolbar-gap"></span>
			<div v-if="page_count > 1" class="ss-pager">
				<button
					type="button"
					class="ss-icon-btn ss-icon-btn--sm"
					aria-label="หน้าก่อน"
					:disabled="page === 0"
					@click="page--"
				>
					<Icon name="chevron-left" :size="18" />
				</button>
				<span>{{ page + 1 }} / {{ page_count }}</span>
				<button
					type="button"
					class="ss-icon-btn ss-icon-btn--sm"
					aria-label="หน้าถัดไป"
					:disabled="page >= page_count - 1"
					@click="page++"
				>
					<Icon name="chevron-right" :size="18" />
				</button>
			</div>
		</footer>
	</div>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import Icon from "./Icon.vue";
import { app } from "../app.js";

const props = defineProps({
	rows: { type: Array, required: true },
	columns: { type: Array, required: true },
	row_key: { type: String, default: "name" },
	clickable: { type: Boolean, default: true },
	late: Function, // (row) => แสดงแถบแดงต้นแถว
	page_size: { type: Number, default: 30 },
	selectable: Boolean,
	selected: { type: Set, default: () => new Set() },
});
const emit = defineEmits(["open", "update:selected"]);

const sort_key = ref(null);
const order = ref("asc");
const page = ref(0);

function compare(a, b) {
	if (typeof a === "number" && typeof b === "number") return a - b;
	return String(a ?? "").localeCompare(String(b ?? ""), "th", { numeric: true });
}

const sorted = computed(() => {
	const column = props.columns.find((c) => c.key === sort_key.value);
	if (!column) return props.rows;
	const value = typeof column.sort === "function" ? column.sort : (row) => row[column.key];
	const direction = order.value === "asc" ? 1 : -1;
	return [...props.rows].sort((a, b) => direction * compare(value(a), value(b)));
});

const page_count = computed(() => Math.max(1, Math.ceil(props.rows.length / props.page_size)));
const start = computed(() => page.value * props.page_size);
const page_rows = computed(() => sorted.value.slice(start.value, start.value + props.page_size));

watch(
	() => props.rows,
	() => (page.value = 0)
);

function set_sort(column) {
	if (sort_key.value === column.key) order.value = order.value === "asc" ? "desc" : "asc";
	else {
		sort_key.value = column.key;
		order.value = "asc";
	}
	page.value = 0;
}

const all_checked = computed(
	() => props.rows.length > 0 && props.rows.every((r) => props.selected.has(r[props.row_key]))
);
const some_checked = computed(() => props.rows.some((r) => props.selected.has(r[props.row_key])));

function toggle(key) {
	const next = new Set(props.selected);
	if (next.has(key)) next.delete(key);
	else next.add(key);
	emit("update:selected", next);
}

function toggle_all() {
	emit("update:selected", all_checked.value ? new Set() : new Set(props.rows.map((r) => r[props.row_key])));
}

function aria_sort(column) {
	if (!column.sort || sort_key.value !== column.key) return undefined;
	return order.value === "asc" ? "ascending" : "descending";
}

function step(event, delta) {
	const row = event.target.closest("tr");
	const next = delta > 0 ? row.nextElementSibling : row.previousElementSibling;
	next?.focus();
}
</script>
