<template>
	<!-- รายการเอกสารจัดซื้อ/ขาย (kind = ชื่อหน้า: mr/po/pi/qtn/so/si) -->
	<div>
		<TopBar :title="config.label" :subtitle="subtitle">
			<template #actions>
				<a
					class="ss-icon-btn"
					:href="new_url"
					:aria-label="`สร้าง${config.label}ในระบบเต็ม`"
					:title="`สร้าง${config.label} (ระบบเต็ม)`"
				>
					<Icon name="plus" :size="21" :stroke="2.4" />
				</a>
				<button
					type="button"
					class="ss-icon-btn"
					:class="{ 'is-spinning': loading }"
					aria-label="โหลดใหม่"
					@click="reload"
				>
					<Icon name="refresh" :size="20" />
				</button>
			</template>
		</TopBar>

		<div class="ss-content">
			<ScopeSwitch v-if="config.project" />
			<div class="ss-search">
				<Icon name="search" :size="18" />
				<input
					v-model="search"
					type="search"
					:placeholder="`ค้นหาเลขที่${config.party ? ` / ${config.party}` : ''}`"
				/>
			</div>
			<div class="ss-filters">
				<button
					v-for="f in filters"
					:key="f.value"
					type="button"
					class="ss-filter"
					:class="{ 'is-active': filter === f.value }"
					@click="filter = f.value"
				>
					{{ f.label }}
				</button>
			</div>

			<Skeleton v-if="rows === null" :rows="4" />
			<Empty
				v-else-if="!rows.length"
				:icon="config.icon"
				:title="`ไม่มี${config.label}`"
				:text="
					search
						? 'ลองค้นหาด้วยคำอื่น'
						: state.doc_scope === 'project' && config.project
						? 'ลองดูทุกโครงการ'
						: ''
				"
			/>
			<template v-else>
				<!-- แท็บเล็ต/จอใหญ่: ตาราง, มือถือ: การ์ด -->
				<DocTable v-if="wide" :rows="rows" :kind="kind" />
				<TransitionGroup v-else tag="div" class="ss-list" name="ss-list" appear>
					<DocCard v-for="(row, i) in rows" :key="row.name" :row="row" :kind="kind" :i="i % 30" />
				</TransitionGroup>
				<button
					v-if="more"
					type="button"
					class="ss-btn ss-btn--ghost ss-btn--block"
					:disabled="loading"
					@click="load(true)"
				>
					<span v-if="loading" class="ss-spinner"></span>
					<template v-else>โหลดเพิ่ม</template>
				</button>
			</template>
		</div>
	</div>
</template>

<script setup>
import { computed, onBeforeUnmount, ref, watch } from "vue";
import Icon from "../../components/Icon.vue";
import TopBar from "../../components/TopBar.vue";
import Skeleton from "../../components/Skeleton.vue";
import Empty from "../../components/Empty.vue";
import DocCard from "./DocCard.vue";
import DocTable from "./DocTable.vue";
import ScopeSwitch from "./ScopeSwitch.vue";
import { DOC_KINDS } from "../../sections.js";
import { call, replace_params, show_error, state } from "../../api.js";

const kind = state.route.view;
const config = DOC_KINDS[kind];
const FILTERS = ["todo", "draft", "done", "all"];

const filters = [
	{ value: "todo", label: config.todo },
	{ value: "draft", label: "ร่าง" },
	{ value: "done", label: "เสร็จแล้ว" },
	{ value: "all", label: "ทั้งหมด" },
];
const filter = ref(FILTERS.includes(state.route.params.filter) ? state.route.params.filter : "todo");
const search = ref("");
const rows = ref(null);
const mq_wide = window.matchMedia("(min-width: 768px)");
const wide = ref(mq_wide.matches);
const on_media = () => (wide.value = mq_wide.matches);
mq_wide.addEventListener("change", on_media);
onBeforeUnmount(() => mq_wide.removeEventListener("change", on_media));
const more = ref(false);
const loading = ref(false);

const subtitle = computed(() =>
	config.project && state.doc_scope === "project" ? state.project?.project_name : "ทุกโครงการ"
);
const new_url = `/app/${config.doctype.toLowerCase().replace(/ /g, "-")}/new${
	kind === "mr" ? "?material_request_type=Purchase" : ""
}`;

let request_id = 0;
async function load(append = false) {
	const id = ++request_id;
	loading.value = true;
	try {
		const result = await call("consbiz.site_docs.get_docs", {
			kind,
			project: state.project?.name,
			scope: state.doc_scope,
			filter: filter.value,
			search: search.value.trim() || undefined,
			start: append ? rows.value.length : 0,
		});
		if (id !== request_id) return;
		rows.value = append ? [...rows.value, ...result.rows] : result.rows;
		more.value = result.more;
	} catch (error) {
		show_error(error);
		rows.value ??= [];
	} finally {
		if (id === request_id) loading.value = false;
	}
}

function reload() {
	rows.value = null;
	load();
}

let timer = null;
watch(search, () => {
	clearTimeout(timer);
	timer = setTimeout(reload, 300);
});
watch(filter, (value) => {
	replace_params(kind, { filter: value });
	reload();
});
watch(() => state.doc_scope, reload);
load();
</script>
