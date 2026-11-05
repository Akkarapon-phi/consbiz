<template>
	<!-- แถวรายการของฟอร์มจัดซื้อ/ขาย (DocForm.vue)
	     แท็บเล็ต/จอใหญ่ (wide): ตารางแก้ไขในช่อง แบบตารางของระบบเต็ม แถวล่างสุดพิมพ์ค้นหาแล้วเพิ่มรายการ (↑↓ / Enter / Esc)
	     Enter ในช่องจำนวน → ราคา → กลับไปช่องค้นหา (กรอกต่อเนื่องด้วยคีย์บอร์ด)
	     มือถือ: การ์ดต่อรายการ เพิ่มรายการจาก sheet (emit browse) -->
	<div v-if="wide" ref="root" class="ss-grid-wrap">
		<table class="ss-grid" :class="{ 'is-qty-only': is_mr }">
			<colgroup>
				<col class="c-idx" />
				<col class="c-item" />
				<col class="c-qty" />
				<col class="c-uom" />
				<col v-if="!is_mr" class="c-rate" />
				<col v-if="!is_mr" class="c-amount" />
				<col v-if="date_field" class="c-date" />
				<col class="c-del" />
			</colgroup>
			<thead>
				<tr>
					<th class="is-idx">#</th>
					<th>รายการ</th>
					<th class="is-num">จำนวน</th>
					<th>หน่วย</th>
					<th v-if="!is_mr" class="is-num">ราคา/หน่วย</th>
					<th v-if="!is_mr" class="is-num">จำนวนเงิน</th>
					<th v-if="date_field">{{ date_label }}</th>
					<th><span class="ss-sr">ลบ</span></th>
				</tr>
			</thead>
			<TransitionGroup tag="tbody" name="ss-row">
				<tr
					v-for="(row, i) in items"
					:key="row.uid"
					:class="{ 'is-error': show_errors && error(row) }"
				>
					<td class="is-idx">{{ i + 1 }}</td>
					<td class="is-item">
						<b>{{ row.item_name || row.item_code }}</b>
						<small>{{ row.item_code }}</small>
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
							@keydown.enter.prevent="next($event, is_mr ? 'search' : 'rate')"
						/>
					</td>
					<td>
						<select v-model="row.uom" class="ss-cell" :aria-label="`หน่วย ${row.item_name}`">
							<option v-for="u in row.uoms" :key="u" :value="u">{{ u }}</option>
						</select>
					</td>
					<td v-if="!is_mr">
						<input
							v-model.number="row.rate"
							class="ss-cell ss-cell--num"
							type="number"
							inputmode="decimal"
							min="0"
							step="any"
							:aria-label="`ราคา ${row.item_name}`"
							data-col="rate"
							@focus="$event.target.select()"
							@keydown.enter.prevent="next($event, 'search')"
						/>
					</td>
					<td v-if="!is_mr" class="is-num is-amount">{{ money(amount(row)) }}</td>
					<td v-if="date_field">
						<input
							v-model="row[date_field]"
							class="ss-cell"
							type="date"
							:aria-label="`${date_label} ${row.item_name}`"
						/>
					</td>
					<td class="is-del">
						<button
							type="button"
							class="ss-icon-btn ss-icon-btn--sm"
							:aria-label="`ลบ ${row.item_name}`"
							title="ลบแถว"
							@click="$emit('remove', row)"
						>
							<Icon name="trash" :size="16" />
						</button>
					</td>
				</tr>
			</TransitionGroup>
			<tfoot>
				<tr class="ss-grid-add">
					<td class="is-idx"><Icon name="plus" :size="15" :stroke="2.6" /></td>
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
										<template v-if="it.rate && !is_mr">{{ money(it.rate) }}</template>
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

	<!-- มือถือ: การ์ด -->
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
				</div>
				<button
					type="button"
					class="ss-icon-btn ss-icon-btn--sm ss-line-del"
					:aria-label="`ลบ ${row.item_name}`"
					@click="$emit('remove', row)"
				>
					<Icon name="trash" :size="17" />
				</button>
				<div class="ss-line-inputs" :class="{ 'is-qty-only': is_mr }">
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
					<label class="ss-field">
						<span class="ss-field-label">หน่วย</span>
						<select v-model="row.uom" class="ss-input">
							<option v-for="u in row.uoms" :key="u" :value="u">{{ u }}</option>
						</select>
					</label>
					<label v-if="!is_mr" class="ss-field">
						<span class="ss-field-label">ราคา/หน่วย</span>
						<input
							v-model.number="row.rate"
							class="ss-input ss-input--num"
							type="number"
							inputmode="decimal"
							min="0"
							step="any"
							@focus="$event.target.select()"
						/>
					</label>
					<div v-if="!is_mr" class="ss-line-amount">
						<span class="ss-field-label">จำนวนเงิน</span>
						<b>{{ money(amount(row)) }}</b>
					</div>
				</div>
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
import { money } from "../../api.js";

const props = defineProps({
	items: { type: Array, required: true },
	wide: Boolean,
	is_mr: Boolean,
	// ช่องวันที่รายแถว (schedule_date / delivery_date) ไม่มี = ไม่แสดงคอลัมน์
	date_field: String,
	date_label: String,
	show_errors: Boolean,
	// (txt) => Promise<items> จาก site_docs.search_items
	search_fn: { type: Function, required: true },
});
const emit = defineEmits(["add", "remove", "browse"]);

const root = ref(null);
const search_input = ref(null);
const txt = ref("");
const results = ref([]);
const loading = ref(false);
const open = ref(false);
const active = ref(0);
let timer = null;
let request = 0;

// คอลัมน์ที่ช่องค้นหาคลุม (ทุกคอลัมน์ยกเว้น # และปุ่มลบ)
const span = computed(() => 3 + (props.is_mr ? 0 : 2) + (props.date_field ? 1 : 0));

const amount = (row) => (Number(row.qty) || 0) * (Number(row.rate) || 0);
function error(row) {
	return Number(row.qty) > 0 ? "" : "ใส่จำนวนมากกว่า 0";
}

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
	const inputs = root.value?.querySelectorAll('tbody tr:last-child input[data-col="qty"]');
	inputs?.[0]?.focus();
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
