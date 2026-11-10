<template>
	<div :class="{ 'ss-has-bar': open_items.length }">
		<TopBar :title="doc?.borrower_name || 'ใบยืม'" :subtitle="params.name" back_to="borrow">
			<template #actions>
				<a
					v-if="boot.desk"
					class="ss-icon-btn"
					:href="desk_url('Equipment Borrowing', params.name)"
					aria-label="เปิดในระบบ"
				>
					<Icon name="external" :size="20" />
				</a>
			</template>
		</TopBar>

		<div class="ss-content">
			<Skeleton v-if="!doc" :rows="3" />
			<template v-else>
				<div class="ss-split">
					<div class="ss-split-main">
						<div
							class="ss-banner"
							:class="
								doc.overdue
									? 'tone-rose'
									: doc.status === 'Returned'
									? 'tone-green'
									: 'tone-amber'
							"
						>
							<Icon
								:name="doc.overdue ? 'alert' : doc.status === 'Returned' ? 'check' : 'clock'"
								:size="20"
							/>
							<div>
								<div class="ss-banner-title">{{ STATUS[doc.status] || doc.status }}</div>
								<div class="ss-banner-text">
									ยืม {{ thai_date(doc.date, { year: true }) }}
									<template v-if="doc.due_date">
										· กำหนดคืน {{ thai_date(doc.due_date, { year: true }) }}</template
									>
								</div>
							</div>
						</div>

						<template v-if="open_items.length">
							<div class="ss-row-actions">
								<span class="ss-muted">บันทึกการคืน</span>
								<button
									type="button"
									class="ss-btn ss-btn--soft ss-btn--sm"
									@click="return_all"
								>
									<Icon name="check" :size="16" :stroke="2.6" /> คืนครบทั้งหมด
								</button>
							</div>
							<div class="ss-list">
								<div
									v-for="(row, i) in open_items"
									:key="row.item_code"
									class="ss-card ss-item"
									:class="{
										'is-complete': row.qty >= row.outstanding_qty,
										'is-partial': row.qty > 0 && row.qty < row.outstanding_qty,
									}"
									:style="{ '--i': i }"
								>
									<div class="ss-item-head">
										<span class="ss-thumb"><Icon name="wrench" :size="20" /></span>
										<span class="ss-card-main">
											<span class="ss-card-title">{{ row.item_name }}</span>
											<span class="ss-card-meta"
												>ค้างคืน <b>{{ num(row.outstanding_qty) }}</b>
												{{ row.uom }} จาก {{ num(row.qty_borrowed) }}</span
											>
										</span>
									</div>
									<div class="ss-item-controls">
										<Stepper v-model="row.qty" :max="row.outstanding_qty" />
										<div class="ss-conditions">
											<button
												v-for="c in CONDITIONS"
												:key="c.value"
												type="button"
												class="ss-condition"
												:class="[
													`tone-${c.tone}`,
													{ 'is-active': row.condition === c.value },
												]"
												@click="row.condition = c.value"
											>
												{{ c.label }}
											</button>
										</div>
									</div>
								</div>
							</div>

							<div class="ss-form">
								<label class="ss-field">
									<span class="ss-field-label">ผู้นำมาคืน</span>
									<input
										v-model="returned_by"
										class="ss-input"
										:placeholder="doc.borrower_name"
									/>
								</label>
								<div class="ss-field">
									<span class="ss-field-label">ลายเซ็นผู้คืน</span>
									<SignaturePad v-model="signature" />
								</div>
								<div class="ss-field">
									<span class="ss-field-label">รูปสภาพอุปกรณ์</span>
									<PhotoInput v-model="photos" :max="1" />
								</div>
								<label class="ss-field">
									<span class="ss-field-label">หมายเหตุ</span>
									<input v-model="remarks" class="ss-input" placeholder="เช่น ใบมีดบิ่น" />
								</label>
							</div>
						</template>
					</div>
					<aside class="ss-split-side">
						<h2 class="ss-section-title">รายการที่ยืม</h2>
						<div class="ss-list">
							<div
								v-for="(it, i) in doc.items"
								:key="it.item_code"
								class="ss-card ss-card--row"
								:style="{ '--i': i }"
							>
								<span class="ss-card-main">
									<span class="ss-card-title">{{ it.item_name }}</span>
									<span class="ss-card-meta">
										คืนแล้ว {{ num(it.returned_qty) }}
										<template v-if="it.lost_qty">
											·
											<span class="ss-text-danger"
												>หาย {{ num(it.lost_qty) }}</span
											></template
										>
									</span>
								</span>
								<span class="ss-qty"
									><b>{{ num(it.qty) }}</b
									><small>{{ it.uom }}</small></span
								>
							</div>
						</div>

						<template v-if="doc.returns.length">
							<h2 class="ss-section-title">ประวัติการคืน</h2>
							<div class="ss-timeline">
								<div
									v-for="(r, i) in doc.returns"
									:key="i"
									class="ss-timeline-row"
									:class="`tone-${COND_TONE[r.condition]}`"
								>
									<span class="ss-timeline-dot"></span>
									<div>
										<b>{{ item_name(r.item_code) }} × {{ num(r.qty) }}</b>
										<small
											>{{ thai_date(r.date) }} · {{ COND_LABEL[r.condition]
											}}<template v-if="r.returned_by">
												· {{ r.returned_by }}</template
											></small
										>
									</div>
								</div>
							</div>
						</template>
					</aside>
				</div>
			</template>
		</div>

		<Teleport to="#ss-layer">
			<Transition name="ss-bar">
				<div v-if="open_items.length" class="ss-bottom-bar">
					<div class="ss-bar-summary">
						<b>คืน {{ returning.length }}</b> รายการ
					</div>
					<button
						type="button"
						class="ss-btn ss-btn--primary ss-btn--lg"
						:disabled="!returning.length || saving || photos.some((p) => p.uploading)"
						@click="submit"
					>
						<span v-if="saving" class="ss-spinner"></span>
						<template v-else>บันทึกรับคืน</template>
					</button>
				</div>
			</Transition>
		</Teleport>
	</div>
