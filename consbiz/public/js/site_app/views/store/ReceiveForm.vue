<template>
	<div class="ss-has-bar">
		<TopBar :title="source?.party || 'ตรวจรับของ'" :subtitle="params.name" back_to="receive" />

		<div class="ss-content">
			<Skeleton v-if="!source" :rows="3" />
			<template v-else>
				<div class="ss-split">
					<div class="ss-split-main">
						<div class="ss-banner" :class="source.employer ? 'tone-violet' : 'tone-blue'">
							<Icon :name="source.employer ? 'building' : 'file'" :size="20" />
							<div>
								<div class="ss-banner-title">
									{{ source.employer ? "วัสดุผู้ว่าจ้างจัดหา" : "รับตามใบสั่งซื้อ" }}
								</div>
								<div class="ss-banner-text">
									สั่งวันที่ {{ thai_date(source.date, { year: true }) }}
									<template v-if="source.schedule_date">
										· กำหนดส่ง
										{{ thai_date(source.schedule_date, { year: true }) }}</template
									>
								</div>
							</div>
						</div>

						<div class="ss-row-actions">
							<span class="ss-muted">{{ rows.length }} รายการค้างรับ</span>
							<button type="button" class="ss-btn ss-btn--soft ss-btn--sm" @click="fill_all">
								<Icon name="check" :size="16" :stroke="2.6" /> รับครบทุกรายการ
							</button>
						</div>

						<TransitionGroup tag="div" class="ss-list" name="ss-list" appear>
							<div
								v-for="(row, i) in rows"
								:key="row.row"
								class="ss-card ss-item"
								:class="row_state(row)"
								:style="{ '--i': i }"
							>
								<div class="ss-item-head">
									<span class="ss-thumb">
										<img v-if="row.image" :src="row.image" alt="" loading="lazy" />
										<Icon v-else name="package" :size="22" />
									</span>
									<span class="ss-card-main">
										<span class="ss-card-title">{{ row.item_name }}</span>
										<span class="ss-card-meta">
											ค้างรับ <b>{{ num(row.pending) }}</b> {{ row.uom }}
											<template v-if="row.received">
												· รับแล้ว {{ num(row.received) }}</template
											>
										</span>
									</span>
									<button
										type="button"
										class="ss-full-btn"
										:class="{
											'is-on':
												row.qty === row.pending - row.rejected_qty && row.qty > 0,
										}"
										@click="fill(row)"
									>
										<Icon name="check" :size="16" :stroke="3" /> ครบ
									</button>
								</div>

								<div class="ss-item-controls">
									<div class="ss-control">
										<span class="ss-control-label">รับเข้า</span>
										<Stepper
											v-model="row.qty"
											:max="row.pending - row.rejected_qty"
											tone="brand"
										/>
									</div>
									<div class="ss-control">
										<span class="ss-control-label">ตีกลับ</span>
										<Stepper
											v-model="row.rejected_qty"
											:max="row.pending - row.qty"
											tone="danger"
										/>
									</div>
								</div>

								<Transition name="ss-expand">
									<div v-if="row.rejected_qty > 0" class="ss-reasons">
										<button
											v-for="r in REASONS"
											:key="r"
											type="button"
											class="ss-reason"
											:class="{ 'is-active': row.reason === r }"
											@click="row.reason = row.reason === r ? '' : r"
										>
											{{ r }}
										</button>
										<input
											v-model="row.reason_text"
											class="ss-input ss-input--sm"
											placeholder="เหตุผลอื่น / รายละเอียด"
										/>
									</div>
								</Transition>
							</div>
						</TransitionGroup>
					</div>
					<aside class="ss-split-side">
						<h2 class="ss-section-title">ข้อมูลการส่ง</h2>
						<div class="ss-form">
							<label class="ss-field">
								<span class="ss-field-label">เลขที่ใบส่งของ</span>
								<input
									v-model="form.delivery_note"
									class="ss-input"
									placeholder="เช่น DN-6811-0045"
								/>
							</label>
							<div class="ss-form-row">
								<label class="ss-field">
									<span class="ss-field-label">ผู้ส่ง / ขนส่ง</span>
									<input
										v-model="form.delivered_by"
										class="ss-input"
										placeholder="ชื่อคนขับ"
									/>
								</label>
								<label class="ss-field">
									<span class="ss-field-label">ทะเบียนรถ</span>
									<input
										v-model="form.vehicle_no"
										class="ss-input"
										placeholder="1กข 1234"
									/>
								</label>
							</div>
							<label class="ss-field">
								<span class="ss-field-label">หมายเหตุ</span>
								<textarea
									v-model="form.remarks"
									class="ss-input"
									rows="2"
									placeholder="ถ้ามี"
								></textarea>
							</label>
							<div class="ss-field">
								<span class="ss-field-label">รูปใบส่งของ / สินค้า</span>
								<PhotoInput v-model="photos" />
							</div>
						</div>
					</aside>
				</div>
			</template>
		</div>

		<Teleport to="#ss-layer">
			<Transition name="ss-bar">
				<div v-if="source" class="ss-bottom-bar">
					<div class="ss-bar-summary">
						<b>รับ {{ accepted_count }}</b> รายการ
						<span v-if="rejected_count" class="ss-text-danger">
							· ตีกลับ {{ rejected_count }}</span
						>
					</div>
					<button
						type="button"
						class="ss-btn ss-btn--primary ss-btn--lg"
						:disabled="!accepted_count && !rejected_count"
						@click="confirm = true"
					>
						ยืนยันรับของ
					</button>
				</div>
			</Transition>
		</Teleport>

		<Sheet :open="confirm" title="ยืนยันรับของ" :subtitle="source?.party" @close="confirm = false">
			<div class="ss-summary-list">
				<div v-for="row in touched" :key="row.row" class="ss-summary-row">
					<span class="ss-summary-name">{{ row.item_name }}</span>
					<span class="ss-summary-qty">
						<b v-if="row.qty">{{ num(row.qty) }}</b>
						<em v-if="row.rejected_qty" class="ss-text-danger"
							>ตีกลับ {{ num(row.rejected_qty) }}</em
						>
						<small>{{ row.uom }}</small>
					</span>
				</div>
			</div>
			<p v-if="!accepted_count" class="ss-note ss-note--warn">
				ไม่มีรายการที่รับเข้า ระบบจะบันทึกการตีกลับไว้ที่
				{{ source?.employer ? "คำขอ" : "ใบสั่งซื้อ" }} อย่างเดียว
			</p>
			<p v-else class="ss-note">
				รับเข้าคลังของโครงการทันที ยอดตีกลับยังค้างที่ใบสั่งซื้อให้ผู้ขายส่งใหม่
			</p>
			<template #footer>
				<button
					type="button"
					class="ss-btn ss-btn--primary ss-btn--block ss-btn--lg"
					:disabled="saving || uploading"
					@click="submit"
				>
					<span v-if="saving" class="ss-spinner"></span>
					<template v-else>{{ uploading ? "รออัปโหลดรูป…" : "บันทึกการรับ" }}</template>
				</button>
			</template>
		</Sheet>
	</div>
