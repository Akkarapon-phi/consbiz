<!-- สรุปวันทำงานรายเดือน (หมวด hr ของแอปออฟฟิศ, API consbiz/hr_attendance.py) เฉพาะ HR
     แถว = พนักงาน ช่อง = วัน (สถานะตาม day_state ใน hr_attendance.py) คลิกช่อง = รายละเอียดวัน + ตัดสิน (decide_days)
     ปุ่ม "บันทึก Attendance" = close_period (วันมาทำงาน/ขาดงานถึงเมื่อวาน ต้องตัดสินวันรอตัดสินให้ครบก่อน) -->
<template>
	<div>
		<TopBar title="สรุปวันทำงาน">
			<template #search>
				<HeaderSearch v-if="wide" v-model="txt" placeholder="ค้นหาชื่อพนักงาน ตำแหน่ง แผนก" />
			</template>
			<template #actions>
				<button
					v-if="!wide"
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
			<div v-if="wide" class="ss-list-head">
				<StatusTabs v-model="filter" :options="tabs" />
				<div class="ss-list-tools">
					<span class="hr-month">
						<button type="button" class="ss-icon-btn" aria-label="เดือนก่อน" title="เดือนก่อน" @click="shift(-1)">
							<Icon name="chevron-left" :size="17" />
						</button>
						<DateInput
							v-model="month"
							picker="month"
							variant="tool"
							:max="this_month"
							label="เลือกเดือน"
						/>
						<button
							type="button"
							class="ss-icon-btn"
							aria-label="เดือนถัดไป"
							title="เดือนถัดไป"
							:disabled="month >= this_month"
							@click="shift(1)"
						>
							<Icon name="chevron-right" :size="17" />
						</button>
					</span>
					<ProjectFilter />
					<button
						type="button"
						class="ss-icon-btn"
						:class="{ 'is-spinning': loading }"
						aria-label="โหลดใหม่"
						title="โหลดใหม่"
						@click="load"
					>
						<Icon name="refresh" :size="17" />
					</button>
					<button
						type="button"
						class="ss-btn ss-btn--primary ss-list-create"
						:disabled="busy || !to_close"
						:title="close_hint"
						@click="close_period"
					>
						<Icon name="check" :size="18" :stroke="2.6" />
						<span>บันทึก Attendance{{ to_close ? ` (${num(to_close)})` : "" }}</span>
					</button>
				</div>
			</div>
			<template v-else>
				<div class="hr-month hr-month--mobile">
					<button type="button" class="ss-icon-btn" aria-label="เดือนก่อน" @click="shift(-1)">
						<Icon name="chevron-left" :size="20" />
					</button>
					<DateInput v-model="month" picker="month" :max="this_month" label="เลือกเดือน" />
					<button type="button" class="ss-icon-btn" aria-label="เดือนถัดไป" :disabled="month >= this_month" @click="shift(1)">
						<Icon name="chevron-right" :size="20" />
					</button>
				</div>
				<Segmented v-model="filter" :options="tabs" />
			</template>

			<div v-if="data && data.payroll_based_on !== 'Attendance'" class="ss-banner tone-amber hr-banner">
				<Icon name="alert" :size="20" />
				<div>
					<div class="ss-banner-title">Payroll ยังคิดเงินเดือนตาม{{ data.payroll_based_on === "Leave" ? "ใบลา" : data.payroll_based_on }}</div>
					<div class="ss-banner-text">
						ตั้ง Payroll Settings → Payroll Based On = Attendance แล้ววันขาดงาน/ครึ่งวันที่บันทึกจากหน้านี้จึงหักเงินเดือน
					</div>
				</div>
			</div>

			<Skeleton v-if="data === null" :rows="6" />
			<Empty
				v-else-if="!shown.length"
				icon="users"
				:title="filter === 'flag' ? 'ไม่มีวันที่รอตัดสิน' : 'ไม่มีพนักงาน'"
				:text="filter === 'flag' ? '' : 'พนักงาน Active ของบริษัทนี้ในเดือนที่เลือก'"
			/>

			<!-- จอ ≥ 768: ตารางคน x วัน -->
			<div v-else-if="wide" class="hr-grid-wrap">
				<table class="hr-grid">
					<thead>
						<tr>
							<th class="hr-name">พนักงาน</th>
							<th
								v-for="d in days"
								:key="d.iso"
								class="hr-day"
								:class="{ 'is-weekend': d.weekend, 'is-today': d.iso === data.today }"
							>
								<span>{{ d.day }}</span>
								<small>{{ d.dow }}</small>
							</th>
							<th class="hr-total" title="มาทำงาน (วัน)">มา</th>
							<th class="hr-total" title="ครึ่งวัน">½</th>
							<th class="hr-total" title="ขาดงาน">ขาด</th>
							<th class="hr-total" title="ลา">ลา</th>
							<th class="hr-total" title="รอตัดสิน">รอ</th>
							<th class="hr-total hr-total--min" title="มาสาย (นาที) เข้าหลัง 08:05 นับจาก 08:00">สาย</th>
							<th class="hr-total hr-total--min" title="กลับก่อน 17:00 (นาที)">กลับก่อน</th>
						</tr>
					</thead>
					<tbody>
						<tr v-for="row in shown" :key="row.employee">
							<th class="hr-name" title="ดูทั้งเดือน / เวลาที่ไม่ได้ทำงาน" @click="open_person(row)">
								<span class="ss-cell-main">{{ row.employee_name }}</span>
								<small>{{ row_sub(row) }}</small>
							</th>
							<td
								v-for="d in days"
								:key="d.iso"
								class="hr-cell"
								:class="[`is-${cell_of(row, d.iso).tone}`, { 'is-weekend': d.weekend, 'is-auto': cell_of(row, d.iso).auto }]"
								:title="cell_of(row, d.iso).title"
								@click="open_day(row, d.iso)"
							>
								<span>{{ cell_of(row, d.iso).glyph }}</span>
								<i v-if="row.days[d.iso]?.worked" class="hr-worked"></i>
								<i v-if="lost(row.days[d.iso])" class="hr-late"></i>
							</td>
							<td class="hr-total">{{ row.totals.present || "" }}</td>
							<td class="hr-total">{{ row.totals.half || "" }}</td>
							<td
								class="hr-total"
								:class="{ 'is-red': row.totals.absent }"
								:title="row.totals.waived ? `ขาด/ครึ่งวันที่ไม่หักเงิน ${row.totals.waived} วัน` : ''"
							>
								{{ row.totals.absent || "" }}<small v-if="row.totals.waived" class="hr-excused-count">+{{ row.totals.waived }}</small>
							</td>
							<td class="hr-total">{{ row.totals.leave || "" }}</td>
							<td class="hr-total" :class="{ 'is-amber': row.totals.flag }">{{ row.totals.flag || "" }}</td>
							<td class="hr-total hr-total--min" :title="row.totals.late_count ? `${row.totals.late_count} ครั้ง` : ''">
								{{ row.totals.late_min || "" }}
							</td>
							<td class="hr-total hr-total--min" :title="row.totals.early_count ? `${row.totals.early_count} ครั้ง` : ''">
								{{ row.totals.early_min || "" }}
							</td>
						</tr>
					</tbody>
				</table>
			</div>

			<!-- มือถือ: การ์ดต่อคน (ตัวเลขสรุป) แตะ = ปฏิทินของคนนั้น + รายการวันที่รอตัดสิน -->
			<div v-else class="ss-list">
				<button v-for="row in shown" :key="row.employee" type="button" class="ss-card" @click="open_person(row)">
					<div class="ss-card-head">
						<span class="ss-card-main">
							<span class="ss-card-title">{{ row.employee_name }}</span>
							<span class="ss-card-meta">{{ row_sub(row) }}</span>
						</span>
						<span v-if="row.totals.flag" class="ss-tag tone-amber">รอตัดสิน {{ row.totals.flag }}</span>
						<Icon v-else name="chevron-right" :size="18" />
					</div>
					<div class="hr-counts">
						<span><b>{{ row.totals.present }}</b>มา</span>
						<span><b>{{ row.totals.half }}</b>ครึ่งวัน</span>
						<span :class="{ 'is-red': row.totals.absent }"
							><b>{{ row.totals.absent }}<small v-if="row.totals.waived" class="hr-excused-count">+{{ row.totals.waived }}</small></b>ขาด</span
						>
						<span><b>{{ row.totals.leave }}</b>ลา</span>
					</div>
					<div v-if="row.totals.late_count || row.totals.early_count" class="ss-card-meta">
						สาย {{ row.totals.late_count }} ครั้ง ({{ row.totals.late_min }} นาที) · กลับก่อน {{ row.totals.early_count }} ครั้ง ({{ row.totals.early_min }} นาที)
					</div>
				</button>
			</div>

			<div v-if="wide && data?.rows?.length" class="hr-legend">
				<span v-for="item in LEGEND" :key="item.label" class="hr-legend-item">
					<span class="hr-cell hr-cell--legend" :class="[`is-${item.tone}`, { 'is-auto': item.auto }]"><span>{{ item.glyph }}</span></span>
					{{ item.label }}
				</span>
				<span class="hr-legend-item"><span class="hr-cell hr-cell--legend"><i class="hr-worked"></i></span>ลงเวลาในวันหยุด</span>
				<span class="hr-legend-item"><span class="hr-cell hr-cell--legend"><i class="hr-late"></i></span>สาย / กลับก่อน</span>
			</div>
		</div>

		<Teleport to="#ss-layer">
			<div v-if="!wide && data" class="ss-bottom-bar">
				<button type="button" class="ss-btn ss-btn--primary ss-btn--lg" :disabled="busy || !to_close" @click="close_period">
					<span v-if="busy" class="ss-spinner"></span>
					<span>บันทึก Attendance{{ to_close ? ` (${num(to_close)})` : "" }}</span>
				</button>
			</div>
		</Teleport>

		<ApprovalSheet :item="reviewing" @close="reviewing = null" @done="on_reviewed" />

		<Sheet :open="!!person" :title="person?.employee_name" :subtitle="month_label" @close="person = null">
			<template v-if="person">
				<div class="ss-facts">
					<div class="ss-fact">
						<span>มาสาย</span><b>{{ person.totals.late_count }} ครั้ง · {{ person.totals.late_min }} นาที</b>
					</div>
					<div class="ss-fact">
						<span>กลับก่อน</span><b>{{ person.totals.early_count }} ครั้ง · {{ person.totals.early_min }} นาที</b>
					</div>
					<div v-if="person.totals.waived" class="ss-fact">
						<span>ขาด/ครึ่งวันที่ไม่หักเงิน (ตักเตือน)</span><b>{{ person.totals.waived }} วัน</b>
					</div>
					<template v-if="unpaid">
						<div class="ss-fact">
							<span>ค่าจ้างต่อนาที</span>
							<b>{{ unpaid.base ? `${money(unpaid.per_minute)} บาท (เงินเดือน ÷ 30 ÷ 8 ÷ 60)` : "ยังไม่มีโครงสร้างเงินเดือน" }}</b>
						</div>
						<div v-if="unpaid.existing" class="ss-fact">
							<span>ไม่จ่ายเวลาที่ไม่ได้ทำงานแล้ว</span><b>{{ money(unpaid.existing.amount) }} บาท ({{ unpaid.existing.name }})</b>
						</div>
						<div v-else-if="unpaid.minutes" class="ss-fact">
							<span>ถ้าไม่จ่าย {{ unpaid.minutes }} นาที</span><b>{{ money(unpaid.amount) }} บาท</b>
						</div>
					</template>
				</div>
				<button
					v-if="person.totals.waived"
					type="button"
					class="ss-btn ss-btn--ghost-danger"
					:disabled="busy"
					@click="charge_waived"
				>
					หักเงินวันที่ยกเว้นไว้ {{ person.totals.waived }} วัน
				</button>
				<p class="ss-note">จ่ายค่าจ้างเต็มตามปกติ นาทีสาย/กลับก่อนบันทึกไว้ทางวินัย สายเกินเหตุหรือบ่อยครั้ง HR สั่งไม่จ่ายเวลาที่ไม่ได้ทำงานของเดือนนี้ได้</p>
				<p v-if="unpaid?.slip" class="ss-note">ออกสลิป {{ unpaid.slip }} แล้ว แก้การหักไม่ได้</p>
				<div v-else-if="unpaid && !unpaid.component" class="ss-note hr-howto">
					<b>ยังไม่ได้ตั้งรายการหัก "ไม่จ่ายเวลาที่ไม่ได้ทำงาน" ของบริษัท {{ unpaid.company }}</b>
					<ol>
						<li>
							สร้าง Salary Component ใหม่
							(<a href="/app/salary-component/new" target="_blank">เปิดฟอร์ม</a>): ชื่อ เช่น "หักเวลาที่ไม่ได้ทำงาน",
							Type = <b>Deduction</b>, ตาราง Accounts ใส่บริษัท + บัญชีที่ใช้ลงรายการหัก แล้วบันทึก
						</li>
						<li>
							เปิดฟอร์มบริษัท (<a :href="`/app/company/${encodeURIComponent(unpaid.company)}`" target="_blank">{{ unpaid.company }}</a>)
							หัวข้อ "Self Service: เบิกเงิน" ช่อง <b>รายการหักไม่จ่ายเวลาที่ไม่ได้ทำงาน</b> เลือกรายการจากข้อ 1 แล้วบันทึก
						</li>
						<li>กลับมาหน้านี้ ปิดแล้วเปิดชื่อพนักงานใหม่</li>
					</ol>
					<small>ต้องเป็นผู้ที่แก้ Salary Component / Company ได้ (HR Manager หรือ System Manager)</small>
				</div>
				<template v-else-if="unpaid && !unpaid.existing && unpaid.minutes && unpaid.base">
					<label class="ss-field">
						<span class="ss-field-label">เหตุผล</span>
						<textarea v-model="unpaid_note" class="ss-input" rows="2"></textarea>
					</label>
					<button type="button" class="ss-btn ss-btn--ghost-danger" :disabled="busy || !unpaid_note.trim()" @click="set_unpaid">
						ไม่จ่ายเวลาที่ไม่ได้ทำงาน {{ money(unpaid.amount) }} บาท
					</button>
				</template>
				<button v-else-if="unpaid?.existing" type="button" class="ss-btn ss-btn--soft" :disabled="busy" @click="cancel_unpaid">
					ยกเลิกการไม่จ่าย
				</button>
				<template v-if="flagged_days(person).length">
					<div class="ss-field-label">รอตัดสิน {{ flagged_days(person).length }} วัน</div>
					<div class="ss-list">
						<button
							v-for="iso in flagged_days(person)"
							:key="iso"
							type="button"
							class="ss-card ss-card--row"
							@click="open_day(person, iso, true)"
						>
							<span class="hr-cell is-amber hr-cell--legend"><span>!</span></span>
							<span class="ss-card-main">
								<span class="ss-card-title">{{ thai_date(iso, { year: true }) }}</span>
								<span class="ss-card-meta">{{ person.days[iso].note }}</span>
							</span>
							<Icon name="chevron-right" :size="18" />
						</button>
					</div>
				</template>
				<div class="hr-cal">
					<span v-for="d in DOW" :key="d" class="hr-cal-dow">{{ d }}</span>
					<span v-for="n in lead_blanks" :key="`b${n}`"></span>
					<button
						v-for="d in days"
						:key="d.iso"
						type="button"
						class="hr-cell hr-cal-day"
						:class="[`is-${cell_of(person, d.iso).tone}`, { 'is-auto': cell_of(person, d.iso).auto, 'is-today': d.iso === data.today }]"
						:disabled="cell_of(person, d.iso).tone === 'none'"
						:aria-label="`${d.day} ${cell_of(person, d.iso).title}`"
						@click="open_day(person, d.iso, true)"
					>
						<small>{{ d.day }}</small>
						<span>{{ cell_of(person, d.iso).glyph }}</span>
					</button>
				</div>
				<div class="hr-legend">
					<span v-for="item in LEGEND" :key="item.label" class="hr-legend-item">
						<span class="hr-cell hr-cell--legend" :class="[`is-${item.tone}`, { 'is-auto': item.auto }]"><span>{{ item.glyph }}</span></span>
						{{ item.label }}
					</span>
				</div>
			</template>
		</Sheet>

		<Sheet :open="!!viewing" :title="viewing?.employee_name" :subtitle="viewing ? thai_date(viewing.date, { year: true }) : ''" @close="close_day">
			<Skeleton v-if="viewing && !viewing.cell" :rows="3" />
			<template v-else-if="viewing">
				<div class="ss-facts">
					<div class="ss-fact">
						<span>สถานะ</span>
						<b><span class="ss-tag" :class="`tone-${state_tag(viewing.cell).tone}`">{{ state_tag(viewing.cell).label }}</span></b>
					</div>
					<div v-if="viewing.cell.note" class="ss-fact"><span>หมายเหตุ</span><b>{{ viewing.cell.note }}</b></div>
					<div v-if="viewing.cell.in || viewing.cell.out" class="ss-fact">
						<span>เข้า – ออก</span>
						<b>{{ viewing.cell.in || "—" }} – {{ viewing.cell.out || "—" }}<template v-if="viewing.cell.hours != null"> ({{ viewing.cell.hours }} ชม.)</template></b>
					</div>
					<div v-if="viewing.cell.late" class="ss-fact"><span>มาสาย</span><b>{{ viewing.cell.late }} นาที</b></div>
					<div v-if="viewing.cell.early" class="ss-fact"><span>กลับก่อน</span><b>{{ viewing.cell.early }} นาที</b></div>
					<div v-for="l in viewing.leaves" :key="l.name" class="ss-fact">
						<span>ใบลา {{ l.name }}</span>
						<b>
							{{ l.leave_type }} · {{ LEAVE_STATUS[l.status] || l.status }}
							<button v-if="l.status === 'Open'" type="button" class="ss-link" @click="review('leave', l.name)">พิจารณา</button>
						</b>
					</div>
					<div v-if="viewing.attendance" class="ss-fact">
						<span>Attendance</span><b>{{ viewing.attendance.name }} ({{ STATUS_LABEL[viewing.attendance.status] || viewing.attendance.status }})</b>
					</div>
				</div>

				<div v-if="viewing.logs.length" class="ss-list">
					<div v-for="log in viewing.logs" :key="log.name" class="ss-card ss-card--row">
						<a
							v-if="log.has_selfie"
							:href="selfie_url(log.name)"
							target="_blank"
							class="ss-thumb"
						><img :src="selfie_url(log.name)" alt="รูปเซลฟี่" loading="lazy" /></a>
						<span v-else class="ss-thumb"><Icon :name="log.manual ? 'pen' : 'clock'" :size="20" /></span>
						<span class="ss-card-main">
							<span class="ss-card-title">{{ log.log_type === "IN" ? "เข้างาน" : "ออกงาน" }} {{ time_of(log.time) }} น.</span>
							<span class="ss-card-meta">
								{{ log.manual ? "แจ้งย้อนหลัง" : log.distance != null ? `ห่าง ${num(log.distance)} ม.` : log.device_id || "" }}
								<template v-if="log.reason"> · {{ log.reason }}</template>
							</span>
						</span>
						<button
							v-if="log.approval === 'Pending'"
							type="button"
							class="ss-btn ss-btn--soft"
							@click="review('checkin', log.name)"
						>
							พิจารณา
						</button>
						<span v-else-if="log.approval" class="ss-tag" :class="`tone-${APPROVAL[log.approval].tone}`">{{
							APPROVAL[log.approval].label
						}}</span>
					</div>
				</div>

				<p v-if="viewing.locked" class="ss-note">{{ viewing.locked }}</p>
				<template v-else-if="can_decide">
					<div class="ss-field">
						<span class="ss-field-label">{{ viewing.cell.s === "marked" ? "แก้เป็น" : "บันทึกเป็น" }}</span>
						<Segmented v-model="decision" :options="DECISION_OPTIONS" />
					</div>
					<label v-if="WAIVABLE.includes(decision)" class="ss-toggle" :class="{ 'is-on': waive }">
						<input v-model="waive" type="checkbox" />
						<span class="ss-toggle-track"><span></span></span>
						<span>
							<b>ไม่หักเงิน (ตักเตือน)</b>
							<small>บันทึกว่าขาด/ครึ่งวันไว้ทางวินัย แต่จ่ายค่าจ้างเต็ม หักภายหลังได้จากหน้าของพนักงาน</small>
						</span>
					</label>
					<label class="ss-field">
						<span class="ss-field-label">หมายเหตุ</span>
						<textarea v-model="note" class="ss-input" rows="2"></textarea>
					</label>
					<label v-if="other_flags.length" class="ss-toggle" :class="{ 'is-on': apply_all }">
						<input v-model="apply_all" type="checkbox" />
						<span class="ss-toggle-track"><span></span></span>
						<span>
							<b>ใช้กับทุกวันที่รอตัดสินของคนนี้</b>
							<small>อีก {{ other_flags.length }} วันในเดือนนี้</small>
						</span>
					</label>
				</template>
			</template>
			<template v-if="viewing?.cell && !viewing.locked && can_decide" #footer>
				<button type="button" class="ss-btn ss-btn--ghost" @click="close_day">ยกเลิก</button>
				<button type="button" class="ss-btn ss-btn--primary ss-btn--lg" :disabled="busy || !decision" @click="decide">
					<span v-if="busy" class="ss-spinner"></span>
					<span>บันทึก{{ apply_all ? ` ${other_flags.length + 1} วัน` : "" }}</span>
				</button>
			</template>
		</Sheet>
	</div>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import Icon from "../../../shared/components/Icon.vue";
