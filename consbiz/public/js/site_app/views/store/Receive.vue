<template>
	<div>
		<TopBar title="รับของ" :subtitle="state.project?.project_name">
			<template #search>
				<HeaderSearch
					v-if="wide"
					v-model="txt"
					:placeholder="
						tab === 'pending'
							? 'ค้นหาเลขที่ ผู้ขาย หรือวัสดุ'
							: 'ค้นหาเลขที่ ผู้ส่ง หรือวัสดุ'
					"
				/>
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
				<StatusTabs v-model="tab" :options="tabs" />
				<div class="ss-list-tools">
					<button
						v-if="tab === 'pending'"
						type="button"
						class="ss-tool ss-tool--toggle"
						:class="{ 'is-active': only_overdue }"
						:aria-pressed="only_overdue"
						@click="only_overdue = !only_overdue"
					>
						<Icon name="alert" :size="15" /> เกินกำหนด
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
			<Segmented v-else v-model="tab" :options="tabs" />

			<Transition name="ss-fade" mode="out-in">
				<div v-if="tab === 'pending'" key="pending">
					<Skeleton v-if="pending === null" />
					<Empty
						v-else-if="!pending.length"
						icon="sparkles"
						title="ไม่มีของรอรับ"
						text="ใบสั่งซื้อของโครงการนี้รับครบแล้ว"
					/>
					<Empty v-else-if="!pending_rows.length" icon="search" title="ไม่พบรายการ" />
					<DataTable
						v-else-if="wide"
						:rows="pending_rows"
						:columns="PENDING_COLUMNS"
						:late="(d) => d.overdue"
						@open="(d) => go('receive-form', { doctype: d.doctype, name: d.name })"
					>
						<template #name="{ row }">
							<span class="ss-doc-no">{{ row.name }}</span>
							<span class="ss-doc-meta">
								<span
									class="ss-tag"
									:class="row.employer ? 'tone-violet' : 'tone-blue'"
									>{{ row.employer ? "ผู้ว่าจ้างจัดหา" : "ใบสั่งซื้อ" }}</span
								>
							</span>
						</template>
						<template #party="{ row }">
							<span class="ss-cell-main" :title="row.party">{{
								row.party || "ไม่ระบุผู้ขาย"
							}}</span>
						</template>
						<template #items="{ row }">
							<span class="ss-cell-main" :title="items_text(row)">{{
								items_text(row)
							}}</span>
						</template>
						<template #date="{ row }">{{
							thai_date(row.date, { year: true })
						}}</template>
						<template #schedule_date="{ row }">
							<span v-if="row.schedule_date" :class="{ 'is-due': row.overdue }">{{
								thai_date(row.schedule_date, { year: true })
							}}</span>
						</template>
						<template #progress="{ row }">
							<span class="ss-table-pct">
								<i
									><b
										:style="{ width: `${Math.min(100, row.progress || 0)}%` }"
									></b
								></i>
								{{ Math.round(row.progress || 0) }}%
							</span>
						</template>
					</DataTable>
					<TransitionGroup v-else tag="div" class="ss-list" name="ss-list" appear>
						<button
							v-for="(d, i) in pending_rows"
							:key="d.name"
							type="button"
							class="ss-card"
							:style="{ '--i': i }"
							@click="go('receive-form', { doctype: d.doctype, name: d.name })"
						>
							<div class="ss-card-head">
								<span
									class="ss-avatar"
									:class="`tone-${d.employer ? 'violet' : tone(d.party)}`"
									>{{ initials(d.party) }}</span
								>
								<span class="ss-card-main">
									<span class="ss-card-title">{{
										d.party || "ไม่ระบุผู้ขาย"
									}}</span>
									<span class="ss-card-meta">
										<span
											class="ss-tag"
											:class="d.employer ? 'tone-violet' : 'tone-blue'"
											>{{
												d.employer ? "ผู้ว่าจ้างจัดหา" : "ใบสั่งซื้อ"
											}}</span
										>
										{{ d.name }}
									</span>
								</span>
								<span
									v-if="d.schedule_date"
									class="ss-due"
									:class="{ 'is-late': d.overdue }"
								>
									<Icon :name="d.overdue ? 'alert' : 'calendar'" :size="13" />
									{{ relative_date(d.schedule_date) }}
								</span>
							</div>
							<div class="ss-chips">
								<span v-for="n in d.items.names" :key="n" class="ss-chip">{{
									n
								}}</span>
								<span v-if="d.items.count > 3" class="ss-chip ss-chip--more"
									>+{{ d.items.count - 3 }} รายการ</span
								>
							</div>
							<div v-if="d.progress > 0" class="ss-progress">
								<span :style="{ width: `${Math.min(d.progress, 100)}%` }"></span>
								<em>รับแล้ว {{ Math.round(d.progress) }}%</em>
							</div>
						</button>
					</TransitionGroup>
				</div>

				<div v-else key="done">
					<Skeleton v-if="done === null" />
					<Empty
						v-else-if="!done.length"
						icon="history"
						title="ยังไม่มีการรับของ"
						text="ใบรับของ 90 วันล่าสุดจะแสดงที่นี่"
					/>
					<Empty v-else-if="!done_rows.length" icon="search" title="ไม่พบรายการ" />
					<DataTable
						v-else-if="wide"
						:rows="done_rows"
						:columns="DONE_COLUMNS"
						@open="(d) => go('receipt', { doctype: d.doctype, name: d.name })"
					>
						<template #name="{ row }">
							<span class="ss-doc-no">{{ row.name }}</span>
							<span v-if="row.employer || row.rejected" class="ss-doc-meta">
								<span v-if="row.employer" class="ss-tag tone-violet"
									>ผู้ว่าจ้างจัดหา</span
								>
								<span v-if="row.rejected" class="ss-tag tone-rose">มีตีกลับ</span>
							</span>
						</template>
						<template #party="{ row }">
							<span class="ss-cell-main" :title="row.party">{{
								row.party || "—"
							}}</span>
						</template>
						<template #items="{ row }">
							<span class="ss-cell-main" :title="items_text(row)">{{
								items_text(row)
							}}</span>
						</template>
						<template #date="{ row }">
							{{ thai_date(row.date, { year: true }) }}
							<small>{{ short_time(row.time) }}</small>
						</template>
					</DataTable>
					<template v-else>
						<template v-for="group in done_groups" :key="group.date">
							<div class="ss-day">{{ relative_date(group.date) }}</div>
							<div class="ss-list">
								<button
									v-for="(d, i) in group.rows"
									:key="d.name"
									type="button"
									class="ss-card"
									:style="{ '--i': i }"
									@click="go('receipt', { doctype: d.doctype, name: d.name })"
								>
									<div class="ss-card-head">
										<span class="ss-avatar ss-avatar--done"
											><Icon name="check" :size="18" :stroke="3"
										/></span>
										<span class="ss-card-main">
											<span class="ss-card-title">{{
												d.party || "รับของ"
											}}</span>
											<span class="ss-card-meta">
												{{ d.name }}
												<template v-if="d.delivery_note">
													· ใบส่งของ {{ d.delivery_note }}</template
												>
											</span>
										</span>
										<span class="ss-time">{{ short_time(d.time) }}</span>
									</div>
									<div class="ss-chips">
										<span v-if="d.employer" class="ss-tag tone-violet"
											>ผู้ว่าจ้างจัดหา</span
										>
										<span v-if="d.rejected" class="ss-tag tone-rose"
											>มีตีกลับ</span
										>
										<span
											v-for="n in d.items.names"
											:key="n"
											class="ss-chip"
											>{{ n }}</span
										>
										<span
											v-if="d.items.count > 3"
											class="ss-chip ss-chip--more"
											>+{{ d.items.count - 3 }}</span
										>
									</div>
								</button>
							</div>
						</template>
					</template>
				</div>
			</Transition>
		</div>
	</div>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import Icon from "../../../shared/components/Icon.vue";
