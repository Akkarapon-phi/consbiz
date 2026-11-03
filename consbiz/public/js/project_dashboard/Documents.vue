<script setup>
// Tab "เอกสารโครงการ": เอกสารที่อ้างแผนงานนี้แยกตามกลุ่ม (จำนวน ฉบับล่าสุด สถานะ) ปุ่มสร้างใหม่/ดูทั้งหมด และรายงาน
// ข้อมูลจาก dashboard.get_documents (แสดงเฉพาะ DocType ที่ผู้ใช้มีสิทธิ์อ่าน) สไตล์ร่วมกับ Dashboard.vue (.pd-pill, .pd-tone-*)
import { onMounted, ref } from "vue";
import { date, document_indicator } from "./format";

const API = "consbiz.consbiz.doctype.construction_management.dashboard.get_documents";

// ไอคอน lucide และโทนสีของแต่ละเอกสาร
const LOOK = {
	"Construction Baseline": ["flag", "blue"],
	"Construction Resource Plan": ["users", "blue"],
	"Construction Material Plan": ["package", "blue"],
	"Daily Request": ["clipboard", "orange"],
	"Daily Report": ["file-text", "green"],
	"Variation Order": ["git-pull-request", "orange"],
	"Extension of Time": ["hourglass", "orange"],
	"Inspection Request": ["clipboard-check", "green"],
	"Punch List": ["list-checks", "red"],
};
const REPORT_ICONS = {
	"Construction Delay Analysis": "triangle-alert",
	"Construction Earned Value": "trending-up",
	"Construction Resource Histogram": "activity",
};

const props = defineProps({ name: String });
const data = ref(null);

async function load() {
	const { message } = await frappe.call(API, { name: props.name });
	data.value = message;
}
defineExpose({ load });
onMounted(load);

const icon = (name, size = "md") => frappe.utils.icon(name, size);
const look = (doctype) => LOOK[doctype] || ["file-text", "gray"];
const slug = (doctype) => frappe.router.slug(doctype);

function create(item) {
	frappe.new_doc(item.doctype, { construction_management: props.name });
}

function open_all(item) {
	if (item.single) {
		frappe.set_route("Form", item.doctype, props.name);
		return;
	}
	frappe.route_options = { construction_management: props.name };
	frappe.set_route("List", item.doctype);
}

function open_report(report) {
	frappe.set_route("query-report", report.name, { construction_management: props.name });
}
</script>

<template>
	<div class="pdoc">
		<div v-if="!data" class="pdoc-grid">
			<div v-for="i in 6" :key="i" class="pdoc-skeleton" />
		</div>
		<template v-else>
			<section v-for="group in data.groups" :key="group.label" class="pdoc-group">
				<h6 class="pdoc-group-title">{{ group.label }}</h6>
				<div class="pdoc-grid">
					<article
						v-for="item in group.items"
						:key="item.doctype"
						class="pdoc-card"
						:class="`pd-tone-${look(item.doctype)[1]}`"
					>
						<header class="pdoc-head">
							<span class="pdoc-icon" v-html="icon(look(item.doctype)[0])" />
							<a href="#" class="pdoc-title" @click.prevent="open_all(item)">{{ item.label }}</a>
							<span v-if="!item.single" class="pdoc-count">{{ item.count }}</span>
						</header>

						<ul v-if="item.recent.length && !item.single" class="pdoc-list">
							<li v-for="row in item.recent" :key="row.name">
								<a :href="`/app/${slug(item.doctype)}/${encodeURIComponent(row.name)}`" class="pdoc-row">
									<span class="pdoc-row-name">
										<span class="pdoc-row-title">{{ row.title || row.name }}</span>
										<span v-if="row.date" class="pdoc-row-date">{{ date(row.date) }}</span>
									</span>
									<span
										v-if="document_indicator(row, item.submittable)"
										class="pd-pill pd-pill-sm"
										:class="`pd-tone-${document_indicator(row, item.submittable).color}`"
									>
										{{ document_indicator(row, item.submittable).label }}
									</span>
								</a>
							</li>
						</ul>
						<div v-else class="pdoc-note">
							<template v-if="item.single">
								{{ item.count ? __("สร้างแล้ว · 1 ฉบับต่อแผนงาน") : __("ยังไม่ได้สร้าง") }}
							</template>
							<template v-else>{{ __("ยังไม่มีเอกสาร") }}</template>
						</div>

						<footer class="pdoc-foot">
							<span v-if="item.drafts" class="pd-pill pd-pill-sm pd-tone-gray">
								{{ __("ฉบับร่าง {0}", [item.drafts]) }}
							</span>
							<span class="pdoc-actions">
								<button v-if="item.count" type="button" class="pdoc-btn" @click="open_all(item)">
									{{ item.single ? __("เปิด") : __("ดูทั้งหมด") }}
								</button>
								<button
									v-if="item.can_create && !(item.single && item.count)"
									type="button"
									class="pdoc-btn pdoc-btn-primary"
									@click="create(item)"
								>
									<span v-html="icon('plus', 'xs')" />{{ __("สร้าง") }}
								</button>
							</span>
						</footer>
					</article>
				</div>
			</section>

			<section v-if="data.reports.length" class="pdoc-group">
				<h6 class="pdoc-group-title">{{ __("รายงาน") }}</h6>
				<div class="pdoc-grid">
					<button
						v-for="report in data.reports"
						:key="report.name"
						type="button"
						class="pdoc-card pdoc-report pd-tone-blue"
						@click="open_report(report)"
					>
						<span class="pdoc-icon" v-html="icon(REPORT_ICONS[report.name] || 'file-text')" />
						<span class="pdoc-report-text">
							<span class="pdoc-title">{{ report.label }}</span>
							<span class="pdoc-note">{{ report.description }}</span>
						</span>
						<span class="pdoc-arrow" v-html="icon('chevron-right', 'sm')" />
					</button>
				</div>
			</section>
		</template>
	</div>
