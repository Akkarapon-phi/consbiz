<template>
	<!-- ตารางเอกสารจัดซื้อ/ขาย (แท็บเล็ต/จอใหญ่) มือถือใช้การ์ด (DocCard.vue)
	     หัวคอลัมน์กดเรียงได้ (emit sort) ช่องเลือกหลายแถว (toggle / toggle-all) ปุ่ม PDF/เปิดระบบเต็มโผล่เมื่อชี้แถว
	     แท็บเล็ต: ซ่อน .col-opt และย้ายสถานะ/วันที่ไปใต้เลขที่ (.col-compact) ให้พอดีความกว้าง -->
	<div class="ss-table-wrap">
		<table class="ss-table ss-table--list">
			<thead>
				<tr>
					<th class="col-check">
						<input
							type="checkbox"
							class="ss-check"
							aria-label="เลือกทั้งหมด"
							:checked="all_checked"
							:indeterminate.prop="some_checked && !all_checked"
							@change="$emit('toggle-all')"
						/>
					</th>
					<th v-for="c in columns" :key="c.key" :class="c.class" :aria-sort="aria_sort(c)">
						<button v-if="c.sort" type="button" class="ss-th-sort" @click="$emit('sort', c.sort)">
							{{ c.label }}
							<Icon
								:name="
									sort === c.sort
										? order === 'asc'
											? 'chevron-up'
											: 'chevron-down'
										: 'arrow-up-down'
								"
								:size="13"
								:stroke="2.4"
								:class="{ 'is-idle': sort !== c.sort }"
							/>
						</button>
						<template v-else>{{ c.label }}</template>
					</th>
					<th class="col-actions"><span class="ss-sr">คำสั่ง</span></th>
				</tr>
			</thead>
			<tbody>
				<tr
					v-for="(row, i) in rows"
					:key="row.name"
					:class="{ 'is-late': row.overdue, 'is-selected': selected.has(row.name) }"
					:style="{ '--i': Math.min(i, 20) }"
					tabindex="0"
					@click="open(row)"
					@keydown.enter="open(row)"
				>
					<td class="col-check" @click.stop>
						<input
							type="checkbox"
							class="ss-check"
							:aria-label="`เลือก ${row.name}`"
							:checked="selected.has(row.name)"
							@change="$emit('toggle', row.name)"
						/>
					</td>
					<td class="is-id">
						{{ row.name }}
						<small v-if="row.bill_no">บิล {{ row.bill_no }}</small>
						<small class="col-compact-date">{{ thai_date(row.date, { year: true }) }}</small>
						<span class="ss-tag col-compact" :class="`tone-${row.status_tone}`">{{
							row.status_label
						}}</span>
					</td>
					<td class="is-party" :title="row.party || row.title">
						<span>{{ row.party || row.title || row.name }}</span>
						<small v-if="row.project && state.doc_scope === 'all'">{{ row.project }}</small>
					</td>
					<td class="is-date col-date">{{ thai_date(row.date, { year: true }) }}</td>
					<td v-if="config.due" class="is-date col-opt" :class="{ 'is-due': row.overdue }">
						<template v-if="row.due">{{ thai_date(row.due, { year: true }) }}</template>
					</td>
					<td v-for="[field] in config.progress || []" :key="field" class="col-opt col-progress">
						<span v-if="row.docstatus === 1" class="ss-table-pct">
							<i><b :style="{ width: `${Math.min(100, row[field] || 0)}%` }"></b></i>
							{{ Math.round(row[field] || 0) }}%
						</span>
					</td>
					<td v-if="has_amount" class="is-num">{{ money(row.amount) }}</td>
					<td v-if="has_outstanding" class="is-num" :class="{ 'is-due': row.overdue }">
						<template v-if="row.outstanding">{{ money(row.outstanding) }}</template>
					</td>
					<td class="col-status">
						<span class="ss-tag" :class="`tone-${row.status_tone}`">{{ row.status_label }}</span>
					</td>
					<td class="col-actions" @click.stop>
						<div class="ss-row-tools">
							<button
								type="button"
								class="ss-icon-btn ss-icon-btn--sm"
								:aria-label="`PDF ${row.name}`"
								title="ดู PDF"
								@click="$emit('pdf', row)"
							>
								<Icon name="file" :size="16" />
							</button>
							<a
								class="ss-icon-btn ss-icon-btn--sm"
								:href="desk_url(config.doctype, row.name)"
								:aria-label="`เปิด ${row.name} ในระบบเต็ม`"
								title="เปิดในระบบเต็ม"
							>
								<Icon name="external" :size="16" />
							</a>
						</div>
					</td>
				</tr>
			</tbody>
		</table>
	</div>
</template>

<script setup>
import { computed } from "vue";
import Icon from "../../components/Icon.vue";
import { DOC_KINDS } from "../../sections.js";
import { desk_url, go, money, state, thai_date } from "../../api.js";

const props = defineProps({
	rows: Array,
	kind: String,
	sort: String,
	order: String,
	selected: { type: Set, default: () => new Set() },
});
defineEmits(["sort", "toggle", "toggle-all", "pdf"]);

const config = computed(() => DOC_KINDS[props.kind]);
const has_amount = computed(() => props.kind !== "mr");
const has_outstanding = computed(() => ["pi", "si"].includes(props.kind));
const all_checked = computed(() => props.rows.length && props.rows.every((r) => props.selected.has(r.name)));
const some_checked = computed(() => props.rows.some((r) => props.selected.has(r.name)));

// หัวคอลัมน์ (ลำดับตรงกับ <td>) sort = key ของ site_docs.SORTS
const columns = computed(() => {
	const c = config.value;
	return [
		{ key: "name", label: "เลขที่", sort: "name" },
		{ key: "party", label: c.party || "เรื่อง", sort: c.party ? "party" : null },
		{ key: "date", label: "วันที่", sort: "date", class: "col-date" },
		...(c.due ? [{ key: "due", label: c.due, sort: "due", class: "col-opt" }] : []),
		...(c.progress || []).map(([field, label]) => ({ key: field, label, class: "col-opt col-progress" })),
		...(has_amount.value ? [{ key: "amount", label: "ยอดเงิน", sort: "amount", class: "is-num" }] : []),
		...(has_outstanding.value
			? [{ key: "outstanding", label: "ค้าง", sort: "outstanding", class: "is-num" }]
			: []),
		{ key: "status", label: "สถานะ", sort: "status", class: "col-status" },
	];
});

function aria_sort(column) {
	if (!column.sort || props.sort !== column.sort) return undefined;
	return props.order === "asc" ? "ascending" : "descending";
}

const open = (row) => go(`${config.value.section}-doc`, { kind: props.kind, name: row.name });
</script>