import TopBar from "../../../shared/components/TopBar.vue";
import Segmented from "../../../shared/components/Segmented.vue";
import Skeleton from "../../../shared/components/Skeleton.vue";
import Empty from "../../../shared/components/Empty.vue";
import Sheet from "../../../shared/components/Sheet.vue";
import DateInput from "../../../shared/components/DateInput.vue";
import ApprovalSheet from "../../../shared/approvals/ApprovalSheet.vue";
import { find_pending } from "../../../shared/approvals/kinds.js";
import StatusTabs from "../../../shared/components/StatusTabs.vue";
import HeaderSearch from "../../../shared/components/HeaderSearch.vue";
import ProjectFilter from "../../../shared/docs/ProjectFilter.vue";
import { matches, use_wide } from "../../../shared/table.js";
import {
	call,
	money,
	num,
	post,
	replace_params,
	scope_args,
	scope_key,
	show_error,
	state,
	thai_date,
	toast,
} from "../../../shared/api.js";

const API = "consbiz.hr_attendance";
// glyph/สีของช่อง (tone = class is-<tone> ใน <style>) auto = ระบบคำนวณ ยังไม่บันทึก Attendance (เส้นประ)
const LEGEND = [
	{ tone: "green", glyph: "✓", label: "มาทำงาน (บันทึกแล้ว)" },
	{ tone: "green", glyph: "✓", label: "มาทำงาน (ยังไม่บันทึก)", auto: true },
	{ tone: "orange", glyph: "½", label: "ครึ่งวัน" },
	{ tone: "red", glyph: "ข", label: "ขาดงาน" },
	{ tone: "waived", glyph: "ข", label: "ขาด/ครึ่งวัน ไม่หักเงิน (ตักเตือน)" },
	{ tone: "blue", glyph: "ล", label: "ลา" },
	{ tone: "amber", glyph: "!", label: "รอตัดสิน" },
	{ tone: "gray", glyph: "ห", label: "วันหยุด" },
	{ tone: "gray", glyph: "ย", label: "หยุดประจำสัปดาห์" },
];
const STATUS_LABEL = {
	Present: "มาทำงาน",
	"Work From Home": "ทำงานนอกสถานที่",
	"Half Day": "ครึ่งวัน",
	Absent: "ขาดงาน",
	"On Leave": "ลา",
};
const DECISION_OPTIONS = [
	{ value: "Present", label: "มาทำงาน" },
	{ value: "Half Day", label: "ครึ่งวัน" },
	{ value: "Absent", label: "ขาดงาน" },
];
// สถานะที่ติ๊กไม่หักเงินได้ (ตรงกับ WAIVABLE ใน hr_attendance.py)
const WAIVABLE = ["Absent", "Half Day"];
const APPROVAL = {
	Pending: { label: "รอยืนยัน", tone: "amber" },
	Approved: { label: "ยืนยันแล้ว", tone: "green" },
	Rejected: { label: "ไม่ยืนยัน", tone: "rose" },
};
const LEAVE_STATUS = { Open: "รออนุมัติ", Approved: "อนุมัติแล้ว", Rejected: "ไม่อนุมัติ", Cancelled: "ยกเลิก" };
const DOW = ["อา", "จ", "อ", "พ", "พฤ", "ศ", "ส"];
// วันที่ระบบสรุปเอง → สถานะ Attendance (ตรงกับ AUTO_STATUS ใน hr_attendance.py)
const AUTO = { present: "Present", absent: "Absent" };

