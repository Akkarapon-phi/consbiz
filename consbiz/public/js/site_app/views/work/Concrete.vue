<template>
	<div>
		<TopBar title="คอนกรีต" :subtitle="state.project?.project_name">
			<template #search>
				<HeaderSearch v-if="wide" v-model="txt" placeholder="ค้นหางาน WBS หรือตำแหน่ง" />
			</template>
			<template #actions>
				<button
					v-if="!wide || !data?.construction_management"
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
			<Skeleton v-if="data === null" />
			<Empty
				v-else-if="!data.construction_management"
				icon="layers"
				title="โครงการนี้ยังไม่มีแผนงาน"
				text="บันทึกคอนกรีตต้องอ้างงาน (WBS) ในแผนงานก่อสร้าง"
			/>
			<template v-else>
				<div class="ss-stats ss-stats--3">
					<div class="ss-stat tone-orange" style="--i: 0">
						<span class="ss-stat-icon"><Icon name="calendar" :size="20" /></span>
						<span class="ss-stat-value">{{ num(month_total) }}</span>
						<span class="ss-stat-label">เดือนนี้ (คิว)</span>
					</div>
					<div class="ss-stat tone-orange" style="--i: 1">
						<span class="ss-stat-icon"><Icon name="truck" :size="20" /></span>
						<span class="ss-stat-value">{{ num(total) }}</span>
						<span class="ss-stat-label">ทั้งหมด (คิว)</span>
					</div>
					<div class="ss-stat tone-orange" style="--i: 2">
						<span class="ss-stat-icon"><Icon name="flag" :size="20" /></span>
						<span class="ss-stat-value">{{ num(submitted.length) }}</span>
						<span class="ss-stat-label">จุดที่เทแล้ว</span>
					</div>
				</div>

				<div v-if="wide" class="ss-list-head">
					<StatusTabs
						model-value="all"
						:options="[
							{ value: 'all', label: 'ใบเทคอนกรีต', count: data.docs.length },
						]"
					/>
					<div class="ss-list-tools">
						<button
							v-if="boot.can.concrete"
							type="button"
							class="ss-btn ss-btn--primary ss-list-create"
							@click="go('concrete-form')"
						>
							<Icon name="plus" :size="18" :stroke="2.6" />
							<span>เทคอนกรีต</span>
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

				<Empty
					v-if="!data.docs.length"
					icon="truck"
					title="ยังไม่มีบันทึกการเท"
					text="กดปุ่ม + เพื่อเริ่มบันทึกการเทจุดแรก"
				/>
				<Empty v-else-if="!groups.length" icon="search" title="ไม่พบรายการ" />
				<DataTable
					v-else-if="wide"
					:rows="shown_docs"
					:columns="COLUMNS"
					@open="(d) => go('concrete-form', { name: d.name })"
				>
					<template #name="{ row }">
						<span class="ss-doc-no">{{ row.name }}</span>
						<span v-if="row.docstatus === 0" class="ss-doc-meta"
							><span class="ss-tag tone-amber">ร่าง</span></span
						>
					</template>
					<template #task_name="{ row }">
						<span class="ss-cell-main" :title="row.task_name">{{
							row.task_name || row.wbs
						}}</span>
						<small
							>{{ row.wbs
							}}<template v-if="row.location"> · {{ row.location }}</template></small
						>
					</template>
					<template #date="{ row }">{{ thai_date(row.date, { year: true }) }}</template>
					<template #total_qty="{ row }"
						><b>{{ num(row.total_qty) }}</b></template
					>
					<template #planned_qty="{ row }">{{
						row.planned_qty ? num(row.planned_qty) : "—"
					}}</template>
					<template #employer_qty="{ row }">{{
						row.employer_qty ? num(row.employer_qty) : "—"
					}}</template>
				</DataTable>
				<template v-else>
					<template v-for="group in groups" :key="group.date">
						<div class="ss-day">{{ relative_date(group.date) }}</div>
						<div class="ss-list">
							<button
								v-for="(d, i) in group.rows"
								:key="d.name"
								type="button"
								class="ss-card"
								:style="{ '--i': i }"
								@click="go('concrete-form', { name: d.name })"
							>
								<div class="ss-card-head">
									<span class="ss-avatar tone-orange"
										><Icon name="truck" :size="18"
									/></span>
									<span class="ss-card-main">
										<span class="ss-card-title">{{
											d.task_name || d.wbs
										}}</span>
										<span class="ss-card-meta">
											<span class="ss-wbs">{{ d.wbs }}</span>
											<template v-if="d.location">
												· {{ d.location }}</template
											>
										</span>
									</span>
									<span class="ss-qty"
										><b>{{ num(d.total_qty) }}</b
										><small>คิว</small></span
									>
								</div>
								<div class="ss-chips">
									<span v-if="d.docstatus === 0" class="ss-tag tone-amber"
										>ร่าง</span
									>
									<span class="ss-chip"
										><Icon name="ticket" :size="13" />
										{{ d.ticket_count }} คัน</span
									>
									<span v-if="d.concrete_item_name" class="ss-chip">{{
										d.concrete_item_name
									}}</span>
									<span v-if="d.employer_qty" class="ss-tag tone-violet"
										>ผู้ว่าจ้าง {{ num(d.employer_qty) }}</span
									>
									<span
										v-if="d.planned_qty"
										class="ss-chip"
										:class="{
											'ss-text-danger': d.total_qty > d.planned_qty * 1.05,
										}"
									>
										แผน {{ num(d.planned_qty) }}
									</span>
								</div>
							</button>
						</div>
					</template>
				</template>
			</template>
		</div>

		<Teleport to="#ss-layer">
			<Transition name="ss-pop">
				<button
					v-if="data?.construction_management && !wide && boot.can.concrete"
					type="button"
					class="ss-fab"
					@click="go('concrete-form')"
				>
					<Icon name="plus" :size="26" :stroke="2.6" />
					<span>เทคอนกรีต</span>
				</button>
			</Transition>
		</Teleport>
	</div>
