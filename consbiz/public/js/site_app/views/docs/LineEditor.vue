<template>
	<!-- แถวรายการของฟอร์มจัดซื้อ/ขาย (DocForm.vue)
	     จอกว้าง (wide): ตารางแก้ไขในช่องแบบระบบเต็ม
	       - ลากที่จับ (⋮⋮) ย้ายลำดับแถว (emit reorder), ช่องติ๊กเลือกหลายแถวแล้วลบ (emit remove [rows])
	       - ปากกา = รายละเอียดของแถว (emit detail) เช่น คำอธิบาย WBS
	       - แถวล่างสุดพิมพ์ค้นหาแล้วเพิ่ม (↑↓ / Enter / Esc) Enter ในช่องจำนวน → ราคา → กลับช่องค้นหา
	     มือถือ: การ์ดต่อรายการ เพิ่มจาก sheet (emit browse) -->
	<div v-if="wide" ref="root" class="ss-grid-wrap">
		<div v-if="picked.size" class="ss-grid-bulk">
			<span
				>เลือก <b>{{ picked.size }}</b> แถว</span
			>
			<button type="button" class="ss-btn ss-btn--ghost ss-btn--sm" @click="picked = new Set()">
				ยกเลิกเลือก
			</button>
			<button type="button" class="ss-btn ss-btn--danger ss-btn--sm" @click="remove_picked">
				<Icon name="trash" :size="15" /> ลบที่เลือก
			</button>
		</div>
		<table class="ss-grid">
			<colgroup>
				<col class="c-grip" />
				<col class="c-check" />
				<col class="c-idx" />
				<col class="c-item" />
				<col class="c-qty" />
				<col class="c-uom" />
				<col class="c-rate" />
				<col class="c-amount" />
				<col v-if="date_field" class="c-date" />
				<col v-if="is_mr" class="c-flag" />
				<col class="c-tools" />
			</colgroup>
			<thead>
				<tr>
					<th></th>
					<th>
						<input
							type="checkbox"
							class="ss-check"
							aria-label="เลือกทุกแถว"
							:checked="items.length && picked.size === items.length"
							:indeterminate.prop="picked.size > 0 && picked.size < items.length"
							@change="toggle_all"
						/>
					</th>
					<th class="is-idx">#</th>
					<th>รายการ</th>
					<th class="is-num">จำนวน</th>
					<th>หน่วย</th>
					<th class="is-num">หน่วยละ</th>
					<th class="is-num">เป็นเงิน</th>
					<th v-if="date_field">{{ date_label }}</th>
					<th v-if="is_mr" class="is-center">ไม่คิดภาษี</th>
					<th><span class="ss-sr">คำสั่ง</span></th>
				</tr>
			</thead>
			<tbody>
				<tr
					v-for="(row, i) in items"
					:key="row.uid"
					:class="{
						'is-error': show_errors && error(row),
						'is-picked': picked.has(row),
						'is-active': row === active_row,
						'is-dragging': drag_from === i,
						'is-drop-before': drop_at === i && drag_from !== null && drag_from > i,
						'is-drop-after': drop_at === i && drag_from !== null && drag_from < i,
					}"
					:draggable="drag_ready === i"
					@focusin="$emit('focus-row', row)"
					@click="$emit('focus-row', row)"
					@dragstart="drag_start($event, i)"
					@dragover.prevent="drop_at = i"
					@drop.prevent="drop(i)"
					@dragend="drag_end"
				>
					<td class="is-grip">
						<span
							class="ss-grip"
							title="ลากเพื่อย้ายลำดับ"
							aria-hidden="true"
							@pointerdown="drag_ready = i"
							@pointerup="drag_ready = null"
						>
							<Icon name="grip" :size="15" :stroke="2.6" />
						</span>
					</td>
					<td class="is-check">
						<input
							type="checkbox"
							class="ss-check"
							:aria-label="`เลือก ${row.item_name}`"
							:checked="picked.has(row)"
							@change="toggle(row)"
						/>
					</td>
					<td class="is-idx">{{ i + 1 }}</td>
					<td class="is-item">
						<b :title="row.item_name">{{ row.item_name || row.item_code }}</b>
						<small
							>{{ row.item_code
							}}<template v-if="row.custom_wbs"> · WBS {{ row.custom_wbs }}</template></small
						>
						<RichText
							v-if="has_desc(row)"
							:html="row.description"
							:lines="2"
							class="ss-item-desc"
						/>
						<small v-if="show_errors && error(row)" class="is-error-text">{{ error(row) }}</small>
					</td>
					<td>
						<input
							v-model.number="row.qty"
							class="ss-cell ss-cell--num"
							type="number"
							inputmode="decimal"
							min="0"
							step="any"
							:aria-label="`จำนวน ${row.item_name}`"
							data-col="qty"
							@focus="$event.target.select()"
							@keydown.enter.prevent="next($event, 'rate')"
						/>
					</td>
					<td>
						<SelectBox
							v-model="row.uom"
							variant="cell"
							:label="`หน่วย ${row.item_name}`"
							:options="(row.uoms || [row.uom]).map((u) => ({ value: u, label: u }))"
						/>
					</td>
					<td>
						<MoneyInput
							v-model="row.rate"
							class="ss-cell ss-cell--num"
							:aria-label="`หน่วยละ ${row.item_name}`"
							data-col="rate"
							@keydown.enter.prevent="next($event, 'search')"
						/>
					</td>
					<td class="is-num is-amount">{{ money(amount(row)) }}</td>
					<td v-if="date_field">
						<DateInput
							v-model="row[date_field]"
							variant="cell"
							:label="`${date_label} ${row.item_name}`"
						/>
					</td>
					<td v-if="is_mr" class="is-center">
						<input
							v-model="row.custom_vat_nocal"
							type="checkbox"
							class="ss-check"
							:true-value="1"
							:false-value="0"
							:aria-label="`ไม่คิดภาษี ${row.item_name}`"
						/>
					</td>
					<td class="is-tools">
						<button
							type="button"
							class="ss-icon-btn ss-icon-btn--sm"
							:aria-label="`รายละเอียด ${row.item_name}`"
							title="รายละเอียด"
							@click="$emit('detail', row)"
						>
							<Icon name="pen" :size="15" />
						</button>
						<button
							type="button"
							class="ss-icon-btn ss-icon-btn--sm"
							:aria-label="`ลบ ${row.item_name}`"
							title="ลบแถว"
							@click="$emit('remove', row)"
						>
							<Icon name="trash" :size="15" />
						</button>
					</td>
				</tr>
			</tbody>
			<tfoot>
				<tr class="ss-grid-add">
					<td colspan="3" class="is-idx"><Icon name="plus" :size="15" :stroke="2.6" /></td>
					<td :colspan="span">
						<div class="ss-typeahead">
							<input
								ref="search_input"
								v-model="txt"
								class="ss-cell ss-cell--search"
								type="search"
								placeholder="พิมพ์รหัสหรือชื่อสินค้าเพื่อเพิ่มรายการ…"
								aria-label="เพิ่มรายการ"
								autocomplete="off"
								role="combobox"
								:aria-expanded="open"
								@input="search"
								@focus="txt && (open = true)"
								@blur="close_soon"
								@keydown.down.prevent="move(1)"
								@keydown.up.prevent="move(-1)"
								@keydown.enter.prevent="pick(results[active])"
								@keydown.esc="open = false"
							/>
							<button type="button" class="ss-link" @click="$emit('browse')">
								เลือกหลายรายการ
							</button>
							<ul
								v-if="open && (results.length || loading)"
								class="ss-typeahead-list"
								role="listbox"
							>
								<li v-if="loading && !results.length" class="is-note">กำลังค้นหา…</li>
								<li
									v-for="(it, i) in results"
									:key="it.item_code"
									role="option"
									:aria-selected="i === active"
									:class="{ 'is-active': i === active }"
									@mousedown.prevent="pick(it)"
									@mouseenter="active = i"
								>
									<span>
										<b>{{ it.item_name }}</b>
										<small>{{ it.item_code }} · {{ it.item_group }}</small>
									</span>
									<span class="is-num">
										<template v-if="it.rate">{{ money(it.rate) }}</template>
										<small>{{ it.stock_uom }}</small>
									</span>
								</li>
							</ul>
						</div>
					</td>
				</tr>
			</tfoot>
		</table>
	</div>

	<!-- มือถือ / แท็บเล็ตแนวตั้ง: การ์ด -->
	<div v-else>
		<TransitionGroup tag="div" class="ss-list ss-list--form ss-lines" name="ss-list">
			<div
				v-for="(row, i) in items"
				:key="row.uid"
				class="ss-card ss-line"
				:class="{ 'is-late': show_errors && error(row) }"
				:style="{ '--i': Math.min(i, 12) }"
			>
				<div class="ss-line-info">
					<span class="ss-card-title">{{ row.item_name || row.item_code }}</span>
					<span class="ss-card-meta">{{ row.item_code }}</span>
					<RichText v-if="has_desc(row)" :html="row.description" :lines="3" class="ss-item-desc" />
				</div>
				<div class="ss-line-del">
					<button
						type="button"
						class="ss-icon-btn ss-icon-btn--sm"
						:aria-label="`รายละเอียด ${row.item_name}`"
						@click="$emit('detail', row)"
					>
						<Icon name="pen" :size="16" />
					</button>
					<button
						type="button"
						class="ss-icon-btn ss-icon-btn--sm"
						:aria-label="`ลบ ${row.item_name}`"
						@click="$emit('remove', row)"
					>
						<Icon name="trash" :size="16" />
					</button>
				</div>
				<div class="ss-line-inputs">
					<label class="ss-field">
						<span class="ss-field-label">จำนวน</span>
						<input
							v-model.number="row.qty"
							class="ss-input ss-input--num"
							type="number"
							inputmode="decimal"
							min="0"
							step="any"
							@focus="$event.target.select()"
						/>
					</label>
					<div class="ss-field">
						<span class="ss-field-label">หน่วย</span>
						<SelectBox
							v-model="row.uom"
							label="หน่วย"
							:options="(row.uoms || [row.uom]).map((u) => ({ value: u, label: u }))"
						/>
					</div>
					<label class="ss-field">
						<span class="ss-field-label">หน่วยละ</span>
						<MoneyInput v-model="row.rate" class="ss-input ss-input--num" aria-label="หน่วยละ" />
					</label>
					<div class="ss-line-amount">
						<span class="ss-field-label">เป็นเงิน</span>
						<b>{{ money(amount(row)) }}</b>
					</div>
				</div>
				<label v-if="is_mr" class="ss-checkline">
					<input v-model="row.custom_vat_nocal" type="checkbox" :true-value="1" :false-value="0" />
					<span>ไม่คิดภาษี</span>
				</label>
				<div v-if="show_errors && error(row)" class="ss-field-error">{{ error(row) }}</div>
			</div>
		</TransitionGroup>
		<button type="button" class="ss-add-row" @click="$emit('browse')">
			<Icon name="plus" :size="20" :stroke="2.6" /> เพิ่มรายการ
		</button>
	</div>