import TopBar from "../../../shared/components/TopBar.vue";
import Segmented from "../../../shared/components/Segmented.vue";
import Skeleton from "../../../shared/components/Skeleton.vue";
import Empty from "../../../shared/components/Empty.vue";
import DataTable from "../../../shared/components/DataTable.vue";
import StatusTabs from "../../../shared/components/StatusTabs.vue";
import HeaderSearch from "../../../shared/components/HeaderSearch.vue";
import { matches, use_wide } from "../../../shared/table.js";
import {
	call,
	go,
	initials,
	relative_date,
	remember_tab,
	short_time,
	show_error,
	state,
	thai_date,
	tone,
	boot,
} from "../../../shared/api.js";

const PENDING_COLUMNS = [
	{ key: "name", label: "เลขที่", sort: true, class: "col-no" },
	{ key: "party", label: "ผู้ขาย / ผู้ว่าจ้าง", sort: true, class: "col-party" },
	{ key: "items", label: "รายการ", class: "col-subject" },
	{ key: "date", label: "วันที่เอกสาร", sort: true, class: "col-date is-date col-wide" },
	{ key: "schedule_date", label: "กำหนดส่ง", sort: true, class: "col-date is-date" },
	{ key: "progress", label: "รับแล้ว", sort: true, class: "col-pct" },
];
const DONE_COLUMNS = [
	{ key: "name", label: "เลขที่", sort: true, class: "col-no" },
	{ key: "party", label: "ผู้ส่ง", sort: true, class: "col-party" },
	{ key: "items", label: "รายการ", class: "col-subject" },
	{ key: "delivery_note", label: "เลขที่ใบส่งของ", sort: true, class: "col-date col-wide" },
	{
		key: "date",
		label: "วันที่รับ",
		sort: (row) => `${row.date} ${row.time}`,
		class: "col-date is-date",
	},
];