</template>

<script setup>
import { computed, inject, ref } from "vue";
import Icon from "../../../shared/components/Icon.vue";
import TopBar from "../../../shared/components/TopBar.vue";
import Skeleton from "../../../shared/components/Skeleton.vue";
import Stepper from "../../../shared/components/Stepper.vue";
import SignaturePad from "../../../shared/components/SignaturePad.vue";
import PhotoInput from "../../../shared/components/PhotoInput.vue";
import {
	back,
	boot,
	call,
	celebrate,
	desk_url,
	num,
	post,
	show_error,
	state,
	thai_date,
	vibrate,
} from "../../../shared/api.js";

const STATUS = {
	Borrowed: "ยืมอยู่",
	"Partially Returned": "คืนบางส่วน",
	Returned: "คืนครบแล้ว",
	Cancelled: "ยกเลิก",
};
const CONDITIONS = [
	{ value: "Good", label: "ปกติ", tone: "green" },
	{ value: "Damaged", label: "ชำรุด", tone: "amber" },
	{ value: "Lost", label: "สูญหาย", tone: "rose" },
];
const COND_LABEL = { Good: "ปกติ", Damaged: "ชำรุด", Lost: "สูญหาย" };
const COND_TONE = { Good: "green", Damaged: "amber", Lost: "rose" };

const reload_summary = inject("reload_summary");
const params = state.route.params;
const doc = ref(null);
const open_items = ref([]);
const returned_by = ref("");
const signature = ref(null);
const photos = ref([]);
const remarks = ref("");
const saving = ref(false);

const returning = computed(() => open_items.value.filter((r) => r.qty > 0));
const item_name = (code) => doc.value.items.find((i) => i.item_code === code)?.item_name || code;

function return_all() {
	vibrate(12);
	open_items.value.forEach((r) => (r.qty = r.outstanding_qty));
}

async function load() {
	try {
		const data = await call("get_borrowing", { name: params.name });
		doc.value = data;
		open_items.value = (data.can_return ? data.items : [])
			.filter((i) => i.outstanding_qty > 0 && data.status !== "Cancelled")
			.map((i) => ({ ...i, qty_borrowed: i.qty, qty: 0, condition: "Good" }));
	} catch (error) {
		show_error(error);
		back("borrow");
	}
}

async function submit() {
	saving.value = true;
	try {
		await post("consbiz.consbiz.doctype.equipment_borrowing.equipment_borrowing.record_return", {
			name: params.name,
			items: returning.value.map((r) => ({
				item_code: r.item_code,
				qty: r.qty,
				condition: r.condition,
			})),
			returned_by: returned_by.value || doc.value.borrower_name,
			signature: signature.value,
			photo: photos.value[0]?.file_url,
			remarks: remarks.value,
		});
		reload_summary();
		await celebrate("รับคืนเรียบร้อย", `${returning.value.length} รายการ`);
		back("borrow");
	} catch (error) {
		show_error(error);
	} finally {
		saving.value = false;
	}
}

load();
</script>
