<!-- หมวดทรัพยากร: วัสดุที่ต้องสั่ง / ยอดวัสดุ / คนและเครื่องจักร / Gantt / สรุปรายเดือน ทุกเมนูคือหน้านี้ แสดงตามชื่อ view
     ปุ่มขอซื้อแสดงตามสิทธิ์สร้างใบขอซื้อ (p.data.can_request) -->
<template>
	<div>
		<TopBar :title="PANES[view].title" :subtitle="state.project?.project_name">
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
import ResourcePane from "../pm/planner/ResourcePane.vue";
import { boot, go, state } from "../../../shared/api.js";
import { load_board, resource_board } from "./resource_board.js";

const PANES = {
	resources: { pane: "material", title: "วัสดุที่ต้องสั่ง" },
	"resource-supply": { pane: "supply", title: "ยอดวัสดุ" },
	"resource-people": { pane: "people", title: "คนและเครื่องจักร" },
	"resource-gantt": { pane: "gantt", title: "Gantt ทรัพยากร" },
	"resource-monthly": { pane: "monthly", title: "สรุปรายเดือน" },
};

// จับค่าตอนสร้างหน้า: ระหว่าง animation ออก route เปลี่ยนแล้ว หน้าเก่าต้องแสดงของเดิม
const view = state.route.view;
const pane = PANES[view].pane;
const board = resource_board(state.project.name);
load_board(board);
</script>
