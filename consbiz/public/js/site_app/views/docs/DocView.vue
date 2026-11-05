<template>
	<!-- รายละเอียดเอกสารจัดซื้อ/ขาย: หัวเอกสาร, ความคืบหน้า, รายการ, ยอดรวม, เอกสารต้นทาง/ปลายทาง, PDF, ส่งเอกสาร -->
	<div :class="{ 'ss-has-bar': doc?.can_submit }">
		<TopBar :title="config.label" :subtitle="params.name" :back_to="params.kind">
			<template #actions>
				<button
					v-if="doc"
					type="button"
					class="ss-icon-btn"
					aria-label="PDF / แชร์"
					title="PDF / แชร์"
					@click="pdf = true"
				>
					<Icon name="file" :size="19" />
				</button>
				<a
					class="ss-icon-btn"
					:href="desk_url(config.doctype, params.name)"
					aria-label="เปิดในระบบเต็ม"
					title="เปิดในระบบเต็ม"
				>
					<Icon name="external" :size="19" />
				</a>
			</template>
		</TopBar>

		<div class="ss-content">
			<Skeleton v-if="!doc" :rows="3" />
			<div v-else class="ss-split">
				<div class="ss-split-main">
					<div class="ss-doc-head">
						<div class="ss-doc-head-top">
							<span class="ss-tag" :class="`tone-${doc.status_tone}`">{{
								doc.status_label
							}}</span>
							<span class="ss-doc-date">{{ thai_date(doc.date, { year: true }) }}</span>
						</div>
						<div class="ss-doc-party">
							<small>{{ config.party || "เรื่อง" }}</small>
							<b>{{ doc.party || doc.title || doc.name }}</b>
						</div>
						<div class="ss-doc-total">
							<div>
								<small>ยอดรวม</small>
								<b>{{ money(doc.totals.grand_total) }}</b>
							</div>
							<div v-if="doc.totals.outstanding_amount" class="is-due">
								<small>ค้าง{{ config.section === "buy" ? "จ่าย" : "รับ" }}</small>
								<b>{{ money(doc.totals.outstanding_amount) }}</b>
							</div>
						</div>
						<!-- ป้าย-ค่า เรียงแถว (มือถือไม่หักตัวเลข/ชื่อกลางคำ) -->
						<dl class="ss-kv">
							<template v-if="doc.due">
								<dt>{{ config.due || "ต้องการภายใน" }}</dt>
								<dd>{{ thai_date(doc.due, { year: true }) }}</dd>
							</template>
							<template v-if="doc.bill_no">
								<dt>เลขที่บิลผู้ขาย</dt>
								<dd>{{ doc.bill_no }}</dd>
							</template>
							<template v-if="doc.project">
								<dt>โครงการ</dt>
								<dd>{{ doc.project }}</dd>
							</template>
							<dt>ผู้ทำเอกสาร</dt>
							<dd>{{ doc.owner_name }}</dd>
						</dl>
						<div v-for="p in progress" :key="p.label" class="ss-doc-progress">
							<span>{{ p.label }}</span>
							<div class="ss-plan-bar ss-plan-bar--sm">
								<span
									class="ss-plan-bar-actual"
									:style="{ width: `${Math.min(100, p.value)}%` }"
								></span>
							</div>
							<b>{{ Math.round(p.value) }}%</b>
						</div>
					</div>

					<h2 class="ss-section-title">
						รายการ <span class="ss-count">{{ doc.items.length }}</span>
					</h2>
					<div class="ss-list ss-list--form">
						<div
							v-for="(it, i) in doc.items"
							:key="i"
							class="ss-card"
							:style="{ '--i': Math.min(i, 12) }"
						>
							<div class="ss-doc-row">
								<span class="ss-doc-title">{{ it.item_name || it.item_code }}</span>
								<b class="ss-doc-money">{{ money(it.amount) }}</b>
							</div>
							<div class="ss-card-head">
								<span class="ss-card-main">
									<span class="ss-card-meta"
										>{{ num(it.qty) }} {{ it.uom }} × {{ money(it.rate)
										}}<template v-if="it.schedule_date || it.delivery_date">
											· ส่ง
											{{ thai_date(it.schedule_date || it.delivery_date) }}</template
										></span
									>
								</span>
							</div>
							<div v-if="item_progress(it)" class="ss-chips">
								<span class="ss-chip">{{ item_progress(it) }}</span>
							</div>
						</div>
					</div>
				</div>

				<aside class="ss-split-side">
					<h2 class="ss-section-title ss-section-title--first">ยอดเงิน</h2>
					<div class="ss-totals">
						<div v-if="doc.totals.total !== undefined">
							<span>รวมเป็นเงิน</span><b>{{ money(doc.totals.total) }}</b>
						</div>
						<div v-if="doc.totals.discount_amount">
							<span>ส่วนลด</span><b>−{{ money(doc.totals.discount_amount) }}</b>
						</div>
						<div v-for="t in doc.taxes" :key="t.description">
							<span
								>{{ t.description }}<template v-if="t.rate"> {{ t.rate }}%</template></span
							><b>{{ money(t.amount) }}</b>
						</div>
						<div class="is-grand">
							<span>ยอดรวมทั้งสิ้น</span
							><b>{{ money(doc.totals.rounded_total || doc.totals.grand_total) }}</b>
						</div>
					</div>

					<template v-if="doc.before.length || doc.after.length">
						<h2 class="ss-section-title">เอกสารที่เกี่ยวข้อง</h2>
						<div class="ss-flow">
							<button
								v-for="l in [
									...doc.before.map((x) => ({ ...x, dir: 'before' })),
									...doc.after.map((x) => ({ ...x, dir: 'after' })),
								]"
								:key="l.doctype + l.name"
								type="button"
								class="ss-flow-item"
								@click="open_link(l)"
							>
								<Icon
									:name="l.dir === 'before' ? 'chevron-left' : 'chevron-right'"
									:size="16"
								/>
								<span class="ss-flow-main">
									<small>{{ link_label(l.doctype) }}</small>
									<b>{{ l.name }}</b>
								</span>
								<span class="ss-tag" :class="`tone-${l.status_tone}`">{{
									l.status_label
								}}</span>
							</button>
						</div>
					</template>

					<template v-if="doc.remarks">
						<h2 class="ss-section-title">หมายเหตุ</h2>
						<div class="ss-text-block">{{ doc.remarks }}</div>
					</template>
				</aside>
			</div>
		</div>

		<Teleport to="#ss-layer">
			<Transition name="ss-bar">
				<div v-if="doc?.can_submit" class="ss-bottom-bar">
					<a class="ss-btn ss-btn--ghost ss-btn--lg" :href="desk_url(config.doctype, params.name)"
						>แก้ไข</a
					>
					<button
						type="button"
						class="ss-btn ss-btn--primary ss-btn--lg ss-grow"
						:disabled="busy"
						@click="confirm = true"
					>
						ส่ง{{ config.label }}
					</button>
				</div>
			</Transition>
		</Teleport>

		<Sheet :open="confirm" :title="`ส่ง${config.label}`" :subtitle="params.name" @close="confirm = false">
			<p class="ss-muted">ส่งแล้วแก้ไขไม่ได้ ต้องยกเลิกแล้วแก้ไขในระบบเต็ม</p>
			<div v-if="doc" class="ss-facts ss-facts--grid">
				<div class="ss-fact">
					<span>{{ config.party || "เรื่อง" }}</span
					><b>{{ doc.party || doc.title }}</b>
				</div>
				<div class="ss-fact">
					<span>ยอดรวม</span><b>{{ money(doc.totals.grand_total) }}</b>
				</div>
			</div>
			<template #footer>
				<button
					type="button"
					class="ss-btn ss-btn--primary ss-btn--block ss-btn--lg"
					:disabled="busy"
					@click="submit"
				>
					<span v-if="busy" class="ss-spinner"></span>
					<template v-else>ยืนยันส่ง</template>
				</button>
			</template>
		</Sheet>

		<PdfViewer
			:open="pdf"
			:url="doc?.pdf_url"
			:name="params.name"
			:title="config.label"
			@close="pdf = false"
		/>
	</div>