const wide = use_wide();
const data = ref(null);
const loading = ref(false);
const busy = ref(false);
const txt = ref("");
const filter = ref("all");
const now = new Date();
const this_month = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
const month = ref(/^\d{4}-\d{2}$/.test(state.route.params.month || "") ? state.route.params.month : this_month);

const viewing = ref(null);
const decision = ref(null);
const waive = ref(false);
const note = ref("");
const apply_all = ref(false);

const month_label = computed(() =>
	new Date(`${month.value}-01T00:00:00`).toLocaleDateString("th-TH-u-ca-buddhist", { month: "long", year: "numeric" })
);
const days = computed(() => {
	if (!data.value) return [];
	const out = [];
	const end = new Date(`${data.value.end}T00:00:00`);
	for (let d = new Date(`${data.value.start}T00:00:00`); d <= end; d.setDate(d.getDate() + 1)) {
		const iso = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
		out.push({ iso, day: d.getDate(), dow: DOW[d.getDay()], weekend: [0, 6].includes(d.getDay()) });
	}
	return out;
});
const rows = computed(() => data.value?.rows || []);
const tabs = computed(() => [
	{ value: "all", label: "ทั้งหมด", count: rows.value.length },
	{ value: "flag", label: "รอตัดสิน", count: rows.value.filter((r) => r.totals.flag).length },
	{ value: "absent", label: "มีวันขาด", count: rows.value.filter((r) => r.totals.absent).length },
]);
const shown = computed(() =>
	rows.value.filter(
		(r) =>
			(filter.value === "all" || r.totals[filter.value]) &&
			matches(txt.value, r.employee_name, r.employee, r.designation, r.department, r.project)
	)
);
const flagged_total = computed(() => rows.value.reduce((sum, r) => sum + r.totals.flag, 0));
// วันที่ระบบสรุปได้เอง (มาทำงาน/ขาดงาน) ยังไม่ได้บันทึก Attendance
const to_close = computed(() =>
	rows.value.reduce((sum, r) => sum + Object.values(r.days).filter((c) => AUTO[c.s]).length, 0)
);
const close_hint = computed(() =>
	flagged_total.value ? `ยังมี ${flagged_total.value} วันที่รอตัดสิน ตัดสินให้ครบก่อน` : "บันทึกวันมาทำงาน/ครึ่งวัน/ขาดงานถึงเมื่อวาน"
);

