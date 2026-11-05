<template>
	<!-- รายการเอกสารจัดซื้อ/ขายแบบตาราง (แท็บเล็ต/จอใหญ่) มือถือใช้การ์ด (DocCard.vue)
	     แท็บเล็ต: ซ่อน .col-opt (กำหนดส่ง/ความคืบหน้า) และย้ายสถานะไปใต้เลขที่ (.col-compact) ให้พอดีความกว้าง -->
	<div class="ss-table-wrap">
		<table class="ss-table">
			<thead>
				<tr>
					<th>เลขที่</th>
					<th>{{ config.party || "เรื่อง" }}</th>
					<th class="col-date">วันที่</th>
					<th class="col-opt">{{ config.due || "ต้องการภายใน" }}</th>
					<th v-for="[, label] in config.progress || []" :key="label" class="col-opt">
						{{ label }}
					</th>
					<th v-if="has_amount" class="is-num">ยอดเงิน</th>
					<th v-if="has_outstanding" class="is-num">ค้าง</th>
					<th class="col-status">สถานะ</th>
				</tr>
			</thead>
			<tbody>
				<tr
					v-for="(row, i) in rows"
					:key="row.name"
					:class="{ 'is-late': row.overdue }"
					:style="{ '--i': Math.min(i, 20) }"
					tabindex="0"
					@click="open(row)"
					@keydown.enter="open(row)"
				>
					<td class="is-id">
						{{ row.name }}
						<small v-if="row.bill_no">บิล {{ row.bill_no }}</small>
						<small class="col-compact-date">{{ thai_date(row.date, { year: true }) }}</small>
						<span class="ss-tag col-compact" :class="`tone-${row.status_tone}`">{{
							row.status_label
						}}</span>
					</td>
					<td class="is-party">
						<span>{{ row.party || row.title || row.name }}</span>
						<small v-if="row.project && state.doc_scope === 'all'">{{ row.project }}</small>
					</td>
					<td class="is-date col-date">{{ thai_date(row.date, { year: true }) }}</td>
					<td class="is-date col-opt" :class="{ 'is-due': row.overdue }">
						<template v-if="row.due">{{ thai_date(row.due, { year: true }) }}</template>
					</td>
					<td v-for="[field] in config.progress || []" :key="field" class="col-opt">
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
				</tr>
			</tbody>
		</table>
	</div>
</template>

<script setup>
import { computed } from "vue";
import { DOC_KINDS } from "../../sections.js";
import { go, money, state, thai_date } from "../../api.js";

const props = defineProps({ rows: Array, kind: String });
const config = computed(() => DOC_KINDS[props.kind]);
const has_amount = computed(() => props.rows.some((r) => r.amount !== undefined));
const has_outstanding = computed(() => props.rows.some((r) => r.outstanding !== undefined));

const open = (row) => go(`${config.value.section}-doc`, { kind: props.kind, name: row.name });
</script>
