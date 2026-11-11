<!-- แผงรายละเอียด + อนุมัติ/ไม่อนุมัติของเอกสารที่รออนุมัติ (ชนิดใน KINDS ของ kinds.js) ใช้ร่วมกันทุกที่:
     โมดูลอนุมัติ (ApproveInbox.vue รวมทุกโมดูล) และหน้าของแต่ละโมดูล (เช่น หมวดบุคคล) item = to_item(kind, row ของ get_inbox)
     history = ดูอย่างเดียว / review = false ถ้าผู้ใช้ไม่มีสิทธิ์อนุมัติเอกสารนั้น emit done หลังอนุมัติ/ไม่อนุมัติ -->
<template>
<Sheet
	:open="!!item"
	:title="item?.row.employee_name"
	:subtitle="item && `${item.title} · ${item.row.name}`"
	@close="close"
>
	<template v-if="item">
		<!-- ใบลา -->
		<template v-if="item.kind === 'leave'">
			<div class="ss-facts">
				<div class="ss-fact"><span>ประเภท</span><b>{{ item.row.leave_type }}</b></div>
				<div class="ss-fact"><span>วันที่</span><b>{{ leave_range(item.row) }}</b></div>
				<div class="ss-fact"><span>จำนวน</span><b>{{ days(item.row.total_leave_days) }} วัน</b></div>
				<div v-if="item.row.balance != null" class="ss-fact">
					<span>คงเหลือก่อนลา</span><b>{{ days(item.row.balance) }} วัน</b>
				</div>
				<div v-if="item.row.description" class="ss-fact"><span>เหตุผล</span><b>{{ item.row.description }}</b></div>
				<div class="ss-fact"><span>ส่งเมื่อ</span><b>{{ thai_date(item.row.posting_date, { year: true }) }}</b></div>
			</div>
			<div v-if="item.row.attachments?.length" class="ss-photos">
				<a v-for="f in item.row.attachments" :key="f.name" :href="f.url" target="_blank" class="ss-photo">
					<img :src="f.url" :alt="f.file_name" />
				</a>
			</div>
		</template>

		<!-- ลงเวลา -->
		<template v-else-if="item.kind === 'checkin'">
			<div v-if="!item.row.manual" class="ss-selfie">
				<img v-if="item.row.has_selfie" :src="selfie_url(item.row.name)" alt="รูปเซลฟี่" />
				<div v-else class="ss-selfie-empty"><Icon name="camera" :size="28" /><span>ไม่มีรูปเซลฟี่</span></div>
			</div>
			<div class="ss-facts">
				<div class="ss-fact">
					<span>{{ item.row.log_type === "IN" ? "เข้างาน" : "ออกงาน" }}</span>
					<b>{{ thai_date(item.row.time, { year: true }) }} {{ time_of(item.row.time) }} น.</b>
				</div>
				<div class="ss-fact"><span>เหตุผล</span><b>{{ item.row.reason }}</b></div>
				<template v-if="!item.row.manual">
					<div v-if="item.row.distance != null" class="ss-fact">
						<span>ระยะจากจุดลงเวลา</span><b>{{ num(item.row.distance) }} ม.</b>
					</div>
					<div v-if="item.row.accuracy" class="ss-fact">
						<span>ความแม่นยำ GPS</span><b>±{{ num(item.row.accuracy) }} ม.</b>
					</div>
				</template>
				<div v-else class="ss-fact"><span>ประเภท</span><b>แจ้งลืมลงเวลาออก (ไม่มี GPS/รูป)</b></div>
				<div v-if="item.row.project" class="ss-fact"><span>โครงการ</span><b>{{ item.row.project }}</b></div>
				<div v-if="item.row.review_note" class="ss-fact"><span>หมายเหตุผู้ยืนยัน</span><b>{{ item.row.review_note }}</b></div>
			</div>
		</template>

		<!-- ใบเบิก -->
		<template v-else-if="item.kind === 'advance'">
			<div class="ss-facts">
				<div class="ss-fact"><span>จำนวนเงิน</span><b>{{ money(item.row.advance_amount) }} บาท</b></div>
				<div class="ss-fact"><span>วัตถุประสงค์</span><b>{{ item.row.purpose }}</b></div>
				<div v-if="item.row.required_date" class="ss-fact">
					<span>ต้องการรับเงิน</span><b>{{ thai_date(item.row.required_date, { year: true }) }}</b>
				</div>
				<template v-if="item.row.advance_type === 'Salary Advance'">
					<div v-if="item.row.base_salary != null" class="ss-fact"><span>เงินเดือน</span><b>{{ money(item.row.base_salary) }}</b></div>
					<div v-if="item.row.limit_amount != null" class="ss-fact"><span>วงเงิน</span><b>{{ money(item.row.limit_amount) }}</b></div>
					<div class="ss-fact"><span>หักคืน</span><b>{{ item.row.installments || 1 }} งวด</b></div>
				</template>
				<div v-if="item.row.approved_by" class="ss-fact"><span>ผู้อนุมัติ</span><b>{{ item.row.approved_by }}</b></div>
				<div v-if="item.row.executive_approved_by" class="ss-fact">
					<span>ผู้บริหารอนุมัติ</span><b>{{ item.row.executive_approved_by }}</b>
				</div>
				<div v-if="item.row.reject_reason" class="ss-fact"><span>เหตุผลที่ไม่อนุมัติ</span><b>{{ item.row.reject_reason }}</b></div>
			</div>
			<p v-if="!history && item.row.needs_executive" class="ss-note ss-note--warn">
				เกินวงเงิน: อนุมัติแล้วส่งต่อให้ผู้บริหารอนุมัติอีกขั้น
			</p>
		</template>

		<!-- ใบเคลียร์ / เบิกคืน -->
		<template v-else>
			<Skeleton v-if="!detail" :rows="2" />
			<template v-else>
				<div class="ss-list">
					<div v-for="(r, i) in detail.expenses" :key="i" class="ss-card ss-card--row">
						<a v-if="r.receipt" :href="r.receipt" target="_blank" class="ss-thumb"><img :src="r.receipt" alt="" loading="lazy" /></a>
						<span v-else class="ss-thumb"><Icon name="file" :size="20" /></span>
						<span class="ss-card-main">
							<span class="ss-card-title">{{ r.expense_type }}</span>
							<span class="ss-card-meta">{{ thai_date(r.expense_date, { year: true }) }} · {{ r.description }}</span>
						</span>
						<b class="ss-money">{{ money(r.amount) }}</b>
					</div>
				</div>
				<div class="ss-facts">
					<div class="ss-fact"><span>รวม</span><b>{{ money(detail.total_claimed_amount) }} บาท</b></div>
					<div v-for="a in detail.advances" :key="a.employee_advance" class="ss-fact">
						<span>ตัดเงินสำรองจ่าย {{ a.employee_advance }}</span><b>{{ money(a.allocated_amount) }}</b>
					</div>
					<div v-if="detail.remark" class="ss-fact"><span>หมายเหตุ</span><b>{{ detail.remark }}</b></div>
					<div v-if="detail.reject_reason" class="ss-fact">
						<span>เหตุผลที่ไม่อนุมัติ</span><b>{{ detail.reject_reason }}</b>
					</div>
				</div>
			</template>
		</template>

		<EmployeeContext
			v-if="item.row.employee"
			:employee="item.row.employee"
			:kind="item.kind"
			:from_date="context_dates(item)[0]"
			:to_date="context_dates(item)[1]"
		/>

		<label v-if="!history && can_review" class="ss-field">
			<span class="ss-field-label">เหตุผล (ต้องระบุถ้าไม่อนุมัติ)</span>
			<textarea v-model="reason" class="ss-input" rows="2"></textarea>
		</label>
	</template>
	<template v-if="item && !history" #footer>
		<div class="ss-review-actions">
			<button
				type="button"
				class="ss-btn ss-btn--ghost-danger ss-btn--lg"
				:disabled="busy || !reason.trim()"
				@click="review(false)"
			>
				ไม่อนุมัติ
			</button>
			<button type="button" class="ss-btn ss-btn--primary ss-btn--lg" :disabled="busy" @click="review(true)">
				<span v-if="busy" class="ss-spinner"></span>
				<span>{{ item.row.needs_executive ? "อนุมัติ ส่งผู้บริหาร" : "อนุมัติ" }}</span>
			</button>
		</div>
	</template>
