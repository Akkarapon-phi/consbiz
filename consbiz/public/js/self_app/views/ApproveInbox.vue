<!-- โมดูลอนุมัติ = ที่รวมเอกสารรออนุมัติของทุกโมดูล เมนูย่อย = โมดูล (approve = ทุกโมดูล, approve-<โมดูล> เช่น approve-hr)
     tab = ชนิดเอกสาร, ปุ่มสลับ รออนุมัติ / พิจารณาแล้ว (31 วัน) อยู่ขวาของแถบ tab (มือถือ = เหนือ tab)
     แต่ละโมดูลอนุมัติในหน้าของตัวเองได้ด้วย ApprovalSheet ชุดเดียวกัน
     ชนิด (KINDS ตรงกับ consbiz/approvals.py): ใบลา / ลงเวลา / ใบเบิก / ใบเคลียร์-เบิกคืน แต่ละชนิดเห็นตามสิทธิ์ (boot.can.approve_<ชนิด>)
     แตะรายการ = แผงรายละเอียด + อนุมัติ/ไม่อนุมัติ (ไม่อนุมัติต้องมีเหตุผล) params.name = เปิดเอกสารนั้นทันที (จากการแจ้งเตือน) -->
<template>
	<div>
		<TopBar :title="page_title" no_project>
			<template #actions>
				<button
					v-if="!wide"
					type="button"
					class="ss-icon-btn"
					:class="{ 'is-spinning': loading }"
					aria-label="โหลดใหม่"
					@click="load"
				>
					<Icon name="refresh" :size="20" />
				</button>
			</template>
		</TopBar>

		<div class="ss-content">
			<div v-if="wide" class="ss-list-head">
				<StatusTabs v-model="tab" :options="tabs" />
				<div class="ss-list-tools">
					<Segmented v-model="mode" :options="MODES" />
					<button
						type="button"
						class="ss-icon-btn"
						:class="{ 'is-spinning': loading }"
						aria-label="โหลดใหม่"
						@click="load"
					>
						<Icon name="refresh" :size="17" />
					</button>
				</div>
			</div>
			<Segmented v-if="!wide" v-model="mode" :options="MODES" />
			<div v-if="!wide" class="ss-tabs">
				<button
					v-for="t in tabs"
					:key="t.value"
					type="button"
					class="ss-tab"
					:class="{ 'is-active': tab === t.value }"
					@click="tab = t.value"
				>
					{{ t.label }} <span class="ss-tab-count">{{ t.count }}</span>
				</button>
			</div>

			<Skeleton v-if="data === null" :rows="4" />
			<Empty
				v-else-if="!shown.length"
				icon="clipboard-check"
				:title="history ? 'ยังไม่มีเอกสารที่พิจารณาแล้ว' : 'ไม่มีเอกสารรออนุมัติ'"
				:text="history ? 'แสดงย้อนหลัง 31 วัน' : ''"
			/>
			<div v-else class="ss-list">
				<button
					v-for="(item, i) in shown"
					:key="item.key"
					type="button"
					class="ss-card ss-card--row"
					:style="{ '--i': Math.min(i, 20) }"
					@click="open(item)"
				>
					<span class="ss-avatar" :class="`tone-${tone(item.row.employee)}`">{{ initials(item.row.employee_name) }}</span>
					<span class="ss-card-main">
						<span class="ss-card-title">{{ item.row.employee_name }}</span>
						<span class="ss-card-meta">
							<span class="ss-tag" :class="`tone-${KINDS[item.kind].tone}`">{{ item.title }}</span>
							{{ item.sub }}
						</span>
					</span>
					<span class="ss-leave-side">
						<b v-if="item.amount != null" class="ss-money">{{ money(item.amount) }}</b>
						<span v-if="item.status" class="ss-tag" :class="`tone-${item.status.tone}`">{{ item.status.label }}</span>
					</span>
				</button>
			</div>
		</div>

		<ApprovalSheet :item="viewing" :history="history" @close="viewing = null" @done="on_done" />
	</div>
</template>

<script setup>
import { computed, inject, ref, watch } from "vue";
import Icon from "../../shared/components/Icon.vue";
import TopBar from "../../shared/components/TopBar.vue";
import Skeleton from "../../shared/components/Skeleton.vue";
import Empty from "../../shared/components/Empty.vue";
import StatusTabs from "../../shared/components/StatusTabs.vue";
import Segmented from "../../shared/components/Segmented.vue";
import ApprovalSheet from "../../shared/approvals/ApprovalSheet.vue";
import { inbox_items, KINDS, kinds_of, MODULES } from "../../shared/approvals/kinds.js";
import { use_wide } from "../../shared/table.js";
import { boot, call, initials, money, show_error, state, tone } from "../../shared/api.js";

const reload_summary = inject("reload_summary");
const params = state.route.params;
const MODES = [
	{ value: "pending", label: "รออนุมัติ" },
	{ value: "done", label: "พิจารณาแล้ว" },
];
const mode = ref("pending");
const history = computed(() => mode.value === "done");
// approve-hr = เฉพาะโมดูลบุคคล
const module = state.route.view.startsWith("approve-") ? state.route.view.slice(8) : null;
const page_title = module ? `อนุมัติ: ${MODULES[module]?.label || module}` : "อนุมัติทั้งหมด";

const data = ref(null);
const loading = ref(false);
const wide = use_wide();
const tab = ref("all");
const viewing = ref(null);

const items = computed(() => inbox_items(data.value, { history: history.value, module }));
const tabs = computed(() => [
	{ value: "all", label: "ทั้งหมด", count: items.value.length },
	...kinds_of(module)
		.filter((kind) => boot.can?.[`approve_${kind}`])
		.map((kind) => ({ value: kind, label: KINDS[kind].label, count: items.value.filter((i) => i.kind === kind).length })),
]);
const shown = computed(() => items.value.filter((i) => tab.value === "all" || i.kind === tab.value));

async function load() {
	loading.value = true;
	try {
		data.value = await call(history.value ? "consbiz.approvals.get_history" : "consbiz.approvals.get_inbox", { module });
		if (params.name && !viewing.value) {
			const item = items.value.find((i) => i.row.name === params.name);
			if (item) open(item);
		}
	} catch (error) {
		show_error(error);
		data.value ??= {};
	} finally {
		loading.value = false;
	}
}
load();
watch(mode, () => {
	data.value = null;
	tab.value = "all";
	load();
});

const open = (item) => (viewing.value = item);

async function on_done() {
	viewing.value = null;
	reload_summary?.("approve");
	await load();
}
</script>
