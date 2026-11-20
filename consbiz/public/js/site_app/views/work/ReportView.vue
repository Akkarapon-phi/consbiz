<template>
	<div>
		<TopBar
			:title="kind.label"
			:subtitle="params.name"
			back_to="reports"
			:back_params="doc ? { day: doc.date } : {}"
		/>

		<div class="ss-content">
			<FormHead
				v-if="setup"
				model-value="main"
				:tabs="[{ value: 'main', label: kind.label }]"
				:actions="actions"
				:menu="menu"
				:busy="busy"
				:on-print="setup.pdf_url ? () => (pdf_sheet = true) : null"
			/>
			<Skeleton v-if="!setup" :rows="3" />
			<div v-else class="ss-split">
				<div class="ss-split-main">
					<div class="ss-doc-head">
						<div class="ss-doc-head-top">
							<span class="ss-tag" :class="`tone-${status.tone}`">{{ status.label }}</span>
							<span class="ss-doc-date">{{ long_date(doc.date) }}</span>
						</div>
						<div class="ss-facts ss-facts--grid">
							<div class="ss-fact">
								<span>{{ is_report ? "ผู้ควบคุมงาน" : "ผู้ขออนุมัติ" }}</span>
								<b>{{
									(is_report ? doc.supervisor_name : doc.requested_by) || setup.owner_name
								}}</b>
							</div>
							<div v-if="is_report" class="ss-fact">
								<span>สภาพอากาศ</span><b>{{ doc.weather || "–" }}</b>
							</div>
							<div v-else class="ss-fact">
								<span>เวลาทำงาน</span><b>{{ doc.start_time }}–{{ doc.end_time }} น.</b>
							</div>
							<div v-if="is_report && doc.weather_impact" class="ss-fact">
								<span>ผลกระทบ</span><b>{{ doc.weather_impact }}</b>
							</div>
							<div v-if="!is_report" class="ss-fact">
								<span>ผู้อนุมัติ</span><b>{{ doc.approver_name || doc.approver }}</b>
							</div>
							<div v-if="doc.daily_request" class="ss-fact">
								<span>ตามคำขอ</span>
								<b
									><button
										type="button"
										class="ss-link"
										@click="go('report-view', { kind: 'drq', name: doc.daily_request })"
									>
										{{ doc.daily_request }}
									</button></b
								>
							</div>
						</div>
						<div v-if="doc.status === 'Rejected'" class="ss-banner tone-rose">
							<Icon name="ban" :size="22" />
							<div>
								<div class="ss-banner-title">ไม่อนุมัติ</div>
								<div class="ss-banner-text">{{ doc.rejection_reason }}</div>
							</div>
						</div>
					</div>

					<div v-if="doc.docstatus === 1 || !is_report" class="ss-metric-row">
						<div class="ss-metric tone-orange">
							<span>{{ is_report ? "ความคืบหน้าวันนี้" : "จะเพิ่มขึ้น" }}</span>
							<b>+{{ pct(is_report ? doc.today_progress : doc.planned_progress) }}%</b>
							<small>ของทั้งโครงการ</small>
						</div>
						<div class="ss-metric" :class="variance < 0 ? 'tone-rose' : 'tone-green'">
							<span>{{ is_report ? "สะสม" : "คาดว่าสะสม" }}</span>
							<b>{{ pct(is_report ? doc.cumulative_progress : doc.expected_progress) }}%</b>
							<small
								>แผน {{ pct(doc.baseline_progress) }}% ·
								{{ variance >= 0 ? "เร็วกว่า" : "ช้ากว่า" }}
								{{ pct(Math.abs(variance)) }}%</small
							>
						</div>
					</div>

					<h2 class="ss-section-title">
						{{ is_report ? "งานที่ทำ" : "งานที่จะทำ" }}
						<span class="ss-count">{{ doc.items.length }}</span>
					</h2>
					<div class="ss-list">
						<div
							v-for="(row, i) in doc.items"
							:key="row.wbs"
							class="ss-card"
							:style="{ '--i': i }"
						>
							<div class="ss-card-head">
								<span class="ss-card-main">
									<span class="ss-card-title">{{ row.item_name }}</span>
									<span class="ss-card-meta"
										><i class="ss-wbs">{{ row.wbs }}</i> {{ row.group_path }}</span
									>
								</span>
								<span class="ss-qty">
									<b>{{ row.boq_qty ? num(row.qty) : `${pct(row.percent)}%` }}</b>
									<small>{{ row.boq_qty ? row.uom : "งานเหมา" }}</small>
								</span>
							</div>
							<div class="ss-chips">
								<span v-if="row.boq_qty" class="ss-chip">{{ pct(row.percent) }}% ของงาน</span>
								<span class="ss-chip"
									>สะสม {{ pct(Number(row.previous_percent) + Number(row.percent)) }}%</span
								>
								<span v-if="row.location" class="ss-chip"
									><Icon name="pin" :size="12" /> {{ row.location }}</span
								>
							</div>
							<div v-if="row.remarks" class="ss-note-line is-muted">{{ row.remarks }}</div>
						</div>
					</div>
				</div>

				<aside class="ss-split-side">
					<h2 class="ss-section-title ss-section-title--first">
						บุคลากร <span class="ss-section-total">{{ labour_total }} คน</span>
					</h2>
					<div class="ss-res-chips">
						<span v-for="r in doc.labour" :key="r.role" class="ss-chip"
							>{{ r.role }} <b>{{ r.qty }}</b></span
						>
						<span v-if="!doc.labour.length" class="ss-muted">ไม่ได้ระบุ</span>
					</div>
					<h2 class="ss-section-title">เครื่องจักร</h2>
					<div class="ss-res-chips">
						<span v-for="r in doc.equipment" :key="r.equipment" class="ss-chip"
							>{{ r.equipment }} <b>{{ r.qty }}</b
							><template v-if="r.hours"> · {{ num(r.hours) }} ชม.</template></span
						>
						<span v-if="!doc.equipment.length" class="ss-muted">ไม่ได้ระบุ</span>
					</div>
					<template v-for="block in text_blocks" :key="block.label">
						<h2 class="ss-section-title">{{ block.label }}</h2>
						<div class="ss-text-block" :class="block.tone && `tone-${block.tone}`">
							{{ block.text }}
						</div>
					</template>
				</aside>
			</div>
		</div>


		<DeleteSheet
			:open="deleting"
			:label="kind.label"
			:name="params.name"
			method="consbiz.site_app.delete_report"
			:args="{ doctype: kind.doctype, name: params.name }"
			@close="deleting = false"
			@deleted="after_delete"
		/>

		<PdfViewer
			:open="pdf_sheet"
			:url="setup?.pdf_url"
			:name="params.name"
			:title="kind.label"
			@close="pdf_sheet = false"
		/>

		<Sheet
			:open="rejecting"
			title="ไม่อนุมัติ"
			subtitle="ผู้ขอแก้ไขแล้วส่งขออนุมัติใหม่ได้"
			@close="rejecting = false"
		>
			<label class="ss-field">
				<span class="ss-field-label">เหตุผล<em>*</em></span>
				<textarea
					v-model="reason"
					class="ss-input"
					rows="3"
					placeholder="เช่น ยังไม่ได้รับอนุมัติแบบ ให้เลื่อนไปวันพรุ่งนี้"
				></textarea>
			</label>
			<template #footer>
				<button
					type="button"
					class="ss-btn ss-btn--primary ss-btn--block ss-btn--lg"
					:disabled="busy || !reason.trim()"
					@click="reject"
				>
					ยืนยันไม่อนุมัติ
				</button>
			</template>
		</Sheet>
	</div>