const row_sub = (row) =>
	[row.designation, row.project && (data.value.projects[row.project] || row.project)].filter(Boolean).join(" · ");
const flagged_days = (row) => Object.keys(row.days).filter((iso) => row.days[iso].s === "flag");
const time_of = (value) => String(value || "").slice(11, 16);
const selfie_url = (name) => `/api/method/consbiz.self_service.selfie?name=${encodeURIComponent(name)}`;

function cell_of(row, iso) {
	const c = row.days[iso] || { s: "inactive" };
	const hours = c.hours != null ? ` ${c.hours} ชม.` : "";
	const lost_text = [c.late && `สาย ${c.late} นาที`, c.early && `กลับก่อน ${c.early} นาที`].filter(Boolean).join(" ");
	const times = c.in || c.out ? ` ${c.in || "—"}–${c.out || "—"}${hours}${lost_text ? ` (${lost_text})` : ""}` : "";
	const base = (tone, glyph, label, auto = false) => ({
		tone,
		glyph,
		auto,
		label,
		title: `${label}${times}${c.note ? ` · ${c.note}` : ""}`,
	});
	switch (c.s) {
		case "marked":
			if (c.waived) return base("waived", c.status === "Half Day" ? "½" : "ข", `${STATUS_LABEL[c.status]} ไม่หักเงิน (ตักเตือน)`);
			if (c.status === "Half Day") return base(c.leave_type ? "blue" : "orange", "½", c.leave_type ? `ลาครึ่งวัน (${c.leave_type})` : "ครึ่งวัน");
			if (c.status === "Absent") return base("red", "ข", "ขาดงาน");
			if (c.status === "On Leave") return base("blue", "ล", `ลา (${c.leave_type || ""})`);
			return base("green", "✓", STATUS_LABEL[c.status] || c.status);
		case "present":
			return base("green", "✓", "มาทำงาน (ยังไม่บันทึก)", true);
		case "absent":
			return base("red", "ข", "ขาดงาน (ยังไม่บันทึก)", true);
		case "flag":
			return base("amber", "!", "รอตัดสิน");
		case "holiday":
			return base("gray", "ห", "วันหยุด");
		case "day_off":
			return base("gray", "ย", "หยุดประจำสัปดาห์");
		case "future":
			return base("none", "", "ยังไม่ถึงวัน");
		default:
			return base("none", "–", "ไม่อยู่ในช่วงทำงาน");
	}
}

