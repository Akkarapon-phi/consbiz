<template>
	<div>
		<TopBar title="เอกสารโครงการ" :subtitle="state.project?.project_name">
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
			<Skeleton v-if="data === null" :rows="4" />
			<Empty
				v-else-if="data === false"
				icon="layers"
				title="โครงการนี้ยังไม่มีแผนงาน"
				text="เอกสารโครงการอ้างแผนงานก่อสร้าง"
			/>
			<template v-else>
				<template v-for="group in data.groups" :key="group.label">
					<h2 class="ss-section-title">{{ group.label }}</h2>
					<div class="ss-list">
						<div
							v-for="(item, i) in group.items"
							:key="item.doctype"
							class="ss-card"
							:style="{ '--i': i }"
						>
							<div class="ss-card-head">
								<span class="ss-avatar" :class="`tone-${tone_of(item.doctype)}`">
									<Icon :name="icon_of(item.doctype)" :size="18" />
								</span>
								<span class="ss-card-main">
									<span class="ss-card-title">{{ item.label }}</span>
									<span class="ss-card-meta"
										>{{ item.count }} ฉบับ<template v-if="item.drafts">
											· ร่าง {{ item.drafts }}</template
										></span
									>
								</span>
								<a class="ss-link" :href="list_url(item)">ดูทั้งหมด</a>
							</div>
							<div v-if="item.recent?.length" class="ss-doc-recent">
								<a
									v-for="r in item.recent"
									:key="r.name"
									:href="desk_url(item.doctype, r.name)"
									class="ss-doc-line"
									@click="open_in_app(item, r, $event)"
								>
									<span>
										<b>{{ r.title || r.name }}</b>
										<small
											>{{ r.title ? r.name : ""
											}}{{
												r.date ? ` · ${thai_date(r.date, { year: true })}` : ""
											}}</small
										>
									</span>
									<span class="ss-tag" :class="`tone-${status_of(r).tone}`">{{
										status_of(r).label
									}}</span>
								</a>
							</div>
						</div>
					</div>
				</template>

				<template v-if="data.reports?.length">
					<h2 class="ss-section-title">รายงาน</h2>
					<div class="ss-list">
						<a
							v-for="(r, i) in data.reports"
							:key="r.name"
							class="ss-card ss-card--row"
							:style="{ '--i': i }"
							:href="`/app/query-report/${encodeURIComponent(
								r.name
							)}?construction_management=${encodeURIComponent(data.construction_management)}`"
						>
							<span class="ss-avatar tone-indigo"><Icon name="trending" :size="18" /></span>
							<span class="ss-card-main">
								<span class="ss-card-title">{{ r.label }}</span>
								<span class="ss-card-sub">{{ r.description }}</span>
							</span>
							<Icon name="external" :size="16" />
						</a>
					</div>
				</template>
			</template>
		</div>
	</div>
</template>

<script setup>
import { ref } from "vue";
import Icon from "../../../shared/components/Icon.vue";
import TopBar from "../../../shared/components/TopBar.vue";
import Skeleton from "../../../shared/components/Skeleton.vue";
import Empty from "../../../shared/components/Empty.vue";
import { call, desk_url, go, show_error, state, thai_date } from "../../../shared/api.js";

const data = ref(null);
const loading = ref(false);

const ICONS = {
	"Construction Baseline": ["layers", "indigo"],
	"Construction Resource Plan": ["users", "teal"],
	"Construction Material Plan": ["cart", "orange"],
	"Daily Request": ["send", "blue"],
	"Daily Report": ["clipboard", "orange"],
	"Variation Order": ["swap", "violet"],
	"Extension of Time": ["clock", "amber"],
	"Inspection Request": ["search-check", "teal"],
	"Punch List": ["list-checks", "rose"],
};
const icon_of = (doctype) => ICONS[doctype]?.[0] || "file";
const tone_of = (doctype) => ICONS[doctype]?.[1] || "blue";

// สถานะ (ช่องสถานะของแต่ละชนิด หรือ docstatus)
const STATUS = {
	Pending: ["รออนุมัติ", "amber"],
	Approved: ["อนุมัติแล้ว", "green"],
	Rejected: ["ไม่อนุมัติ", "rose"],
	Completed: ["ทำรายงานแล้ว", "green"],
	Passed: ["ผ่าน", "green"],
	"Passed with Comments": ["ผ่าน (มีข้อแนะนำ)", "teal"],
	Failed: ["ไม่ผ่าน", "rose"],
	Open: ["ยังแก้ไม่ครบ", "amber"],
	Closed: ["ปิดแล้ว", "green"],
	Cancelled: ["ยกเลิก", "gray"],
};
function status_of(r) {
	if (r.status && STATUS[r.status]) return { label: STATUS[r.status][0], tone: STATUS[r.status][1] };
	if (r.docstatus === 2) return { label: "ยกเลิก", tone: "gray" };
	return r.docstatus === 1 ? { label: "ส่งแล้ว", tone: "green" } : { label: "ร่าง", tone: "gray" };
}

const slug = (doctype) => doctype.toLowerCase().replace(/ /g, "-");
const list_url = (item) =>
	`/app/${slug(item.doctype)}?construction_management=${encodeURIComponent(
		data.value.construction_management
	)}`;
// รายงาน/ขออนุมัติเปิดในแอป (หมวดควบคุมงาน) ที่เหลือเปิดในระบบเต็ม
const IN_APP = { "Daily Report": "dr", "Daily Request": "drq" };
function open_in_app(item, r, event) {
	if (!IN_APP[item.doctype]) return;
	event.preventDefault();
	go("report-view", { kind: IN_APP[item.doctype], name: r.name });
}

async function load() {
	loading.value = true;
	try {
		data.value =
			(await call("consbiz.site_app.get_pm_documents", { project: state.project.name })) || false;
	} catch (error) {
		show_error(error);
		data.value ??= false;
	} finally {
		loading.value = false;
	}
}

load();
</script>