</template>

<script setup>
import { computed, nextTick, ref } from "vue";
import Icon from "../../components/Icon.vue";
import SelectBox from "../../components/SelectBox.vue";
import DateInput from "../../components/DateInput.vue";
import MoneyInput from "../../components/MoneyInput.vue";
import RichText from "../../components/RichText.vue";
import { html_text, money } from "../../api.js";

const props = defineProps({
	items: { type: Array, required: true },
	wide: Boolean,
	is_mr: Boolean,
	// ช่องวันที่รายแถว (schedule_date / delivery_date) ไม่มี = ไม่แสดงคอลัมน์
	date_field: String,
	date_label: String,
	show_errors: Boolean,
	// แถวที่แสดงในแผงข้อมูลประกอบ (ไฮไลต์)
	active_row: Object,
	// (txt) => Promise<items> จาก site_docs.search_items
	search_fn: { type: Function, required: true },
});
const emit = defineEmits(["add", "remove", "reorder", "detail", "browse", "focus-row"]);

const root = ref(null);
const search_input = ref(null);
const txt = ref("");
const results = ref([]);
const loading = ref(false);
const open = ref(false);
const active = ref(0);
let timer = null;
let request = 0;

// คอลัมน์ที่ช่องค้นหาคลุม (รายการ ถึง ก่อนปุ่มท้ายแถว)
const span = computed(() => 5 + (props.date_field ? 1 : 0) + (props.is_mr ? 1 : 0) + 1);