</template>

<script setup>
import FormHead from "../../../shared/components/FormHead.vue";
import { LABELS, doc_menu, step_actions } from "../../../shared/form_actions.js";
import { computed, inject, ref } from "vue";
import Icon from "../../../shared/components/Icon.vue";
import TopBar from "../../../shared/components/TopBar.vue";
import Skeleton from "../../../shared/components/Skeleton.vue";
import Sheet from "../../../shared/components/Sheet.vue";
import PdfViewer from "../../../shared/components/PdfViewer.vue";
import DeleteSheet from "../../../shared/components/DeleteSheet.vue";
import { REPORT_KINDS } from "../../sections.js";
import { call, celebrate, desk_url, go, num, post, show_error, state } from "../../../shared/api.js";

const reload_summary = inject("reload_summary");
const params = state.route.params;
const kind = REPORT_KINDS[params.kind] || REPORT_KINDS.dr;
const is_report = kind.doctype === "Daily Report";

const setup = ref(null);
const doc = computed(() => setup.value?.doc);
const busy = ref(false);
const rejecting = ref(false);
const reason = ref("");
const pdf_sheet = ref(false);

const pct = (value) => (Number(value) || 0).toLocaleString("th-TH", { maximumFractionDigits: 2 });
const MONTHS = [
	"ม.ค.",
	"ก.พ.",
	"มี.ค.",
	"เม.ย.",
	"พ.ค.",
	"มิ.ย.",
	"ก.ค.",
	"ส.ค.",
	"ก.ย.",
	"ต.ค.",
	"พ.ย.",
	"ธ.ค.",
];
const DAYS = ["อาทิตย์", "จันทร์", "อังคาร", "พุธ", "พฤหัสบดี", "ศุกร์", "เสาร์"];
const long_date = (value) => {
	const [y, m, d] = String(value).split("-").map(Number);
	return `วัน${DAYS[new Date(y, m - 1, d).getDay()]} ${d} ${MONTHS[m - 1]} ${y + 543}`;
};

