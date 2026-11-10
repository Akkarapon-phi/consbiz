<!-- เมนูเอกสารของหมวดแผนงาน: 1 ชนิดเอกสาร = 1 tab (จำใน URL) เห็นเฉพาะชนิดที่มีสิทธิ์อ่าน
     รายการจาก site_app.get_pm_document_rows, จำนวน/สิทธิ์สร้างจาก site_app.get_pm_documents
     งานลด-เพิ่ม/EOT/ขอตรวจงาน/Punch List สร้างและดูในแอป (views/project_docs/) รายงานประจำวัน/ขออนุมัติเปิดในแอปแผนสัญญาเปิดระบบเต็ม -->
<template>
	<div>
		<TopBar title="เอกสารโครงการ" :subtitle="state.project?.project_name">
			<template #search>
				<HeaderSearch v-if="wide && active" v-model="txt" placeholder="ค้นหาเลขที่ หรือเรื่อง" />
			</template>
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
			<Skeleton v-if="data === null" :rows="4" />
			<Empty
				v-else-if="data === false"
				icon="layers"
				title="โครงการนี้ยังไม่มีแผนงาน"
				text="เอกสารโครงการอ้างแผนงานก่อสร้าง"
			/>
			<Empty v-else-if="!tabs.length" icon="file" title="ไม่มีเอกสารที่เปิดดูได้" />
			<template v-else>
				<div v-if="wide" class="ss-list-head ss-list-head--many">
					<StatusTabs v-model="tab" :options="tabs" />
					<div class="ss-list-tools">
						<button
							v-if="can_create"
							type="button"
							class="ss-btn ss-btn--primary ss-list-create"
							@click="create"
						>
							<Icon name="plus" :size="18" :stroke="2.6" />
							<span>สร้าง</span>
						</button>
						<button
							type="button"
							class="ss-icon-btn"
							:class="{ 'is-spinning': loading }"
							aria-label="โหลดใหม่"
							@click="load"
						>
							<Icon name="refresh" :size="17" />
						</button>
					</div>
				</div>
				<nav v-else class="ss-tabs" aria-label="ชนิดเอกสาร">
					<button
						v-for="t in tabs"
						:key="t.value"
						type="button"
						class="ss-tab"
						:class="{ 'is-active': tab === t.value }"
						@click="tab = t.value"
					>
						{{ t.label }}
						<span v-if="t.count" class="ss-tab-count">{{ t.count }}</span>
					</button>
				</nav>

				<!-- แผนฉบับเดียวต่อโครงการ + รายงาน -->
				<template v-if="!active">
					<div class="ss-list">
						<a
							v-for="(item, i) in plan_items"
							:key="item.doctype"
							class="ss-card ss-card--row"
							:style="{ '--i': i }"
							:href="plan_url(item)"
						>
							<span class="ss-avatar" :class="`tone-${item.doctype === 'Construction Resource Plan' ? 'teal' : 'orange'}`">
								<Icon :name="item.doctype === 'Construction Resource Plan' ? 'users' : 'cart'" :size="18" />
							</span>
							<span class="ss-card-main">
								<span class="ss-card-title">{{ item.label }}</span>
								<span class="ss-card-sub">{{ item.count ? "เปิดดูแผน" : "ยังไม่ได้สร้าง" }}</span>
							</span>
							<Icon name="external" :size="16" />
						</a>
						<a
							v-for="(r, i) in data.reports"
							:key="r.name"
							class="ss-card ss-card--row"
							:style="{ '--i': i + plan_items.length }"
							:href="`/app/query-report/${encodeURIComponent(r.name)}?construction_management=${encodeURIComponent(data.construction_management)}`"
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

				<Skeleton v-else-if="rows === null" />
				<Empty
					v-else-if="!rows.length"
					:icon="active.icon"
					:title="`ยังไม่มี ${active.label}`"
					:text="can_create ? 'กดปุ่ม + เพื่อสร้าง' : ''"
				/>
				<Empty v-else-if="!shown_rows.length" icon="search" title="ไม่พบรายการ" />
				<DataTable
					v-else-if="wide"
					:key="tab"
					:rows="shown_rows"
					:columns="columns"
					:late="(r) => r.status_tone === 'rose'"
					@open="open_row"
				>
					<template v-for="c in columns" #[c.key]="{ row }">
						<template v-if="c.key === 'name'">
							<span class="ss-doc-no">{{ row.name }}</span>
							<span v-if="row.status_label" class="ss-doc-meta">
								<span class="ss-tag" :class="`tone-${row.status_tone}`">{{ row.status_label }}</span>
							</span>
						</template>
						<template v-else-if="c.key === 'title'">
							<span class="ss-cell-main" :title="row.title">{{ row.title }}</span>
							<small v-if="active.sub?.(row)">{{ active.sub(row) }}</small>
						</template>
						<i v-else-if="c.key === 'wbs'" class="ss-wbs">{{ row.wbs }}</i>
						<template v-else>{{ c.format ? c.format(row[c.key], row) : row[c.key] }}</template>
					</template>
				</DataTable>
				<TransitionGroup v-else :key="tab" tag="div" class="ss-list" name="ss-list" appear>
					<button
						v-for="(r, i) in shown_rows"
						:key="r.name"
						type="button"
						class="ss-card"
						:class="{ 'is-late': r.status_tone === 'rose' }"
						:style="{ '--i': i }"
						@click="open_row(r)"
					>
						<div class="ss-card-head">
							<span class="ss-avatar" :class="`tone-${r.status_tone || 'indigo'}`">
								<Icon :name="active.icon" :size="18" />
							</span>
							<span class="ss-card-main">
								<span class="ss-card-title">{{ r.title || long_date(r.date) || r.name }}</span>
								<span v-if="active.sub?.(r)" class="ss-card-meta">{{ active.sub(r) }}</span>
							</span>
							<span v-if="r.status_label" class="ss-tag" :class="`tone-${r.status_tone}`">{{ r.status_label }}</span>
						</div>
						<div class="ss-chips">
							<span v-for="chip in active.chips(r).filter((c) => c.text)" :key="chip.icon" class="ss-chip">
								<Icon :name="chip.icon" :size="12" /> {{ chip.text }}
							</span>
							<span v-if="r.title" class="ss-chip ss-chip--id">{{ r.name }}</span>
						</div>
					</button>
				</TransitionGroup>

				<a v-if="active && rows && item && item.count > rows.length" class="ss-link" :href="list_url(item)">
					แสดง {{ rows.length }} จาก {{ item.count }} ฉบับ ดูทั้งหมดในระบบเต็ม
				</a>
			</template>
		</div>

		<Teleport to="#ss-layer">
			<Transition name="ss-pop">
				<button v-if="can_create && !wide" type="button" class="ss-fab" @click="create">
					<Icon name="plus" :size="26" :stroke="2.6" />
					<span>สร้าง {{ active.label }}</span>
				</button>
			</Transition>
		</Teleport>
	</div>