// รายละเอียดที่ต่างจากชื่อรายการ (ERPNext ตั้ง description = ชื่อรายการเป็นค่าเริ่มต้น)
const has_desc = (row) => {
	const text = html_text(row.description);
	return !!text && text !== row.item_name;
};
const amount = (row) => (Number(row.qty) || 0) * (Number(row.rate) || 0);
function error(row) {
	return Number(row.qty) > 0 ? "" : "ใส่จำนวนมากกว่า 0";
}

// ---------------------------------------------------------------- เลือกหลายแถว

const picked = ref(new Set());
function toggle(row) {
	const next = new Set(picked.value);
	next.has(row) ? next.delete(row) : next.add(row);
	picked.value = next;
}
function toggle_all() {
	picked.value = picked.value.size === props.items.length ? new Set() : new Set(props.items);
}
function remove_picked() {
	emit("remove", [...picked.value]);
	picked.value = new Set();
}

// ---------------------------------------------------------------- ลากย้ายลำดับ (ลากได้เฉพาะเมื่อกดที่จับ ช่องกรอกยังเลือกข้อความได้)

const drag_ready = ref(null);
const drag_from = ref(null);
const drop_at = ref(null);

function drag_start(event, index) {
	drag_from.value = index;
	event.dataTransfer.effectAllowed = "move";
	event.dataTransfer.setData("text/plain", String(index));
}