const STATUS = {
	Pending: ["รออนุมัติ", "amber"],
	Approved: ["อนุมัติแล้ว", "blue"],
	Completed: ["ทำรายงานแล้ว", "green"],
	Rejected: ["ไม่อนุมัติ", "rose"],
};
const status = computed(() => {
	const d = doc.value;
	if (!is_report) {
		const [label, tone] = STATUS[d.status] || [d.status, "gray"];
		return { label, tone };
	}
	return d.docstatus === 1 ? { label: "ส่งแล้ว", tone: "green" } : { label: "ร่าง", tone: "gray" };
});
const variance = computed(() => Number(doc.value?.progress_variance) || 0);
const labour_total = computed(() => doc.value.labour.reduce((sum, r) => sum + (Number(r.qty) || 0), 0));

const text_blocks = computed(() => {
	const d = doc.value;
	return [
		{ label: "ปัญหา / อุปสรรค", text: d.problems, tone: "amber" },
		{ label: "วัสดุที่ต้องใช้", text: d.materials },
		{ label: "มาตรการความปลอดภัย", text: d.safety_measures },
		{ label: "หมายเหตุ", text: d.remarks },
	].filter((b) => b.text);
});

const deleting = ref(false);
// หัวฟอร์ม: รายงานประจำวัน ร่าง → ยืนยัน, คำขออนุมัติ รออนุมัติ → ผู้อนุมัติ: ไม่อนุมัติ / อนุมัติ → ทำรายงานจากคำขอ
const actions = computed(() => {
	const s = setup.value;
	const d = doc.value;
	if (!s) return [];
	const edit = s.editable && {
		label: d.status === "Rejected" ? "แก้ไขแล้วส่งใหม่" : "แก้ไข",
		icon: "pen",
		tone: s.can_submit ? "soft" : "primary",
		run: () => go("report-form", { kind: params.kind, name: d.name }),
	};
	return step_actions({
		stage: s.can_approve ? "pending" : s.editable ? "draft" : "done",
		submit: s.can_approve
			? { label: LABELS.approve, run: approve }
			: s.can_submit && { label: LABELS.confirm, run: submit },
		reject: s.can_approve && (() => (rejecting.value = true)),
		next: [
			!s.report &&
				s.can_make_report && {
					label: "ทำรายงานจากคำขอนี้",
					icon: "plus",
					run: () => go("report-form", { kind: "dr", name: "new", date: d.date, from: d.name }),
				},
		],
		extra: [!s.can_approve && edit],
	});
});
const menu = computed(() => {
	const s = setup.value;
	if (!s) return [];
	return doc_menu({
		items: [
			s.report && {
				label: "เปิดรายงานของคำขอนี้",
				icon: "file",
				run: () => go("report-view", { kind: "dr", name: s.report }),
			},
		],
		refresh: load,
		desk: [kind.doctype, params.name],
		remove: s.can_delete && (() => (deleting.value = true)),
	});
});

function after_delete() {
	reload_summary();
	go("reports", { tab: params.kind === "drq" ? "request" : "report" }, { replace: true });
}

async function load() {
	try {
		setup.value = await call("consbiz.site_app.get_report_form", {
			project: state.project.name,
			doctype: kind.doctype,
			name: params.name,
			view: 1,
		});
	} catch (error) {
		show_error(error);
	}
}

async function run(method, args, title) {
	busy.value = true;
	try {
		await post(method, args);
		await celebrate(title, params.name);
		reload_summary();
		await load();
	} catch (error) {
		show_error(error);
	} finally {
		busy.value = false;
	}
}

const submit = () => run("consbiz.site_app.submit_report", { name: params.name }, "ส่งรายงานแล้ว");
const approve = () => run("consbiz.site_app.approve_request", { name: params.name }, "อนุมัติแล้ว");
async function reject() {
	rejecting.value = false;
	await run(
		"consbiz.site_app.reject_request",
		{ name: params.name, reason: reason.value.trim() },
		"ไม่อนุมัติแล้ว"
	);
	reason.value = "";
}

load();
</script>
