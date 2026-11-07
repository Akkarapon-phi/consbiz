<!-- การ์ดเอกสารจัดซื้อ/ขายในรายการ: คู่ค้า เลขที่ วันที่ ยอดเงิน สถานะ และความคืบหน้า (รับของ/วางบิล) -->
<template>
	<button
		type="button"
		class="ss-card"
		:class="{ 'is-late': row.overdue }"
		:style="{ '--i': i }"
		@click="go(`${config.section}-doc`, { kind, name: row.name })"
	>
		<!-- 2 บรรทัดเต็มความกว้าง (มือถือไม่บีบชื่อคู่ค้า): ชื่อ + สถานะ / เลขที่ วันที่ + ยอดเงิน -->
		<div class="ss-doc-row">
			<span class="ss-doc-title">{{ row.party || row.title || row.name }}</span>
			<span class="ss-tag" :class="`tone-${row.status_tone}`">{{ row.status_label }}</span>
		</div>
		<div class="ss-doc-row is-sub">
			<span class="ss-doc-meta"
				>{{ row.name }} · {{ thai_date(row.date, { year: true })
				}}<template v-if="row.bill_no"> · บิล {{ row.bill_no }}</template></span
			>
			<b v-if="row.amount !== undefined" class="ss-doc-money">{{ money(row.amount) }}</b>
		</div>
		<div v-if="progress.length || show_due || row.outstanding" class="ss-chips ss-chips--wrap">
			<span v-if="row.outstanding && row.outstanding !== row.amount" class="ss-chip"
				>ค้าง <b>{{ money(row.outstanding) }}</b></span
			>
			<span v-if="show_due" class="ss-due" :class="{ 'is-late': row.overdue }">
				<Icon :name="row.overdue ? 'alert' : 'clock'" :size="13" />
				{{ config.due || "กำหนด" }} {{ relative_date(row.due) }}
			</span>
			<span v-for="p in progress" :key="p.label" class="ss-chip ss-chip--pct">
				{{ p.label }} <b>{{ Math.round(p.value) }}%</b>
				<i :style="{ width: `${Math.min(100, p.value)}%` }"></i>
			</span>
		</div>
	</button>
</template>

<script setup>
import { computed } from "vue";
import Icon from "../components/Icon.vue";
import { DOC_KINDS } from "./kinds.js";
import { go, money, relative_date, thai_date } from "../api.js";

const props = defineProps({ row: Object, kind: String, i: { type: Number, default: 0 } });
const config = computed(() => DOC_KINDS[props.kind]);
const progress = computed(() =>
	props.row.docstatus === 1
		? (config.value.progress || [])
				// null = ไม่มีขั้นนี้ (สั่งซื้อของใบขอซื้อผู้ว่าจ้างจัดหา)
				.filter(([field]) => props.row[field] != null)
				.map(([field, label]) => ({ label, value: Number(props.row[field]) || 0 }))
		: []
);
// วันครบกำหนดแสดงเมื่อเอกสารยังรอดำเนินการ (สถานะสีเหลือง/แดง)
const show_due = computed(
	() => props.row.due && props.row.docstatus === 1 && ["amber", "rose"].includes(props.row.status_tone)
);
</script>
