<!-- ตั้งค่า HR (หมวด hr ของแอปออฟฟิศ, API consbiz/hr_setup.py): ตรวจความพร้อมของการตั้งค่า HR/เงินเดือนของบริษัท
     แต่ละข้อ = สถานะ (ผ่าน/ควรแก้/ต้องแก้) + คำอธิบาย + ปุ่มแก้อัตโนมัติ (HR Manager) หรือลิงก์ไปฟอร์มในระบบเต็ม -->
<template>
	<div>
		<TopBar title="ตั้งค่า HR">
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
				<StatusTabs v-model="filter" :options="tabs" />
				<div class="ss-list-tools">
					<button
						type="button"
						class="ss-icon-btn"
						:class="{ 'is-spinning': loading }"
						aria-label="โหลดใหม่"
						title="ตรวจใหม่"
						@click="load"
					>
						<Icon name="refresh" :size="17" />
					</button>
					<button
						v-if="data?.can_fix"
						type="button"
						class="ss-btn ss-btn--primary ss-list-create"
						:disabled="busy || !fixable.length"
						@click="fix_all"
					>
						<Icon name="check" :size="18" :stroke="2.6" />
						<span>แก้อัตโนมัติ{{ fixable.length ? ` ${fixable.length} ข้อ` : "" }}</span>
					</button>
				</div>
			</div>
			<Segmented v-else v-model="filter" :options="tabs" />

			<Skeleton v-if="data === null" :rows="6" />
			<template v-else>
				<p v-if="!data.can_fix" class="ss-note">แก้อัตโนมัติได้เฉพาะ HR Manager / System Manager</p>
				<section v-for="(label, group) in data.groups" v-show="shown(group).length" :key="group" class="hr-setup-group">
					<div class="ss-field-label">{{ label }}</div>
					<div class="ss-list">
						<div v-for="c in shown(group)" :key="c.key" class="ss-card ss-card--row hr-check" :class="`is-${c.status}`">
							<span class="hr-check-icon"><Icon :name="ICON[c.status]" :size="18" :stroke="2.4" /></span>
							<span class="ss-card-main">
								<span class="ss-card-title">{{ c.title }}</span>
								<span class="hr-check-detail">{{ c.detail }}</span>
							</span>
							<span class="hr-check-actions">
								<button
									v-if="c.fix && data.can_fix && c.status !== 'ok'"
									type="button"
									class="ss-btn ss-btn--soft"
									:disabled="busy"
									:title="c.fix"
									@click="fix(c)"
								>
									<span v-if="busy === c.key" class="ss-spinner"></span>
									<span>{{ c.fix }}</span>
								</button>
								<a v-if="c.link && c.status !== 'ok'" class="ss-btn ss-btn--ghost" :href="c.link" target="_blank">
									{{ c.link_label || "เปิดฟอร์ม" }}
								</a>
							</span>
						</div>
					</div>
				</section>
				<Empty v-if="!data.checks.filter(match).length" icon="check" title="ไม่มีข้อที่ต้องแก้" />
			</template>
		</div>

		<Teleport to="#ss-layer">
			<div v-if="!wide && data?.can_fix && fixable.length" class="ss-bottom-bar">
				<button type="button" class="ss-btn ss-btn--primary ss-btn--lg" :disabled="busy" @click="fix_all">
					<span v-if="busy" class="ss-spinner"></span>
					<span>แก้อัตโนมัติ {{ fixable.length }} ข้อ</span>
				</button>
			</div>
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
import { use_wide } from "../../../shared/table.js";
import { call, post, show_error, state, toast } from "../../../shared/api.js";

const API = "consbiz.hr_setup";
const ICON = { ok: "check", warn: "info", error: "alert" };

const wide = use_wide();
const data = ref(null);
const loading = ref(false);
const busy = ref(null);
const filter = ref("todo");

const checks = computed(() => data.value?.checks || []);
const count = (fn) => checks.value.filter(fn).length;
const tabs = computed(() => [
	{ value: "todo", label: "ต้องแก้", count: count((c) => c.status !== "ok") },
	{ value: "all", label: "ทั้งหมด", count: checks.value.length },
]);
const match = (c) => filter.value === "all" || c.status !== "ok";
const shown = (group) => checks.value.filter((c) => c.group === group && match(c));
const fixable = computed(() => checks.value.filter((c) => c.fix && c.status !== "ok"));

async function load() {
	loading.value = true;
	try {
		data.value = await call(`${API}.get_checks`, { company: state.company || undefined });
	} catch (error) {
		show_error(error);
	} finally {
		loading.value = false;
	}
}

async function fix(c, quiet = false) {
	busy.value = c.key;
	try {
		const r = await post(`${API}.apply_fix`, { key: c.key, company: data.value.company });
		Object.assign(c, { status: r.status, detail: r.detail, fix: r.fix, link: r.link, link_label: r.link_label });
		if (!quiet) toast(`${c.title}: แก้แล้ว`, "success");
		return true;
	} catch (error) {
		show_error(error);
		return false;
	} finally {
		busy.value = null;
	}
}

// แก้ตามลำดับในรายการ (นโยบายวันลาก่อนโควตา) หยุดเมื่อข้อไหนไม่สำเร็จ
// บางข้อแก้ได้หลังข้ออื่นผ่าน (โควตาวันลาต้องมีนโยบายก่อน) จึงตรวจใหม่แล้ววนอีกรอบ
async function fix_all() {
	let done = 0;
	for (let pass = 0; pass < 3 && fixable.value.length; pass += 1) {
		for (const c of [...fixable.value]) {
			if (!(await fix(c, true))) return load();
			done += 1;
		}
		await load();
	}
	toast(`แก้แล้ว ${done} ข้อ`, "success");
}

watch(() => state.company, load);
load();
</script>

<style scoped>
.hr-setup-group {
	margin-top: 12px;
}
.hr-check {
	align-items: flex-start;
}
.hr-check-icon {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	flex: none;
	width: 30px;
	height: 30px;
	border-radius: 50%;
	color: var(--tone);
	background: var(--tone-bg);
}
.hr-check.is-ok .hr-check-icon {
	--tone: var(--tone-green);
	--tone-bg: var(--tone-green-bg);
}
.hr-check.is-warn .hr-check-icon {
	--tone: var(--tone-amber);
	--tone-bg: var(--tone-amber-bg);
}
.hr-check.is-error .hr-check-icon {
	--tone: var(--tone-rose);
	--tone-bg: var(--tone-rose-bg);
}
.hr-check-detail {
	color: var(--ss-text-2);
	font-size: var(--ss-fs);
	white-space: normal;
}
.hr-check-actions {
	display: flex;
	flex-wrap: wrap;
	gap: 6px;
	justify-content: flex-end;
	flex: none;
	max-width: 45%;
}
@media (max-width: 767px) {
	.hr-check {
		flex-wrap: wrap;
	}
	.hr-check-actions {
		max-width: none;
		width: 100%;
		justify-content: flex-start;
		padding-left: 40px;
	}
}
</style>
