<template>
	<div>
		<TopBar title="ยืม-คืนอุปกรณ์" :subtitle="state.project?.project_name">
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
					{ value: 'out', label: 'ค้างคืน', count: data?.outstanding.length || 0 },
					{ value: 'done', label: 'คืนครบแล้ว' },
				]"
			/>

			<Skeleton v-if="data === null" />
			<Transition v-else name="ss-fade" mode="out-in">
				<div v-if="tab === 'out'" key="out">
					<Empty
						v-if="!data.outstanding.length"
						icon="sparkles"
						title="ไม่มีอุปกรณ์ค้างคืน"
						text="อุปกรณ์ของโครงการอยู่ในคลังครบ"
					/>
					<TransitionGroup v-else tag="div" class="ss-list" name="ss-list" appear>
						<button
							v-for="(b, i) in data.outstanding"
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
								<span v-if="b.due_date" class="ss-due" :class="{ 'is-late': b.overdue }">
									<Icon :name="b.overdue ? 'alert' : 'clock'" :size="13" />
									{{ b.overdue ? "เกินกำหนด" : "คืน" }} {{ relative_date(b.due_date) }}
								</span>
							</div>
							<div class="ss-chips">
								<span v-for="it in b.items" :key="it.item_code" class="ss-chip">
									{{ it.item_name || it.item_code }} <b>× {{ num(it.outstanding_qty) }}</b>
								</span>
							</div>
						</button>
					</TransitionGroup>
				</div>
				<div v-else key="done">
					<Empty v-if="!data.returned.length" icon="history" title="ยังไม่มีรายการคืนครบ" />
					<div v-else class="ss-list">
						<button
							v-for="(b, i) in data.returned"
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
								<span class="ss-card-meta">{{ b.name }} · ยืม {{ thai_date(b.date) }}</span>
							</span>
							<Icon name="chevron-right" :size="18" />
						</button>
					</div>
				</div>
			</Transition>
		</div>

		<Transition name="ss-pop">
			<button v-if="boot.can.borrow" type="button" class="ss-fab" @click="go('borrow-new')">
				<Icon name="plus" :size="26" :stroke="2.6" />
				<span>ยืมอุปกรณ์</span>
			</button>
		</Transition>
	</div>
</template>

<script setup>
import { ref, watch } from "vue";
import Icon from "../components/Icon.vue";
import TopBar from "../components/TopBar.vue";
import Segmented from "../components/Segmented.vue";
import Skeleton from "../components/Skeleton.vue";
import Empty from "../components/Empty.vue";
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
} from "../api.js";

const tab = ref(state.route.params.tab === "done" ? "done" : "out");
const data = ref(null);
const loading = ref(false);

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