</template>

<script setup>
import { computed, nextTick, ref, watch } from "vue";
import Icon from "../../../shared/components/Icon.vue";
import TopBar from "../../../shared/components/TopBar.vue";
import Skeleton from "../../../shared/components/Skeleton.vue";
import Empty from "../../../shared/components/Empty.vue";
import DataTable from "../../../shared/components/DataTable.vue";
import HeaderSearch from "../../../shared/components/HeaderSearch.vue";
import StatusTabs from "../../../shared/components/StatusTabs.vue";
import {
	boot,
	call,
	desk_url,
	go,
	money,
	remember_tab,
	show_error,
	state,
	thai_date,
} from "../../../shared/api.js";
import { matches, use_wide } from "../../../shared/table.js";
import { PROJECT_KINDS } from "../project_docs/kinds.js";

const long_date = (value) => (value ? thai_date(value, { year: true }) : "");
const days = (value) => (value ? `${value} วัน` : "—");
const percent = (value) => `${Number(value || 0).toFixed(2)}%`;

const NO = { key: "name", label: "เลขที่", sort: true, class: "col-no" };
const SUBJECT = { key: "title", label: "เรื่อง", sort: true, class: "col-subject" };
const date_col = (key, label) => ({ key, label, sort: true, class: "col-date is-date", format: long_date });

const CAUSES = {
	"Variation Order": "งานเพิ่ม-ลด",
	"Employer Delay": "ผู้ว่าจ้างล่าช้า",
	"Force Majeure": "เหตุสุดวิสัย",
	Other: "อื่นๆ",
};

