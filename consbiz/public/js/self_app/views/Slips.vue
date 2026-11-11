<!-- สลิปเงินเดือนของตัวเอง (Salary Slip ที่ Submit แล้ว) กดแล้วดูรายรับ/รายการหัก + PDF (self_service.slip_pdf) -->
<template>
	<div>
		<TopBar title="สลิปเงินเดือน" no_project>
			<template #actions>
				<button
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
			<Skeleton v-if="rows === null" :rows="3" />
			<Empty
				v-else-if="!rows.length"
				icon="file"
				title="ยังไม่มีสลิปเงินเดือน"
				text="สลิปจะแสดงเมื่อฝ่ายบุคคลออกสลิปของงวดนั้นแล้ว"
			/>
			<div v-else class="ss-list">
				<button
					v-for="(row, i) in rows"
					:key="row.name"
					type="button"
					class="ss-card ss-card--row"
					:style="{ '--i': i }"
					@click="open(row)"
				>
					<span class="ss-avatar tone-green"><Icon name="file" :size="18" /></span>
					<span class="ss-card-main">
						<span class="ss-card-title">{{ period(row) }}</span>
						<span class="ss-card-meta">จ่าย {{ thai_date(row.posting_date, { year: true }) }}</span>
					</span>
					<span class="ss-qty"><b>{{ money(row.rounded_total || row.net_pay) }}</b><small>บาท</small></span>
				</button>
			</div>
		</div>

		<Sheet :open="!!slip" :title="slip ? period(slip) : ''" :subtitle="slip?.name" @close="slip = null">
			<Skeleton v-if="slip && !slip.earnings" :rows="2" />
			<template v-else-if="slip">
				<h2 class="ss-section-title">รายรับ</h2>
				<div class="ss-facts">
					<div v-for="r in slip.earnings" :key="r.component" class="ss-fact">
						<span>{{ r.component }}</span><b>{{ money(r.amount) }}</b>
					</div>
					<div class="ss-fact"><span>รวมรายรับ</span><b>{{ money(slip.gross_pay) }}</b></div>
				</div>
				<template v-if="slip.deductions.length">
					<h2 class="ss-section-title">รายการหัก</h2>
					<div class="ss-facts">
						<div v-for="r in slip.deductions" :key="r.component" class="ss-fact">
							<span>{{ r.component }}</span><b>{{ money(r.amount) }}</b>
						</div>
						<div class="ss-fact"><span>รวมรายการหัก</span><b>{{ money(slip.total_deduction) }}</b></div>
					</div>
				</template>
				<div class="ss-facts">
					<div class="ss-fact">
						<span>รับสุทธิ</span><b class="ss-slip-net">{{ money(slip.rounded_total || slip.net_pay) }} บาท</b>
					</div>
					<div class="ss-fact">
						<span>วันทำงาน</span><b>{{ num(slip.payment_days) }} / {{ num(slip.total_working_days) }} วัน</b>
					</div>
				</div>
			</template>
			<template v-if="slip?.pdf_url" #footer>
				<button type="button" class="ss-btn ss-btn--primary ss-btn--block ss-btn--lg" @click="pdf_open = true">
					<Icon name="printer" :size="18" />
					<span>ดู PDF</span>
				</button>
			</template>
		</Sheet>

		<PdfViewer
			:open="pdf_open"
			:url="slip?.pdf_url"
			:name="slip?.name"
			title="สลิปเงินเดือน"
			@close="pdf_open = false"
		/>
	</div>
</template>

<script setup>
import { ref } from "vue";
import Icon from "../../shared/components/Icon.vue";
import TopBar from "../../shared/components/TopBar.vue";
import Skeleton from "../../shared/components/Skeleton.vue";
import Empty from "../../shared/components/Empty.vue";
import Sheet from "../../shared/components/Sheet.vue";
import PdfViewer from "../../shared/components/PdfViewer.vue";
import { call, money, num, show_error, thai_date } from "../../shared/api.js";

const API = "consbiz.self_service.";
const MONTHS = [
	"มกราคม",
	"กุมภาพันธ์",
	"มีนาคม",
	"เมษายน",
	"พฤษภาคม",
	"มิถุนายน",
	"กรกฎาคม",
	"สิงหาคม",
	"กันยายน",
	"ตุลาคม",
	"พฤศจิกายน",
	"ธันวาคม",
];

const rows = ref(null);
const loading = ref(false);
const slip = ref(null);
const pdf_open = ref(false);

// งวดเต็มเดือน = "พฤศจิกายน 2569" ไม่เต็มเดือน = ช่วงวันที่
function period(row) {
	const [y, m, d] = String(row.start_date).split("-").map(Number);
	const end = new Date(y, m, 0).getDate();
	if (d === 1 && row.end_date === `${y}-${String(m).padStart(2, "0")}-${end}`)
		return `${MONTHS[m - 1]} ${y + 543}`;
	return `${thai_date(row.start_date)} – ${thai_date(row.end_date, { year: true })}`;
}

async function load() {
	loading.value = true;
	try {
		rows.value = await call(`${API}get_slips`);
	} catch (error) {
		show_error(error);
		rows.value ??= [];
	} finally {
		loading.value = false;
	}
}
load();

async function open(row) {
	slip.value = { ...row };
	try {
		const detail = await call(`${API}get_slip`, { name: row.name });
		if (slip.value?.name === row.name) slip.value = detail;
	} catch (error) {
		show_error(error);
		slip.value = null;
	}
}
</script>