function state_tag(c) {
	const view = cell_of({ days: { x: c } }, "x");
	const tone = { green: "green", orange: "orange", red: "rose", blue: "blue", amber: "amber", waived: "rose" }[view.tone];
	return { tone: tone || "gray", label: view.label };
}

const viewing_row = computed(() => viewing.value && rows.value.find((r) => r.employee === viewing.value.employee));
const can_decide = computed(() => {
	const s = viewing.value?.cell?.s;
	if (!s || !(s === "flag" || s === "marked" || AUTO[s])) return false;
	// วันลาแก้ที่ใบลา
	const c = viewing.value.cell;
	return !(s === "marked" && (c.leave_type || c.status === "On Leave"));
});
const other_flags = computed(() =>
	viewing.value?.cell?.s === "flag" && viewing_row.value
		? flagged_days(viewing_row.value).filter((iso) => iso !== String(viewing.value.date).slice(0, 10))
		: []
);

// ปฏิทินของคน (มือถือ) เปิดวันแล้วปิดวัน = กลับมาที่ปฏิทิน
const person = ref(null);
const return_to = ref(null);
const unpaid = ref(null);
const unpaid_note = ref("");
// สาย/กลับก่อนในวันที่นับว่ามาทำงาน
const lost = (c) => !!c && (c.late || c.early) && (c.s === "present" || ["Present", "Work From Home"].includes(c.status));

