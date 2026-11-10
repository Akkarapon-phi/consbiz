<template>
	<div>
		<TopBar title="ยืม-คืนอุปกรณ์" :subtitle="state.project?.project_name">
			<template #search>
				<HeaderSearch
					v-if="wide"
					v-model="txt"
					:placeholder="'ค้นหาเลขที่ ผู้ยืม หรืออุปกรณ์'"
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
						v-if="tab === 'out'"
						type="button"
						class="ss-tool ss-tool--toggle"
						:class="{ 'is-active': only_overdue }"
						:aria-pressed="only_overdue"
						@click="only_overdue = !only_overdue"
					>
						<Icon name="alert" :size="15" /> เกินกำหนด
					</button>
					<button
						v-if="boot.can.borrow"
						type="button"
						class="ss-btn ss-btn--primary ss-list-create"
						@click="go('borrow-new')"
					>
						<Icon name="plus" :size="18" :stroke="2.6" />
						<span>ยืมอุปกรณ์</span>
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

			<Skeleton v-if="data === null" />
			<Transition v-else name="ss-fade" mode="out-in">
				<div v-if="tab === 'out'" key="out">
					<Empty
						v-if="!data.outstanding.length"
						icon="sparkles"
						title="ไม่มีอุปกรณ์ค้างคืน"
						text="อุปกรณ์ของโครงการอยู่ในคลังครบ"
					/>
					<Empty v-else-if="!out_rows.length" icon="search" title="ไม่พบรายการ" />
					<DataTable
						v-else-if="wide"
						:rows="out_rows"
						:columns="OUT_COLUMNS"
						:late="(b) => b.overdue"
						@open="(b) => go('borrow-detail', { name: b.name })"
					>
						<template #name="{ row }">
							<span class="ss-doc-no">{{ row.name }}</span>
							<span class="ss-doc-meta">
								<span
									class="ss-tag"
									:class="row.overdue ? 'tone-rose' : STATUS[row.status].tone"
									>{{
										row.overdue ? "เกินกำหนด" : STATUS[row.status].label
									}}</span
								>
							</span>
						</template>
						<template #borrower_name="{ row }">
							<span class="ss-cell-main" :title="row.borrower_name">{{
								row.borrower_name
							}}</span>
						</template>
						<template #items="{ row }">
							<span class="ss-cell-main" :title="equipment_text(row)">{{
								equipment_text(row)
							}}</span>
						</template>
						<template #date="{ row }">{{
							thai_date(row.date, { year: true })
						}}</template>
						<template #due_date="{ row }">
							<span v-if="row.due_date" :class="{ 'is-due': row.overdue }">{{
								thai_date(row.due_date, { year: true })
							}}</span>
						</template>
					</DataTable>
					<TransitionGroup v-else tag="div" class="ss-list" name="ss-list" appear>
						<button
							v-for="(b, i) in out_rows"
							:key="b.name"
							type="button"
							class="ss-card"
							:class="{ 'is-late': b.overdue }"
							:style="{ '--i': i }"
							@click="go('borrow-detail', { name: b.name })"
						>
							<div class="ss-card-head">
								<span class="ss-avatar" :class="`tone-${tone(b.borrower_name)}`">{{
									initials(b.borrower_name)
								}}</span>
								<span class="ss-card-main">
									<span class="ss-card-title">{{ b.borrower_name }}</span>
									<span class="ss-card-meta"
										>ยืม {{ relative_date(b.date) }} · {{ b.name }}</span
									>
								</span>
								<span
									v-if="b.due_date"
									class="ss-due"
									:class="{ 'is-late': b.overdue }"
								>
									<Icon :name="b.overdue ? 'alert' : 'clock'" :size="13" />
									{{ b.overdue ? "เกินกำหนด" : "คืน" }}
									{{ relative_date(b.due_date) }}
								</span>
							</div>
							<div class="ss-chips">
								<span v-for="it in b.items" :key="it.item_code" class="ss-chip">
									{{ it.item_name || it.item_code }}
									<b>× {{ num(it.outstanding_qty) }}</b>
								</span>
							</div>
						</button>
					</TransitionGroup>
				</div>
				<div v-else key="done">
					<Empty
						v-if="!data.returned.length"
						icon="history"
						title="ยังไม่มีรายการคืนครบ"
					/>
					<Empty v-else-if="!returned_rows.length" icon="search" title="ไม่พบรายการ" />
					<DataTable
						v-else-if="wide"
						:rows="returned_rows"
						:columns="RETURNED_COLUMNS"
						@open="(b) => go('borrow-detail', { name: b.name })"
					>
						<template #name="{ row }">
							<span class="ss-doc-no">{{ row.name }}</span>
							<span class="ss-doc-meta"
								><span class="ss-tag tone-green">คืนครบ</span></span
							>
						</template>
						<template #borrower_name="{ row }">
							<span class="ss-cell-main" :title="row.borrower_name">{{
								row.borrower_name
							}}</span>
						</template>
						<template #date="{ row }">{{
							thai_date(row.date, { year: true })
						}}</template>
						<template #due_date="{ row }">
							<template v-if="row.due_date">{{
								thai_date(row.due_date, { year: true })
							}}</template>
						</template>
					</DataTable>
					<div v-else class="ss-list">
						<button
							v-for="(b, i) in returned_rows"
							:key="b.name"
							type="button"
							class="ss-card ss-card--row"
							:style="{ '--i': i }"
							@click="go('borrow-detail', { name: b.name })"
						>
							<span class="ss-avatar ss-avatar--done"
								><Icon name="check" :size="18" :stroke="3"
							/></span>
							<span class="ss-card-main">
								<span class="ss-card-title">{{ b.borrower_name }}</span>
								<span class="ss-card-meta"
									>{{ b.name }} · ยืม {{ thai_date(b.date) }}</span
								>
							</span>
							<Icon name="chevron-right" :size="18" />
						</button>
					</div>
				</div>
			</Transition>
		</div>

		<Teleport to="#ss-layer">
			<Transition name="ss-pop">
				<button
					v-if="boot.can.borrow && !wide"
					type="button"
					class="ss-fab"
					@click="go('borrow-new')"
				>
					<Icon name="plus" :size="26" :stroke="2.6" />
					<span>ยืมอุปกรณ์</span>
				</button>
			</Transition>
		</Teleport>
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
	boot,
	call,
	go,
	initials,
	num,
	relative_date,
	remember_tab,
	show_error,
	state,
	thai_date,
	tone,
} from "../../../shared/api.js";

