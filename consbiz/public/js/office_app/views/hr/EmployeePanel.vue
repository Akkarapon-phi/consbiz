<!-- ข้อมูลพนักงาน 1 คน (API consbiz.hr_people.get_employee) ใช้ทั้งแผงตัวอย่างของรายการ (compact) และหน้าเต็ม (HrEmployee.vue)
     ข้อมูลหลัก / เวลาทำงานเดือนนี้ / วันลาคงเหลือ / ค่าจ้าง (ผู้ทำเงินเดือน) / เอกสารที่ผูก (เปิดในแอปถ้ามีหน้า ไม่งั้นระบบเต็ม) -->
<template>
	<div class="hr-emp" :class="{ 'is-compact': compact }">
		<Skeleton v-if="!data" :rows="4" />
		<template v-else>
			<header class="hr-emp-head">
				<span class="ss-avatar hr-emp-avatar" :class="`tone-${tone(info.employee_name)}`">
					<img v-if="info.image" :src="info.image" alt="" />
					<template v-else>{{ initials(info.employee_name) }}</template>
				</span>
				<div class="hr-emp-title">
					<h2>{{ info.employee_name }}</h2>
					<p>{{ [info.designation, info.department].filter(Boolean).join(" · ") || info.name }}</p>
					<div class="hr-emp-tags">
						<span class="ss-tag" :class="info.status === 'Active' ? 'tone-green' : 'tone-gray'">{{ STATUS[info.status] || info.status }}</span>
						<span class="ss-tag tone-gray">{{ info.name }}</span>
						<span v-if="!info.user_id" class="ss-tag tone-amber">ไม่มีบัญชีผู้ใช้</span>
					</div>
				</div>
				<div class="hr-emp-actions">
					<button v-if="compact" type="button" class="ss-btn ss-btn--soft" @click="go('hr-employee', { name: info.name })">
						<Icon name="maximize" :size="14" /> เปิดเต็ม
					</button>
					<button v-if="data.can_edit" type="button" class="ss-btn ss-btn--ghost" @click="go('md-doc', { kind: 'md-employees', name: info.name })">
						<Icon name="pen" :size="14" /> แก้ข้อมูล
					</button>
				</div>
			</header>

			<dl class="hr-emp-facts">
				<div><dt>โครงการที่ประจำ</dt><dd>{{ info.project_name || info.custom_project || "—" }}</dd></div>
				<div><dt>เริ่มงาน</dt><dd>{{ info.date_of_joining ? thai_date(info.date_of_joining, { year: true }) : "—" }}<small v-if="info.tenure"> ({{ tenure_text }})</small></dd></div>
				<div><dt>กะประจำ</dt><dd>{{ info.default_shift || "กะเริ่มต้นบริษัท" }}</dd></div>
				<div><dt>โทร</dt><dd>{{ info.cell_number || "—" }}</dd></div>
				<div v-if="data.pay?.current"><dt>ค่าจ้าง</dt><dd>{{ money(data.pay.current.base) }}<small v-if="data.pay.upcoming.length"> → {{ money(data.pay.upcoming[0].base) }} ({{ thai_date(data.pay.upcoming[0].from_date) }})</small></dd></div>
				<div v-if="info.relieving_date"><dt>วันที่ออก</dt><dd>{{ thai_date(info.relieving_date, { year: true }) }}</dd></div>
			</dl>

			<section v-if="data.attendance" class="hr-emp-block">
				<h3>เวลาทำงานเดือนนี้</h3>
				<div class="hr-emp-counts">
					<span><b>{{ data.attendance.present }}</b>มาทำงาน</span>
					<span><b>{{ data.attendance.leave }}</b>ลา</span>
					<span :class="{ 'is-red': data.attendance.absent }"><b>{{ data.attendance.absent }}</b>ขาด</span>
					<span :class="{ 'is-amber': data.attendance.late_count }"><b>{{ data.attendance.late_count }}</b>สาย</span>
					<span v-if="data.attendance.flag" class="is-amber"><b>{{ data.attendance.flag }}</b>รอตัดสิน</span>
				</div>
			</section>

			<section v-if="data.leave.length" class="hr-emp-block">
				<h3>วันลาคงเหลือ</h3>
				<div class="hr-emp-leaves">
					<span v-for="l in data.leave" :key="l.leave_type">{{ l.leave_type }} <b>{{ days(l.remaining) }}</b>/{{ days(l.allocated) }}</span>
				</div>
			</section>

			<section class="hr-emp-block">
				<h3>เอกสาร</h3>
				<div class="hr-emp-docs">
					<div v-for="g in shown_docs" :key="g.doctype" class="hr-emp-doc">
						<div class="hr-emp-doc-head">
							<b>{{ g.label }}</b>
							<span class="ss-tag tone-gray">{{ g.count }}</span>
							<a v-if="g.count" class="ss-link" :href="`/app/${g.slug}?employee=${encodeURIComponent(info.name)}`" target="_blank">ทั้งหมด</a>
						</div>
						<button
							v-for="r in g.rows.slice(0, compact ? 2 : 6)"
							:key="r.name"
							type="button"
							class="hr-emp-doc-row"
							@click="open_doc(g, r)"
						>
							<span>{{ r.date ? thai_date(r.date, { year: true }) : r.name }}</span>
							<span class="hr-emp-doc-value">{{ value_text(g, r) }}</span>
							<span v-if="r.docstatus === 0" class="ss-tag tone-amber">ร่าง</span>
						</button>
					</div>
				</div>
				<p v-if="!compact && hidden_count" class="hr-emp-none">ไม่มีเอกสาร: {{ empty_docs.map((g) => g.label).join(", ") }}</p>
			</section>
		</template>
	</div>
