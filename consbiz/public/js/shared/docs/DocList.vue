<!-- รายการเอกสารจัดซื้อ/ขาย (kind = ชื่อหน้า: mr/po/pi/qtn/so/si) แบบระบบ SaaS:
     แท็บสถานะ (มีจำนวน) / แถบเครื่องมือ (ค้นหา ช่วงวันที่ คู่ค้า เกินกำหนด ขอบเขต ส่งออก) / ตารางเรียงคอลัมน์ได้ เลือกหลายแถว
     ท้ายตาราง: ยอดรวมทั้งชุดตามตัวกรอง + แบ่งหน้า  มือถือ: การ์ด + ตัวกรองใน sheet + โหลดเพิ่ม -->
<template>
	<div :class="{ 'ss-has-bar': selected.size }">
		<TopBar :title="config.label" :subtitle="subtitle" no_project>
			<template #search>
				<HeaderSearch
					v-if="wide"
					ref="search_input"
					v-model="search"
					:placeholder="search_placeholder"
				/>
			</template>
			<template #actions>
				<button
					v-if="!wide"
					type="button"
					class="ss-icon-btn"
					:class="{ 'is-spinning': loading }"
					aria-label="โหลดใหม่"
					title="โหลดใหม่"
					@click="reload"
				>
					<Icon name="refresh" :size="20" />
				</button>
				<button
					v-if="!wide && can_create"
					type="button"
					class="ss-btn ss-btn--primary ss-list-create"
					:aria-label="`สร้าง${config.label}`"
					@click="go(`${config.section}-form`, { kind, name: 'new' })"
				>
					<Icon name="plus" :size="18" :stroke="2.6" />
					<span>สร้าง{{ config.label }}</span>
				</button>
			</template>
		</TopBar>

		<div class="ss-content ss-list-page">
			<!-- แท็บสถานะ พร้อมจำนวนตามตัวกรองปัจจุบัน -->
			<!-- มือถือ: แท็บสถานะ / จอ ≥768: แท็บอยู่ในหัวรายการ ต่อเป็นการ์ดเดียวกับตาราง -->
			<nav v-if="!wide" class="ss-tabs" aria-label="สถานะ">
				<button
					v-for="f in tabs"
					:key="f.value"
					type="button"
					class="ss-tab"
					:class="{ 'is-active': filter === f.value }"
					@click="filter = f.value"
				>
					{{ f.label }}
					<span v-if="counts" class="ss-tab-count">{{ counts[f.value] ?? 0 }}</span>
				</button>
			</nav>

			<!-- แถบเครื่องมือ -->
			<div :class="wide ? 'ss-list-head' : 'ss-toolbar'">
				<label v-if="!wide" class="ss-toolbar-search">
					<Icon name="search" :size="17" />
					<input
						ref="search_input"
						v-model="search"
						type="search"
						:placeholder="search_placeholder"
					/>
				</label>
				<template v-if="wide">
					<StatusTabs v-model="filter" :options="status_options" />
					<div class="ss-list-tools">
						<!-- กันที่ไว้เสมอ (ซ่อนด้วย visibility) ความกว้างของแถวตัวกรองจึงไม่เปลี่ยนตามปุ่มนี้ -->
						<button
							type="button"
							class="ss-tool ss-tool--filter"
							:class="{ 'is-active': filter_count }"
							:style="{ visibility: filters_hidden ? 'visible' : 'hidden' }"
							aria-label="ตัวกรองเพิ่มเติม"
							title="ตัวกรองเพิ่มเติม"
							@click="filter_sheet = true"
						>
							<Icon name="sliders" :size="17" />
							<span v-if="filter_count" class="ss-tab-count">{{
								filter_count
							}}</span>
						</button>
						<div ref="filters_box" class="ss-list-filters">
							<SelectBox
								v-model="range"
								variant="tool"
								label="ช่วงวันที่"
								:options="RANGES"
								placeholder="ทุกวันที่"
							>
								<template #prefix><Icon name="calendar" :size="15" /></template>
							</SelectBox>
							<template v-if="range === 'custom'">
								<DateInput
									v-model="date_from"
									variant="tool"
									label="ตั้งแต่"
									placeholder="ตั้งแต่"
									clearable
								/>
								<DateInput
									v-model="date_to"
									variant="tool"
									label="ถึง"
									placeholder="ถึง"
									clearable
								/>
							</template>
							<Picker
								v-if="config.party"
								v-model="party"
								class="ss-tool-picker"
								:label="config.party"
								:placeholder="`${config.party}ทั้งหมด`"
								:display_value="party_label"
								:remote_fn="search_parties"
								clearable
								@select="(o) => (party_label = o.label)"
							/>
							<button
								v-if="config.due"
								type="button"
								class="ss-tool ss-tool--toggle"
								:class="{ 'is-active': overdue }"
								:aria-pressed="overdue"
								@click="overdue = !overdue"
							>
								<Icon name="alert" :size="15" /> เกินกำหนด
							</button>
							<ProjectFilter v-if="app.project_filter && config.project" />
							<SelectBox
								v-else-if="config.project"
								:model-value="state.doc_scope"
								variant="tool"
								label="ขอบเขต"
								:options="SCOPES"
								@update:model-value="set_doc_scope"
							/>
						</div>
						<button
							v-if="can_export"
							type="button"
							class="ss-icon-btn"
							:disabled="exporting"
							aria-label="ส่งออก CSV"
							title="ส่งออก CSV (ตามตัวกรอง)"
							@click="export_csv()"
						>
							<Icon name="receive" :size="19" />
						</button>
						<button
							v-if="can_create"
							type="button"
							class="ss-btn ss-btn--primary ss-list-create"
							:aria-label="`สร้าง${config.label}`"
							@click="go(`${config.section}-form`, { kind, name: 'new' })"
						>
							<Icon name="plus" :size="18" :stroke="2.6" />
							<span>สร้าง{{ config.label }}</span>
						</button>
						<button
							type="button"
							class="ss-icon-btn"
							:class="{ 'is-spinning': loading }"
							aria-label="โหลดใหม่"
							title="โหลดใหม่"
							@click="reload"
						>
							<Icon name="refresh" :size="17" />
						</button>
					</div>
				</template>
				<button
					v-else
					type="button"
					class="ss-tool ss-tool--filter"
					:class="{ 'is-active': active_filters.length }"
					@click="filter_sheet = true"
				>
					<Icon name="sliders" :size="17" />
					<span v-if="active_filters.length" class="ss-tab-count">{{
						active_filters.length
					}}</span>
				</button>
			</div>

			<!-- ตัวกรองที่ใช้อยู่ -->
			<div v-if="!wide && active_filters.length" class="ss-active-filters">
				<span v-for="f in active_filters" :key="f.key" class="ss-filter-chip">
					{{ f.label }}
					<button type="button" :aria-label="`ล้าง ${f.label}`" @click="f.clear()">
						<Icon name="x" :size="13" :stroke="2.6" />
					</button>
				</span>
				<button type="button" class="ss-link" @click="clear_filters">ล้างทั้งหมด</button>
			</div>

			<Skeleton v-if="rows === null" :rows="4" />
			<Empty
				v-else-if="!rows.length"
				:icon="config.icon"
				:title="`ไม่มี${config.label}`"
				:text="empty_text"
			/>
			<div v-else class="ss-list-body" :class="{ 'has-preview': preview_on }">
				<div class="ss-list-main">
					<DocTable
						v-if="wide"
						:rows="rows"
						:kind="kind"
						:sort="sort"
						:order="order"
						:selected="selected"
						:preview="preview_on"
						:active="active"
						@sort="set_sort"
						@toggle="toggle"
						@toggle-all="toggle_all"
						@select="(row) => (active = row.name)"
					/>
					<TransitionGroup v-else tag="div" class="ss-list" name="ss-list" appear>
						<DocCard
							v-for="(row, i) in rows"
							:key="row.name"
							:row="row"
							:kind="kind"
							:i="i % 30"
						/>
					</TransitionGroup>

					<!-- ท้ายรายการ: ยอดรวมทั้งชุด + แบ่งหน้า (มือถือ = โหลดเพิ่ม) -->
					<footer v-if="wide" class="ss-list-foot">
						<span class="ss-list-range">
							แสดง <b>{{ start + 1 }}–{{ start + rows.length }}</b> จาก
							<b>{{ total }}</b>
						</span>
						<span v-if="sums.amount != null" class="ss-list-sum">
							ยอดรวม <b>{{ money(sums.amount) }}</b>
						</span>
						<span v-if="sums.outstanding" class="ss-list-sum is-due">
							ค้าง <b>{{ money(sums.outstanding) }}</b>
						</span>
						<span class="ss-toolbar-gap"></span>
						<label class="ss-list-size">
							แถวต่อหน้า
							<SelectBox
								v-model="page_size"
								variant="tool"
								label="แถวต่อหน้า"
								:options="
									[30, 50, 100].map((n) => ({ value: n, label: String(n) }))
								"
							/>
						</label>
						<div class="ss-pager">
							<button
								type="button"
								class="ss-icon-btn ss-icon-btn--sm"
								aria-label="หน้าก่อน"
								:disabled="!start || loading"
								@click="page(-1)"
							>
								<Icon name="chevron-left" :size="18" />
							</button>
							<span>{{ page_no }} / {{ page_count }}</span>
							<button
								type="button"
								class="ss-icon-btn ss-icon-btn--sm"
								aria-label="หน้าถัดไป"
								:disabled="!more || loading"
								@click="page(1)"
							>
								<Icon name="chevron-right" :size="18" />
							</button>
						</div>
					</footer>
					<button
						v-else-if="more"
						type="button"
						class="ss-btn ss-btn--ghost ss-btn--block"
						:disabled="loading"
						@click="load(true)"
					>
						<span v-if="loading" class="ss-spinner"></span>
						<template v-else>โหลดเพิ่ม ({{ rows.length }} จาก {{ total }})</template>
					</button>
				</div>
				<!-- จอ ≥1480: ตัวอย่างเอกสารข้างตาราง -->
				<DocPreview
					v-if="preview_on"
					:key="active"
					:kind="kind"
					:name="active"
					@close="active = null"
					@changed="load()"
				/>
			</div>
		</div>

		<!-- เลือกหลายแถว: ส่งเอกสารร่าง / ส่งออกที่เลือก -->
		<Teleport to="#ss-layer">
			<Transition name="ss-bar">
				<div v-if="selected.size" class="ss-bottom-bar ss-bulk-bar">
					<span class="ss-bar-summary">
						เลือก <b>{{ selected.size }}</b> รายการ
						<template v-if="selected_sum"> · {{ money(selected_sum) }}</template>
					</span>
					<button
						type="button"
						class="ss-btn ss-btn--ghost"
						@click="selected = new Set()"
					>
						ยกเลิกเลือก
					</button>
					<button
						v-if="can_export"
						type="button"
						class="ss-btn ss-btn--ghost"
						@click="export_csv(selected_rows)"
					>
						<Icon name="receive" :size="16" /> ส่งออก
					</button>
					<button
						v-if="can_submit"
						type="button"
						class="ss-btn ss-btn--primary"
						:disabled="!selected_drafts.length"
						:title="selected_drafts.length ? '' : 'ส่งได้เฉพาะเอกสารร่าง'"
						@click="bulk_sheet = true"
					>
						<Icon name="send" :size="16" /> ส่งเอกสาร ({{ selected_drafts.length }})
					</button>
				</div>
			</Transition>
		</Teleport>

		<Sheet
			:open="bulk_sheet"
			:title="`ส่ง${config.label} ${selected_drafts.length} ใบ`"
			@close="bulk_sheet = false"
		>
			<template v-if="bulk_results">
				<div class="ss-bulk-results">
					<div
						v-for="r in bulk_results"
						:key="r.name"
						class="ss-bulk-row"
						:class="{ 'is-fail': !r.ok }"
					>
						<Icon :name="r.ok ? 'check' : 'alert'" :size="16" />
						<b>{{ r.name }}</b>
						<span>{{ r.ok ? "ส่งแล้ว" : r.error }}</span>
					</div>
				</div>
			</template>
			<p v-else class="ss-muted">
				ส่งแล้วแก้ไขไม่ได้ ใบที่ส่งไม่ผ่านจะไม่กระทบใบอื่น
				<template v-if="selected.size > selected_drafts.length">
					(ข้ามใบที่ไม่ใช่ร่าง {{ selected.size - selected_drafts.length }} ใบ)</template
				>
			</p>
			<template #footer>
				<button
					v-if="!bulk_results"
					type="button"
					class="ss-btn ss-btn--primary ss-btn--block ss-btn--lg"
					:disabled="busy"
					@click="bulk_submit"
				>
					<span v-if="busy" class="ss-spinner"></span>
					<template v-else>ยืนยันส่ง {{ selected_drafts.length }} ใบ</template>
				</button>
				<button
					v-else
					type="button"
					class="ss-btn ss-btn--ghost ss-btn--block"
					@click="bulk_sheet = false"
				>
					ปิด
				</button>
			</template>
		</Sheet>

		<!-- ตัวกรองทั้งหมด (มือถือ + ปุ่มตัวกรองเมื่อแถวหัวรายการไม่พอ) มือถือมีการเรียงด้วย -->
		<Sheet :open="filter_sheet" title="ตัวกรอง" @close="filter_sheet = false">
			<div class="ss-form">
				<div class="ss-field">
					<span class="ss-field-label">ช่วงวันที่</span>
					<div class="ss-choices">
						<button
							v-for="r in RANGES"
							:key="r.value"
							type="button"
							class="ss-choice"
							:class="{ 'is-active': range === r.value }"
							@click="range = r.value"
						>
							{{ r.label }}
						</button>
					</div>
					<div v-if="range === 'custom'" class="ss-form-row">
						<DateInput
							v-model="date_from"
							label="ตั้งแต่"
							placeholder="ตั้งแต่"
							clearable
						/>
						<DateInput v-model="date_to" label="ถึง" placeholder="ถึง" clearable />
					</div>
				</div>
				<Picker
					v-if="config.party"
					v-model="party"
					:label="config.party"
					:placeholder="`${config.party}ทั้งหมด`"
					:display_value="party_label"
					:remote_fn="search_parties"
					clearable
					@select="(o) => (party_label = o.label)"
				/>
				<div v-if="!wide" class="ss-field">
					<span class="ss-field-label">เรียงตาม</span>
					<div class="ss-choices">
						<button
							v-for="s in sort_options"
							:key="s.value"
							type="button"
							class="ss-choice"
							:class="{ 'is-active': sort === s.value }"
							@click="set_sort(s.value)"
						>
							{{ s.label }}
							<Icon
								v-if="sort === s.value"
								:name="order === 'asc' ? 'chevron-up' : 'chevron-down'"
								:size="14"
							/>
						</button>
					</div>
				</div>
				<label v-if="config.due" class="ss-toggle" :class="{ 'is-on': overdue }">
					<input v-model="overdue" type="checkbox" />
					<span class="ss-toggle-track"><span></span></span>
					<span><b>เฉพาะที่เกินกำหนด</b></span>
				</label>
				<ProjectFilter v-if="app.project_filter && config.project" />
				<ScopeSwitch v-else-if="config.project" />
			</div>
			<template #footer>
				<button type="button" class="ss-btn ss-btn--ghost" @click="clear_filters">
					ล้าง
				</button>
				<button
					type="button"
					class="ss-btn ss-btn--primary ss-grow"
					@click="filter_sheet = false"
				>
					ดู {{ total ?? "" }} รายการ
				</button>
			</template>
		</Sheet>

		<PdfViewer
			:open="!!pdf_row"
			:url="pdf_row?.pdf_url"
			:name="pdf_row?.name"
			:title="config.label"
			@close="pdf_row = null"
		/>
	</div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import Icon from "../components/Icon.vue";
