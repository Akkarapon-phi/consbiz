<template>
	<div>
		<TopBar title="คอนกรีต" :subtitle="state.project?.project_name" back_to="work">
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
			<Skeleton v-if="data === null" />
			<Empty
				v-else-if="!data.construction_management"
				icon="layers"
				title="โครงการนี้ยังไม่มีแผนงาน"
				text="บันทึกคอนกรีตต้องอ้างงาน (WBS) ในแผนงานก่อสร้าง"
			/>
			<template v-else>
				<div class="ss-metric-row">
					<div class="ss-metric tone-violet">
						<span>เดือนนี้</span>
						<b>{{ num(month_total) }}</b>
						<small>คิว</small>
					</div>
					<div class="ss-metric tone-blue">
						<span>ทั้งหมด</span>
						<b>{{ num(total) }}</b>
						<small>คิว · {{ data.docs.filter((d) => d.docstatus === 1).length }} จุด</small>
					</div>
				</div>

				<Empty
					v-if="!data.docs.length"
					icon="truck"
					title="ยังไม่มีบันทึกการเท"
					text="กดปุ่ม + เพื่อเริ่มบันทึกการเทจุดแรก"
				/>
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
								<span class="ss-avatar tone-violet"><Icon name="concrete" :size="18" /></span>
								<span class="ss-card-main">
									<span class="ss-card-title">{{ d.task_name || d.wbs }}</span>
									<span class="ss-card-meta">
										<span class="ss-wbs">{{ d.wbs }}</span>
										<template v-if="d.location"> · {{ d.location }}</template>
									</span>
								</span>
								<span class="ss-qty"
									><b>{{ num(d.total_qty) }}</b
									><small>คิว</small></span
								>
							</div>
							<div class="ss-chips">
								<span v-if="d.docstatus === 0" class="ss-tag tone-amber">ร่าง</span>
								<span class="ss-chip"
									><Icon name="ticket" :size="13" /> {{ d.ticket_count }} คัน</span
								>
								<span v-if="d.strength" class="ss-chip">{{ d.strength }}</span>
								<span v-if="d.employer_qty" class="ss-tag tone-violet"
									>ผู้ว่าจ้าง {{ num(d.employer_qty) }}</span
								>
								<span
									v-if="d.planned_qty"
									class="ss-chip"
									:class="{ 'ss-text-danger': d.total_qty > d.planned_qty * 1.05 }"
								>
									แผน {{ num(d.planned_qty) }}
								</span>
							</div>
						</button>
					</div>
				</template>
			</template>
		</div>

		<Teleport to="#ss-layer">
			<Transition name="ss-pop">
				<button
					v-if="data?.construction_management"
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
import { call, go, num, relative_date, show_error, state, today } from "../../../shared/api.js";

const data = ref(null);
const loading = ref(false);

const submitted = computed(() => (data.value?.docs || []).filter((d) => d.docstatus === 1));
const total = computed(() => submitted.value.reduce((s, d) => s + (d.total_qty || 0), 0));
const month_total = computed(() =>
	submitted.value
		.filter((d) => String(d.date).slice(0, 7) === today().slice(0, 7))
		.reduce((s, d) => s + (d.total_qty || 0), 0)
);
const groups = computed(() => {
	const out = [];
	for (const row of data.value?.docs || []) {
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
