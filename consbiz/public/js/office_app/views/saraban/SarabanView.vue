<!-- ดูเอกสารสารบรรณ (kinds.js) ต้นแบบ = หน้าดูเอกสารโครงการ (ProjectDocView.vue): หัวเอกสาร + ข้อมูล + แถบปุ่มล่าง
     ร่าง = แก้/Submit/ลบ, Submit แล้ว: หนังสือเข้า = เสนออนุมัติ/พิจารณา/ถอนเรื่อง/เปลี่ยนผู้อนุมัติ,
     หนังสือออก = บันทึกสถานะ, ใบนำส่ง = บันทึกการส่ง/รับ + สร้างใบปะหน้า, ใบปะหน้า = พิมพ์ตามขนาดซอง
     แก้ฉบับ (amend) และไฟล์แนบใช้ระบบเต็ม -->
<template>
	<div class="ss-has-bar">
		<TopBar :title="kind.label" :subtitle="params.name" :back_to="params.kind">
			<template #actions>
				<button
					v-if="view?.pdf_url"
					type="button"
					class="ss-icon-btn"
					aria-label="PDF / พิมพ์"
					title="PDF / พิมพ์"
					@click="open_pdf(view.pdf_url)"
				>
					<Icon name="printer" :size="19" />
				</button>
				<a
					class="ss-icon-btn"
					:href="desk_url(kind.doctype, params.name)"
					aria-label="เปิดในระบบเต็ม"
					title="เปิดในระบบเต็ม"
					><Icon name="external" :size="19"
				/></a>
			</template>
		</TopBar>

		<div class="ss-content">
			<Skeleton v-if="!view" :rows="4" />
			<div v-else class="ss-split">
				<div class="ss-split-main">
					<div class="ss-doc-head">
						<div class="ss-doc-head-top">
							<span class="ss-tag" :class="`tone-${doc.status_tone}`">{{
								doc.status_label
							}}</span>
							<span class="ss-doc-date">{{ doc.name }}</span>
						</div>
						<h2 class="ss-section-title">{{ heading }}</h2>
						<div class="ss-facts ss-facts--grid">
							<div v-for="f in facts" :key="f.label" class="ss-fact">
								<span>{{ f.label }}</span
								><b>{{ f.value }}</b>
							</div>
						</div>
					</div>

					<div v-if="waiting_me" class="ss-banner tone-amber">
						<Icon name="alert" :size="22" />
						<div>
							<div class="ss-banner-title">รอคุณพิจารณา</div>
							<div class="ss-banner-text">หนังสือนี้เสนอให้คุณอนุมัติ</div>
						</div>
					</div>

					<div v-for="b in notes" :key="b.label">
						<h2 class="ss-section-title">{{ b.label }}</h2>
						<p class="ss-note-line ss-pre">{{ b.text }}</p>
					</div>

					<!-- ใบปะหน้า: พิมพ์ตามขนาดซอง -->
					<template v-if="view.prints?.length">
						<h2 class="ss-section-title">พิมพ์</h2>
						<div class="ss-chips">
							<button
								v-for="p in view.prints"
								:key="p.format"
								type="button"
								class="ss-btn ss-btn--soft"
								@click="open_pdf(p.url, p.format)"
							>
								<Icon name="printer" :size="16" /> {{ p.format }}
							</button>
						</div>
					</template>

					<!-- ใบนำส่ง: ใบปะหน้าที่สร้างจากใบนี้ -->
					<template v-if="view.envelopes?.length">
						<h2 class="ss-section-title">ใบปะหน้าซอง</h2>
						<div class="ss-chips">
							<button
								v-for="e in view.envelopes"
								:key="e.name"
								type="button"
								class="ss-chip ss-link"
								@click="go('saraban-doc', { kind: 'envelopes', name: e.name })"
							>
								<Icon name="mail" :size="12" /> {{ e.name }}
							</button>
						</div>
					</template>
				</div>

				<aside v-if="doc.items" class="ss-split-side">
					<h2 class="ss-section-title">รายการเอกสาร ({{ doc.items.length }})</h2>
					<Empty v-if="!doc.items.length" icon="file" title="ไม่มีรายการ" />
					<div v-else class="ss-list">
						<div
							v-for="(row, i) in doc.items"
							:key="row.name"
							class="ss-card"
							:style="{ '--i': i }"
						>
							<div class="ss-card-head">
								<span class="ss-card-main">
									<span class="ss-card-title">{{
										row.description || row.document_no || row.reference_name
									}}</span>
									<span class="ss-card-meta">
										{{
											SOURCE_LABELS[row.reference_doctype] ||
											row.reference_doctype ||
											"พิมพ์เอง"
										}}
										{{ row.document_no ? `· ${row.document_no}` : "" }}
									</span>
								</span>
								<span v-if="row.amount" class="ss-qty"
									><b>{{ money(row.amount) }}</b></span
								>
							</div>
							<div class="ss-chips">
								<span v-if="row.date" class="ss-chip"
									><Icon name="calendar" :size="12" />
									{{ thai_date(row.date, { year: true }) }}</span
								>
								<span v-if="row.qty" class="ss-chip"
									>{{ num(row.qty) }} {{ row.unit || "" }}</span
								>
								<span v-if="row.remark" class="ss-chip">{{ row.remark }}</span>
							</div>
						</div>
						<div v-if="items_total" class="ss-fact">
							<span>ยอดรวม</span><b>{{ money(items_total) }}</b>
						</div>
					</div>
				</aside>
			</div>
		</div>

		<Teleport to="#ss-layer">
			<Transition name="ss-bar">
				<div v-if="actions.length" class="ss-bottom-bar">
					<button
						v-for="a in actions"
						:key="a.label"
						type="button"
						class="ss-btn ss-btn--lg"
						:class="
							a.primary
								? 'ss-btn--primary ss-grow'
								: a.danger
								? 'ss-btn--ghost-danger'
								: 'ss-btn--ghost'
						"
						:disabled="busy"
						@click="a.run"
					>
						{{ a.label }}
					</button>
				</div>
			</Transition>
		</Teleport>

		<DeleteSheet
			:open="deleting"
			:label="kind.label"
			:name="params.name"
			:method="`${API}.delete_doc`"
			:args="{ kind: params.kind, name: params.name }"
			@close="deleting = false"
			@deleted="after_delete"
		/>

		<!-- ยืนยัน Submit / ยกเลิก / ถอนเรื่อง -->
		<Sheet
			:open="!!confirm"
			:title="confirm?.title"
			:subtitle="params.name"
			@close="confirm = null"
		>
			<p class="ss-note-line">{{ confirm?.text }}</p>
			<template #footer>
				<div class="ss-sheet-actions">
					<button
						type="button"
						class="ss-btn ss-btn--block ss-btn--lg"
						:class="confirm?.danger ? 'ss-btn--danger' : 'ss-btn--primary'"
						:disabled="busy"
						@click="confirm.run"
					>
						{{ confirm?.button }}
					</button>
				</div>
			</template>
		</Sheet>

		<!-- หนังสือเข้า: เลือกผู้อนุมัติ (เสนอ / เปลี่ยน) -->
		<Sheet
			:open="!!choosing"
			:title="choosing === 'propose' ? 'เสนออนุมัติ' : 'เปลี่ยนผู้อนุมัติ'"
			@close="choosing = null"
		>
			<div class="ss-form">
				<div v-if="choosing === 'change' && doc?.approver" class="ss-fact">
					<span>ผู้อนุมัติปัจจุบัน</span><b>{{ doc.approver_name || doc.approver }}</b>
				</div>
				<Picker
					v-model="approver"
					label="ผู้อนุมัติ"
					:options="approver_options"
					required
					empty_text="ไม่มีผู้ใช้ที่มี Role Approver"
				/>
			</div>
			<template #footer>
				<div class="ss-sheet-actions">
					<button
						type="button"
						class="ss-btn ss-btn--primary ss-btn--block ss-btn--lg"
						:disabled="busy || !approver"
						@click="save_approver"
					>
						{{ choosing === "propose" ? "เสนอ" : "บันทึก" }}
					</button>
				</div>
			</template>
		</Sheet>

		<!-- หนังสือเข้า: พิจารณาอนุมัติ -->
		<Sheet
			:open="!!deciding"
			title="พิจารณาอนุมัติ"
			:subtitle="params.name"
			@close="deciding = null"
		>
			<div v-if="deciding" class="ss-form">
				<label class="ss-field">
					<span class="ss-field-label">วันที่<em>*</em></span>
					<DateInput v-model="deciding.approve_date" label="วันที่" />
				</label>
				<label class="ss-field">
					<span class="ss-field-label"
						>หมายเหตุ <small>(ไม่อนุมัติต้องระบุเหตุผล)</small></span
					>
					<textarea v-model="deciding.remark" class="ss-input" rows="3"></textarea>
				</label>
			</div>
			<template #footer>
				<div class="ss-sheet-actions">
					<button
						type="button"
						class="ss-btn ss-btn--ghost-danger ss-btn--lg"
						:disabled="busy"
						@click="decide(0)"
					>
						ไม่อนุมัติ
					</button>
					<button
						type="button"
						class="ss-btn ss-btn--primary ss-btn--lg ss-grow"
						:disabled="busy"
						@click="decide(1)"
					>
						อนุมัติ
					</button>
				</div>
			</template>
		</Sheet>

		<!-- แก้หลัง Submit: สถานะหนังสือออก / การส่งของใบนำส่ง -->
		<Sheet
			:open="!!updating"
			:title="params.kind === 'transmittals' ? 'บันทึกการส่ง' : 'บันทึกสถานะ'"
			@close="updating = null"
		>
			<div v-if="updating" class="ss-form">
				<div v-if="params.kind === 'letters-out'" class="ss-field">
					<span class="ss-field-label">สถานะเอกสาร</span>
					<SelectBox
						v-model="updating.document_status"
						label="สถานะเอกสาร"
						:options="LETTER_OUT_STATUS"
					/>
				</div>
				<template v-else>
					<label class="ss-field">
						<span class="ss-field-label">วันที่ส่ง</span>
						<DateInput v-model="updating.sent_date" label="วันที่ส่ง" clearable />
					</label>
					<label class="ss-field">
						<span class="ss-field-label">ผู้รับเอกสาร</span>
						<input v-model="updating.received_by" class="ss-input" />
					</label>
					<label class="ss-field">
						<span class="ss-field-label">วันที่รับ</span>
						<DateInput v-model="updating.received_date" label="วันที่รับ" clearable />
					</label>
				</template>
			</div>
			<template #footer>
				<div class="ss-sheet-actions">
					<button
						type="button"
						class="ss-btn ss-btn--primary ss-btn--block ss-btn--lg"
						:disabled="busy"
						@click="save_update"
					>
						บันทึก
					</button>
				</div>
			</template>
		</Sheet>

		<PdfViewer
			:open="!!pdf"
			:url="pdf?.url"
			:name="params.name"
			:title="pdf?.title"
			@close="pdf = null"
		/>
	</div>