import TopBar from "../components/TopBar.vue";
import Skeleton from "../components/Skeleton.vue";
import Empty from "../components/Empty.vue";
import Picker from "../components/Picker.vue";
import Sheet from "../components/Sheet.vue";
import PdfViewer from "../components/PdfViewer.vue";
import SelectBox from "../components/SelectBox.vue";
import StatusTabs from "../components/StatusTabs.vue";
import { use_overflow_row } from "../table.js";
import HeaderSearch from "../components/HeaderSearch.vue";
import DateInput from "../components/DateInput.vue";
import DocCard from "./DocCard.vue";
import DocTable from "./DocTable.vue";
import DocPreview from "./DocPreview.vue";
import ScopeSwitch from "./ScopeSwitch.vue";
import ProjectFilter from "./ProjectFilter.vue";
import { use_shortcuts } from "../shortcuts.js";
import { app } from "../app.js";
import { DOC_KINDS, can_doc } from "./kinds.js";
import {
	call,
	go,
	iso_date,
	money,
	post,
	replace_params,
	scope_args,
	scope_key,
	set_doc_scope,
	show_error,
	state,
	thai_date,
	toast,
} from "../api.js";

const kind = state.route.view;
const config = DOC_KINDS[kind];
const FILTERS = ["todo", "draft", "done", "all"];
const RANGES = [
	{ value: "", label: "ทุกวันที่" },
	{ value: "month", label: "เดือนนี้" },
	{ value: "last_month", label: "เดือนก่อน" },
	{ value: "90", label: "90 วันล่าสุด" },
	{ value: "year", label: "ปีนี้" },
	{ value: "custom", label: "กำหนดเอง" },
];
const SCOPES = [
	{ value: "project", label: "โครงการนี้" },
	{ value: "all", label: "ทุกโครงการ" },
];
const PREF_KEY = `consbiz.site.list.${kind}`;