const STATUS = {
	Borrowed: { label: "ยืมอยู่", tone: "tone-blue" },
	"Partially Returned": { label: "คืนบางส่วน", tone: "tone-amber" },
};
const OUT_COLUMNS = [
	{ key: "name", label: "เลขที่", sort: true, class: "col-no" },
	{ key: "borrower_name", label: "ผู้ยืม", sort: true, class: "col-party" },
	{ key: "items", label: "อุปกรณ์ค้างคืน", class: "col-subject" },
	{ key: "date", label: "วันที่ยืม", sort: true, class: "col-date is-date" },
	{ key: "due_date", label: "กำหนดคืน", sort: true, class: "col-date is-date" },
];
const RETURNED_COLUMNS = [
	{ key: "name", label: "เลขที่", sort: true, class: "col-no" },
	{ key: "borrower_name", label: "ผู้ยืม", sort: true, class: "col-subject" },
	{ key: "date", label: "วันที่ยืม", sort: true, class: "col-date is-date" },
	{ key: "due_date", label: "กำหนดคืน", sort: true, class: "col-date is-date" },
];

const tab = ref(state.route.params.tab === "done" ? "done" : "out");
const data = ref(null);
const loading = ref(false);
const wide = use_wide();
const txt = ref("");
const only_overdue = ref(false);

const tabs = computed(() => [
	{ value: "out", label: "ค้างคืน", count: data.value?.outstanding.length || 0 },
	{ value: "done", label: "คืนครบแล้ว" },
]);
const equipment_text = (b) =>
	b.items.map((it) => `${it.item_name || it.item_code} × ${num(it.outstanding_qty)}`).join(", ");
const out_rows = computed(() =>
	(data.value?.outstanding || []).filter(
		(b) =>
			(!only_overdue.value || b.overdue) &&
			matches(
				txt.value,
				b.name,
				b.borrower_name,
				...b.items.map((it) => it.item_name || it.item_code)
			)
	)
);
const returned_rows = computed(() =>
	(data.value?.returned || []).filter((b) => matches(txt.value, b.name, b.borrower_name))
);

async function load() {
	loading.value = true;
	try {
		data.value = await call("get_borrowings", { project: state.project.name });
	} catch (error) {
		show_error(error);
		data.value ??= { outstanding: [], returned: [] };
	} finally {
		loading.value = false;
	}
}

watch(tab, (value) => remember_tab("borrow", value, "out"));
load();
</script>