</template>

<script setup>
import { computed } from "vue";
import Icon from "../../../shared/components/Icon.vue";
import Skeleton from "../../../shared/components/Skeleton.vue";
import { go, initials, money, thai_date, tone } from "../../../shared/api.js";

const props = defineProps({
	data: { type: Object, default: null },
	compact: Boolean,
});
const STATUS = { Active: "ทำงานอยู่", Inactive: "ไม่ใช้งาน", Suspended: "พักงาน", Left: "ลาออกแล้ว" };
const LEVEL = { Verbal: "ด้วยวาจา", "Written 1": "ครั้งที่ 1", "Written 2": "ครั้งที่ 2", Final: "ครั้งสุดท้าย" };
const REASON = { "On Duty": "มาทำงาน", "Work From Home": "ทำงานที่บ้าน" };

const info = computed(() => props.data?.info || {});
const tenure_text = computed(() => {
	const t = info.value.tenure;
	if (!t) return "";
	return [t.years ? `${t.years} ปี` : "", t.months ? `${t.months} เดือน` : ""].filter(Boolean).join(" ") || "ไม่ถึงเดือน";
});
const days = (v) => (Number.isInteger(Number(v)) ? String(Number(v)) : Number(v).toFixed(1));
// แผงย่อแสดงเฉพาะชนิดที่มีเอกสาร หน้าเต็มแสดงชนิดที่มี + บอกชื่อชนิดที่ไม่มี
const shown_docs = computed(() => (props.data?.docs || []).filter((g) => g.count));
const empty_docs = computed(() => (props.data?.docs || []).filter((g) => !g.count));
const hidden_count = computed(() => empty_docs.value.length);

function value_text(g, r) {
	if (r.value == null || r.value === "") return r.status || "";
	if (typeof r.value === "number") return money(r.value);
	if (g.doctype === "Employee Warning") return LEVEL[r.value] || r.value;
	if (g.doctype === "Attendance Request") return REASON[r.value] || r.value;
	return r.value;
}
function open_doc(g, r) {
	if (g.app_kind) return go("hr-doc", { kind: g.app_kind, name: r.name });
	window.open(`/app/${g.slug}/${encodeURIComponent(r.name)}`, "_blank");
}
</script>