const tabs = [
	{ value: "todo", label: config.todo },
	{ value: "draft", label: "ร่าง" },
	{ value: "done", label: "เสร็จแล้ว" },
	{ value: "all", label: "ทั้งหมด" },
];
const sort_options = [
	{ value: "date", label: "วันที่" },
	...(config.due ? [{ value: "due", label: config.due }] : []),
	{ value: "name", label: "เลขที่" },
	...(config.party ? [{ value: "party", label: config.party }] : []),
	...(kind !== "mr" ? [{ value: "amount", label: "ยอดเงิน" }] : []),
];

// การเรียง/จำนวนแถวต่อหน้า จำในเครื่อง
const prefs = (() => {
	try {
		return JSON.parse(localStorage.getItem(PREF_KEY) || "{}");
	} catch {
		return {};
	}
})();

const filter = ref(
	FILTERS.includes(state.route.params.filter) ? state.route.params.filter : "todo"
);
const search = ref("");
const range = ref("");
const date_from = ref("");
const date_to = ref("");
const party = ref(null);
const party_label = ref("");
const overdue = ref(false);
const sort = ref(prefs.sort || "date");
const order = ref(prefs.order || "desc");
const page_size = ref(prefs.page_size || 30);
const start = ref(0);

const rows = ref(null);
const total = ref(null);
const counts = ref(null);
const status_options = computed(() =>
	tabs.map((f) => ({ ...f, count: counts.value ? counts.value[f.value] ?? 0 : undefined }))
);
const sums = ref({});
const more = ref(false);
const loading = ref(false);
const exporting = ref(false);
const can_create = can_doc(kind, "create");
const can_submit = can_doc(kind, "submit");
const can_export = can_doc(kind, "export");
const selected = ref(new Set());
const filter_sheet = ref(false);
const bulk_sheet = ref(false);
const bulk_results = ref(null);
const busy = ref(false);
const pdf_row = ref(null);