</template>

<script setup>
import { computed, inject, ref } from "vue";
import DateInput from "../../../shared/components/DateInput.vue";
import DeleteSheet from "../../../shared/components/DeleteSheet.vue";
import Empty from "../../../shared/components/Empty.vue";
import Icon from "../../../shared/components/Icon.vue";
import PdfViewer from "../../../shared/components/PdfViewer.vue";
import Picker from "../../../shared/components/Picker.vue";
import SelectBox from "../../../shared/components/SelectBox.vue";
import Sheet from "../../../shared/components/Sheet.vue";
import Skeleton from "../../../shared/components/Skeleton.vue";
import TopBar from "../../../shared/components/TopBar.vue";
import {
	back,
	call,
	celebrate,
	desk_url,
	go,
	money,
	num,
	post,
	show_error,
	state,
	thai_date,
	today,
} from "../../../shared/api.js";
import {
	API,
	LETTER_OUT_STATUS,
	LI,
	SARABAN_KINDS,
	SOURCE_LABELS,
	recipient_label,
} from "./kinds.js";

const reload_summary = inject("reload_summary");
const params = state.route.params;
const kind = SARABAN_KINDS[params.kind];

const view = ref(null);
const doc = computed(() => view.value?.doc);
const busy = ref(false);
const deleting = ref(false);
const confirm = ref(null);
const choosing = ref(null);
const approver = ref(null);
const deciding = ref(null);
const updating = ref(null);
const pdf = ref(null);

