<template>
	<div>
		<TopBar title="ตรวจงาน" :subtitle="state.project?.project_name">
			<template #search>
				<HeaderSearch
					v-if="wide"
					v-model="txt"
					placeholder="ค้นหาเรื่อง งาน หรือตำแหน่ง"
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
						v-if="can_create"
						type="button"
						class="ss-btn ss-btn--primary ss-list-create"
						@click="create"
					>
						<Icon name="plus" :size="18" :stroke="2.6" />
						<span>{{ create_label }}</span>
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

			<Skeleton v-if="rows === null" />
			<Empty
				v-else-if="!rows.length"
				:icon="tab === 'inspection' ? 'search-check' : 'list-checks'"
				:title="tab === 'inspection' ? 'ยังไม่มีใบขอตรวจงาน' : 'ไม่มี Punch List'"
				text="กดปุ่ม + เพื่อสร้าง"
			/>
			<Empty v-else-if="!shown_rows.length" icon="search" title="ไม่พบรายการ" />
			<DataTable
				v-else-if="wide"
				:key="tab"
				:rows="shown_rows"
				:columns="tab === 'inspection' ? INSPECTION_COLUMNS : PUNCH_COLUMNS"
				:late="(r) => r.status_tone === 'rose'"
				@open="open_doc"
			>
				<template #name="{ row }">
					<span class="ss-doc-no">{{ row.name }}</span>
					<span class="ss-doc-meta">
						<span class="ss-tag" :class="`tone-${row.status_tone}`">{{
							row.status_label
						}}</span>
					</span>
				</template>
				<template #title="{ row }">
					<span class="ss-cell-main" :title="row.title">{{ row.title }}</span>
					<small>{{ row.item_name || row.inspection_request || "" }}</small>
				</template>
				<template #wbs="{ row }"
					><i v-if="row.wbs" class="ss-wbs">{{ row.wbs }}</i></template
				>
				<template #request_date="{ row }">{{
					thai_date(row.request_date, { year: true })
				}}</template>
				<template #inspection_date="{ row }">
					<template v-if="row.inspection_date">{{
						thai_date(row.inspection_date, { year: true })
					}}</template>
				</template>
				<template #date="{ row }">{{ thai_date(row.date, { year: true }) }}</template>
				<template #open_items="{ row }">
					<b v-if="row.status === 'Open' && row.open_items">{{ row.open_items }}</b>
					<template v-else>—</template>
				</template>
			</DataTable>
			<Transition v-else name="ss-fade" mode="out-in">
				<TransitionGroup :key="tab" tag="div" class="ss-list" name="ss-list" appear>
					<button
						v-for="(r, i) in shown_rows"
						:key="r.name"
						type="button"
						class="ss-card"
						:class="{ 'is-late': r.status_tone === 'rose' }"
						:style="{ '--i': i }"
						@click="open_doc(r)"
					>
						<div class="ss-card-head">
							<span class="ss-avatar" :class="`tone-${r.status_tone}`">
								<Icon
									:name="tab === 'inspection' ? 'search-check' : 'list-checks'"
									:size="18"
								/>
							</span>
							<span class="ss-card-main">
								<span class="ss-card-title">{{ r.title }}</span>
								<span class="ss-card-meta">
									<i v-if="r.wbs" class="ss-wbs">{{ r.wbs }}</i>
									{{ r.item_name || r.inspection_request || "" }}
									<template v-if="r.location"> · {{ r.location }}</template>
								</span>
							</span>
							<span class="ss-tag" :class="`tone-${r.status_tone}`">{{
								r.status_label
							}}</span>
						</div>
						<div class="ss-chips">
							<template v-if="tab === 'inspection'">
								<span class="ss-chip"
									><Icon name="calendar" :size="12" /> ขอ
									{{ thai_date(r.request_date) }}</span
								>
								<span v-if="r.inspection_date" class="ss-chip"
									><Icon name="search-check" :size="12" /> ตรวจ
									{{ relative_date(r.inspection_date) }}</span
								>
								<span v-if="r.inspector" class="ss-chip"
									><Icon name="user" :size="12" /> {{ r.inspector }}</span
								>
							</template>
							<template v-else>
								<span class="ss-chip"
									><Icon name="calendar" :size="12" />
									{{ thai_date(r.date) }}</span
								>
								<span
									v-if="r.status === 'Open' && r.open_items"
									class="ss-tag tone-amber"
									>ค้าง {{ r.open_items }} รายการ</span
								>
							</template>
							<span class="ss-chip ss-chip--id">{{ r.name }}</span>
						</div>
					</button>
				</TransitionGroup>
			</Transition>
		</div>

		<Teleport to="#ss-layer">
			<Transition name="ss-pop">
				<button
					v-if="can_create && !wide"
					type="button"
					class="ss-fab"
					@click="create"
				>
					<Icon name="plus" :size="26" :stroke="2.6" />
					<span>{{ create_label }}</span>
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
import StatusTabs from "../../../shared/components/StatusTabs.vue";
import DataTable from "../../../shared/components/DataTable.vue";
import HeaderSearch from "../../../shared/components/HeaderSearch.vue";
import { matches, use_wide } from "../../../shared/table.js";
import {
	boot,
	call,
	go,
	relative_date,
	remember_tab,
	show_error,
	state,
	thai_date,
} from "../../../shared/api.js";