// จอใหญ่มาก (≥1480): ตารางคู่กับตัวอย่างเอกสาร คลิกแถว = ดูตัวอย่าง
const mq_xl = window.matchMedia("(min-width: 1480px)");
const xl = ref(mq_xl.matches);
const on_xl = () => (xl.value = mq_xl.matches);
mq_xl.addEventListener("change", on_xl);
onBeforeUnmount(() => mq_xl.removeEventListener("change", on_xl));
const active = ref(null);
const preview_on = computed(() => xl.value && !!active.value && !!rows.value?.length);
// โหลดรายการใหม่: แถวที่ดูอยู่ไม่อยู่ในหน้านี้ = ดูแถวแรกแทน
watch(rows, (list) => {
	if (!xl.value || !list) return;
	if (!list.some((r) => r.name === active.value)) active.value = list[0]?.name || null;
});

const mq_wide = window.matchMedia("(min-width: 768px)");
const wide = ref(mq_wide.matches);
const on_media = () => (wide.value = mq_wide.matches);
mq_wide.addEventListener("change", on_media);
onBeforeUnmount(() => mq_wide.removeEventListener("change", on_media));

const subtitle = computed(() => {
	const { scope, company } = scope_args();
	const project =
		config.project && scope === "project" ? state.project?.project_name : "ทุกโครงการ";
	return company ? `${project} · ${company}` : project;
});
const page_no = computed(() => Math.floor(start.value / page_size.value) + 1);
const page_count = computed(() => Math.max(1, Math.ceil((total.value || 0) / page_size.value)));
const empty_text = computed(() =>
	search.value || active_filters.value.length
		? "ลองเปลี่ยนคำค้นหรือล้างตัวกรอง"
		: scope_args().scope === "project" && config.project
		? "ลองดูทุกโครงการ"
		: ""
);