const date = (value) => (value ? thai_date(value, { year: true }) : "–");
const label = (field) => doc.value.labels?.[field] || doc.value[field] || "–";

const heading = computed(() => kind.title(doc.value) || doc.value.name);
const waiting_me = computed(() => !!view.value?.can_decide);

const facts = computed(() => {
	const d = doc.value;
	const list = {
		"letters-in": [
			["เลขที่หนังสือ", d.document_no || "–"],
			["ลงวันที่", date(d.document_date)],
			["ลงรับวันที่", date(d.receive_date)],
			["ผู้รับ", d.receiver_name || d.receiver || "–"],
			["บริษัท", d.company || "–"],
			["โครงการ", label("project")],
			...(d.approver ? [["ผู้อนุมัติ", d.approver_name || d.approver]] : []),
			...(d.approve_date ? [["วันที่พิจารณา", date(d.approve_date)]] : []),
		],
		"letters-out": [
			["ลงวันที่", date(d.document_date)],
			["วันที่ส่ง", date(d.sent_date)],
			["ผู้ส่ง", d.sender_name || d.sender || "–"],
			["ผู้รับ", d.receiver || "–"],
			["วันที่รับ", date(d.receive_date)],
			["บริษัท", d.company || "–"],
			["โครงการ", label("project")],
		],
		transmittals: [
			["วันที่", date(d.date)],
			["เอกสารถึงวันที่", date(d.to_date)],
			["ประเภทผู้รับ", recipient_label(d.recipient_type)],
			["ผู้รับ", d.recipient_name || label("party")],
			["เรียน", d.contact_person || "–"],
			["บริษัท", d.company || "–"],
			["โครงการ", label("project")],
			...(d.docstatus === 1
				? [
						["วันที่ส่ง", date(d.sent_date)],
						["ผู้รับเอกสาร", d.received_by || "–"],
						["วันที่รับ", date(d.received_date)],
				  ]
				: []),
		],
		envelopes: [
			["วันที่ส่ง", date(d.send_date)],
			["ผู้รับ (ผู้ติดต่อ)", label("receiver")],
			["ผู้ส่ง", [d.sender_name, d.sender_tel].filter(Boolean).join(" โทร ") || "–"],
			["บริษัท", d.company || "–"],
			...(d.reference_name ? [["อ้างอิง", d.reference_name]] : []),
		],
	};
	return list[params.kind].map(([l, value]) => ({ label: l, value }));
});

