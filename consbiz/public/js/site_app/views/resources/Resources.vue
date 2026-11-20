<!-- เมนูทรัพยากรของหมวดแผนงาน: tab วัสดุที่ต้องสั่ง / ยอดวัสดุ / คนและเครื่องจักร / Gantt / สรุปรายเดือน
     แต่ละ tab คือ view ของตัวเอง (URL เดิม, sections.js tab.sub) ทุก tab คือหน้านี้ แสดงตามชื่อ view
     ปุ่มขอซื้อแสดงตามสิทธิ์สร้างใบขอซื้อ (p.data.can_request) -->
<template>
	<div>
		<TopBar title="ทรัพยากร" :subtitle="state.project?.project_name">
			<template #actions>
				<button
					v-if="pane === 'material' && boot.sections.includes('buy')"
					type="button"
					class="ss-icon-btn"
					aria-label="ดูใบขอซื้อของโครงการ"
					title="ดูใบขอซื้อของโครงการ"
					@click="go('mr', { filter: 'all' })"
				>
					<Icon name="clipboard" :size="20" />
				</button>
				<button
					type="button"
					class="ss-icon-btn"
					:class="{ 'is-spinning': board.planner.loading }"
					aria-label="โหลดใหม่"
					@click="load_board(board, { force: true })"
				>
					<Icon name="refresh" :size="20" />
				</button>
			</template>
		</TopBar>
		<div class="ss-content">
			<ListHead v-if="wide" class="ss-res-head" :model-value="view" :tabs="TABS" @update:model-value="open_pane" />
			<div v-else class="ss-res-head">
				<Segmented :model-value="view" :options="TABS" @update:model-value="open_pane" />
			</div>
			<Skeleton v-if="!board.loaded.value" :rows="6" />
			<Empty
				v-else-if="!board.planner.data"
				icon="layers"
				title="โครงการนี้ยังไม่มีแผนงาน"
				text="แผนทรัพยากรอ้างงานในแผนงานก่อสร้าง สร้างแผนงานก่อน"
			/>
			<ResourcePane v-else :p="board.planner" :view="pane" :request_project="state.project.name" />
		</div>
	</div>
</template>

<script setup>
import Icon from "../../../shared/components/Icon.vue";
import TopBar from "../../../shared/components/TopBar.vue";
import Skeleton from "../../../shared/components/Skeleton.vue";
import Empty from "../../../shared/components/Empty.vue";
import Segmented from "../../../shared/components/Segmented.vue";
import ResourcePane from "../pm/planner/ResourcePane.vue";
import ListHead from "../../../shared/components/ListHead.vue";
import { boot, go, state } from "../../../shared/api.js";
import { use_wide } from "../../../shared/table.js";
import { load_board, resource_board } from "./resource_board.js";

const PANES = {
	resources: { pane: "material", title: "วัสดุที่ต้องสั่ง", short: "ต้องสั่ง" },
	"resource-supply": { pane: "supply", title: "ยอดวัสดุ", short: "ยอดวัสดุ" },
	"resource-people": { pane: "people", title: "คนและเครื่องจักร", short: "คน/เครื่อง" },
	"resource-gantt": { pane: "gantt", title: "Gantt ทรัพยากร", short: "Gantt" },
	"resource-monthly": { pane: "monthly", title: "สรุปรายเดือน", short: "รายเดือน" },
};
const wide = use_wide();
const TABS = Object.entries(PANES).map(([value, p]) => ({ value, label: wide.value ? p.title : p.short }));
// สลับ tab = เปลี่ยน view (แทนที่ประวัติ ปุ่มย้อนกลับไม่ไล่ทีละ tab) ข้อมูลใช้ board ชุดเดิม ไม่โหลดใหม่
const open_pane = (value) => value !== view && go(value, {}, { replace: true });

// จับค่าตอนสร้างหน้า: ระหว่าง animation ออก route เปลี่ยนแล้ว หน้าเก่าต้องแสดงของเดิม
const view = state.route.view;
const pane = PANES[view].pane;
const board = resource_board(state.project.name);
load_board(board);
</script>
