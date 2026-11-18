<!-- เงินเดือน (ตกลง 2026-11-17, เดิมหน้า สลิป): ค่าจ้างปัจจุบัน + ที่จะปรับ (Salary Structure Assignment ที่ยังไม่ถึงวัน)
     เงินได้สะสม / ประกันสังคมสะสมของปี (สลิปที่ยืนยันแล้ว) + รายการสลิป กดแล้วดูรายรับ/รายการหัก + PDF
     ปุ่มตา = ซ่อนตัวเลข (จำในเครื่อง) API consbiz.self_home.get_pay / self_service.get_slip -->
<template>
	<div>
		<TopBar title="เงินเดือน" no_project>
			<template #actions>
				<button type="button" class="ss-icon-btn" :aria-label="hidden ? 'แสดงตัวเลข' : 'ซ่อนตัวเลข'" @click="toggle_hidden">
					<Icon :name="hidden ? 'eye' : 'ban'" :size="20" />
				</button>
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
			<Skeleton v-if="data === null" :rows="3" />
			<template v-else>
				<section class="ss-card ss-pay-hero">
					<span class="ss-pay-label">เงินเดือนปัจจุบัน</span>
					<b class="ss-pay-amount">{{ data.current ? amount(data.current.base) : "—" }}<small v-if="data.current"> บาท/เดือน</small></b>
					<span v-if="data.current" class="ss-pay-meta">
						ตั้งแต่ {{ thai_date(data.current.from_date, { year: true }) }}
						<template v-if="data.previous && !hidden">
							· ปรับจาก {{ money(data.previous.base) }} ({{ change_text(data.current.base - data.previous.base) }})
						</template>
					</span>
					<span v-else class="ss-pay-meta">ยังไม่มีข้อมูลค่าจ้าง ติดต่อฝ่ายบุคคล</span>
				</section>

				<div v-for="u in data.upcoming" :key="u.from_date" class="ss-card ss-card--row ss-pay-upcoming">
					<span class="ss-avatar tone-blue"><Icon name="trending" :size="18" /></span>
					<span class="ss-card-main">
						<span class="ss-card-title">ปรับเงินเดือนเป็น {{ amount(u.base) }} บาท</span>
						<span class="ss-card-meta">มีผล {{ thai_date(u.from_date, { year: true }) }}<template v-if="!hidden"> · {{ change_text(u.change) }}</template></span>
					</span>
				</div>

				<h2 class="ss-section-title">สะสมปี {{ data.year + 543 }}</h2>
				<div class="ss-stats ss-stats--3">
					<div class="ss-stat tone-green" style="--i: 0">
						<span class="ss-stat-icon"><Icon name="wallet" :size="20" /></span>
						<span class="ss-stat-value">{{ amount(data.ytd.gross, true) }}</span>
						<span class="ss-stat-label">เงินได้สะสม ({{ data.ytd.slips }} งวด)</span>
					</div>
					<div class="ss-stat tone-green" style="--i: 1">
						<span class="ss-stat-icon"><Icon name="receive" :size="20" /></span>
						<span class="ss-stat-value">{{ amount(data.ytd.net, true) }}</span>
						<span class="ss-stat-label">รับสุทธิสะสม</span>
					</div>
					<div class="ss-stat tone-green" style="--i: 2">
						<span class="ss-stat-icon"><Icon name="shield" :size="20" /></span>
						<span class="ss-stat-value">{{ amount(data.ytd.sso, true) }}</span>
						<span class="ss-stat-label">ประกันสังคมสะสม</span>
					</div>
				</div>
				<p class="ss-note">
					ประกันสังคมที่หักในระบบทั้งหมด {{ amount(data.sso_total) }} บาท
					<template v-if="data.last_year.slips"> · ปี {{ data.year + 542 }} เงินได้ {{ amount(data.last_year.gross) }} บาท</template>
					· นายจ้างสมทบอีกเท่ากัน
				</p>

				<h2 class="ss-section-title">สลิปเงินเดือน</h2>
				<Empty
					v-if="!data.slips.length"
					icon="file"
					title="ยังไม่มีสลิปเงินเดือน"
					text="สลิปจะแสดงเมื่อฝ่ายบุคคลออกสลิปของงวดนั้นแล้ว"
				/>
				<div v-else class="ss-list">
					<button
						v-for="(row, i) in data.slips"
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
						<span class="ss-qty"><b>{{ amount(row.rounded_total || row.net_pay) }}</b><small>บาท</small></span>
					</button>
				</div>
			</template>
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

const data = ref(null);
const HIDE_KEY = "consbiz.self.pay.hidden";
const hidden = ref(read_hidden());

function read_hidden() {
	try {
		return localStorage.getItem(HIDE_KEY) === "1";
	} catch {
		return false;
	}
}
function toggle_hidden() {
	hidden.value = !hidden.value;
	try {
		localStorage.setItem(HIDE_KEY, hidden.value ? "1" : "0");
	} catch {
		// เก็บในเครื่องไม่ได้ = ใช้ได้เฉพาะรอบนี้
	}
}
const amount = (value, short = false) => (hidden.value ? "•••••" : money(value, { short }));
const change_text = (diff) => {
	const pct = data.value?.current?.base ? (diff / (data.value.current.base - diff)) * 100 : 0;
	return `${diff >= 0 ? "+" : "−"}${money(Math.abs(diff))}${pct ? ` (${Math.abs(pct).toFixed(1)}%)` : ""}`;
};
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
		data.value = await call("consbiz.self_home.get_pay");
	} catch (error) {
		show_error(error);
		data.value ??= { current: null, previous: null, upcoming: [], ytd: {}, last_year: {}, slips: [], year: new Date().getFullYear() };
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
