<template>
	<div>
		<TopBar title="รับของ" :subtitle="state.project?.project_name">
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
					{ value: 'pending', label: 'รอรับ', count: pending?.length || 0 },
					{ value: 'done', label: 'รับแล้ว' },
				]"
			/>

			<Transition name="ss-fade" mode="out-in">
				<div v-if="tab === 'pending'" key="pending">
					<Skeleton v-if="pending === null" />
					<Empty
						v-else-if="!pending.length"
						icon="sparkles"
						title="ไม่มีของรอรับ"
						text="ใบสั่งซื้อของโครงการนี้รับครบแล้ว"
					/>
					<TransitionGroup v-else tag="div" class="ss-list" name="ss-list" appear>
						<button
							v-for="(d, i) in pending"
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
									<span class="ss-card-title">{{ d.party || "ไม่ระบุผู้ขาย" }}</span>
									<span class="ss-card-meta">
										<span
											class="ss-tag"
											:class="d.employer ? 'tone-violet' : 'tone-blue'"
											>{{ d.employer ? "ผู้ว่าจ้างจัดหา" : "ใบสั่งซื้อ" }}</span
										>
										{{ d.name }}
									</span>
								</span>
								<span v-if="d.schedule_date" class="ss-due" :class="{ 'is-late': d.overdue }">
									<Icon :name="d.overdue ? 'alert' : 'calendar'" :size="13" />
									{{ relative_date(d.schedule_date) }}
								</span>
							</div>
							<div class="ss-chips">
								<span v-for="n in d.items.names" :key="n" class="ss-chip">{{ n }}</span>
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
											<span class="ss-card-title">{{ d.party || "รับของ" }}</span>
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
										<span v-if="d.rejected" class="ss-tag tone-rose">มีตีกลับ</span>
										<span v-for="n in d.items.names" :key="n" class="ss-chip">{{
											n
										}}</span>
										<span v-if="d.items.count > 3" class="ss-chip ss-chip--more"
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
import {
	call,
	go,
	initials,
	relative_date,
	remember_tab,
	short_time,
	show_error,
	state,
	tone,
} from "../../../shared/api.js";

const tab = ref(state.route.params.tab === "done" ? "done" : "pending");
const pending = ref(null);
const done = ref(null);
const loading = ref(false);

const done_groups = computed(() => {
	const groups = [];
	for (const row of done.value || []) {
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
		if (tab.value === "pending") pending.value = await call("get_pending_receipts", { project });
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