// tab: เรียงตามลำดับที่แสดง create = สร้างจากหน้านี้ได้ (รายงานประจำวัน/ขออนุมัติสร้างจากปฏิทินของหมวดควบคุมงาน)
// sub = บรรทัดรองของแถว, chips = ข้อมูลบนการ์ดมือถือ, คอลัมน์ optional = แสดงเมื่อ server ส่งค่ามา
const TABS = [
	{
		value: "vo",
		doctype: "Variation Order",
		label: "งานลด-เพิ่ม",
		icon: "swap",
		create: true,
		columns: [
			NO,
			SUBJECT,
			date_col("date", "วันที่"),
			{ key: "net_amount", label: "ยอดสุทธิ", sort: true, class: "is-num", optional: true, format: (v) => money(v) },
			{ key: "extension_days", label: "ขยายเวลา", sort: true, class: "is-num", format: days },
		],
		sub: (r) => r.reference_no,
		chips: (r) => [
			{ icon: "calendar", text: thai_date(r.date) },
			{ icon: "clock", text: r.extension_days ? days(r.extension_days) : "" },
			{ icon: "trending", text: r.net_amount === undefined ? "" : money(r.net_amount) },
		],
	},
	{
		value: "eot",
		doctype: "Extension of Time",
		label: "ขยายเวลา (EOT)",
		icon: "clock",
		create: true,
		columns: [
			NO,
			SUBJECT,
			date_col("date", "วันที่"),
			{ key: "requested_days", label: "วันที่ขอ", sort: true, class: "is-num", format: days },
			{ key: "approved_days", label: "วันที่อนุมัติ", sort: true, class: "is-num", format: days },
			date_col("revised_finish_date", "วันจบใหม่"),
		],
		sub: (r) => CAUSES[r.cause] || r.cause,
		chips: (r) => [
			{ icon: "calendar", text: thai_date(r.date) },
			{ icon: "clock", text: `ขอ ${days(r.requested_days)}` },
			{ icon: "search-check", text: r.approved_days ? `อนุมัติ ${days(r.approved_days)}` : "" },
		],
	},
	{
		value: "inspection",
		doctype: "Inspection Request",
		label: "ขอตรวจงาน",
		icon: "search-check",
		create: true,
		columns: [
			NO,
			SUBJECT,
			{ key: "wbs", label: "WBS", sort: true, class: "col-date" },
			{ key: "location", label: "ตำแหน่ง", sort: true, class: "col-date col-wide" },
			date_col("request_date", "วันที่ขอ"),
			date_col("inspection_date", "วันที่ตรวจ"),
		],
		sub: (r) => r.item_name,
		chips: (r) => [
			{ icon: "calendar", text: `ขอ ${thai_date(r.request_date)}` },
			{ icon: "search-check", text: r.inspection_date ? `ตรวจ ${thai_date(r.inspection_date)}` : "" },
			{ icon: "user", text: r.inspector },
		],
	},
	{
		value: "punch",
		doctype: "Punch List",
		label: "Punch List",
		icon: "list-checks",
		create: true,
		columns: [
			NO,
			SUBJECT,
			date_col("date", "วันที่"),
			{ key: "open_items", label: "รายการค้าง", sort: true, class: "is-num", format: (v, r) => (r.status === "Open" && v) || "—" },
		],
		sub: (r) => r.inspection_request,
		chips: (r) => [
			{ icon: "calendar", text: thai_date(r.date) },
			{ icon: "alert", text: r.status === "Open" && r.open_items ? `ค้าง ${r.open_items} รายการ` : "" },
		],
	},
	{
		value: "dr",
		doctype: "Daily Report",
		label: "รายงานประจำวัน",
		icon: "clipboard",
		kind: "dr",
		columns: [
			NO,
			date_col("date", "วันที่"),
			{ key: "supervisor_name", label: "ผู้ควบคุมงาน", sort: true, class: "col-subject" },
			{ key: "today_progress", label: "% วันนี้", sort: true, class: "is-num", format: percent },
			{ key: "cumulative_progress", label: "% สะสม", sort: true, class: "is-num", format: percent },
		],
		chips: (r) => [
			{ icon: "user", text: r.supervisor_name },
			{ icon: "trending", text: `สะสม ${percent(r.cumulative_progress)}` },
		],
	},
	{
		value: "drq",
		doctype: "Daily Request",
		label: "ขออนุมัติ",
		icon: "send",
		kind: "drq",
		columns: [
			NO,
			date_col("date", "วันที่"),
			{ key: "requested_by", label: "ผู้ขอ", sort: true, class: "col-subject" },
		],
		chips: (r) => [{ icon: "user", text: r.requested_by }],
	},
	{
		value: "baseline",
		doctype: "Construction Baseline",
		label: "แผนสัญญา",
		icon: "layers",
		columns: [SUBJECT, date_col("baseline_date", "วันที่")],
		chips: (r) => [{ icon: "calendar", text: thai_date(r.baseline_date) }],
	},
];
const PLANS = "plans";