</template>

<script setup>
import { computed, inject, ref } from "vue";
import Icon from "../../components/Icon.vue";
import TopBar from "../../components/TopBar.vue";
import Skeleton from "../../components/Skeleton.vue";
import Sheet from "../../components/Sheet.vue";
import PdfViewer from "../../components/PdfViewer.vue";
import { DOC_KINDS } from "../../sections.js";
import { call, celebrate, desk_url, go, money, num, post, show_error, state, thai_date } from "../../api.js";

const reload_summary = inject("reload_summary");
const params = state.route.params;
const config = DOC_KINDS[params.kind] || DOC_KINDS.po;

const doc = ref(null);
const busy = ref(false);
const confirm = ref(false);
const pdf = ref(false);

const progress = computed(() =>
	doc.value?.docstatus === 1
		? (config.progress || []).map(([field, label]) => ({ label, value: doc.value.progress[field] || 0 }))
		: []
);

const LINK_LABELS = {
	"Material Request": "ใบขอซื้อ",
	"Purchase Order": "ใบสั่งซื้อ",
	"Purchase Receipt": "ใบรับของ",
	"Purchase Invoice": "ใบแจ้งหนี้ซื้อ",
	Quotation: "ใบเสนอราคา",
	"Sales Order": "ใบสั่งขาย",
	"Delivery Note": "ใบส่งของ",
	"Sales Invoice": "ใบแจ้งหนี้ขาย",
	"Payment Entry": "รับ/จ่ายเงิน",
};
const link_label = (doctype) => LINK_LABELS[doctype] || doctype;