</template>

<style scoped>
.pdoc {
	padding: var(--padding-sm) 0 var(--padding-xl);
}
.pdoc-group {
	margin-bottom: 28px;
}
.pdoc-group-title {
	margin: 0 0 12px 4px;
	color: var(--text-muted);
	font-size: var(--text-xs);
	font-weight: 700;
	letter-spacing: 0.06em;
	text-transform: uppercase;
}
.pdoc-grid {
	display: grid;
	grid-template-columns: repeat(auto-fill, minmax(min(300px, 100%), 1fr));
	gap: 16px;
}
.pdoc-card {
	display: flex;
	flex-direction: column;
	gap: 14px;
	min-width: 0;
	padding: 18px 20px;
	border: 1px solid var(--pd-border);
	border-radius: var(--pd-radius);
	background: var(--card-bg);
	box-shadow: var(--pd-shadow);
	text-align: left;
	color: var(--text-color);
	transition:
		transform 0.15s ease,
		box-shadow 0.15s ease;
}
.pdoc-card:hover {
	box-shadow: var(--pd-shadow-hover);
}
.pdoc-head {
	display: flex;
	align-items: center;
	gap: 12px;
}
.pdoc-icon {
	display: grid;
	flex: none;
	place-items: center;
	width: 40px;
	height: 40px;
	border-radius: 12px;
	background: var(--pd-tone-bg);
	color: var(--pd-tone-fg);
}
.pdoc-icon :deep(svg) {
	stroke: currentColor;
}
.pdoc-title {
	flex: 1;
	min-width: 0;
	color: var(--heading-color);
	font-size: var(--text-md);
	font-weight: 700;
}
a.pdoc-title:hover {
	text-decoration: none;
	color: var(--pd-tone-fg);
}
.pdoc-count {
	min-width: 32px;
	padding: 2px 10px;
	border-radius: 999px;
	background: var(--subtle-fg);
	color: var(--heading-color);
	font-size: var(--text-sm);
	font-weight: 700;
	text-align: center;
	font-variant-numeric: tabular-nums;
}
.pdoc-list {
	display: flex;
	flex-direction: column;
	gap: 2px;
	margin: 0;
	padding: 0;
	list-style: none;
}
.pdoc-row {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 10px;
	padding: 8px 10px;
	margin: 0 -10px;
	border-radius: var(--pd-radius-sm);
	color: var(--text-color);
	transition: background 0.15s ease;
}
.pdoc-row:hover {
	background: var(--fg-hover-color);
	text-decoration: none;
}
.pdoc-row-name {
	display: flex;
	flex-direction: column;
	min-width: 0;
}
.pdoc-row-title {
	overflow: hidden;
	font-weight: 500;
	text-overflow: ellipsis;
	white-space: nowrap;
}
.pdoc-row-date {
	color: var(--text-muted);
	font-size: var(--text-xs);
}
.pdoc-note {
	color: var(--text-muted);
	font-size: var(--text-sm);
}
.pdoc-card > .pdoc-note {
	padding: 14px;
	border-radius: var(--pd-radius-sm);
	background: var(--subtle-fg);
	text-align: center;
}
.pdoc-foot {
	display: flex;
	align-items: center;
	gap: 8px;
	margin-top: auto;
}
.pdoc-actions {
	display: flex;
	gap: 8px;
	margin-left: auto;
}
.pdoc-btn {
	display: inline-flex;
	align-items: center;
	gap: 4px;
	height: 30px;
	padding: 0 14px;
	border: 1px solid var(--pd-border);
	border-radius: var(--radius);
	background: var(--card-bg);
	color: var(--text-color);
	font-size: var(--text-sm);
	font-weight: 500;
	transition: background 0.15s ease;
}
.pdoc-btn:hover {
	background: var(--fg-hover-color);
}
.pdoc-btn-primary {
	border-color: transparent;
	background: var(--btn-primary, var(--primary));
	color: var(--neutral-white, #fff);
}
.pdoc-btn-primary:hover {
	background: var(--btn-primary, var(--primary));
	opacity: 0.9;
}
.pdoc-btn-primary :deep(svg) {
	stroke: currentColor;
}
.pdoc-report {
	flex-direction: row;
	align-items: center;
	cursor: pointer;
}
.pdoc-report:hover {
	transform: translateY(-2px);
}
.pdoc-report-text {
	display: flex;
	flex: 1;
	flex-direction: column;
	gap: 2px;
	min-width: 0;
}
.pdoc-arrow {
	display: flex;
	color: var(--text-muted);
}
.pdoc-skeleton {
	height: 170px;
	border-radius: var(--pd-radius);
	background: linear-gradient(90deg, var(--control-bg), var(--subtle-fg), var(--control-bg));
	background-size: 200% 100%;
	animation: pdoc-shimmer 1.2s ease-in-out infinite;
}
@keyframes pdoc-shimmer {
	to {
		background-position: -200% 0;
	}
}
</style>