const notes = computed(() => {
	const d = doc.value;
	return [
		{
			label: "จาก",
			text: params.kind === "envelopes" && (strip(d.from_display) || d.labels?.from),
		},
		{
			label: "ถึง",
			text: params.kind === "envelopes" && (strip(d.to_display) || d.labels?.to),
		},
		{ label: "หมายเหตุ", text: params.kind === "envelopes" && d.remark },
		{
			label: d.status === LI.REJECTED ? "เหตุผลที่ไม่อนุมัติ" : "หมายเหตุผู้อนุมัติ",
			text: d.approve_remark,
		},
	].filter((b) => b.text);
});
// ที่อยู่จาก get_address_display เป็น HTML (<br>) แสดงเป็นข้อความหลายบรรทัด
function strip(html) {
	if (!html) return "";
	const box = document.createElement("div");
	box.innerHTML = html.replace(/<br\s*\/?>/gi, "\n");
	return box.textContent.trim();
}

const items_total = computed(() =>
	(doc.value.items || []).reduce((sum, r) => sum + (Number(r.amount) || 0), 0)
);
const approver_options = computed(() =>
	(view.value?.approvers || []).filter(
		(a) => choosing.value !== "change" || a.value !== doc.value.approver
	)
);

const actions = computed(() => {
	const v = view.value;
	if (!v) return [];
	const list = [];
	if (v.can_delete) list.push({ label: "ลบ", danger: true, run: () => (deleting.value = true) });
	if (v.can_cancel)
		list.push({
			label: "ยกเลิก",
			danger: true,
			run: () =>
				ask({
					title: `ยกเลิก${kind.label}`,
					text: "ยกเลิกแล้วแก้ไม่ได้ ถ้าต้องแก้ ให้แก้ไขฉบับใหม่ (Amend) ในระบบเต็ม",
					button: "ยืนยันยกเลิก",
					danger: true,
					run: () =>
						run(
							() =>
								post(`${API}.cancel_doc`, {
									kind: params.kind,
									name: params.name,
								}),
							"ยกเลิกแล้ว"
						),
				}),
		});
	if (v.can_edit)
		list.push({
			label: "แก้ไข",
			primary: !v.can_submit,
			run: () => go("saraban-form", { kind: params.kind, name: params.name }),
		});
	if (v.can_submit)
		list.push({
			label: params.kind === "letters-in" ? "ลงรับ" : "Submit",
			primary: true,
			run: () =>
				ask({
					title: params.kind === "letters-in" ? "ลงรับหนังสือ" : `Submit ${kind.label}`,
					text: "Submit แล้วแก้ได้เฉพาะสถานะและวันที่ส่ง-รับ ช่องอื่นต้องยกเลิกแล้วแก้ไขฉบับใหม่",
					button: "ยืนยัน",
					run: () =>
						run(
							() =>
								post(`${API}.submit_doc`, {
									kind: params.kind,
									name: params.name,
								}),
							"บันทึกแล้ว"
						),
				}),
		});
	// หนังสือเข้า
	if (v.can_withdraw)
		list.push({
			label: "ถอนเรื่อง",
			run: () =>
				ask({
					title: "ถอนเรื่อง",
					text: `ถอนเรื่องเสนออนุมัติจาก ${
						doc.value.approver_name || doc.value.approver
					} ใช่หรือไม่`,
					button: "ถอนเรื่อง",
					danger: true,
					run: () =>
						run(() => post(`${API}.withdraw`, { name: params.name }), "ถอนเรื่องแล้ว"),
				}),
		});
	if (v.can_change_approver)
		list.push({ label: "เปลี่ยนผู้อนุมัติ", run: () => choose("change") });
	if (v.can_propose)
		list.push({ label: "เสนออนุมัติ", primary: true, run: () => choose("propose") });
	if (v.can_decide)
		list.push({
			label: "พิจารณาอนุมัติ",
			primary: true,
			run: () => (deciding.value = { approve_date: today(), remark: "" }),
		});
	// หนังสือออก / ใบนำส่ง
	if (v.can_update)
		list.push({
			label: params.kind === "transmittals" ? "บันทึกการส่ง" : "บันทึกสถานะ",
			primary: !v.can_envelope,
			run: open_update,
		});
	if (v.can_envelope)
		list.push({
			label: "สร้างใบปะหน้า",
			primary: true,
			run: () => go("saraban-form", { kind: "envelopes", name: "new", source: params.name }),
		});
	return list;
});

