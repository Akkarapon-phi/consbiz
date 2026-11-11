<!-- ข้อมูลประกอบของพนักงานในหน้ารายละเอียดเอกสาร HR (API consbiz.approvals.get_context) ใช้ในโมดูลอนุมัติและหมวดบุคคล
     kind leave/checkin = สิทธิ์วันลา ประวัติลา ใครในโครงการลาชนวัน การเข้างานเดือนนี้ (ผู้อนุมัติที่ดูแลพนักงานคนนั้น)
     kind advance/claim = เงินเดือน วงเงิน ยอดค้างหักคืน ประวัติการเบิก (เฉพาะผู้อนุมัติการเบิก/HR) -->
<template>
	<section v-if="loading || error || ctx" class="ss-emp-context">
		<div class="ss-field-label">ข้อมูลประกอบ</div>
		<Skeleton v-if="loading" :rows="2" />
		<p v-else-if="error" class="ss-note">{{ error }}</p>
		<template v-else-if="ctx">
			<template v-if="ctx.leave">
				<div v-if="ctx.leave.balances.length" class="ss-emp-chips">
					<span v-for="b in ctx.leave.balances" :key="b.leave_type" class="ss-chip">
						{{ b.leave_type }} <b>{{ num(b.remaining) }}</b>/{{ num(b.allocated) }}
					</span>
				</div>
				<p v-else class="ss-note">ยังไม่มีโควตาวันลา (ลาได้แค่ลาไม่รับค่าจ้าง)</p>
				<div v-if="ctx.leave.attendance" class="ss-facts">
					<div class="ss-fact">
						<span>เข้างานเดือนนี้</span>
						<b>
							มา {{ ctx.leave.attendance.present }} · ขาด {{ ctx.leave.attendance.absent }} · ลา {{ ctx.leave.attendance.leave }}
							<template v-if="ctx.leave.attendance.late_count"> · สาย {{ ctx.leave.attendance.late_count }} ครั้ง</template>
						</b>
					</div>
				</div>
				<div v-if="ctx.leave.overlap.length" class="ss-facts">
					<div v-for="(o, i) in ctx.leave.overlap" :key="i" class="ss-fact">
						<span>ลาชนวัน: {{ o.employee_name }}</span>
						<b>{{ range(o.from_date, o.to_date) }} · {{ o.leave_type }}{{ o.status === "Open" ? " (รออนุมัติ)" : "" }}</b>
					</div>
				</div>
				<div v-if="ctx.leave.recent.length" class="ss-facts">
					<div v-for="r in ctx.leave.recent" :key="r.name" class="ss-fact">
						<span>{{ range(r.from_date, r.to_date) }} · {{ r.leave_type }}</span>
						<b>{{ num(r.total_leave_days) }} วัน{{ r.status === "Open" ? " (รออนุมัติ)" : "" }}</b>
					</div>
				</div>
			</template>

			<template v-if="ctx.money">
				<div class="ss-facts">
					<div class="ss-fact"><span>เงินเดือน</span><b>{{ ctx.money.limit.base ? money(ctx.money.limit.base) : "ยังไม่กำหนด" }}</b></div>
					<div class="ss-fact">
						<span>วงเงินเบิกล่วงหน้า ({{ num(ctx.money.limit.percent) }}%)</span>
						<b>ใช้ {{ money(ctx.money.limit.used) }} / {{ money(ctx.money.limit.limit) }}</b>
					</div>
				</div>
				<div v-if="ctx.money.advances.length" class="ss-facts">
					<div v-for="a in ctx.money.advances" :key="a.name" class="ss-fact">
						<span>{{ thai_date(a.posting_date) }} · {{ a.advance_type === "Salary Advance" ? "เงินเดือนล่วงหน้า" : "เงินสำรองจ่าย" }}</span>
						<b>
							{{ money(a.advance_amount) }}
							<template v-if="a.repayment"> · ค้างหัก {{ money(a.repayment.remaining) }}</template>
							<template v-else-if="a.unclaimed"> · ค้างเคลียร์ {{ money(a.unclaimed) }}</template>
							<template v-else-if="a.docstatus === 0"> · {{ a.approval === "Rejected" ? "ไม่อนุมัติ" : "รออนุมัติ" }}</template>
						</b>
					</div>
				</div>
				<p v-else class="ss-note">ยังไม่เคยเบิก</p>
			</template>
		</template>
	</section>
</template>

<script setup>
import { ref, watch } from "vue";
import Skeleton from "./Skeleton.vue";
import { call, money, num, thai_date } from "../api.js";

const props = defineProps({
	employee: { type: String, required: true },
	// leave / checkin / advance / claim
	kind: { type: String, required: true },
	from_date: String,
	to_date: String,
});

const ctx = ref(null);
const loading = ref(false);
const error = ref("");

const range = (a, b) => (a === b ? thai_date(a) : `${thai_date(a)} – ${thai_date(b)}`);

async function load() {
	loading.value = true;
	error.value = "";
	ctx.value = null;
	try {
		ctx.value = await call("consbiz.approvals.get_context", {
			employee: props.employee,
			kind: props.kind,
			from_date: props.from_date,
			to_date: props.to_date,
		});
	} catch (e) {
		// ไม่มีสิทธิ์ดูข้อมูลประกอบ: ไม่แสดง (ไม่ขวางการอนุมัติ)
		error.value = e?.message && !/ไม่มีสิทธิ์/.test(e.message) ? e.message : "";
	} finally {
		loading.value = false;
	}
}

watch(() => [props.employee, props.kind, props.from_date], load, { immediate: true });
</script>