</Sheet>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import Icon from "../components/Icon.vue";
import Skeleton from "../components/Skeleton.vue";
import Sheet from "../components/Sheet.vue";
import EmployeeContext from "../components/EmployeeContext.vue";
import { call, money, num, post, show_error, thai_date, toast } from "../api.js";
import { context_dates, days, KINDS, leave_range, time_of } from "./kinds.js";

const props = defineProps({
	item: { type: Object, default: null },
	history: Boolean,
	// false = ดูอย่างเดียว (ผู้ใช้ไม่มีสิทธิ์อนุมัติเอกสารนี้)
	review_allowed: { type: Boolean, default: true },
});
const emit = defineEmits(["close", "done"]);

const busy = ref(false);
const reason = ref("");
const detail = ref(null);
const can_review = computed(() => props.review_allowed);
const selfie_url = (name) => `/api/method/consbiz.self_service.selfie?name=${encodeURIComponent(name)}`;

watch(
	() => props.item?.key,
	async () => {
		reason.value = "";
		detail.value = null;
		if (props.item?.kind !== "claim") return;
		const key = props.item.key;
		try {
			const result = await call("consbiz.self_advance.get_claim", { name: props.item.row.name });
			if (props.item?.key === key) detail.value = result;
		} catch (error) {
			show_error(error);
		}
	},
	{ immediate: true }
);

function close() {
	if (!busy.value) emit("close");
}

async function review(approve) {
	const { kind, row } = props.item;
	const config = KINDS[kind];
	busy.value = true;
	try {
		const result = await post(config.method, { name: row.name, approve: approve ? 1 : 0, [config.reason]: reason.value });
		toast(
			result === "Pending Executive" ? "อนุมัติแล้ว ส่งต่อผู้บริหาร" : approve ? "อนุมัติแล้ว" : "บันทึกไม่อนุมัติแล้ว",
			"success"
		);
		emit("done", { kind, name: row.name, approve });
	} catch (error) {
		show_error(error);
	} finally {
		busy.value = false;
	}
}
</script>