async function load_unpaid(employee) {
	unpaid.value = null;
	try {
		const info = await call(`${API}.get_person`, { employee, month: month.value });
		if (person.value?.employee === employee) unpaid.value = info;
	} catch (error) {
		show_error(error);
	}
}
function open_person(row) {
	person.value = row;
	unpaid_note.value = "";
	load_unpaid(row.employee);
}
async function set_unpaid() {
	busy.value = true;
	try {
		const r = await post(`${API}.set_unpaid_time`, { employee: person.value.employee, month: month.value, note: unpaid_note.value });
		toast(`ไม่จ่ายเวลาที่ไม่ได้ทำงาน ${money(r.amount)} บาท (${r.name})`, "success");
		unpaid_note.value = "";
		await load_unpaid(person.value.employee);
	} catch (error) {
		show_error(error);
	} finally {
		busy.value = false;
	}
}
// ขาดบ่อย/เกินเหตุ: วันที่ยกเว้นไว้ทั้งเดือนบันทึกเป็นสถานะจริง (หักเงิน)
async function charge_waived() {
	if (!confirm(`หักเงินวันที่ยกเว้นไว้ ${person.value.totals.waived} วันของเดือนนี้?`)) return;
	busy.value = true;
	try {
		const r = await post(`${API}.charge_waived`, { employee: person.value.employee, month: month.value });
		toast(`หักเงิน ${r.done.length} วันแล้ว`, "success");
		const employee = person.value.employee;
		await load();
		const row = rows.value.find((x) => x.employee === employee);
		if (row) open_person(row);
	} catch (error) {
		show_error(error);
	} finally {
		busy.value = false;
	}
}

async function cancel_unpaid() {
	busy.value = true;
	try {
		await post(`${API}.cancel_unpaid_time`, { employee: person.value.employee, month: month.value });
		toast("ยกเลิกการไม่จ่ายแล้ว", "success");
		await load_unpaid(person.value.employee);
	} catch (error) {
		show_error(error);
	} finally {
		busy.value = false;
	}
}
const lead_blanks = computed(() => (data.value ? new Date(`${data.value.start}T00:00:00`).getDay() : 0));

function close_day() {
	viewing.value = null;
	if (return_to.value) {
		const row = rows.value.find((r) => r.employee === return_to.value);
		if (row) open_person(row);
	}
	return_to.value = null;
}