// ช่วงวันที่สำเร็จรูป → วันเริ่ม-วันสิ้นสุด
const dates = computed(() => {
	const now = new Date();
	const y = now.getFullYear();
	const m = now.getMonth();
	if (range.value === "month")
		return [iso_date(new Date(y, m, 1)), iso_date(new Date(y, m + 1, 0))];
	if (range.value === "last_month")
		return [iso_date(new Date(y, m - 1, 1)), iso_date(new Date(y, m, 0))];
	if (range.value === "90") return [iso_date(new Date(y, m, now.getDate() - 90)), iso_date(now)];
	if (range.value === "year")
		return [iso_date(new Date(y, 0, 1)), iso_date(new Date(y, 11, 31))];
	if (range.value === "custom") return [date_from.value || null, date_to.value || null];
	return [null, null];
});

const active_filters = computed(() => {
	const out = [];
	if (range.value) {
		const [from, to] = dates.value;
		const label =
			range.value === "custom"
				? [from && thai_date(from, { year: true }), to && thai_date(to, { year: true })]
						.filter(Boolean)
						.join(" – ") || "กำหนดเอง"
				: RANGES.find((r) => r.value === range.value).label;
		out.push({ key: "range", label, clear: () => (range.value = "") });
	}
	if (party.value) {
		out.push({
			key: "party",
			label: party_label.value || party.value,
			clear: () => ((party.value = null), (party_label.value = "")),
		});
	}
	if (overdue.value)
		out.push({ key: "overdue", label: "เกินกำหนด", clear: () => (overdue.value = false) });
	return out;
});