<style scoped>
.hr-emp { display: flex; flex-direction: column; gap: 14px; }
.hr-emp-head { display: flex; align-items: flex-start; gap: 12px; flex-wrap: wrap; }
.hr-emp-avatar { width: 52px; height: 52px; font-size: var(--ss-fs-lg); }
.hr-emp-avatar img { width: 100%; height: 100%; object-fit: cover; border-radius: inherit; }
.hr-emp-title { flex: 1; min-width: 160px; }
.hr-emp-title h2 { margin: 0; font-size: var(--ss-fs-xl); font-weight: 650; }
.hr-emp-title p { margin: 2px 0 6px; color: var(--ss-muted); font-size: var(--ss-fs); }
.hr-emp-tags { display: flex; gap: 6px; flex-wrap: wrap; }
.hr-emp-actions { display: flex; gap: 6px; flex-wrap: wrap; }
.hr-emp-actions .ss-btn { height: 32px; padding: 0 12px; border-radius: 999px; gap: 4px; }
.hr-emp-facts {
	display: grid;
	grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
	gap: 1px;
	margin: 0;
	overflow: hidden;
	border: 1px solid var(--ss-work-line, var(--ss-border));
	border-radius: 12px;
	background: var(--ss-work-line, var(--ss-border));
}
.hr-emp-facts > div { padding: 8px 12px; background: var(--ss-work-card, var(--ss-surface)); }
.hr-emp-facts dt { color: var(--ss-muted); font-size: var(--ss-fs-sm); }
.hr-emp-facts dd { margin: 2px 0 0; font-weight: 600; }
.hr-emp-facts small { color: var(--ss-muted); font-weight: 400; }
.hr-emp-block h3 { margin: 0 0 8px; font-size: var(--ss-fs); font-weight: 650; }
.hr-emp-counts { display: grid; grid-template-columns: repeat(auto-fill, minmax(84px, 1fr)); gap: 8px; }
.hr-emp-counts span {
	display: flex;
	flex-direction: column;
	padding: 8px 10px;
	border-radius: 10px;
	background: color-mix(in srgb, var(--ss-text) 4%, transparent);
	color: var(--ss-muted);
	font-size: var(--ss-fs-sm);
}
.hr-emp-counts b { color: var(--ss-text); font-size: var(--ss-fs-lg); font-variant-numeric: tabular-nums; }
.hr-emp-counts .is-red b { color: #be123c; }
.hr-emp-counts .is-amber b { color: #b45309; }
.hr-emp-leaves { display: flex; flex-wrap: wrap; gap: 6px 14px; color: var(--ss-muted); font-size: var(--ss-fs-sm); }
.hr-emp-leaves b { color: var(--ss-text); }
.hr-emp-docs { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 10px; }
.is-compact .hr-emp-docs { grid-template-columns: 1fr; }
.hr-emp-doc {
	padding: 10px 12px;
	border: 1px solid var(--ss-work-line, var(--ss-border));
	border-radius: 12px;
}
.hr-emp-doc-head { display: flex; align-items: center; gap: 6px; margin-bottom: 4px; }
.hr-emp-doc-head b { font-weight: 600; }
.hr-emp-doc-head .ss-link { margin-left: auto; font-size: var(--ss-fs-sm); }
.hr-emp-doc-row {
	display: flex;
	align-items: center;
	gap: 8px;
	width: 100%;
	padding: 5px 0;
	border: 0;
	border-top: 1px solid var(--ss-work-line, var(--ss-border));
	background: none;
	color: var(--ss-text);
	font-size: var(--ss-fs-sm);
	text-align: left;
	cursor: pointer;
}
.hr-emp-doc-row:hover { color: var(--ss-brand); }
.hr-emp-doc-value { margin-left: auto; color: var(--ss-muted); white-space: nowrap; }
.hr-emp-none { margin: 8px 0 0; color: var(--ss-muted); font-size: var(--ss-fs-sm); }
</style>