const wide = use_wide();
const data = ref(null);
const rows = ref(null);
const loading = ref(false);
const txt = ref("");
const tab = ref(state.route.params.tab || "");

const items = computed(() =>
	Object.fromEntries((data.value?.groups || []).flatMap((g) => g.items).map((i) => [i.doctype, i]))
);
const plan_items = computed(() =>
	["Construction Resource Plan", "Construction Material Plan"].map((d) => items.value[d]).filter(Boolean)
);
const tabs = computed(() => {
	const list = TABS.filter((t) => items.value[t.doctype]).map((t) => ({
		...t,
		count: items.value[t.doctype].count || null,
	}));
	if (plan_items.value.length || data.value?.reports?.length)
		list.push({ value: PLANS, label: "แผนและรายงาน" });
	return list;
});
const active = computed(() => TABS.find((t) => t.value === tab.value));
const item = computed(() => items.value[active.value?.doctype]);
const columns = computed(() =>
	active.value.columns.filter((c) => !c.optional || rows.value?.some((r) => c.key in r))
);
const shown_rows = computed(() =>
	(rows.value || []).filter((r) =>
		matches(txt.value, r.name, r.title, r.wbs, r.item_name, r.location, r.reference_no, r.supervisor_name, r.requested_by)
	)
);
// งานลด-เพิ่มมีราคาในแถว แก้ในแอปเฉพาะผู้ที่เห็นงบต้นทุน (project_docs.py)
const can_create = computed(
	() => !!(active.value?.create && item.value?.can_create && (active.value.value !== "vo" || boot.can?.finance))
);

const slug = (doctype) => doctype.toLowerCase().replace(/ /g, "-");
const list_url = (doc) =>
	`/app/${slug(doc.doctype)}?construction_management=${encodeURIComponent(data.value.construction_management)}`;
const plan_url = (doc) => (doc.recent?.length ? desk_url(doc.doctype, doc.recent[0].name) : list_url(doc));

function open(url) {
	window.location.href = url;
}
// จอแคบ tab เลื่อนแนวนอน: เปิดจากลิงก์หรือเปลี่ยน tab แล้ว tab ที่เลือกต้องอยู่ในจอ
function reveal_tab() {
	nextTick(() =>
		document
			.querySelector(".ss-list-tab.is-active, .ss-tab.is-active")
			?.scrollIntoView({ inline: "center", block: "nearest" })
	);
}
function open_row(row) {
	const project_kind = PROJECT_KINDS[active.value.value];
	if (project_kind) go(project_kind.view, { kind: active.value.value, name: row.name });
	else if (active.value.kind) go("report-view", { kind: active.value.kind, name: row.name });
	else open(desk_url(active.value.doctype, row.name));
}
function create() {
	const key = active.value.value;
	go(PROJECT_KINDS[key].form, { kind: key, name: "new" });
}

let request_id = 0;
async function load_rows() {
	const doctype = active.value?.doctype;
	const id = ++request_id;
	if (!doctype) return;
	try {
		const result = await call("consbiz.site_app.get_pm_document_rows", {
			project: state.project.name,
			doctype,
		});
		if (id === request_id) rows.value = result;
	} catch (error) {
		show_error(error);
		if (id === request_id) rows.value ??= [];
	}
}

async function load() {
	loading.value = true;
	try {
		data.value = (await call("consbiz.site_app.get_pm_documents", { project: state.project.name })) || false;
		// tab ที่จำไว้ไม่มีสิทธิ์/ไม่มีแล้ว: ไป tab แรก (watch โหลดรายการให้)
		if (data.value && tabs.value.length && !tabs.value.some((t) => t.value === tab.value)) {
			tab.value = tabs.value[0].value;
		} else if (data.value) {
			reveal_tab();
			await load_rows();
		}
	} catch (error) {
		show_error(error);
		data.value ??= false;
	} finally {
		loading.value = false;
	}
}

watch(tab, (value) => {
	// ระหว่างโหลด ผู้ใช้อาจออกจากหน้าแล้ว ห้ามเขียน URL ทับ
	if (state.route.view === "pm-docs") remember_tab("pm-docs", value, tabs.value[0]?.value);
	txt.value = "";
	rows.value = null;
	reveal_tab();
	load_rows();
});

load();
</script>