// จอ ≥768: นับรวมโครงการที่เลือก เพราะตัวกรองที่พับอยู่มองไม่เห็นบนหัวรายการ
const filter_count = computed(
	() =>
		active_filters.value.length +
		(app.project_filter && config.project && state.project ? 1 : 0)
);
const filters_box = ref(null);
const filters_hidden = use_overflow_row(filters_box, [
	range,
	date_from,
	date_to,
	party_label,
	overdue,
	() => state.project,
	() => state.doc_scope,
]);

function clear_filters() {
	range.value = "";
	date_from.value = "";
	date_to.value = "";
	party.value = null;
	party_label.value = "";
	overdue.value = false;
}

function args(extra = {}) {
	const [from, to] = dates.value;
	return {
		kind,
		...scope_args(),
		filter: filter.value,
		search: search.value.trim() || undefined,
		sort: sort.value,
		order: order.value,
		date_from: from || undefined,
		date_to: to || undefined,
		party: party.value || undefined,
		overdue: overdue.value ? 1 : undefined,
		page_size: page_size.value,
		...extra,
	};
}

let request_id = 0;
async function load(append = false) {
	const id = ++request_id;
	loading.value = true;
	const offset = append ? rows.value.length : start.value;
	try {
		const result = await call("consbiz.site_docs.get_docs", args({ start: offset }));
		if (id !== request_id) return;
		rows.value = append ? [...rows.value, ...result.rows] : result.rows;
		total.value = result.total;
		counts.value = result.counts;
		sums.value = result.sums || {};
		more.value = result.more;
	} catch (error) {
		show_error(error);
		rows.value ??= [];
	} finally {
		if (id === request_id) loading.value = false;
	}
}

// ตัวกรองเปลี่ยน = กลับหน้าแรก ล้างที่เลือก
function reload() {
	start.value = 0;
	selected.value = new Set();
	rows.value = null;
	load();
}

function page(delta) {
	start.value = Math.max(0, start.value + delta * page_size.value);
	selected.value = new Set();
	load();
	window.scrollTo({ top: 0, behavior: "smooth" });
}

function set_sort(key) {
	if (sort.value === key) order.value = order.value === "asc" ? "desc" : "asc";
	else {
		sort.value = key;
		order.value = ["name", "party"].includes(key) ? "asc" : "desc";
	}
}

function save_prefs() {
	try {
		localStorage.setItem(
			PREF_KEY,
			JSON.stringify({ sort: sort.value, order: order.value, page_size: page_size.value })
		);
	} catch {
		/* เก็บไม่ได้: ใช้ค่าเริ่มต้นครั้งหน้า */
	}
}

let timer = null;
watch(search, () => {
	clearTimeout(timer);
	timer = setTimeout(reload, 300);
});
watch(filter, (value) => {
	replace_params(kind, { filter: value });
	reload();
});
watch([scope_key, dates, party, overdue], reload);
watch([sort, order, page_size], () => {
	save_prefs();
	reload();
});

// ---------------------------------------------------------------- เลือกหลายแถว