</template>

<script setup>
import { computed, inject, reactive, ref } from "vue";
import Icon from "../../components/Icon.vue";
import TopBar from "../../components/TopBar.vue";
import Stepper from "../../components/Stepper.vue";
import Sheet from "../../components/Sheet.vue";
import Skeleton from "../../components/Skeleton.vue";
import PhotoInput from "../../components/PhotoInput.vue";
import { back, call, celebrate, go, num, post, show_error, state, thai_date, vibrate } from "../../api.js";

const REASONS = ["ชำรุด / เสียหาย", "ไม่ตรงสเปก", "ส่งเกิน", "คุณภาพไม่ผ่าน"];
const reload_summary = inject("reload_summary");
const params = state.route.params;

const source = ref(null);
const rows = ref([]);
const photos = ref([]);
const confirm = ref(false);
const saving = ref(false);
const form = reactive({ delivery_note: "", delivered_by: "", vehicle_no: "", remarks: "" });

const touched = computed(() => rows.value.filter((r) => r.qty > 0 || r.rejected_qty > 0));
const accepted_count = computed(() => rows.value.filter((r) => r.qty > 0).length);
const rejected_count = computed(() => rows.value.filter((r) => r.rejected_qty > 0).length);
const uploading = computed(() => photos.value.some((p) => p.uploading));

function row_state(row) {
	if (row.rejected_qty > 0 && !row.qty) return "is-rejected";
	if (row.qty > 0 && row.qty + row.rejected_qty >= row.pending) return "is-complete";
	if (row.qty > 0 || row.rejected_qty > 0) return "is-partial";
	return "";
}

function fill(row) {
	vibrate(10);
	row.qty = row.qty === row.pending - row.rejected_qty ? 0 : row.pending - row.rejected_qty;
}

function fill_all() {
	vibrate(15);
	rows.value.forEach((row) => (row.qty = row.pending - row.rejected_qty));
}

async function load() {
	try {
		const data = await call("get_receipt_source", { doctype: params.doctype, name: params.name });
		rows.value = data.items.map((r) => ({ ...r, qty: 0, rejected_qty: 0, reason: "", reason_text: "" }));
		source.value = data;
	} catch (error) {
		show_error(error);
		back("receive");
	}
}

async function submit() {
	saving.value = true;
	try {
		const result = await post("submit_receipt", {
			doctype: params.doctype,
			name: params.name,
			project: state.project.name,
			items: touched.value.map((r) => ({
				row: r.row,
				qty: r.qty,
				rejected_qty: r.rejected_qty,
				reason: [r.reason, r.reason_text].filter(Boolean).join(" - "),
			})),
			...form,
			files: photos.value.map((p) => p.name).filter(Boolean),
		});
		confirm.value = false;
		reload_summary();
		await celebrate(result.rejected_only ? "บันทึกการตีกลับแล้ว" : "รับของเรียบร้อย", result.name);
		if (result.rejected_only) back("receive");
		else go("receipt", { doctype: result.doctype, name: result.name }, { replace: true });
	} catch (error) {
		show_error(error);
	} finally {
		saving.value = false;
	}
}

load();
</script>