function drop(index) {
	const from = drag_from.value;
	if (from !== null && from !== index) {
		const list = [...props.items];
		const [row] = list.splice(from, 1);
		list.splice(index, 0, row);
		emit("reorder", list);
	}
	drag_end();
}

function drag_end() {
	drag_from.value = drop_at.value = drag_ready.value = null;
}

// ---------------------------------------------------------------- ค้นหาเพิ่มรายการ

function search() {
	clearTimeout(timer);
	open.value = !!txt.value.trim();
	if (!open.value) return;
	timer = setTimeout(async () => {
		const id = ++request;
		loading.value = true;
		try {
			const rows = await props.search_fn(txt.value);
			if (id !== request) return;
			results.value = rows.slice(0, 8);
			active.value = 0;
		} finally {
			if (id === request) loading.value = false;
		}
	}, 200);
}

function move(delta) {
	if (!results.value.length) return;
	open.value = true;
	active.value = (active.value + delta + results.value.length) % results.value.length;
}

// เพิ่มแล้วไปช่องจำนวนของแถวใหม่
async function pick(it) {
	if (!it) return;
	emit("add", it);
	txt.value = "";
	results.value = [];
	open.value = false;
	await nextTick();
	root.value?.querySelector('tbody tr:last-child input[data-col="qty"]')?.focus();
}

function close_soon() {
	setTimeout(() => (open.value = false), 150);
}

// Enter: จำนวน → ราคา → ช่องค้นหา
function next(event, target) {
	if (target === "search") return search_input.value?.focus();
	event.target.closest("tr")?.querySelector(`input[data-col="${target}"]`)?.focus();
}

defineExpose({ focus_search: () => search_input.value?.focus() });
</script>