const can_receive = boot.can.receive || boot.can.receive_employer;
const tab = ref(state.route.params.tab === "done" || !can_receive ? "done" : "pending");
const pending = ref(null);
const done = ref(null);
const loading = ref(false);
const wide = use_wide();
const txt = ref("");
const only_overdue = ref(false);

const tabs = computed(() => [
	...(can_receive ? [{ value: "pending", label: "รอรับ", count: pending.value?.length || 0 }] : []),
	{ value: "done", label: "รับแล้ว" },
]);
const items_text = (d) =>
	`${d.items.names.join(", ")}${
		d.items.count > d.items.names.length
			? ` +${d.items.count - d.items.names.length} รายการ`
			: ""
	}`;
const pending_rows = computed(() =>
	(pending.value || []).filter(
		(d) =>
			(!only_overdue.value || d.overdue) &&
			matches(txt.value, d.name, d.party, ...d.items.names)
	)
);
const done_rows = computed(() =>
	(done.value || []).filter((d) =>
		matches(txt.value, d.name, d.party, d.delivery_note, ...d.items.names)
	)
);

const done_groups = computed(() => {
	const groups = [];
	for (const row of done_rows.value) {
		const date = String(row.date);
		let group = groups.find((g) => g.date === date);
		if (!group) groups.push((group = { date, rows: [] }));
		group.rows.push(row);
	}
	return groups;
});

async function load() {
	loading.value = true;
	const project = state.project.name;
	try {
		if (tab.value === "pending")
			pending.value = await call("get_pending_receipts", { project });
		else done.value = await call("get_receipt_history", { project });
	} catch (error) {
		show_error(error);
		if (tab.value === "pending") pending.value ??= [];
		else done.value ??= [];
	} finally {
		loading.value = false;
	}
}

watch(
	tab,
	(value) => {
		remember_tab("receive", value, "pending");
		load();
	},
	{ immediate: true }
);
</script>