function ask(options) {
	confirm.value = options;
}
function choose(mode) {
	approver.value = null;
	choosing.value = mode;
}
function open_pdf(url, title) {
	pdf.value = { url, title: title || kind.label };
}
function open_update() {
	const d = doc.value;
	updating.value =
		params.kind === "transmittals"
			? {
					sent_date: d.sent_date || today(),
					received_by: d.received_by,
					received_date: d.received_date,
			  }
			: { document_status: d.document_status };
}

async function run(task, message) {
	busy.value = true;
	try {
		const updated = await task();
		if (updated?.doc) view.value = updated;
		else await load();
		reload_summary();
		confirm.value = choosing.value = deciding.value = updating.value = null;
		await celebrate(message, params.name);
	} catch (error) {
		show_error(error);
	} finally {
		busy.value = false;
	}
}

function save_approver() {
	const method = choosing.value === "propose" ? "propose" : "change_approver";
	run(
		() => post(`${API}.${method}`, { name: params.name, approver: approver.value }),
		"เสนออนุมัติแล้ว"
	);
}
function decide(approve) {
	const { approve_date, remark } = deciding.value;
	if (!approve && !remark?.trim()) return show_error(new Error("กรุณาระบุเหตุผลที่ไม่อนุมัติ"));
	run(
		() => post(`${API}.decide`, { name: params.name, approve, approve_date, remark }),
		approve ? "อนุมัติแล้ว" : "บันทึกว่าไม่อนุมัติแล้ว"
	);
}
function save_update() {
	run(
		() =>
			post(`${API}.update_submitted`, {
				kind: params.kind,
				name: params.name,
				data: updating.value,
			}),
		"บันทึกแล้ว"
	);
}

function after_delete() {
	reload_summary();
	go(params.kind, {}, { replace: true });
}

async function load() {
	try {
		view.value = await call(`${API}.get_view`, { kind: params.kind, name: params.name });
	} catch (error) {
		show_error(error);
		back(params.kind);
	}
}
load();
</script>
