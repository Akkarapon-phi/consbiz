<!-- แผนตัดเหล็กของโครงการ (เมนู "ตัดเหล็ก" หมวดควบคุมงาน) ลอกหน้าตาจากคอนกรีต (Concrete.vue)
     API consbiz/bar_cut_app.py หน้าแผน = RebarPlan.vue -->
<template>
	<div>
		<TopBar title="ตัดเหล็ก" :subtitle="state.project?.project_name">
			<template #search>
				<HeaderSearch v-if="wide" v-model="txt" placeholder="ค้นหาแผนตัดเหล็ก" />
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
			<Skeleton v-if="rows === null" />
			<template v-else>
				<div class="ss-stats ss-stats--3">
					<div class="ss-stat tone-orange" style="--i: 0">
						<span class="ss-stat-icon"><Icon name="list-ordered" :size="20" /></span>
						<span class="ss-stat-value">{{ num(rows.length) }}</span>
						<span class="ss-stat-label">แผนตัด</span>
					</div>
					<div class="ss-stat tone-orange" style="--i: 1">
						<span class="ss-stat-icon"><Icon name="package" :size="20" /></span>
						<span class="ss-stat-value">{{ num(Math.round(total_weight)) }}</span>
						<span class="ss-stat-label">เหล็กที่ใช้ (กก.)</span>
					</div>
					<div class="ss-stat tone-orange" style="--i: 2">
						<span class="ss-stat-icon"><Icon name="trash" :size="20" /></span>
						<span class="ss-stat-value">{{ loss.toFixed(1) }}%</span>
						<span class="ss-stat-label">เศษทิ้งเฉลี่ย</span>
					</div>
				</div>

				<div v-if="wide" class="ss-list-head">
					<StatusTabs
						model-value="all"
						:options="[{ value: 'all', label: 'แผนตัดเหล็ก', count: rows.length }]"
					/>
					<div class="ss-list-tools">
						<button
							v-if="boot.can.bar_cut_write"
							type="button"
							class="ss-btn ss-btn--primary ss-list-create"
							@click="create"
						>
							<Icon name="plus" :size="18" :stroke="2.6" />
							<span>แผนตัดเหล็ก</span>
						</button>
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
				<label v-else class="ss-search">
					<Icon name="search" :size="17" />
					<input v-model="txt" type="search" placeholder="ค้นหาแผนตัดเหล็ก" />
				</label>

				<Empty
					v-if="!rows.length"
					icon="list-ordered"
					title="ยังไม่มีแผนตัดเหล็ก"
					text="กดปุ่ม + เพิ่มเหล็กที่ต้องตัด ระบบจัดการตัดให้เหลือเศษน้อยที่สุด"
				/>
				<Empty v-else-if="!shown.length" icon="search" title="ไม่พบรายการ" />
				<DataTable v-else-if="wide" :rows="shown" :columns="COLUMNS" @open="open">
					<template #name="{ row }">
						<span class="ss-doc-no">{{ row.name }}</span>
					</template>
					<template #title="{ row }">
						<span class="ss-cell-main" :title="row.title">{{ row.title }}</span>
					</template>
					<template #date="{ row }">{{
						row.date ? thai_date(row.date, { year: true }) : "—"
					}}</template>
					<template #pieces="{ row }">{{ num(row.pieces) }}</template>
					<template #total_weight="{ row }"
						><b>{{ num(Math.round(row.total_weight || 0)) }}</b></template
					>
					<template #loss_percent="{ row }">{{
						(row.loss_percent || 0).toFixed(1)
					}}</template>
					<template #modified="{ row }">{{ time_ago(row.modified) }}</template>
				</DataTable>
				<div v-else class="ss-list">
					<button
						v-for="(d, i) in shown"
						:key="d.name"
						type="button"
						class="ss-card"
						:style="{ '--i': i }"
						@click="open(d)"
					>
						<div class="ss-card-head">
							<span class="ss-avatar tone-orange"
								><Icon name="list-ordered" :size="18"
							/></span>
							<span class="ss-card-main">
								<span class="ss-card-title">{{ d.title }}</span>
								<span class="ss-card-meta"
									>{{ d.name }} ·
									{{ d.date ? thai_date(d.date, { year: true }) : "" }}</span
								>
							</span>
							<span class="ss-qty"
								><b>{{ num(Math.round(d.total_weight || 0)) }}</b
								><small>กก.</small></span
							>
						</div>
						<div class="ss-chips">
							<span class="ss-chip">{{ num(d.pieces) }} ชิ้น</span>
							<span class="ss-chip"
								>ใช้เหล็ก {{ num(Math.round(d.total_stock_length || 0)) }} ม.</span
							>
							<span class="ss-chip"
								>เศษทิ้ง {{ (d.loss_percent || 0).toFixed(1) }}%</span
							>
						</div>
					</button>
				</div>
			</template>
		</div>

		<Teleport to="#ss-layer">
			<Transition name="ss-pop">
				<button
					v-if="rows && !wide && boot.can.bar_cut_write"
					type="button"
					class="ss-fab"
					@click="create"
				>
					<Icon name="plus" :size="26" :stroke="2.6" />
					<span>แผนตัดเหล็ก</span>
				</button>
			</Transition>
		</Teleport>
	</div>
