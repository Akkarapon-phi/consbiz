<!-- วันหยุดประจำสัปดาห์ (Weekly Day Off): หยุด 1 วันต่อสัปดาห์ เลือกเสาร์หรืออาทิตย์ ใครลงก่อนได้ก่อนตามโควตาของโครงการ มีผลทันที
     tab ของฉัน = 8 สัปดาห์ (สัปดาห์นี้ก่อน) แตะวันเพื่อเลือก/เปลี่ยน ได้ถึงวันหยุดนั้น
     tab ทีม = ใครหยุดวันไหนในสัปดาห์ที่เลือก (พนักงานในโครงการเดียวกัน) API self_service.get_day_off / book_day_off / get_team_day_off -->
<template>
	<div>
		<TopBar title="วันหยุด" no_project>
			<template #actions>
				<button
					v-if="!wide"
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
			<div v-if="wide" class="ss-list-head">
				<StatusTabs v-model="tab" :options="TABS" />
				<div class="ss-list-tools">
					<button
						type="button"
						class="ss-icon-btn"
						:class="{ 'is-spinning': loading }"
						aria-label="โหลดใหม่"
						@click="reload"
					>
						<Icon name="refresh" :size="17" />
					</button>
				</div>
			</div>
			<div v-else class="ss-tabs">
				<button
					v-for="t in TABS"
					:key="t.value"
					type="button"
					class="ss-tab"
					:class="{ 'is-active': tab === t.value }"
					@click="tab = t.value"
				>
					{{ t.label }}
				</button>
			</div>

			<!-- ของฉัน -->
			<template v-if="tab === 'mine'">
				<Skeleton v-if="mine === null" :rows="3" />
				<template v-else>
					<p class="ss-note">
						หยุดสัปดาห์ละ 1 วัน เลือกเสาร์หรืออาทิตย์ ใครลงก่อนได้ก่อน เปลี่ยนได้จนถึงวันหยุดนั้น
						<template v-if="mine.project">
							· {{ mine.project.project_name || mine.project.name }} ทีม {{ mine.team_size }} คน (เสาร์
							{{ mine.capacity.Saturday }} / อาทิตย์ {{ mine.capacity.Sunday }})
						</template>
					</p>
					<div class="ss-dayoff-weeks">
						<section
							v-for="(w, i) in mine.weeks"
							:key="w.week_start"
							class="ss-card ss-dayoff-week"
							:style="{ '--i': i }"
						>
							<div class="ss-dayoff-head">
								<b>{{ week_label(w.week_start) }}</b>
								<span v-if="i === 0" class="ss-tag tone-green">สัปดาห์นี้</span>
								<span v-if="!w.mine && !w.locked && any_open(w)" class="ss-tag tone-amber">ยังไม่ได้เลือก</span>
							</div>
							<div class="ss-dayoff-days">
								<button
									v-for="day in DAYS"
									:key="day"
									type="button"
									class="ss-dayoff-day"
									:class="{
										'is-mine': w.mine === day,
										'is-full': w.days[day].full && w.mine !== day,
									}"
									:disabled="
										busy === w.week_start ||
										w.locked ||
										!w.days[day].open ||
										(w.days[day].full && w.mine !== day)
									"
									@click="pick(w, day)"
								>
									<span class="ss-dayoff-name">
										<Icon v-if="w.mine === day" name="check" :size="16" :stroke="2.6" />
										{{ LABEL[day] }} {{ thai_date(w.days[day].date) }}
									</span>
									<small>{{ slot_text(w, day) }}</small>
								</button>
							</div>
							<button
								v-if="w.mine && !w.locked && w.days[w.mine].open"
								type="button"
								class="ss-link ss-dayoff-clear"
								:disabled="busy === w.week_start"
								@click="pick(w, null)"
							>
								ยกเลิกการเลือก
							</button>
						</section>
					</div>
				</template>
			</template>

			<!-- ทีม -->
			<template v-else>
				<div class="ss-card ss-dayoff-nav">
					<button type="button" class="ss-icon-btn" aria-label="สัปดาห์ก่อน" @click="move(-1)">
						<Icon name="chevron-left" :size="20" />
					</button>
					<b>{{ week_label(team_week) }}</b>
					<button type="button" class="ss-icon-btn" aria-label="สัปดาห์ถัดไป" @click="move(1)">
						<Icon name="chevron-right" :size="20" />
					</button>
				</div>
				<Skeleton v-if="team === null" :rows="3" />
				<Empty
					v-else-if="!team.project"
					icon="users"
					title="ยังไม่ได้ประจำโครงการ"
					text="ตารางทีมแสดงเมื่อฝ่ายบุคคลตั้งโครงการที่ประจำให้แล้ว"
				/>
				<div v-else class="ss-dayoff-team">
					<section v-for="group in team_groups" :key="group.key" class="ss-card ss-dayoff-group">
						<div class="ss-dayoff-head">
							<b>{{ group.label }}</b>
							<span class="ss-tag" :class="`tone-${group.tone}`">{{ group.count }}</span>
						</div>
						<div v-if="!group.people.length" class="ss-dayoff-empty">—</div>
						<div v-for="p in group.people" :key="p.name" class="ss-dayoff-person" :class="{ 'is-me': p.me }">
							<span class="ss-avatar" :class="`tone-${tone(p.name)}`">
								<img v-if="p.image" :src="p.image" alt="" />
								<template v-else>{{ initials(p.employee_name) }}</template>
							</span>
							<span class="ss-card-main">
								<span class="ss-card-title">{{ p.employee_name }}<template v-if="p.me"> (ฉัน)</template></span>
								<span v-if="p.designation" class="ss-card-meta">{{ p.designation }}</span>
							</span>
						</div>
					</section>
				</div>
			</template>
		</div>
	</div>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import Icon from "../../shared/components/Icon.vue";