</template>

<script setup>
import { computed, ref } from "vue";
import Icon from "../../../shared/components/Icon.vue";
import TopBar from "../../../shared/components/TopBar.vue";
import Skeleton from "../../../shared/components/Skeleton.vue";
import Empty from "../../../shared/components/Empty.vue";
import StatusTabs from "../../../shared/components/StatusTabs.vue";
import DataTable from "../../../shared/components/DataTable.vue";
import HeaderSearch from "../../../shared/components/HeaderSearch.vue";
import { matches, use_wide } from "../../../shared/table.js";
import {
	call,
	go,
	num,
	relative_date,
	show_error,
	state,
	thai_date,
	today,
	boot,
} from "../../../shared/api.js";

const COLUMNS = [
	{ key: "name", label: "เลขที่", sort: true, class: "col-no" },
	{ key: "task_name", label: "งาน", sort: true, class: "col-subject" },
	{ key: "date", label: "วันที่เท", sort: true, class: "col-date is-date" },
	{ key: "concrete_item_name", label: "คอนกรีต", sort: true, class: "col-wide" },
	{ key: "ticket_count", label: "จำนวนคัน", sort: true, class: "is-num" },
	{ key: "total_qty", label: "ปริมาณ (คิว)", sort: true, class: "is-num" },
	{ key: "planned_qty", label: "ตามแผน", sort: true, class: "is-num col-wide" },
	{ key: "employer_qty", label: "ผู้ว่าจ้าง", sort: true, class: "is-num col-wide" },
];

const data = ref(null);
const loading = ref(false);
const wide = use_wide();
const txt = ref("");

const submitted = computed(() => (data.value?.docs || []).filter((d) => d.docstatus === 1));
const total = computed(() => submitted.value.reduce((s, d) => s + (d.total_qty || 0), 0));
const month_total = computed(() =>
	submitted.value
		.filter((d) => String(d.date).slice(0, 7) === today().slice(0, 7))
		.reduce((s, d) => s + (d.total_qty || 0), 0)
);
const shown_docs = computed(() =>
	(data.value?.docs || []).filter((row) =>
		matches(txt.value, row.task_name, row.wbs, row.location, row.name)
	)
);
const groups = computed(() => {
	const out = [];
	for (const row of shown_docs.value) {
		const date = String(row.date);
		let group = out.find((g) => g.date === date);
		if (!group) out.push((group = { date, rows: [] }));
		group.rows.push(row);
	}
	return out;
});

async function load() {
	loading.value = true;
	try {
		data.value = await call("get_concrete", { project: state.project.name });
	} catch (error) {
		show_error(error);
		data.value ??= { docs: [] };
	} finally {
		loading.value = false;
	}
}
load();
</script>
