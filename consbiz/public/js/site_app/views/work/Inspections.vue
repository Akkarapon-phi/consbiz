<template>
	<div>
		<TopBar title="ตรวจงาน" :subtitle="state.project?.project_name">
			<template #actions>
				<button
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
			<Segmented
				v-model="tab"
				:options="[
					{
						value: 'inspection',
						label: 'ขอตรวจงาน',
						count: state.summaries.work?.inspections_pending || 0,
					},
					{ value: 'punch', label: 'Punch List', count: state.summaries.work?.punch_open || 0 },
				]"
			/>

			<Skeleton v-if="rows === null" />
			<Empty
				v-else-if="!rows.length"
				:icon="tab === 'inspection' ? 'search-check' : 'list-checks'"
				:title="tab === 'inspection' ? 'ยังไม่มีใบขอตรวจงาน' : 'ไม่มี Punch List'"
				text="กดปุ่ม + เพื่อสร้างในระบบเต็ม"
			/>
			<Transition v-else name="ss-fade" mode="out-in">
				<TransitionGroup :key="tab" tag="div" class="ss-list" name="ss-list" appear>
					<button
						v-for="(r, i) in rows"
						:key="r.name"
						type="button"
						class="ss-card"
						:class="{ 'is-late': r.status_tone === 'rose' }"
						:style="{ '--i': i }"
						@click="open(desk_url(doctype, r.name))"
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
							<span class="ss-tag" :class="`tone-${r.status_tone}`">{{ r.status_label }}</span>
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
									><Icon name="calendar" :size="12" /> {{ thai_date(r.date) }}</span
								>
								<span v-if="r.status === 'Open' && r.open_items" class="ss-tag tone-amber"
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
				<button v-if="can_create" type="button" class="ss-fab" @click="open(new_url)">
					<Icon name="plus" :size="26" :stroke="2.6" />
					<span>{{ tab === "inspection" ? "ขอตรวจงาน" : "สร้าง Punch List" }}</span>
				</button>
			</Transition>
		</Teleport>
	</div>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import Icon from "../../components/Icon.vue";
import TopBar from "../../components/TopBar.vue";
import Segmented from "../../components/Segmented.vue";
import Skeleton from "../../components/Skeleton.vue";
import Empty from "../../components/Empty.vue";
import {
	boot,
	call,
	desk_new_url,
	desk_url,
	relative_date,
	remember_tab,
	show_error,
	state,
	thai_date,
} from "../../api.js";

const tab = ref(state.route.params.tab === "punch" ? "punch" : "inspection");
const rows = ref(null);
const loading = ref(false);
const doctype = computed(() => (tab.value === "punch" ? "Punch List" : "Inspection Request"));

const cm = computed(() => state.summaries.work?.construction_management);
const can_create = computed(
	() => cm.value && (tab.value === "inspection" ? boot.can.inspection : boot.can.punch_list)
);
const new_url = computed(() => desk_new_url(doctype.value, { construction_management: cm.value }));

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

function open(url) {
	window.location.href = url;
}

watch(tab, (value) => {
	remember_tab("inspections", value, "inspection");
	rows.value = null;
	load();
});
load();
</script>
