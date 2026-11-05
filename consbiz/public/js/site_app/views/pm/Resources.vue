<template>
	<!-- แผนทรัพยากร (คน/เครื่องจักร) และแผนจัดซื้อวัสดุ ดูอย่างเดียว ข้อมูลชุดเดียวกับ Tab ทรัพยากรของ CM -->
	<div>
		<TopBar title="ทรัพยากร" :subtitle="state.project?.project_name">
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
					{ value: 'material', label: 'แผนจัดซื้อวัสดุ', count: material_alerts },
					{ value: 'labour', label: 'คน/เครื่องจักร', count: labour_alerts },
				]"
			/>

			<Skeleton v-if="data === null" :rows="4" />
			<Empty
				v-else-if="data === false"
				icon="layers"
				title="โครงการนี้ยังไม่มีแผนงาน"
				text="แผนทรัพยากรและแผนจัดซื้ออ้างงานในแผนงานก่อสร้าง"
			/>

			<!-- แผนจัดซื้อวัสดุ -->
			<template v-else-if="tab === 'material'">
				<Empty
					v-if="!data.material_plan?.exists"
					icon="cart"
					title="ยังไม่มีแผนจัดซื้อวัสดุ"
					text="ใส่วัสดุของแต่ละงานที่หน้า Gantt ในระบบเต็ม"
				/>
				<template v-else>
					<div class="ss-filters">
						<button
							v-for="f in MATERIAL_FILTERS"
							:key="f.value"
							type="button"
							class="ss-filter"
							:class="{ 'is-active': material_filter === f.value }"
							@click="material_filter = f.value"
						>
							{{ f.label }} <span class="ss-filter-count">{{ material_count(f.value) }}</span>
						</button>
					</div>
					<Empty v-if="!materials.length" icon="sparkles" title="ไม่มีวัสดุที่ต้องสั่งในช่วงนี้" />
					<div class="ss-list">
						<div
							v-for="(m, i) in materials"
							:key="m.key"
							class="ss-card"
							:class="{ 'is-late': m.status === 'late' }"
							:style="{ '--i': Math.min(i, 12) }"
						>
							<div class="ss-card-head">
								<span class="ss-card-main">
									<span class="ss-card-title">{{ m.item_label || m.item_code }}</span>
									<span class="ss-card-meta"
										><i class="ss-wbs">{{ m.wbs }}</i> {{ m.item_name }}
										<span v-if="m.customer_provided" class="ss-tag tone-violet"
											>ผู้ว่าจ้างจัดหา</span
										></span
									>
								</span>
								<span class="ss-qty"
									><b>{{ num(m.qty) }}</b
									><small>{{ m.uom }}</small></span
								>
							</div>
							<div class="ss-supply">
								<div v-for="s in SUPPLY" :key="s.key" class="ss-supply-row">
									<span>{{ s.label }}</span>
									<div class="ss-plan-bar ss-plan-bar--sm">
										<span
											class="ss-plan-bar-actual"
											:style="{ width: `${pct_of(m.coverage[s.key], m.qty)}%` }"
										></span>
									</div>
									<b>{{ num(m.coverage[s.key]) }}</b>
								</div>
							</div>
							<div class="ss-chips ss-chips--wrap">
								<span v-if="m.status === 'done'" class="ss-tag tone-green"
									><Icon name="check" :size="12" :stroke="3" /> ครบแล้ว</span
								>
								<span
									v-else-if="m.order_by"
									class="ss-due"
									:class="{ 'is-late': m.status === 'late' }"
								>
									<Icon :name="m.status === 'late' ? 'alert' : 'clock'" :size="13" />
									ต้องสั่ง {{ relative_date(m.order_by) }}
								</span>
								<span v-if="m.required_by" class="ss-chip"
									>ต้องถึงหน้างาน {{ thai_date(m.required_by) }}</span
								>
								<span v-if="m.lead_time_days" class="ss-chip"
									>รอของ {{ m.lead_time_days }} วัน</span
								>
							</div>
						</div>
					</div>
					<button
						v-if="boot.sections.includes('buy')"
						type="button"
						class="ss-btn ss-btn--soft ss-btn--block"
						@click="go('mr', { filter: 'all' })"
					>
						<Icon name="clipboard" :size="17" /> ดูใบขอซื้อของโครงการ
					</button>
				</template>
			</template>

			<!-- คน / เครื่องจักร -->
			<template v-else>
				<Empty
					v-if="!data.resource_plan?.exists"
					icon="users"
					title="ยังไม่มีแผนทรัพยากร"
					text="ใส่คนและเครื่องจักรของแต่ละงานที่หน้า Gantt ในระบบเต็ม"
				/>
				<template v-else>
					<div class="ss-filters">
						<button
							v-for="f in RESOURCE_FILTERS"
							:key="f.value"
							type="button"
							class="ss-filter"
							:class="{ 'is-active': resource_filter === f.value }"
							@click="resource_filter = f.value"
						>
							{{ f.label }}
						</button>
					</div>
					<div class="ss-list">
						<div
							v-for="(r, i) in resources"
							:key="`${r.resource_type}:${r.resource}`"
							class="ss-card"
							:class="{ 'is-late': r.status === 'late' }"
							:style="{ '--i': Math.min(i, 12) }"
						>
							<div class="ss-card-head">
								<span
									class="ss-avatar"
									:class="r.resource_type === 'Labour' ? 'tone-blue' : 'tone-amber'"
								>
									<Icon
										:name="r.resource_type === 'Labour' ? 'users' : 'truck'"
										:size="18"
									/>
								</span>
								<span class="ss-card-main">
									<span class="ss-card-title">{{ r.resource }}</span>
									<span class="ss-card-meta">{{
										r.start_date
											? `${thai_date(r.start_date)} – ${thai_date(r.end_date, {
													year: true,
											  })}`
											: "ยังไม่มีวันในแผน"
									}}</span>
								</span>
								<span class="ss-qty"
									><b>{{ num(r.peak) }}</b
									><small>สูงสุด/วัน</small></span
								>
							</div>
							<div class="ss-chips ss-chips--wrap">
								<span
									v-if="r.book_by"
									class="ss-due"
									:class="{ 'is-late': r.status === 'late' }"
								>
									<Icon :name="r.status === 'late' ? 'alert' : 'clock'" :size="13" />
									ต้องจอง {{ relative_date(r.book_by) }} ({{ r.next_task }})
								</span>
								<span class="ss-chip"
									>รวม {{ num(r.total) }}
									{{ r.resource_type === "Labour" ? "คน-วัน" : "เครื่อง-วัน" }}</span
								>
								<span class="ss-chip">{{ r.tasks.length }} งาน</span>
							</div>
						</div>
					</div>
				</template>
			</template>
		</div>
	</div>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import Icon from "../../../shared/components/Icon.vue";