// ปริมาณที่ดำเนินการแล้วของแต่ละรายการ
// ช่องปริมาณที่เกี่ยวกับเอกสารแต่ละชนิด (แถวของ SO มี ordered_qty ของการผลิต ไม่ใช่การสั่งซื้อ)
const ITEM_PROGRESS = {
	mr: [
		["ordered_qty", "สั่งแล้ว"],
		["received_qty", "รับแล้ว"],
	],
	po: [["received_qty", "รับแล้ว"]],
	so: [["delivered_qty", "ส่งมอบแล้ว"]],
};
function item_progress(it) {
	const pairs = ITEM_PROGRESS[params.kind] || [];
	if (doc.value.docstatus !== 1) return "";
	return pairs
		.filter(([field]) => it[field] !== undefined && it[field] !== null)
		.map(([field, label]) => `${label} ${num(it[field])}/${num(it.qty)}`)
		.join(" · ");
}

// เอกสารจัดซื้อ/ขายเปิดในแอป ที่เหลือ (ใบรับของ, ใบส่งของ, รับ/จ่ายเงิน) เปิดในระบบเต็ม
function open_link(l) {
	if (l.kind) go(`${DOC_KINDS[l.kind].section}-doc`, { kind: l.kind, name: l.name });
	else window.location.href = desk_url(l.doctype, l.name);
}

async function load() {
	try {
		doc.value = await call("consbiz.site_docs.get_doc", { kind: params.kind, name: params.name });
	} catch (error) {
		show_error(error);
	}
}

async function submit() {
	busy.value = true;
	try {
		await post("consbiz.site_docs.submit_doc", { kind: params.kind, name: params.name });
		confirm.value = false;
		await celebrate(`ส่ง${config.label}แล้ว`, params.name);
		reload_summary();
		await load();
	} catch (error) {
		show_error(error);
	} finally {
		busy.value = false;
	}
}

load();
</script>