const INSPECTION_COLUMNS = [
	{ key: "name", label: "เลขที่", sort: true, class: "col-no" },
	{ key: "title", label: "เรื่อง", sort: true, class: "col-subject" },
	{ key: "wbs", label: "WBS", sort: true, class: "col-date" },
	{ key: "location", label: "ตำแหน่ง", sort: true, class: "col-date col-wide" },
	{ key: "request_date", label: "วันที่ขอ", sort: true, class: "col-date is-date" },
	{ key: "inspection_date", label: "วันที่ตรวจ", sort: true, class: "col-date is-date" },
	{ key: "inspector", label: "ผู้ตรวจ", sort: true, class: "col-date col-wide" },
];
const PUNCH_COLUMNS = [
	{ key: "name", label: "เลขที่", sort: true, class: "col-no" },
	{ key: "title", label: "เรื่อง", sort: true, class: "col-subject" },
	{ key: "date", label: "วันที่", sort: true, class: "col-date is-date" },
	{ key: "open_items", label: "รายการค้าง", sort: true, class: "is-num" },
];

const tab = ref((state.route.params.tab === "punch" && boot.can.punch_list) || !boot.can.inspection ? "punch" : "inspection");
const rows = ref(null);
const loading = ref(false);
const wide = use_wide();
const txt = ref("");
const tabs = computed(() => [
	...(boot.can.inspection
		? [{ value: "inspection", label: "ขอตรวจงาน", count: state.summaries.work?.inspections_pending || 0 }]
		: []),
	...(boot.can.punch_list
		? [{ value: "punch", label: "Punch List", count: state.summaries.work?.punch_open || 0 }]
		: []),
]);
const create_label = computed(() =>
	tab.value === "inspection" ? "ขอตรวจงาน" : "สร้าง Punch List"
);
const shown_rows = computed(() =>
	(rows.value || []).filter((r) => matches(txt.value, r.title, r.wbs, r.item_name, r.location))
);
const doctype = computed(() => (tab.value === "punch" ? "Punch List" : "Inspection Request"));

const cm = computed(() => state.summaries.work?.construction_management);
const can_create = computed(
	() => cm.value && (tab.value === "inspection" ? boot.can.create_inspection : boot.can.create_punch_list)
);

let request_id = 0;
async function load() {
	const id = ++request_id;
	loading.value = true;
	try {
		const result = await call("consbiz.site_app.get_inspections", {
			project: state.project.name,
			kind: tab.value,
		});
		if (id === request_id) rows.value = result;
	} catch (error) {
		show_error(error);
		rows.value ??= [];
	} finally {
		if (id === request_id) loading.value = false;
	}
}

function open_doc(row) {
	go("site-doc", { kind: tab.value, name: row.name });
}
function create() {
	go("site-form", { kind: tab.value, name: "new" });
}

watch(tab, (value) => {
	remember_tab("inspections", value, "inspection");
	rows.value = null;
	load();
});
load();
</script>
