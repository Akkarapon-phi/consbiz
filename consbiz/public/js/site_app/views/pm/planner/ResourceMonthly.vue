<!-- สรุปปริมาณที่ใช้แต่ละเดือนแยกตาม Item: วัสดุตามหน่วยของแผน, คน/เครื่องจักร = คน-วัน / คัน-วัน (ชี้ดูจำนวนสูงสุดต่อวัน)
     คำนวณที่ resource_rows.js monthly_usage ค่าตามแผนที่กำลังแสดงอยู่ -->
<template>
	<div class="pl-board">
		<Empty v-if="!usage.months.length" icon="users" title="ยังไม่มีแผนทรัพยากร" text="เพิ่มคน เครื่องจักร หรือวัสดุที่แท็บทรัพยากรของงาน" />
		<div v-else class="rb-month">
			<table>
				<thead>
					<tr>
						<th class="is-name">รายการ</th>
						<th class="is-unit">หน่วย</th>
						<th class="is-total">รวม</th>
						<th v-for="month in usage.months" :key="month.key">{{ month.label }}</th>
					</tr>
				</thead>
				<tbody v-for="section in usage.sections" :key="section.key">
					<tr class="is-section">
						<th class="is-name"><Icon :name="section.icon" :size="14" /> {{ section.label }}</th>
						<td class="is-unit"></td>
						<td class="is-total"></td>
						<td :colspan="usage.months.length"></td>
					</tr>
					<tr v-for="row in section.rows" :key="row.key">
						<th class="is-name" :title="row.code || row.label">{{ row.label }}</th>
						<td class="is-unit">{{ row.unit }}</td>
						<td class="is-total">{{ qty(row.total) }}</td>
						<td v-for="month in usage.months" :key="month.key" :title="peak_title(row, month)">
							{{ qty(row.values.get(month.key)) }}
						</td>
					</tr>
				</tbody>
			</table>
		</div>
	</div>
</template>

<script setup>
import { computed } from "vue";
import Icon from "../../../../shared/components/Icon.vue";
import Empty from "../../../../shared/components/Empty.vue";
import { monthly_usage } from "./resource_rows.js";

const props = defineProps({ p: { type: Object, required: true } });

const usage = computed(() => monthly_usage(props.p));
const format = new Intl.NumberFormat("en-US", { maximumFractionDigits: 2 });
const qty = (value) => (value && Math.abs(value) >= 0.005 ? format.format(value) : "");
function peak_title(row, month) {
	const peak = row.peaks?.get(month.key);
	return peak ? `${row.label} ${month.label}\nสูงสุด ${format.format(peak)} ต่อวัน` : "";
}
</script>
