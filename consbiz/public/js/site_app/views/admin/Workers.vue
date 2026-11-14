<!-- ทะเบียนคนงานรายวันของโครงการ (consbiz.labour.get_workers) คลิกแถว = แก้ในแอป (WorkerSheet: ทีม ค่าแรง บัญชีธนาคาร)
     จอ ≥ 768 เลือกหลายคนแล้ว "ย้ายทีม" (set_team) ทีมใช้จัดกลุ่มในหน้าลงเวลา -->
<template>
	<div>
		<TopBar title="ทะเบียนคนงาน" :subtitle="state.project?.project_name">
			<template #search>
				<HeaderSearch v-if="wide" v-model="txt" placeholder="ค้นหาชื่อ ตำแหน่ง ผรม." />
			</template>
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
				<StatusTabs v-model="status" :options="tabs" />
				<div class="ss-list-tools">
					<button
						type="button"
						class="ss-icon-btn"
						:class="{ 'is-spinning': loading }"
						aria-label="โหลดใหม่"
						title="โหลดใหม่"
						@click="load"
					>
						<Icon name="refresh" :size="17" />
					</button>
					<button
						v-if="data?.can_create"
						type="button"
						class="ss-btn ss-btn--primary ss-list-create"
						@click="adding = true"
					>
						<Icon name="plus" :size="18" :stroke="2.6" />
						<span>คนงานใหม่</span>
					</button>
				</div>
			</div>
			<template v-else>
				<Segmented v-model="status" :options="tabs" />
				<input v-model="txt" class="ss-input wk-search" placeholder="ค้นหาชื่อ ตำแหน่ง ผรม." />
			</template>

			<Skeleton v-if="data === null" />
			<Empty
				v-else-if="!shown.length"
				icon="users"
				:title="data.rows.length ? 'ไม่พบคนงาน' : 'ยังไม่มีคนงานในโครงการนี้'"
			/>
			<DataTable
				v-else-if="wide"
				v-model:selected="selected"
				:rows="shown"
				:columns="COLUMNS"
				:selectable="!!data.can_create"
				@open="open"
			>
				<template #team="{ row }">{{ row.team || (row.payee ? row.payee : "–") }}</template>
				<template #worker_name="{ row }">
					<span class="ss-cell-main">{{ row.worker_name }}</span>
					<small>{{ row.name }}<template v-if="row.nationality"> · {{ row.nationality }}</template></small>
				</template>
				<template #payee="{ row }">{{ row.payee || "บริษัท" }}</template>
				<template #daily_rate="{ row }">{{ money(row.daily_rate) }}</template>
				<template #ot="{ row }">{{ row.ot_flat ? `เหมา ${money(row.ot_hourly_rate)}/ชม.` : "ตามกฎหมาย" }}</template>
				<template #sso_registered="{ row }">
					<span v-if="row.sso_registered" class="ss-tag tone-green">มี</span>
				</template>
			</DataTable>
			<div v-else class="ss-list">
				<button v-for="row in shown" :key="row.name" type="button" class="ss-card" @click="open(row)">
					<div class="ss-card-head">
						<span class="ss-card-main">
							<span class="ss-card-title">{{ row.worker_name }}</span>
							<span class="ss-card-meta">{{ [row.team, row.position, row.payee || "บริษัท"].filter(Boolean).join(" · ") }}</span>
						</span>
						<span class="ss-qty"><b>{{ money(row.daily_rate) }}</b><small>บาท/วัน</small></span>
					</div>
					<div class="ss-chips">
						<span v-if="row.ot_flat" class="ss-chip">OT เหมา {{ money(row.ot_hourly_rate) }}/ชม.</span>
						<span v-if="row.sso_registered" class="ss-tag tone-green">ประกันสังคม</span>
					</div>
				</button>
			</div>
		</div>

		<Teleport to="#ss-layer">
			<Transition name="ss-pop">
				<button v-if="!wide && data?.can_create" type="button" class="ss-fab" @click="adding = true">
					<Icon name="plus" :size="26" :stroke="2.6" />
					<span>คนงานใหม่</span>
				</button>
			</Transition>
		</Teleport>

		<Teleport to="#ss-layer">
			<Transition name="ss-bar">
				<div v-if="wide && selected.size" class="ss-bottom-bar ss-bulk-bar">
					<span class="ss-bar-summary">เลือก <b>{{ selected.size }}</b> คน</span>
					<button type="button" class="ss-btn ss-btn--ghost" @click="selected = new Set()">ยกเลิกเลือก</button>
					<button type="button" class="ss-btn ss-btn--primary" @click="open_move">ย้ายทีม</button>
				</div>
			</Transition>
		</Teleport>

		<Sheet :open="moving" title="ย้ายทีม" :subtitle="`${selected.size} คน`" @close="moving = false">
			<Picker
				v-model="target_team"
				label="ทีม/ชุด"
				:options="teams.map((t) => ({ value: t, label: t }))"
				placeholder="เลือกหรือพิมพ์ชื่อทีมใหม่"
				allow_text
				clearable
			/>
			<p class="ss-note">ว่าง = ไม่ระบุทีม (คนงานของ ผรม. จะอยู่ในทีมชื่อ ผรม.)</p>
			<template #footer>
				<div class="ss-sheet-actions">
					<button type="button" class="ss-btn ss-btn--primary ss-btn--block ss-btn--lg" :disabled="busy" @click="move">
						ย้าย {{ selected.size }} คน
					</button>
				</div>
			</template>
		</Sheet>

		<WorkerSheet
			:open="adding || !!editing"
			:name="editing"
			:project="state.project?.name"
			:teams="teams"
			@close="adding = false; editing = null"
			@saved="on_added"
		/>
	</div>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import Icon from "../../../shared/components/Icon.vue";
