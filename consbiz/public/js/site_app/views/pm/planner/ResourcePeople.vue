<!-- ตารางคน/เครื่องจักร: ช่วงใช้งาน จำนวนสูงสุดต่อวัน ยอดรวม และกำหนดจองครั้งถัดไป (คำนวณจาก plan_groups ชุดเดียวกับ Gantt ทรัพยากร) -->
<template>
	<div class="pl-board">
		<Empty v-if="!rows.length" icon="users" title="ยังไม่มีแผนคนและเครื่องจักร" text="ใส่คนและเครื่องจักรของแต่ละงานที่แท็บทรัพยากรของงาน" />
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
			<div class="rb-month">
				<table>
					<thead>
						<tr>
							<th class="is-name">รายการ</th>
							<th class="is-text">ประเภท</th>
							<th class="is-text">ช่วงใช้งาน</th>
							<th>สูงสุด/วัน</th>
							<th>รวม</th>
							<th>งาน</th>
							<th class="is-text">ต้องจองภายใน</th>
							<th class="is-text">สถานะ</th>
							<th class="is-text">งานถัดไป</th>
						</tr>
					</thead>
					<tbody>
						<tr v-for="row in shown" :key="row.key">
							<th class="is-name" :title="row.label">{{ row.label }}</th>
							<td class="is-text">{{ row.type.label }}</td>
							<td class="is-text">{{ range(row) }}</td>
							<td>{{ num(row.peak) }} {{ row.type.unit }}</td>
							<td>{{ num(row.total) }} {{ row.type.total_unit }}</td>
							<td>{{ row.task_count }}</td>
							<td class="is-text">{{ date(row.next?.target) }}</td>
							<td class="is-text">
								<span v-if="row.pill" class="ss-tag" :class="`tone-${row.pill.tone}`">{{ row.pill.label }}</span>
								<template v-else>-</template>
							</td>
							<td class="is-text rb-task" :title="row.next?.label">{{ row.next?.label || "-" }}</td>
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
import { people_rows } from "./resource_rows.js";

const props = defineProps({ p: { type: Object, required: true } });

const FILTERS = [
	{ value: "all", label: "ทั้งหมด" },
	{ value: "Labour", label: "แรงงาน" },
	{ value: "Equipment", label: "เครื่องจักร" },
];

const rows = computed(() => people_rows(props.p));
const filter = ref("all");
const matches = (row, value) => value === "all" || row.type.key === value;
const count = (value) => rows.value.filter((row) => matches(row, value)).length;
const shown = computed(() => rows.value.filter((row) => matches(row, filter.value)));

const date = (day) => (day === null || day === undefined ? "-" : thai_date(from_day(day), { year: true }));
const range = (row) => (row.first === null ? "ยังไม่มีวันในแผน" : `${date(row.first)} – ${date(row.last)}`);
</script>