async function open_day(row, iso, from_person = false) {
	const c = row.days[iso];
	if (!c || c.s === "future" || c.s === "inactive") return;
	return_to.value = from_person ? row.employee : null;
	person.value = null;
	viewing.value = { employee: row.employee, employee_name: row.employee_name, date: iso };
	decision.value = c.s === "flag" ? c.suggest : AUTO[c.s] || c.status;
	waive.value = !!c.waived;
	note.value = "";
	apply_all.value = false;
	try {
		const detail = await call(`${API}.get_day`, { employee: row.employee, date: iso });
		if (viewing.value?.employee === row.employee && viewing.value.date === iso) viewing.value = detail;
	} catch (error) {
		show_error(error);
		viewing.value = null;
	}
}

// อนุมัติใบลา/ยืนยันการลงเวลาในหน้านี้ (ApprovalSheet ชุดเดียวกับโมดูลอนุมัติ) เสร็จแล้วกลับมาที่วันเดิม
const reviewing = ref(null);
let review_day = null;
async function review(kind, name) {
	try {
		const item = await find_pending(call, kind, name);
		if (!item) return toast("คุณอนุมัติรายการนี้ไม่ได้ (ไม่ได้ดูแลพนักงานคนนี้ หรือเป็นของตัวเอง)", "info");
		review_day = { employee: viewing.value.employee, date: String(viewing.value.date).slice(0, 10) };
		viewing.value = null;
		reviewing.value = item;
	} catch (error) {
		show_error(error);
	}
}
async function on_reviewed() {
	reviewing.value = null;
	await load();
	const row = review_day && rows.value.find((r) => r.employee === review_day.employee);
	if (row) open_day(row, review_day.date);
	review_day = null;
}

async function decide() {
	const dates = [String(viewing.value.date).slice(0, 10), ...(apply_all.value ? other_flags.value : [])];
	busy.value = true;
	try {
		const result = await post(`${API}.decide_days`, {
			employee: viewing.value.employee,
			dates,
			status: decision.value,
			note: note.value,
			waive: waive.value && WAIVABLE.includes(decision.value) ? 1 : 0,
		});
		toast(result.done.length ? `บันทึก Attendance ${result.done.length} วันแล้ว` : "ไม่มีอะไรเปลี่ยน", "success");
		await load();
		close_day();
	} catch (error) {
		show_error(error);
	} finally {
		busy.value = false;
	}
}

async function close_period() {
	if (flagged_total.value) {
		toast(close_hint.value, "warning");
		filter.value = "flag";
		return;
	}
	busy.value = true;
	try {
		const result = await post(`${API}.close_period`, { month: month.value, ...scope_args() });
		toast(
			`บันทึก Attendance ${num(result.created)} วันแล้ว${result.skipped ? ` (ข้าม ${num(result.skipped)} วันที่ออกสลิปแล้ว)` : ""}`,
			"success"
		);
		await load();
	} catch (error) {
		show_error(error);
	} finally {
		busy.value = false;
	}
}

function shift(step) {
	const d = new Date(`${month.value}-01T00:00:00`);
	d.setMonth(d.getMonth() + step);
	const next = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
	if (next > this_month) return;
	month.value = next;
}

async function load() {
	loading.value = true;
	try {
		data.value = await call(`${API}.get_summary_month`, { month: month.value, ...scope_args() });
	} catch (error) {
		show_error(error);
		data.value ??= { rows: [], projects: {} };
	} finally {
		loading.value = false;
	}
}

watch(month, (value) => {
	if (!value || value > this_month) return (month.value = this_month);
	replace_params("hr-attendance", { month: value === this_month ? undefined : value });
	data.value = null;
	load();
});
watch(scope_key, load);
load();
</script>

<style scoped>
.hr-month {
	display: inline-flex;
	align-items: center;
	gap: 4px;
	white-space: nowrap;
}

