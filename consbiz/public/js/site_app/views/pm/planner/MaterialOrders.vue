<!-- ตาราง "วัสดุที่ต้องสั่ง" เรียงตามวันต้องสั่ง (ตรงกับตารางใน Tab ทรัพยากรของระบบเต็ม) ติ๊กเลือกแถวเพื่อขอซื้อได้เมื่อ selectable -->
<template>
	<div class="pl-board">
		<Empty v-if="!orders.length" icon="cart" title="ยังไม่มีแผนจัดซื้อวัสดุ" text="ใส่วัสดุของแต่ละงานที่แท็บทรัพยากรของงาน" />
		<template v-else>
			<div class="ss-filters rb-filters">
				<button
					v-for="option in FILTERS"
					:key="option.value"
					type="button"
					class="ss-filter"
					:class="{ 'is-active': filter === option.value }"
					@click="filter = option.value"
				>
					{{ option.label }} <span class="ss-filter-count">{{ count(option.value) }}</span>
				</button>
			</div>
			<Empty v-if="!shown.length" icon="sparkles" title="ไม่มีรายการในตัวกรองนี้" />
			<div v-else class="rb-month">
				<table>
					<thead>
						<tr>
							<th class="is-name">วัสดุ</th>
							<th class="is-text">งาน</th>
							<th>จำนวน</th>
							<th>Lead Time</th>
							<th class="is-text">ต้องสั่งภายใน</th>
							<th class="is-text">ต้องถึงภายใน</th>
							<th class="is-text">สถานะ</th>
							<th>ขอแล้ว</th>
							<th>สั่งซื้อ</th>
							<th>รับแล้ว</th>
							<th>ยังขาด</th>
						</tr>
					</thead>
					<tbody>
						<tr v-for="order in shown" :key="order.key">
							<th class="is-name" :title="order.row.item_code">
								<input
									v-if="selectable && order.requestable"
									type="checkbox"
									class="rb-check"
									:checked="selected.has(order.row.name)"
									:aria-label="`เลือก ${order.row.item_label || order.row.item_code}`"
									@change="toggle(order)"
								/>
								{{ order.row.item_label || order.row.item_code }}
							</th>
							<td class="is-text rb-task" :title="order.label">{{ order.label }}</td>
							<td>{{ qty(order.row.qty) }} {{ order.row.uom }}</td>
							<td>{{ order.row.lead_time_days || 0 }} วัน</td>
							<td class="is-text">{{ date(order.target) }}</td>
							<td class="is-text">{{ date(order.required_by) }}</td>
							<td class="is-text"><span class="ss-tag" :class="`tone-${order.pill.tone}`">{{ order.pill.label }}</span></td>
							<td>{{ stage(order, "requested") }}</td>
							<td>{{ stage(order, "ordered") }}</td>
							<td>{{ stage(order, "received") }}</td>
							<td :class="{ 'is-short': order.shortfall > 0 }">{{ order.shortfall > 0 ? qty(order.shortfall) : "-" }}</td>
						</tr>
					</tbody>
				</table>
			</div>
		</template>
	</div>
</template>

<script setup>
import { computed, ref } from "vue";
import Empty from "../../../../shared/components/Empty.vue";
import { num, thai_date } from "../../../../shared/api.js";
import { from_day } from "../../../../construction_management/schedule.js";
import { material_orders } from "./resource_rows.js";

const props = defineProps({
	p: { type: Object, required: true },
	selectable: Boolean,
	selected: { type: Object, default: () => new Set() },
});

const FILTERS = [
	{ value: "todo", label: "ต้องสั่ง" },
	{ value: "later", label: "ข้างหน้า" },
	{ value: "done", label: "ขอครบแล้ว" },
	{ value: "all", label: "ทั้งหมด" },
];

const orders = computed(() => material_orders(props.p));
// ไม่มีรายการที่ต้องสั่ง: เปิดทั้งหมด
const filter = ref(orders.value.some((order) => order.bucket === "todo") ? "todo" : "all");
const matches = (order, value) => value === "all" || order.bucket === value;
const count = (value) => orders.value.filter((order) => matches(order, value)).length;
const shown = computed(() => orders.value.filter((order) => matches(order, filter.value)));

const qty = (value) => num(value || 0);
const date = (day) => (day === null || day === undefined ? "-" : thai_date(from_day(day), { year: true }));
const stage = (order, key) => (order.coverage?.[key] ? qty(order.coverage[key]) : "-");

function toggle(order) {
	if (props.selected.has(order.row.name)) props.selected.delete(order.row.name);
	else props.selected.add(order.row.name);
}
</script>
