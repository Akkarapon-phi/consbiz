<!-- แผงข้อมูลของหมวดทรัพยากร view: material (วัสดุที่ต้องสั่ง) / supply (ยอดวัสดุของโครงการ) / people (คน/เครื่องจักร) / gantt / monthly
     request_project = รหัสโครงการ: ติ๊กเลือกวัสดุที่ยังไม่ได้ขอแล้วกด "ขอซื้อ" ได้ (เฉพาะผู้ที่สร้างใบขอซื้อได้ p.data.can_request)
     เปิดฟอร์มใบขอซื้อใหม่พร้อมรายการเฉพาะส่วนที่ยังขาด ยังไม่บันทึกจนกว่าผู้ใช้จะกดบันทึก/ส่งเอง -->
<template>
	<div class="pl-board-host">
		<MaterialOrders v-if="view === 'material'" :p="p" :selectable="can_request" :selected="selected" />
		<MaterialSupply v-else-if="view === 'supply'" :p="p" />
		<ResourcePeople v-else-if="view === 'people'" :p="p" />
		<template v-else-if="view === 'gantt'">
			<Segmented v-model="settings.scale" :options="SCALE_OPTIONS" class="pl-seg" />
			<ResourceBoard :p="p" :settings="settings" />
		</template>
		<ResourceMonthly v-else :p="p" />
		<div v-if="view === 'material' && can_request && requestable.length" class="rb-request">
			<span><b>{{ selected.size }}</b> / {{ requestable.length }} รายการ</span>
			<button type="button" class="pl-tool is-small" :disabled="!due.length" @click="select_due">
				เลือกที่ถึงกำหนด ({{ due.length }})
			</button>
			<button type="button" class="pl-tool is-small" :disabled="!selected.size" @click="selected.clear()">ล้าง</button>
			<button type="button" class="ss-btn ss-btn--primary pl-save" :disabled="!selected.size" @click="send">
				ขอซื้อ
			</button>
		</div>
	</div>
</template>

<script setup>
import { computed, reactive, watch } from "vue";
import Segmented from "../../../../shared/components/Segmented.vue";
import { open_plan_request } from "../../../../shared/docs/kinds.js";
import MaterialOrders from "./MaterialOrders.vue";
import MaterialSupply from "./MaterialSupply.vue";
import ResourcePeople from "./ResourcePeople.vue";
import ResourceBoard from "./ResourceBoard.vue";
import ResourceMonthly from "./ResourceMonthly.vue";
import { PREP_DUE_DAYS, plan_groups } from "./resource_rows.js";

const props = defineProps({
	p: { type: Object, required: true },
	view: { type: String, default: "material" },
	request_project: { type: String, default: null },
});

const SCALE_OPTIONS = [
	{ value: "day", label: "วัน" },
	{ value: "week", label: "สัปดาห์" },
	{ value: "month", label: "เดือน" },
];
const settings = reactive({ scale: "week", zoom: 1 });
const selected = reactive(new Set());

const can_request = computed(() => Boolean(props.request_project && props.p.data?.can_request));
const requestable = computed(() =>
	plan_groups(props.p)
		.flatMap((group) => group.items.flatMap((item) => item.usages))
		.filter((usage) => usage.requestable)
);
const due = computed(() => requestable.value.filter((usage) => usage.target - props.p.cutoff_day <= PREP_DUE_DAYS));

// แถวที่ขอครบแล้ว (หลังโหลดใหม่) ไม่คงไว้ในรายการที่เลือก
watch(requestable, (rows) => {
	const names = new Set(rows.map((usage) => usage.row.name));
	for (const name of [...selected]) if (!names.has(name)) selected.delete(name);
});

function select_due() {
	due.value.forEach((usage) => selected.add(usage.row.name));
}

function send() {
	open_plan_request(props.request_project, [...selected]);
}
</script>