import TopBar from "../../../shared/components/TopBar.vue";
import Skeleton from "../../../shared/components/Skeleton.vue";
import Empty from "../../../shared/components/Empty.vue";
import Segmented from "../../../shared/components/Segmented.vue";
import {
	boot,
	call,
	go,
	num,
	relative_date,
	replace_params,
	show_error,
	state,
	thai_date,
} from "../../../shared/api.js";

const MATERIAL_FILTERS = [
	{ value: "todo", label: "ต้องสั่ง" },
	{ value: "later", label: "ข้างหน้า" },
	{ value: "done", label: "ครบแล้ว" },
	{ value: "all", label: "ทั้งหมด" },
];
const RESOURCE_FILTERS = [
	{ value: "all", label: "ทั้งหมด" },
	{ value: "Labour", label: "แรงงาน" },
	{ value: "Equipment", label: "เครื่องจักร" },
];
const SUPPLY = [
	{ key: "requested", label: "ขอซื้อ" },
	{ key: "ordered", label: "สั่งซื้อ" },
	{ key: "received", label: "รับแล้ว" },
];

const data = ref(null);
const loading = ref(false);
const tab = ref(state.route.params.tab === "labour" ? "labour" : "material");
const material_filter = ref("todo");
const resource_filter = ref("all");

const pct_of = (value, total) => (total ? Math.min(100, ((Number(value) || 0) / total) * 100) : 0);

function material_match(m, f) {
	if (f === "todo") return ["late", "due"].includes(m.status);
	if (f === "later") return m.status === "later" || !m.status;
	if (f === "done") return m.status === "done";
	return true;
}
const material_count = (f) => (data.value?.materials || []).filter((m) => material_match(m, f)).length;
const materials = computed(() =>
	(data.value?.materials || []).filter((m) => material_match(m, material_filter.value))
);
const resources = computed(() =>
	(data.value?.resources || []).filter(
		(r) => resource_filter.value === "all" || r.resource_type === resource_filter.value
	)
);
const material_alerts = computed(() => material_count("todo"));
const labour_alerts = computed(
	() => (data.value?.resources || []).filter((r) => ["late", "due"].includes(r.status)).length
);

watch(tab, (value) => replace_params("resources", { tab: value }));

async function load() {
	loading.value = true;
	try {
		data.value = (await call("consbiz.site_app.get_resources", { project: state.project.name })) || false;
		// ไม่มีวัสดุที่ต้องสั่ง: เปิดทั้งหมด
		if (data.value && !material_count("todo")) material_filter.value = "all";
	} catch (error) {
		show_error(error);
		data.value ??= false;
	} finally {
		loading.value = false;
	}
}

load();
</script>