import TopBar from "../../shared/components/TopBar.vue";
import Skeleton from "../../shared/components/Skeleton.vue";
import Empty from "../../shared/components/Empty.vue";
import StatusTabs from "../../shared/components/StatusTabs.vue";
import { use_wide } from "../../shared/table.js";
import { call, initials, post, show_error, thai_date, toast, tone, today } from "../../shared/api.js";

const API = "consbiz.self_service.";
const DAYS = ["Saturday", "Sunday"];
const LABEL = { Saturday: "เสาร์", Sunday: "อาทิตย์" };
const TABS = [
	{ value: "mine", label: "ของฉัน" },
	{ value: "team", label: "ทีม" },
];

const wide = use_wide();
const tab = ref("mine");
const mine = ref(null);
const team = ref(null);
const loading = ref(false);
const busy = ref("");

const iso = (d) =>
	`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
function add_days(value, n) {
	const [y, m, d] = String(value).slice(0, 10).split("-").map(Number);
	return iso(new Date(y, m - 1, d + n));
}
function monday_of(value) {
	const [y, m, d] = String(value).slice(0, 10).split("-").map(Number);
	const day = new Date(y, m - 1, d).getDay();
	return add_days(value, -((day + 6) % 7));
}
const week_label = (start) => `${thai_date(start)} – ${thai_date(add_days(start, 6), { year: true })}`;
const any_open = (w) => DAYS.some((d) => w.days[d].open);

function slot_text(w, day) {
	const info = w.days[day];
	if (!info.open) return "ผ่านไปแล้ว";
	if (info.limit == null) return w.mine === day ? "วันหยุดของฉัน" : "เลือกได้";
	const used = info.taken + (w.mine === day ? 1 : 0);
	if (w.mine === day) return `วันหยุดของฉัน · ${used}/${info.limit}`;
	return info.full ? `เต็ม ${info.limit}/${info.limit}` : `ว่าง ${info.limit - info.taken} จาก ${info.limit}`;
}

async function load_mine() {
	loading.value = true;
	try {
		mine.value = await call(`${API}get_day_off`);
	} catch (error) {
		show_error(error);
		mine.value ??= { weeks: [], capacity: {} };
	} finally {
		loading.value = false;
	}
}

async function pick(w, day) {
	if (day === w.mine) return;
	busy.value = w.week_start;
	try {
		const result = await post(`${API}book_day_off`, { week_start: w.week_start, day_off: day || "" });
		const at = mine.value.weeks.findIndex((x) => x.week_start === w.week_start);
		if (at >= 0) mine.value.weeks[at] = result;
		toast(day ? `หยุดวัน${LABEL[day]} ${thai_date(result.days[day].date)}` : "ยกเลิกวันหยุดแล้ว", "success");
	} catch (error) {
		show_error(error);
		// อาจมีคนลงไปก่อน: โหลดที่ว่างล่าสุด
		load_mine();
	} finally {
		busy.value = "";
	}
}

// ---------------------------------------------------------------- ทีม

const team_week = ref(monday_of(today()));
async function load_team() {
	team.value = null;
	loading.value = true;
	try {
		team.value = await call(`${API}get_team_day_off`, { week_start: team_week.value });
	} catch (error) {
		show_error(error);
		team.value = { project: null };
	} finally {
		loading.value = false;
	}
}
function move(n) {
	team_week.value = add_days(team_week.value, 7 * n);
}
const team_groups = computed(() => {
	const t = team.value || {};
	const cap = t.capacity || {};
	return [
		{ key: "Saturday", label: `หยุดเสาร์ ${thai_date(add_days(team_week.value, 5))}`, tone: "green", people: t.Saturday || [], count: `${(t.Saturday || []).length}/${cap.Saturday ?? "-"}` },
		{ key: "Sunday", label: `หยุดอาทิตย์ ${thai_date(add_days(team_week.value, 6))}`, tone: "teal", people: t.Sunday || [], count: `${(t.Sunday || []).length}/${cap.Sunday ?? "-"}` },
		{ key: "none", label: "ยังไม่ได้เลือก", tone: "amber", people: t.none || [], count: (t.none || []).length },
	];
});

function reload() {
	if (tab.value === "mine") load_mine();
	else load_team();
}
watch(tab, reload);
watch(team_week, load_team);
load_mine();
</script>