import TopBar from "../../../shared/components/TopBar.vue";
import Skeleton from "../../../shared/components/Skeleton.vue";
import Empty from "../../../shared/components/Empty.vue";
import StatusTabs from "../../../shared/components/StatusTabs.vue";
import Segmented from "../../../shared/components/Segmented.vue";
import DataTable from "../../../shared/components/DataTable.vue";
import HeaderSearch from "../../../shared/components/HeaderSearch.vue";
import WorkerSheet from "./WorkerSheet.vue";
import Sheet from "../../../shared/components/Sheet.vue";
import Picker from "../../../shared/components/Picker.vue";
import { matches, use_wide } from "../../../shared/table.js";
import { call, money, post, show_error, state, toast } from "../../../shared/api.js";

const COLUMNS = [
	{ key: "worker_name", label: "ชื่อ", sort: true, class: "col-subject" },
	{ key: "team", label: "ทีม", sort: true, class: "col-nowrap" },
	{ key: "position", label: "ตำแหน่ง", sort: true, class: "col-nowrap" },
	{ key: "payee", label: "จ่ายผ่าน", sort: true },
	{ key: "daily_rate", label: "ค่าแรง/วัน", sort: true, class: "is-num" },
	{ key: "ot", label: "OT", class: "col-nowrap" },
	{ key: "sso_registered", label: "ประกันสังคม", class: "col-status" },
];

const wide = use_wide();
const data = ref(null);
const loading = ref(false);
const txt = ref("");
const status = ref("Active");
const adding = ref(false);
const editing = ref(null);
const selected = ref(new Set());
const moving = ref(false);
const target_team = ref(null);
const busy = ref(false);
const teams = computed(() => [...new Set((data.value?.rows || []).map((r) => r.team).filter(Boolean))].sort());

const tabs = computed(() => [
	{ value: "Active", label: "ทำงานอยู่" },
	{ value: "Inactive", label: "เลิกจ้าง" },
]);
const shown = computed(() =>
	(data.value?.rows || []).filter((row) => matches(txt.value, row.worker_name, row.position, row.team, row.payee, row.name))
);

async function load() {
	loading.value = true;
	try {
		data.value = await call("consbiz.labour.get_workers", { project: state.project.name, status: status.value });
	} catch (error) {
		show_error(error);
		data.value ??= { rows: [] };
	} finally {
		loading.value = false;
	}
}

function open(row) {
	editing.value = row.name;
}

function open_move() {
	target_team.value = null;
	moving.value = true;
}

async function move() {
	busy.value = true;
	try {
		await post("consbiz.labour.set_team", { workers: [...selected.value], team: target_team.value || "" });
		toast(`ย้าย ${selected.value.size} คนแล้ว`, "success");
		moving.value = false;
		selected.value = new Set();
		await load();
	} catch (error) {
		show_error(error);
	} finally {
		busy.value = false;
	}
}

function on_added() {
	adding.value = false;
	editing.value = null;
	load();
}

watch(status, () => {
	selected.value = new Set();
	load();
});
watch(txt, () => (selected.value = new Set()));
load();
</script>

<style scoped>
.wk-search {
	margin: 8px 0;
}
</style>
