<!-- ตาราง "ยอดวัสดุของโครงการ" 1 แถวต่อ Item หน่วยสต็อก: ต้องใช้ เทียบขอ/สั่ง/รับ แยกซื้อเองกับผู้ว่าจ้างจัดหา (ตรงกับตารางใน Tab ทรัพยากรของระบบเต็ม) -->
<template>
	<div class="pl-board">
		<Empty v-if="!rows.length" icon="cart" title="ยังไม่มีแผนจัดซื้อวัสดุ" text="ใส่วัสดุของแต่ละงานที่แท็บทรัพยากรของงาน" />
		<div v-else class="rb-month">
			<table>
				<thead>
					<tr>
						<th class="is-name">วัสดุ</th>
						<th class="is-text">หน่วย</th>
						<th>ต้องใช้</th>
						<th>ขอซื้อ</th>
						<th>สั่งซื้อ</th>
						<th>รับ</th>
						<th>ผู้ว่าจ้าง: ขอ</th>
						<th>ผู้ว่าจ้าง: รับ</th>
						<th>ยังขาด</th>
					</tr>
				</thead>
				<tbody>
					<tr v-for="row in rows" :key="row.item_code">
						<th class="is-name" :title="row.item_code">{{ row.item_label }}</th>
						<td class="is-text">{{ row.stock_uom }}</td>
						<td class="is-total">{{ qty(row.need) }}</td>
						<td :title="draft_title(row)">{{ cell(row.purchase, "requested") }}</td>
						<td>{{ cell(row.purchase, "ordered") }}</td>
						<td>{{ cell(row.purchase, "received") }}</td>
						<td>{{ cell(row.customer, "requested") }}</td>
						<td>{{ cell(row.customer, "received") }}</td>
						<td :class="{ 'is-short': row.short > 0 }">{{ row.short > 0 ? qty(row.short) : "-" }}</td>
					</tr>
				</tbody>
			</table>
		</div>
	</div>
</template>

<script setup>
import { computed } from "vue";
import Empty from "../../../../shared/components/Empty.vue";
import { num } from "../../../../shared/api.js";
import { material_supply } from "./resource_rows.js";

const props = defineProps({ p: { type: Object, required: true } });

const rows = computed(() => material_supply(props.p));
const qty = (value) => num(value || 0);
const cell = (supply, stage) => (supply?.[stage] ? qty(supply[stage]) : "-");
const draft_title = (row) => (row.purchase?.draft ? `รวมใบร่าง ${qty(row.purchase.draft)}` : "");
</script>