.hr-month--mobile {
	display: flex;
	justify-content: space-between;
	margin-bottom: 8px;
}
.hr-month--mobile .ss-date {
	flex: 1;
}
.hr-banner {
	margin: 8px 0;
}
.hr-grid-wrap {
	overflow: auto;
	max-height: calc(100vh - 170px);
	background: var(--ss-surface);
	border: 1px solid var(--ss-border);
	border-top: 0;
	border-radius: 0 0 10px 10px;
}
.hr-grid {
	border-collapse: separate;
	border-spacing: 0;
	font-size: var(--ss-fs-sm);
	min-width: 100%;
}
.hr-grid thead th {
	position: sticky;
	top: 0;
	z-index: 2;
	height: 30px;
	background: var(--ss-th-bg, var(--ss-surface-2));
	color: var(--ss-th-fg, var(--ss-muted));
	font-weight: 600;
	text-align: center;
	border-bottom: 1px solid var(--ss-border);
}
.hr-grid .hr-name {
	position: sticky;
	left: 0;
	z-index: 1;
	min-width: 200px;
	max-width: 240px;
	padding: 4px 10px;
	text-align: left;
	font-weight: 500;
	background: var(--ss-surface);
	border-right: 1px solid var(--ss-border);
	border-bottom: 1px solid var(--ss-border);
}
.hr-grid thead .hr-name {
	z-index: 3;
	background: var(--ss-th-bg, var(--ss-surface-2));
}
.hr-grid .hr-name small {
	display: block;
	color: var(--ss-muted);
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
}
.hr-day {
	min-width: 28px;
	line-height: 1.1;
}
.hr-day small {
	display: block;
	font-weight: 400;
	opacity: 0.8;
}
.hr-day.is-weekend,
.hr-grid td.is-weekend {
	background-color: var(--ss-surface-2);
}
.hr-day.is-today {
	box-shadow: inset 0 -2px 0 var(--ss-brand);
}
.hr-cell {
	position: relative;
	height: 28px;
	padding: 2px;
	text-align: center;
	border-bottom: 1px solid var(--ss-border);
	cursor: pointer;
}
.hr-cell > span {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	width: 22px;
	height: 22px;
	border-radius: 6px;
	font-weight: 700;
	color: var(--c);
	background: var(--c-bg);
	border: 1px solid transparent;
}
.hr-cell.is-none {
	cursor: default;
	color: var(--ss-muted);
}
.hr-cell.is-none > span {
	color: var(--ss-muted);
	font-weight: 400;
}
.hr-cell.is-green { --c: #15803d; --c-bg: #dcfce7; }
.hr-cell.is-orange { --c: #c2410c; --c-bg: #ffedd5; }
.hr-cell.is-red { --c: #be123c; --c-bg: #ffe4e6; }
.hr-cell.is-blue { --c: #1d4ed8; --c-bg: #dbeafe; }
.hr-cell.is-amber { --c: #92400e; --c-bg: #fde68a; }
.hr-cell.is-gray { --c: var(--ss-muted); --c-bg: transparent; }
/* ขาด/ครึ่งวันที่ไม่หักเงิน: ตัวแดง กรอบทึบ พื้นใส */
.hr-cell.is-waived { --c: #be123c; --c-bg: transparent; }
.hr-cell.is-waived > span {
	border: 1px solid var(--c);
}
.hr-excused-count {
	margin-left: 2px;
	font-size: var(--ss-fs-sm);
	color: var(--ss-muted);
	font-weight: 500;
}
/* ระบบคำนวณ ยังไม่บันทึก Attendance: กรอบประ พื้นใส */
.hr-cell.is-auto > span {
	background: transparent;
	border: 1px dashed var(--c);
}
.hr-cell:not(.is-none):hover > span {
	outline: 2px solid var(--ss-brand);
	outline-offset: 1px;
}
.hr-grid tbody .hr-name {
	cursor: pointer;
}
.hr-grid tbody .hr-name:hover .ss-cell-main {
	color: var(--ss-brand);
	text-decoration: underline;
}
.hr-howto ol {
	margin: 6px 0;
	padding-left: 20px;
}
.hr-howto li + li {
	margin-top: 4px;
}
.hr-howto a {
	color: var(--ss-brand);
	text-decoration: underline;
}
.hr-total--min {
	min-width: 52px;
}
.hr-late {
	position: absolute;
	left: 3px;
	bottom: 3px;
	width: 5px;
	height: 5px;
	border-radius: 50%;
	background: #d97706;
}
.hr-worked {
	position: absolute;
	right: 3px;
	top: 3px;
	width: 5px;
	height: 5px;
	border-radius: 50%;
	background: var(--ss-brand);
}
.hr-total {
	min-width: 34px;
	padding: 0 4px;
	text-align: center;
	font-weight: 600;
	border-left: 1px solid var(--ss-border);
	border-bottom: 1px solid var(--ss-border);
}
.hr-total.is-red {
	color: #be123c;
}
.hr-total.is-amber {
	color: #92400e;
}
.hr-legend {
	display: flex;
	flex-wrap: wrap;
	gap: 6px 16px;
	margin-top: 10px;
	color: var(--ss-muted);
	font-size: var(--ss-fs-sm);
}
.hr-legend-item {
	display: inline-flex;
	align-items: center;
	gap: 6px;
}
.hr-cell--legend {
	display: inline-flex;
	position: relative;
	width: 24px;
	height: 24px;
	border: 0;
	cursor: default;
}
/* มือถือ: ตัวเลขสรุปในการ์ด + ปฏิทินของคน (ช่องแตะได้ 44px) */
.hr-counts {
	display: grid;
	grid-template-columns: repeat(4, 1fr);
	gap: 6px;
	margin-top: 8px;
	text-align: center;
	color: var(--ss-muted);
	font-size: var(--ss-fs-sm);
}
.hr-counts b {
	display: block;
	color: var(--ss-text);
	font-size: var(--ss-fs-lg, var(--ss-fs));
}
.hr-counts .is-red b {
	color: #be123c;
}
.hr-cal {
	display: grid;
	grid-template-columns: repeat(7, 1fr);
	gap: 4px;
	margin: 12px 0;
}
.hr-cal-dow {
	text-align: center;
	color: var(--ss-muted);
	font-size: var(--ss-fs-sm);
}
.hr-cal-day {
	display: flex;
	flex-direction: column;
	align-items: center;
	gap: 2px;
	height: auto;
	min-height: 52px;
	padding: 4px 0;
	border: 0;
	border-radius: 8px;
	background: none;
	color: var(--ss-text);
}
.hr-cal-day small {
	font-size: var(--ss-fs-sm);
	color: var(--ss-muted);
}
.hr-cal-day > span {
	width: 30px;
	height: 30px;
}
.hr-cal-day.is-today small {
	color: var(--ss-brand);
	font-weight: 700;
}
@media (prefers-color-scheme: dark) {
	.hr-counts .is-red b { color: #fb7185; }
	.hr-cell.is-green { --c: #4ade80; --c-bg: rgba(74, 222, 128, 0.16); }
	.hr-cell.is-orange { --c: #fb923c; --c-bg: rgba(251, 146, 60, 0.16); }
	.hr-cell.is-red { --c: #fb7185; --c-bg: rgba(251, 113, 133, 0.16); }
	.hr-cell.is-blue { --c: #60a5fa; --c-bg: rgba(96, 165, 250, 0.16); }
	.hr-cell.is-amber { --c: #fbbf24; --c-bg: rgba(251, 191, 36, 0.18); }
	.hr-total.is-red { color: #fb7185; }
	.hr-total.is-amber { color: #fbbf24; }
}
</style>