</template>

<script setup>
import { computed, ref } from "vue";
import DataTable from "../../../shared/components/DataTable.vue";
import Empty from "../../../shared/components/Empty.vue";
import HeaderSearch from "../../../shared/components/HeaderSearch.vue";
import Icon from "../../../shared/components/Icon.vue";
import Skeleton from "../../../shared/components/Skeleton.vue";
import StatusTabs from "../../../shared/components/StatusTabs.vue";
import TopBar from "../../../shared/components/TopBar.vue";
import { matches, use_wide } from "../../../shared/table.js";
import {
	boot,
	call,
	go,
	num,
	show_error,
	state,
	thai_date,
	time_ago,
} from "../../../shared/api.js";

const API = "consbiz.bar_cut_app";
const COLUMNS = [
	{ key: "name", label: "เลขที่", sort: true, class: "col-no" },
	{ key: "title", label: "ชื่อแผน", sort: true, class: "col-subject" },
	{ key: "date", label: "วันที่", sort: true, class: "col-date is-date" },
	{ key: "pieces", label: "ชิ้น", sort: true, class: "is-num" },
	{ key: "total_weight", label: "เหล็กที่ใช้ (กก.)", sort: true, class: "is-num" },
	{ key: "loss_percent", label: "เศษทิ้ง %", sort: true, class: "is-num" },
	{ key: "modified", label: "แก้ไขล่าสุด", sort: true, class: "col-modified col-wide" },
];

const wide = use_wide();
const rows = ref(null);
const loading = ref(false);
const txt = ref("");

const shown = computed(() =>
	(rows.value || []).filter((r) => matches(txt.value, r.name, r.title))
);
const total_weight = computed(() =>
	(rows.value || []).reduce((s, r) => s + (r.total_weight || 0), 0)
);
// เศษทิ้งเฉลี่ยถ่วงตามความยาวเหล็กที่ใช้
const loss = computed(() => {
	const used = (rows.value || []).reduce((s, r) => s + (r.total_stock_length || 0), 0);
	const scrap = (rows.value || []).reduce(
		(s, r) => s + ((r.loss_percent || 0) * (r.total_stock_length || 0)) / 100,
		0
	);
	return used ? (scrap / used) * 100 : 0;
});

const open = (row) => go("rebar-plan", { name: row.name });
const create = () => go("rebar-plan", { name: "new" });

async function load() {
	loading.value = true;
	try {
		rows.value = await call(`${API}.get_plans`, { project: state.project.name });
	} catch (error) {
		show_error(error);
		rows.value ??= [];
	} finally {
		loading.value = false;
	}
}
load();
</script>