const selected_rows = computed(() => (rows.value || []).filter((r) => selected.value.has(r.name)));
const selected_drafts = computed(() => selected_rows.value.filter((r) => r.docstatus === 0));
const selected_sum = computed(() =>
	selected_rows.value.reduce((s, r) => s + (Number(r.amount) || 0), 0)
);

function toggle(name) {
	const next = new Set(selected.value);
	next.has(name) ? next.delete(name) : next.add(name);
	selected.value = next;
}

function toggle_all() {
	const all = rows.value.every((r) => selected.value.has(r.name));
	selected.value = all ? new Set() : new Set(rows.value.map((r) => r.name));
}

watch(bulk_sheet, (open) => open && (bulk_results.value = null));

async function bulk_submit() {
	busy.value = true;
	try {
		const results = await post("consbiz.site_docs.submit_docs", {
			kind,
			names: selected_drafts.value.map((r) => r.name),
		});
		bulk_results.value = results;
		const ok = results.filter((r) => r.ok).length;
		toast(
			`ส่งแล้ว ${ok} จาก ${results.length} ใบ`,
			ok === results.length ? "success" : "error"
		);
		selected.value = new Set();
		load();
	} catch (error) {
		show_error(error);
	} finally {
		busy.value = false;
	}
}

// ---------------------------------------------------------------- อื่นๆ

function open_pdf(row) {
	pdf_row.value = row;
}

async function search_parties(txt) {
	return call("consbiz.site_docs.search_parties", { kind, txt });
}

// CSV (UTF-8 + BOM ให้ Excel อ่านภาษาไทยได้) ส่งออกทุกแถวตามตัวกรอง หรือเฉพาะที่เลือก
async function export_csv(only = null) {
	exporting.value = true;
	try {
		const data = only || (await call("consbiz.site_docs.get_docs", args({ export: 1 }))).rows;
		const columns = [
			["name", "เลขที่"],
			...(config.party ? [["party", config.party]] : [["title", "เรื่อง"]]),
			...(config.project ? [["project", "โครงการ"]] : []),
			["date", "วันที่"],
			...(config.due ? [["due", config.due]] : []),
			...(kind !== "mr" ? [["amount", "ยอดเงิน"]] : []),
			...(["pi", "si"].includes(kind) ? [["outstanding", "ค้าง"]] : []),
			["status_label", "สถานะ"],
		];
		const cell = (v) => `"${String(v ?? "").replace(/"/g, '""')}"`;
		const lines = [columns.map(([, label]) => cell(label)).join(",")];
		for (const row of data) lines.push(columns.map(([field]) => cell(row[field])).join(","));
		const blob = new Blob(["﻿" + lines.join("\r\n")], { type: "text/csv;charset=utf-8" });
		const href = URL.createObjectURL(blob);
		const link = Object.assign(document.createElement("a"), {
			href,
			download: `${config.label}-${iso_date(new Date())}.csv`,
		});
		document.body.appendChild(link);
		link.click();
		link.remove();
		setTimeout(() => URL.revokeObjectURL(href), 2000);
		toast(`ส่งออก ${data.length} รายการ`, "success");
	} catch (error) {
		show_error(error);
	} finally {
		exporting.value = false;
	}
}

// มือถือ: แท็บที่เลือกอยู่ต้องเห็น (แถบแท็บเลื่อนข้างได้)
onMounted(async () => {
	await nextTick();
	document
		.querySelector(".ss-tab.is-active")
		?.scrollIntoView({ block: "nearest", inline: "center" });
});

load();

// คีย์ลัด (แอปออฟฟิศ): / ค้นหา, n สร้างใหม่, j/k เลื่อนแถว (Enter เปิด)
const search_input = ref(null);
// ค้นได้: เลขที่ / คู่ค้า / เลขที่บิลผู้ขาย (PI) / ชื่อหรือรหัสสินค้า (site_docs.search_filters)
const search_placeholder = `ค้นหาเลขที่${config.party ? ` / ${config.party}` : ""}${
	kind === "pi" ? " / เลขที่บิล" : ""
} / สินค้า`;
use_shortcuts({
	"/": () => search_input.value?.focus(),
	n: () => can_create && go(`${config.section}-form`, { kind, name: "new" }),
	j: () => document.querySelector(".ss-table--list tbody tr")?.focus(),
	k: () => document.querySelector(".ss-table--list tbody tr:last-child")?.focus(),
});
</script>
