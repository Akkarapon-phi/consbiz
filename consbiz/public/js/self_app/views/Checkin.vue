<!-- ภาพรวม (หน้าแรกของ Self Service, ตกลง 2026-11-17, view ชื่อเดิม checkin) API consbiz.self_home.get_home / get_month
     ทักทาย + ลงเวลา (กดปุ่ม = กล้องถ่ายสด LiveCamera + GPS พร้อมกัน ยืนยันใน sheet, server ตรวจรัศมีและใช้เวลาของ server
     นอกรัศมี / GPS คลาดเกิน accuracy_limit = ลงได้แต่ต้องมีเหตุผล รอหัวหน้ายืนยัน)
     ตัวเลขเดือน (มาทำงาน/ลา/ขาด/สาย + ของปี) สิ่งที่ควรทำ (ลืมลงเวลาออก, วันขาดที่แจ้งมาทำงานได้, จองกะ, เคลียร์เงิน, สิทธิ์ลาใกล้หมด)
     ปฏิทินเดือน = สถานะชุดเดียวกับหน้าสรุปวันทำงานของ HR (hr_attendance) แตะวัน = เวลาเข้า-ออก รูปเซลฟี่ คำขอ + แจ้งมาทำงาน/แจ้งเวลาออก
     แจ้งมาทำงาน = Attendance Request (ย้อนหลัง request_days วัน) รายการของฉันที่รออนุมัติ และทางลัดไปฟอร์มขอที่ใช้บ่อย -->
<template>
	<div>
		<TopBar title="ภาพรวม" no_project>
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

		<div class="ss-content ss-work-content">
			<header class="ss-work-greeting">
				<div>
					<h1>{{ greeting }}<template v-if="data?.first_name">, {{ data.first_name }}</template></h1>
					<p>
						{{ long_date(clock) }}
						<template v-if="data?.project"> · {{ data.project.project_name || data.project.name }}</template>
					</p>
				</div>
			</header>

			<Skeleton v-if="data === null" :rows="4" />
			<div v-else class="ss-work-grid ss-self-grid">
				<!-- ลงเวลา -->
				<section class="ss-work-card ss-self-clock" :class="{ 'is-out': data.next_log_type === 'OUT' }">
					<div class="ss-work-head">
						<div>
							<span>{{ data.next_log_type === "OUT" ? "กำลังทำงาน" : "ยังไม่ได้เข้างาน" }}</span>
							<strong class="ss-self-time">{{ clock_text }}</strong>
						</div>
						<span class="ss-self-place" :class="{ 'is-danger': !data.location }">
							<Icon name="pin" :size="13" />
							<template v-if="data.location">
								{{ data.location.location_name || data.location.name }} · {{ num(data.location.radius) }} ม.
							</template>
							<template v-else>ยังลงเวลาไม่ได้</template>
						</span>
					</div>
					<dl class="ss-work-facts">
						<div><dt>เข้างานวันนี้</dt><dd>{{ today_summary.first_in || "—" }}</dd></div>
						<div><dt>ออกงานวันนี้</dt><dd>{{ today_summary.last_out || "—" }}</dd></div>
						<div><dt>ชั่วโมงวันนี้</dt><dd>{{ today_summary.hours }}</dd></div>
						<div><dt>สถานะ</dt><dd>{{ today_status }}</dd></div>
					</dl>
					<p v-if="!data.location" class="ss-note ss-note--warn ss-self-issue">{{ data.location_issue }}</p>
					<div class="ss-work-progress-actions ss-self-clock-actions">
						<button
							type="button"
							class="ss-btn ss-btn--primary"
							:disabled="!data.location || busy"
							@click="start"
						>
							<Icon name="camera" :size="18" />
							{{ data.next_log_type === "OUT" ? "ลงเวลาออกงาน" : "ลงเวลาเข้างาน" }}
						</button>
						<button type="button" class="ss-btn ss-btn--soft" @click="open_request(data.today)">
							<Icon name="clipboard-check" :size="16" /> แจ้งมาทำงาน
						</button>
					</div>
				</section>

				<!-- ตัวเลขของเดือน -->
				<section class="ss-work-stats ss-self-stats" aria-label="สรุปการทำงาน">
					<button type="button" class="is-featured" @click="scroll_to_calendar">
						<span>มาทำงาน <i><Icon name="check" :size="15" /></i></span>
						<strong>{{ days_text(totals.present + totals.half / 2) }}</strong>
						<small>{{ month_label }} · ครึ่งวัน {{ totals.half }} · หยุด {{ totals.off }}</small>
					</button>
					<button type="button" @click="go('leave')">
						<span>ลา <i><Icon name="calendar" :size="15" /></i></span>
						<strong>{{ totals.leave }}</strong>
						<small>ปีนี้ {{ data.year.leave_count }} ครั้ง · {{ days_text(data.year.leave_days) }} วัน</small>
					</button>
					<button type="button" @click="absent_action">
						<span>ขาด <i><Icon name="ban" :size="15" /></i></span>
						<strong>{{ totals.absent }}</strong>
						<small>ปีนี้ {{ data.year.absent }} วัน</small>
					</button>
					<button type="button" @click="scroll_to_calendar">
						<span>สาย <i><Icon name="clock" :size="15" /></i></span>
						<strong>{{ totals.late_count }}</strong>
						<small>{{ totals.late_min ? `${num(totals.late_min)} นาที · ` : "" }}ปีนี้ {{ data.year.late_count }} ครั้ง</small>
					</button>
				</section>

				<!-- สิ่งที่ควรทำ -->
				<section class="ss-work-card ss-self-todo">
					<div class="ss-work-head">
						<h2>สิ่งที่ควรทำ</h2>
						<span v-if="todos.length">{{ todos.length }} รายการ</span>
					</div>
					<div v-if="todos.length" class="ss-work-quick-list">
						<button
							v-for="t in todos"
							:key="t.key"
							type="button"
							:class="`is-${t.tone}`"
							:disabled="!t.run"
							@click="t.run?.()"
						>
							<i><Icon :name="t.icon" :size="17" /></i>
							<span><b>{{ t.title }}</b><small>{{ t.note }}</small></span>
							<Icon v-if="t.run" name="chevron-right" :size="15" />
						</button>
					</div>
					<div v-else class="ss-work-empty"><Icon name="check" :size="18" /> เรียบร้อย ไม่มีงานค้าง</div>
				</section>

				<!-- ปฏิทิน -->
				<section ref="calendar_el" class="ss-work-card ss-self-cal">
					<div class="ss-work-head">
						<h2>{{ month_label }}</h2>
						<div class="ss-self-cal-nav">
							<button type="button" class="ss-icon-btn" aria-label="เดือนก่อน" :disabled="month_loading" @click="move_month(-1)">
								<Icon name="chevron-left" :size="18" />
							</button>
							<button
								v-if="cal.month !== this_month"
								type="button"
								class="ss-btn ss-btn--soft ss-self-cal-today"
								:disabled="month_loading"
								@click="load_month(this_month)"
							>
								เดือนนี้
							</button>
							<button
								type="button"
								class="ss-icon-btn"
								aria-label="เดือนถัดไป"
								:disabled="month_loading || cal.month >= this_month"
								@click="move_month(1)"
							>
								<Icon name="chevron-right" :size="18" />
							</button>
						</div>
					</div>
					<div class="ss-self-cal-grid" :class="{ 'is-loading': month_loading }">
						<span v-for="d in DOW" :key="d" class="ss-self-cal-dow">{{ d }}</span>
						<span v-for="n in lead_blanks" :key="`b${n}`"></span>
						<button
							v-for="d in cal_days"
							:key="d.iso"
							type="button"
							class="ss-self-cal-day"
							:class="[`is-${d.view.tone}`, { 'is-today': d.iso === data.today, 'has-request': d.cell?.request }]"
							:disabled="d.view.tone === 'none' && d.iso !== data.today"
							:aria-label="`${d.day} ${d.view.label}`"
							:title="d.view.label"
							@click="open_day(d.iso)"
						>
							<small>{{ d.day }}</small>
							<span>{{ d.view.glyph }}</span>
							<i v-if="d.cell?.late" class="ss-self-cal-late"></i>
						</button>
					</div>
					<div class="ss-self-legend">
						<span v-for="item in legend" :key="item.key" :class="`is-${item.tone}`">
							<i>{{ item.glyph }}</i>{{ item.label }} <b>{{ item.count }}</b>
						</span>
					</div>
				</section>

				<!-- รออนุมัติ -->
				<section class="ss-work-card ss-self-pending">
					<div class="ss-work-head">
						<h2>รออนุมัติ</h2>
						<span v-if="pending.length">{{ pending.length }} รายการ</span>
					</div>
					<div v-if="pending.length" class="ss-work-quick-list">
						<button v-for="p in pending" :key="`${p.kind}:${p.name}`" type="button" @click="p.run()">
							<i><Icon :name="p.icon" :size="17" /></i>
							<span><b>{{ p.title }}</b><small>{{ p.note }}</small></span>
							<b v-if="p.amount != null" class="ss-self-amount">{{ money(p.amount) }}</b>
							<Icon v-else name="chevron-right" :size="15" />
						</button>
					</div>
					<div v-else class="ss-work-empty"><Icon name="inbox" :size="18" /> ไม่มีรายการรออนุมัติ</div>
				</section>

				<!-- ทางลัด -->
				<section class="ss-work-card ss-work-quick">
					<div class="ss-work-head"><h2>ทางลัด</h2></div>
					<div class="ss-work-quick-list ss-self-shortcuts">
						<button v-for="a in SHORTCUTS" :key="a.label" type="button" @click="a.run()">
							<i><Icon :name="a.icon" :size="17" /></i>
							<span><b>{{ a.label }}</b><small>{{ a.note }}</small></span>
							<Icon name="chevron-right" :size="15" />
						</button>
					</div>
				</section>
			</div>
		</div>

		<!-- รายละเอียดวัน -->
		<Sheet
			:open="!!day"
			:title="day ? thai_date(day.iso, { year: true }) : ''"
			:subtitle="day?.view.label"
			@close="day = null"
		>
			<template v-if="day">
				<div class="ss-facts">
					<div class="ss-fact">
						<span>สถานะ</span>
						<b><span class="ss-tag" :class="`tone-${TAG_TONE[day.view.tone] || 'gray'}`">{{ day.view.label }}</span></b>
					</div>
					<div v-if="day.cell?.note" class="ss-fact"><span>หมายเหตุ</span><b>{{ day.cell.note }}</b></div>
					<div v-if="day.cell?.in || day.cell?.out" class="ss-fact">
						<span>เข้า – ออก</span>
						<b>{{ day.cell.in || "—" }} – {{ day.cell.out || "—" }}<template v-if="day.cell.hours != null"> ({{ day.cell.hours }} ชม.)</template></b>
					</div>
					<div v-if="day.cell?.late" class="ss-fact"><span>มาสาย</span><b>{{ day.cell.late }} นาที</b></div>
					<div v-if="day.cell?.early" class="ss-fact"><span>กลับก่อน</span><b>{{ day.cell.early }} นาที</b></div>
				</div>
				<div v-if="day.logs.length" class="ss-list">
					<button
						v-for="(log, i) in day.logs"
						:key="log.name"
						type="button"
						class="ss-card ss-card--row"
						:style="{ '--i': i }"
						@click="viewing = log"
					>
						<span class="ss-avatar" :class="log.log_type === 'IN' ? 'tone-green' : 'tone-gray'">
							<Icon name="log-out" :size="18" :class="{ 'ss-flip': log.log_type === 'IN' }" />
						</span>
						<span class="ss-card-main">
							<span class="ss-card-title">
								{{ log.log_type === "IN" ? "เข้างาน" : "ออกงาน" }}
								<span v-if="APPROVAL[log.approval]" class="ss-tag" :class="`tone-${APPROVAL[log.approval].tone}`">{{
									APPROVAL[log.approval].label
								}}</span>
							</span>
							<span class="ss-card-meta">
								<template v-if="log.manual">แจ้งย้อนหลัง</template>
								<template v-else-if="log.distance != null">ห่าง {{ num(log.distance) }} ม.</template>
							</span>
						</span>
						<span class="ss-qty"><b>{{ time_of(log.time) }}</b><small>น.</small></span>
					</button>
				</div>
				<div v-for="r in day.requests" :key="r.name" class="ss-card ss-card--row">
					<span class="ss-avatar tone-blue"><Icon name="clipboard-check" :size="18" /></span>
					<span class="ss-card-main">
						<span class="ss-card-title">
							แจ้งมาทำงาน
							<span class="ss-tag" :class="`tone-${request_status(r).tone}`">{{ request_status(r).label }}</span>
						</span>
						<span class="ss-card-meta">{{ REQUEST_REASON[r.reason] }} · {{ leave_range(r) }}</span>
						<span v-if="r.review_note" class="ss-card-meta">เหตุผล: {{ r.review_note }}</span>
					</span>
					<button v-if="r.can_delete" type="button" class="ss-link" :disabled="busy" @click="withdraw_request(r)">ถอน</button>
				</div>
			</template>
			<template v-if="day && (day.cell?.can_request || day.missing)" #footer>
				<button
					v-if="day.missing"
					type="button"
					class="ss-btn ss-btn--soft ss-btn--block ss-btn--lg"
					@click="open_missing(day.missing)"
				>
					แจ้งเวลาออก
				</button>
				<button
					v-if="day.cell?.can_request"
					type="button"
					class="ss-btn ss-btn--primary ss-btn--block ss-btn--lg"
					@click="open_request(day.iso)"
				>
					แจ้งมาทำงานวันนี้
				</button>
			</template>
		</Sheet>

		<!-- แจ้งมาทำงาน (Attendance Request) -->
		<Sheet
			:open="!!request"
			title="แจ้งมาทำงาน"
			form
			:subtitle="`กรณีไม่ได้ลงเวลา ส่งให้${data?.approver_name ? ` ${data.approver_name} ` : 'หัวหน้า'}อนุมัติ`"
			@close="request = null"
		>
			<template v-if="request">
				<div class="ss-field">
					<span class="ss-field-label">ประเภท<em>*</em></span>
					<Segmented v-model="request.reason" :options="REASON_OPTIONS" />
				</div>
				<div class="ss-leave-dates">
					<div class="ss-field">
						<span class="ss-field-label">ตั้งแต่วันที่<em>*</em></span>
						<DateInput v-model="request.from_date" :min="request_min" :max="data.today" @change="on_request_from" />
					</div>
					<div class="ss-field">
						<span class="ss-field-label">ถึงวันที่<em>*</em></span>
						<DateInput v-model="request.to_date" :min="request.from_date" :max="data.today" />
					</div>
				</div>
				<label class="ss-toggle" :class="{ 'is-on': request.half_day }">
					<input v-model="request.half_day" type="checkbox" />
					<span class="ss-toggle-track"><span></span></span>
					<span>ทำงานครึ่งวัน</span>
				</label>
				<div v-if="request.half_day && request.from_date !== request.to_date" class="ss-field">
					<span class="ss-field-label">วันที่ทำงานครึ่งวัน</span>
					<DateInput v-model="request.half_day_date" :min="request.from_date" :max="request.to_date" />
				</div>
				<label class="ss-field">
					<span class="ss-field-label">รายละเอียด<em>*</em></span>
					<textarea
						v-model="request.explanation"
						class="ss-input"
						rows="3"
						placeholder="เช่น ไปตรวจงานที่ไซต์ลูกค้า มือถือแบตหมดจึงไม่ได้ลงเวลา"
					></textarea>
				</label>
				<p class="ss-note">แจ้งย้อนหลังได้ไม่เกิน {{ data.request_days }} วัน อนุมัติแล้วนับเป็นวันทำงาน</p>
			</template>
			<template #footer>
				<button
					type="button"
					class="ss-btn ss-btn--primary ss-btn--block ss-btn--lg"
					:disabled="busy || !can_send_request"
					@click="send_request"
				>
					<span v-if="busy" class="ss-spinner"></span>
					<span>ส่งให้หัวหน้าอนุมัติ</span>
				</button>
			</template>
		</Sheet>

		<Sheet
			:open="!!draft"
			:title="draft?.log_type === 'OUT' ? 'ลงเวลาออกงาน' : 'ลงเวลาเข้างาน'"
			:subtitle="data?.location?.location_name || data?.location?.name"
			form
			@close="cancel"
		>
			<div v-if="draft" class="ss-selfie">
				<button v-if="draft.photo" type="button" class="ss-selfie-retake" @click="camera_open = true">
					<img :src="draft.photo" alt="รูปเซลฟี่" />
					<span><Icon name="camera" :size="14" /> ถ่ายใหม่</span>
				</button>
				<button v-else type="button" class="ss-selfie-empty" @click="camera_open = true">
					<Icon name="camera" :size="28" />
					<span>แตะเพื่อถ่ายรูปเซลฟี่</span>
				</button>
			</div>
			<div v-if="draft" class="ss-facts">
				<div class="ss-fact">
					<span>ตำแหน่ง</span>
					<b v-if="draft.gps_error" class="ss-text-danger">{{ draft.gps_error }}</b>
					<b v-else-if="!draft.position"><span class="ss-spinner"></span> กำลังหาตำแหน่ง…</b>
					<b v-else :class="{ 'ss-text-danger': outside }">
						ห่างจุดลงเวลา {{ num(Math.round(draft.distance)) }} ม.
						<small>(ความแม่นยำ ±{{ num(Math.round(draft.position.accuracy)) }} ม.)</small>
					</b>
				</div>
			</div>
			<template v-if="problem">
				<p class="ss-note ss-note--warn">
					<span>{{ problem }} ลงเวลาได้ แต่ต้องให้{{ data.approver_name ? ` ${data.approver_name} ` : "หัวหน้า"
					}}ยืนยันก่อนจึงจะนับเป็นวันทำงาน</span>
				</p>
				<label class="ss-field">
					<span class="ss-field-label">เหตุผล<em>*</em></span>
					<textarea
						v-model="draft.reason"
						class="ss-input"
						rows="2"
						placeholder="เช่น ไปรับของที่ร้านวัสดุก่อนเข้าไซต์"
					></textarea>
				</label>
			</template>
			<template #footer>
				<button
					v-if="draft?.gps_error"
					type="button"
					class="ss-btn ss-btn--soft ss-btn--block ss-btn--lg"
					@click="locate"
				>
					หาตำแหน่งอีกครั้ง
				</button>
				<button
					v-else
					type="button"
					class="ss-btn ss-btn--primary ss-btn--block ss-btn--lg"
					:disabled="busy || !draft?.photo || !draft?.position || (problem && !draft.reason?.trim())"
					@click="submit"
				>
					<span v-if="busy" class="ss-spinner"></span>
					<span>{{ problem ? "ส่งให้หัวหน้ายืนยัน" : "ยืนยันลงเวลา" }}</span>
				</button>
			</template>
		</Sheet>

		<LiveCamera
			:open="camera_open"
			title="ถ่ายรูปเซลฟี่"
			:max="SELFIE_MAX"
			:quality="SELFIE_QUALITY"
			@capture="on_capture"
			@close="camera_open = false"
		/>

		<Sheet
			:open="!!missing"
			title="แจ้งเวลาออกงาน"
			form
			:subtitle="missing && `${thai_date(missing.date, { year: true })} · เข้างาน ${time_of(missing.check_in)} น.`"
			@close="missing = null"
		>
			<template v-if="missing">
				<label class="ss-field">
					<span class="ss-field-label">เวลาออกงาน<em>*</em></span>
					<input v-model="missing.time" class="ss-input" type="time" />
				</label>
				<label class="ss-field">
					<span class="ss-field-label">เหตุผลที่ลืมลงเวลาออก<em>*</em></span>
					<textarea v-model="missing.reason" class="ss-input" rows="2" placeholder="เช่น แบตมือถือหมด"></textarea>
				</label>
				<p class="ss-note">
					ส่งให้{{ data.approver_name ? ` ${data.approver_name} ` : "หัวหน้า" }}ยืนยัน แจ้งย้อนหลังได้ไม่เกิน 7 วัน
				</p>
			</template>
			<template #footer>
				<button
					type="button"
					class="ss-btn ss-btn--primary ss-btn--block ss-btn--lg"
					:disabled="busy || !missing?.time || !missing?.reason?.trim()"
					@click="send_missing"
				>
					<span v-if="busy" class="ss-spinner"></span>
					<span>ส่งให้หัวหน้ายืนยัน</span>
				</button>
			</template>
		</Sheet>

		<Sheet
			:open="!!viewing"
			:title="viewing?.log_type === 'IN' ? 'เข้างาน' : 'ออกงาน'"
			:subtitle="viewing && `${thai_date(viewing.time, { year: true })} · ${time_of(viewing.time)} น.`"
			@close="viewing = null"
		>
			<div v-if="viewing && !viewing.manual" class="ss-selfie">
				<img v-if="viewing.has_selfie" :src="selfie_url(viewing.name)" alt="รูปเซลฟี่" />
				<div v-else class="ss-selfie-empty">
					<Icon name="camera" :size="28" />
					<span>{{ viewing.purged ? "รูปถูกลบตามระยะเวลาเก็บแล้ว" : "ไม่มีรูปเซลฟี่" }}</span>
				</div>
			</div>
			<div v-if="viewing" class="ss-facts">
				<div v-if="viewing.distance != null" class="ss-fact">
					<span>ระยะจากจุดลงเวลา</span><b>{{ num(viewing.distance) }} ม.</b>
				</div>
				<div v-if="APPROVAL[viewing.approval]" class="ss-fact">
					<span>การยืนยัน</span>
					<b><span class="ss-tag" :class="`tone-${APPROVAL[viewing.approval].tone}`">{{
						APPROVAL[viewing.approval].label
					}}</span></b>
				</div>
				<div v-if="viewing.reason" class="ss-fact"><span>เหตุผล</span><b>{{ viewing.reason }}</b></div>
				<div v-if="viewing.review_note" class="ss-fact">
					<span>หมายเหตุผู้ยืนยัน</span><b>{{ viewing.review_note }}</b>
				</div>
				<div v-if="viewing.shift" class="ss-fact"><span>กะ</span><b>{{ viewing.shift }}</b></div>
				<div class="ss-fact"><span>เลขที่</span><b>{{ viewing.name }}</b></div>
			</div>
		</Sheet>
	</div>
</template>

<script setup>
import { computed, inject, onBeforeUnmount, ref } from "vue";
import Icon from "../../shared/components/Icon.vue";
import TopBar from "../../shared/components/TopBar.vue";
import Skeleton from "../../shared/components/Skeleton.vue";
import Sheet from "../../shared/components/Sheet.vue";
import Segmented from "../../shared/components/Segmented.vue";
import DateInput from "../../shared/components/DateInput.vue";
import LiveCamera from "../../shared/components/LiveCamera.vue";
import {
	call,
	celebrate,
	go,
	money,
	num,
	post,
	relative_date,
	show_error,
	thai_date,
	toast,
	vibrate,
} from "../../shared/api.js";
import { TYPE } from "../../shared/approvals/status.js";
import { leave_range, REQUEST_REASON } from "../../shared/approvals/kinds.js";

const API = "consbiz.self_service.";
const HOME = "consbiz.self_home.";
// เซลฟี่: ด้านยาว 480px คุณภาพ 0.6 (~30-50 KB) ตกลงกับผู้ใช้ 2026-11-11
const SELFIE_MAX = 480;
const SELFIE_QUALITY = 0.6;
const APPROVAL = {
	Pending: { label: "รอยืนยัน", tone: "amber" },
	Approved: { label: "ยืนยันแล้ว", tone: "green" },
	Rejected: { label: "ไม่ยืนยัน", tone: "rose" },
};
const THAI_DAYS = ["อาทิตย์", "จันทร์", "อังคาร", "พุธ", "พฤหัสบดี", "ศุกร์", "เสาร์"];
const MONTHS = ["มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน", "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"];
const DOW = ["อา", "จ", "อ", "พ", "พฤ", "ศ", "ส"];
// โทนของช่องปฏิทิน → สีป้าย (ss-tag)
const TAG_TONE = { green: "green", orange: "amber", blue: "blue", red: "rose", amber: "amber", gray: "gray" };
const REASON_OPTIONS = Object.entries(REQUEST_REASON).map(([value, label]) => ({ value, label }));
const SHORTCUTS = [
	{ label: "ขอลา", note: "ลาป่วย ลากิจ พักร้อน", icon: "calendar", run: () => go("leave", { action: "new" }) },
	{ label: "แจ้งมาทำงาน", note: "กรณีไม่ได้ลงเวลา", icon: "clipboard-check", run: () => open_request() },
	{ label: "จองกะ", note: "เลือกวันเสาร์/อาทิตย์ที่มาทำงาน", icon: "sun", run: () => go("dayoff") },
	{ label: "เบิกเงินเดือนล่วงหน้า", note: "หักคืนจากเงินเดือน", icon: "wallet", run: () => go("advances", { action: "Salary Advance" }) },
	{ label: "เบิกทดรองจ่าย", note: "รับเงินก่อน แล้วเคลียร์ด้วยบิล", icon: "calculator", run: () => go("advances", { action: "Expense Advance" }) },
	{ label: "เบิกสำรองจ่าย", note: "จ่ายเองไปก่อน ส่งบิลเบิกคืน", icon: "receive", run: () => go("advances", { action: "reimburse" }) },
	{ label: "เงินเดือน / สลิป", note: "ยอดสะสม ประกันสังคม", icon: "file", run: () => go("pay") },
];

const reload_summary = inject("reload_summary");
const data = ref(null);
const loading = ref(false);
const busy = ref(false);
const camera_open = ref(false);
const draft = ref(null);
const viewing = ref(null);

// นาฬิกา: เวลาของเครื่อง ปรับตามส่วนต่างกับ server (เวลาที่บันทึกจริงใช้ของ server)
const offset = ref(0);
const clock = ref(new Date());
const timer = setInterval(() => (clock.value = new Date(Date.now() + offset.value)), 1000);
onBeforeUnmount(() => clearInterval(timer));
const pad = (n) => String(n).padStart(2, "0");
const clock_text = computed(() => `${pad(clock.value.getHours())}:${pad(clock.value.getMinutes())}`);
const long_date = (d) =>
	`วัน${THAI_DAYS[d.getDay()]}ที่ ${thai_date(`${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`, { year: true })}`;
const greeting = computed(() => {
	const h = clock.value.getHours();
	return h < 12 ? "สวัสดีตอนเช้า" : h < 17 ? "สวัสดีตอนบ่าย" : "สวัสดีตอนเย็น";
});
const time_of = (value) => String(value || "").slice(11, 16);
const selfie_url = (name) => `/api/method/${API}selfie?name=${encodeURIComponent(name)}`;
const days_text = (value) => {
	const n = Number(value) || 0;
	return Number.isInteger(n) ? String(n) : n.toFixed(1);
};

const today_summary = computed(() => {
	const today = data.value?.today;
	const logs = (data.value?.logs || [])
		.filter((l) => String(l.time).slice(0, 10) === today && l.approval !== "Rejected")
		.reverse();
	const ins = logs.filter((l) => l.log_type === "IN");
	const outs = logs.filter((l) => l.log_type === "OUT");
	// ชั่วโมง = ผลรวมช่วงเข้า → ออกถัดไป (ช่วงที่ยังไม่ออกนับถึงตอนนี้)
	let ms = 0;
	let since = null;
	for (const log of logs) {
		const t = new Date(String(log.time).replace(" ", "T")).getTime();
		if (log.log_type === "IN") since ??= t;
		else if (since != null) {
			ms += t - since;
			since = null;
		}
	}
	if (since != null) ms += clock.value.getTime() - since;
	const minutes = Math.max(0, Math.floor(ms / 60000));
	return {
		first_in: ins.length ? time_of(ins[0].time) : "",
		last_out: outs.length ? time_of(outs[outs.length - 1].time) : "",
		hours: minutes ? `${Math.floor(minutes / 60)}:${pad(minutes % 60)}` : "—",
		pending: logs.some((l) => l.approval === "Pending"),
	};
});
const today_status = computed(() => {
	const cell = data.value?.calendar?.days?.[data.value.today];
	if (cell?.s === "day_off" || cell?.s === "holiday") return "วันหยุด";
	if (today_summary.value.pending) return "รอหัวหน้ายืนยัน";
	if (!today_summary.value.first_in) return "ยังไม่ลงเวลา";
	return data.value.next_log_type === "OUT" ? "อยู่ระหว่างทำงาน" : "ออกงานแล้ว";
});

async function load() {
	loading.value = true;
	try {
		data.value = await call(`${HOME}get_home`, { month: cal.value?.month });
		cal.value = data.value.calendar;
		offset.value = new Date(String(data.value.now).replace(" ", "T")).getTime() - Date.now();
		reload_summary?.("self");
	} catch (error) {
		show_error(error);
		data.value ??= {
			logs: [],
			location: null,
			next_log_type: "IN",
			missing_out: [],
			calendar: { month: this_month, days: {}, totals: {}, logs: [], requests: [] },
			year: {},
			pending: [],
			suggestions: [],
			today: this_month + "-01",
			request_days: 7,
		};
		cal.value ??= data.value.calendar;
	} finally {
		loading.value = false;
	}
}

// ---------------------------------------------------------------- ปฏิทินเดือน

const now = new Date();
const this_month = `${now.getFullYear()}-${pad(now.getMonth() + 1)}`;
const cal = ref(null);
const month_loading = ref(false);
const calendar_el = ref(null);
const totals = computed(() => ({ present: 0, half: 0, off: 0, leave: 0, absent: 0, flag: 0, late_count: 0, late_min: 0, ...(cal.value?.totals || {}) }));
const month_label = computed(() => {
	const [y, m] = (cal.value?.month || this_month).split("-").map(Number);
	return `${MONTHS[m - 1]} ${y + 543}`;
});
const cal_days = computed(() => {
	const [y, m] = (cal.value?.month || this_month).split("-").map(Number);
	const count = new Date(y, m, 0).getDate();
	return Array.from({ length: count }, (_, i) => {
		const iso = `${y}-${pad(m)}-${pad(i + 1)}`;
		const cell = cal.value?.days?.[iso];
		return { iso, day: i + 1, cell, view: cell_view(cell) };
	});
});
const lead_blanks = computed(() => {
	const [y, m] = (cal.value?.month || this_month).split("-").map(Number);
	return new Date(y, m - 1, 1).getDay();
});

// สถานะของช่อง (ตรงกับ cell_of ใน HrAttendance.vue แต่ข้อความสำหรับพนักงาน)
function cell_view(c) {
	const v = (tone, glyph, label) => ({ tone, glyph, label });
	if (!c) return v("none", "", "");
	switch (c.s) {
		case "marked": {
			const waived = c.waived ? " (ไม่หักเงิน)" : "";
			if (c.status === "Half Day")
				return c.leave_type ? v("blue", "½", `ลาครึ่งวัน (${c.leave_type})`) : v("orange", "½", `ครึ่งวัน${waived}`);
			if (c.status === "Absent") return v("red", "ข", `ขาดงาน${waived}`);
			if (c.status === "On Leave") return v("blue", "ล", `ลา${c.leave_type ? ` (${c.leave_type})` : ""}`);
			if (c.status === "Work From Home") return v("green", "✓", "ทำงานที่บ้าน");
			return v("green", "✓", "มาทำงาน");
		}
		case "present":
			return v("green", "✓", "มาทำงาน");
		case "absent":
			return v("red", "ข", "ขาดงาน (ไม่มีการลงเวลา)");
		case "flag":
			return v("amber", "!", "รอตรวจสอบ");
		case "holiday":
			return v("gray", "ห", c.worked ? "วันหยุด (มาทำงาน)" : "วันหยุด");
		case "day_off":
			return v("gray", "ย", c.worked ? "วันหยุดประจำสัปดาห์ (มาทำงาน)" : "วันหยุดประจำสัปดาห์");
		default:
			return v("none", "", c.s === "future" ? "ยังไม่ถึงวัน" : "");
	}
}
const legend = computed(() => [
	{ key: "present", tone: "green", glyph: "✓", label: "มาทำงาน", count: totals.value.present },
	{ key: "half", tone: "orange", glyph: "½", label: "ครึ่งวัน", count: totals.value.half },
	{ key: "off", tone: "gray", glyph: "ย", label: "หยุด", count: totals.value.off },
	{ key: "leave", tone: "blue", glyph: "ล", label: "ลา", count: totals.value.leave },
	{ key: "absent", tone: "red", glyph: "ข", label: "ขาด", count: totals.value.absent },
	{ key: "flag", tone: "amber", glyph: "!", label: "รอตรวจสอบ", count: totals.value.flag },
]);

async function load_month(month) {
	month_loading.value = true;
	try {
		cal.value = await call(`${HOME}get_month`, { month });
	} catch (error) {
		show_error(error);
	} finally {
		month_loading.value = false;
	}
}
function move_month(step) {
	const [y, m] = cal.value.month.split("-").map(Number);
	const d = new Date(y, m - 1 + step, 1);
	load_month(`${d.getFullYear()}-${pad(d.getMonth() + 1)}`);
}
function scroll_to_calendar() {
	calendar_el.value?.scrollIntoView({ behavior: "smooth", block: "start" });
}

// ---------------------------------------------------------------- รายละเอียดวัน

const day = ref(null);
async function open_day(iso) {
	if (cal.value?.month !== iso.slice(0, 7)) await load_month(iso.slice(0, 7));
	const cell = cal.value?.days?.[iso];
	day.value = {
		iso,
		cell,
		view: cell_view(cell),
		logs: (cal.value?.logs || []).filter((l) => String(l.time).slice(0, 10) === iso).reverse(),
		requests: (cal.value?.requests || []).filter((r) => r.from_date <= iso && iso <= r.to_date),
		missing: (data.value?.missing_out || []).find((m) => m.date === iso),
	};
}
function request_status(r) {
	if (r.docstatus === 1) return { label: "อนุมัติแล้ว", tone: "green" };
	if (r.approval === "Rejected") return { label: "ไม่อนุมัติ", tone: "rose" };
	return { label: "รออนุมัติ", tone: "amber" };
}

// ---------------------------------------------------------------- สิ่งที่ควรทำ / รออนุมัติ

const todos = computed(() =>
	(data.value?.suggestions || []).map((s, i) => {
		const key = `${s.kind}:${i}`;
		switch (s.kind) {
			case "missing_out":
				return { key, tone: "amber", icon: "alert", title: `ยังไม่ได้ลงเวลาออก ${relative_date(s.date)}`, note: `เข้างาน ${time_of(s.check_in)} น. · แตะเพื่อแจ้งเวลาออก`, run: () => open_missing(s) };
			case "absent":
				return {
					key,
					tone: "rose",
					icon: "clipboard-check",
					title: `ขาดงาน ${s.dates.length} วัน ที่ยังแจ้งมาทำงานได้`,
					note: `${s.dates.map((d) => thai_date(d)).join(", ")} · มาทำงานแต่ไม่ได้ลงเวลา แจ้งได้ภายใน ${data.value.request_days} วัน`,
					run: () => open_request(s.dates[0]),
				};
			case "overdue_clearing":
				return { key, tone: "rose", icon: "calculator", title: `เงินทดรองจ่ายเลยกำหนดเคลียร์ ${s.count} ใบ`, note: `กำหนด ${thai_date(s.due_date, { year: true })} · ส่งบิลเคลียร์`, run: () => go("advances") };
			case "book_shift":
				return { key, tone: "blue", icon: "sun", title: "ยังไม่ได้จองกะสัปดาห์หน้า", note: `สัปดาห์ ${thai_date(s.week_start)} · เลือกวันเสาร์หรืออาทิตย์ที่มาทำงาน`, run: () => go("dayoff") };
			case "leave_expiring":
				return { key, tone: "blue", icon: "calendar", title: `${s.leave_type} เหลือ ${days_text(s.remaining)} วัน`, note: `ใช้ได้ถึง ${thai_date(s.to_date, { year: true })}`, run: () => go("leave", { action: "new" }) };
			default:
				return { key, tone: "rose", icon: "pin", title: "ยังลงเวลาไม่ได้", note: s.text };
		}
	})
);
const pending = computed(() =>
	(data.value?.pending || []).map((p) => {
		const base = { kind: p.kind, name: p.name, amount: null };
		const range = p.to_date && p.to_date !== String(p.date).slice(0, 10) ? `${thai_date(p.date)} – ${thai_date(p.to_date, { year: true })}` : thai_date(p.date, { year: true });
		switch (p.kind) {
			case "leave":
				return { ...base, icon: "calendar", title: `ลา${p.title}`, note: `${range} · ${days_text(p.days)} วัน`, run: () => go("leave") };
			case "checkin":
				return {
					...base,
					icon: "clock",
					title: p.manual ? "แจ้งลืมลงเวลาออก" : "ลงเวลานอกพื้นที่",
					note: `${p.log_type === "IN" ? "เข้า" : "ออก"} ${thai_date(p.date)} ${time_of(p.date)} น.`,
					run: () => open_day(String(p.date).slice(0, 10)),
				};
			case "attendance":
				return { ...base, icon: "clipboard-check", title: `แจ้งมาทำงาน · ${REQUEST_REASON[p.reason] || ""}`, note: range, run: () => open_day(String(p.date).slice(0, 10)) };
			case "advance":
				return { ...base, icon: "wallet", title: TYPE[p.advance_type] || "ใบเบิก", note: thai_date(p.date, { year: true }), amount: p.amount, run: () => go("advances") };
			default:
				return { ...base, icon: "receive", title: p.clearing ? "เคลียร์เงินทดรองจ่าย" : "เบิกสำรองจ่าย", note: thai_date(p.date, { year: true }), amount: p.amount, run: () => go("advances", {}) };
		}
	})
);
function absent_action() {
	const s = (data.value?.suggestions || []).find((x) => x.kind === "absent");
	if (s) open_request(s.dates[0]);
	else scroll_to_calendar();
}

// ---------------------------------------------------------------- แจ้งมาทำงาน

const request = ref(null);
const request_min = computed(() => {
	const d = new Date(`${data.value?.today}T00:00:00`);
	d.setDate(d.getDate() - (data.value?.request_days || 7));
	return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
});
const can_send_request = computed(() => {
	const r = request.value;
	return r && r.reason && r.from_date && r.to_date && r.to_date >= r.from_date && r.explanation?.trim();
});
function open_request(date) {
	const iso = date || data.value?.today;
	day.value = null;
	request.value = { reason: "On Duty", from_date: iso, to_date: iso, half_day: false, half_day_date: iso, explanation: "" };
}
function on_request_from(value) {
	if (!request.value.to_date || request.value.to_date < value) request.value.to_date = value;
	request.value.half_day_date = value;
}
async function send_request() {
	const r = request.value;
	busy.value = true;
	try {
		await post(`${HOME}request_attendance`, {
			from_date: r.from_date,
			to_date: r.to_date,
			reason: r.reason,
			explanation: r.explanation,
			half_day: r.half_day ? 1 : 0,
			half_day_date: r.from_date === r.to_date ? r.from_date : r.half_day_date,
		});
		request.value = null;
		celebrate("ส่งแจ้งมาทำงานแล้ว", "รอหัวหน้าอนุมัติ");
		await load();
	} catch (error) {
		show_error(error);
	} finally {
		busy.value = false;
	}
}
async function withdraw_request(r) {
	busy.value = true;
	try {
		await post(`${HOME}delete_attendance_request`, { name: r.name });
		day.value = null;
		toast("ถอนคำขอแล้ว", "success");
		await load();
	} catch (error) {
		show_error(error);
	} finally {
		busy.value = false;
	}
}


// ---------------------------------------------------------------- ลงเวลา

function distance_m(a, b) {
	// สูตรเดียวกับ hrms.hr.utils.get_distance_between_coordinates (แสดงผลเท่านั้น server ตรวจซ้ำ)
	const p = Math.PI / 180;
	const x =
		0.5 -
		Math.cos((b.latitude - a.latitude) * p) / 2 +
		(Math.cos(a.latitude * p) * Math.cos(b.latitude * p) * (1 - Math.cos((b.longitude - a.longitude) * p))) / 2;
	return 2 * 6371 * Math.asin(Math.sqrt(x)) * 1000;
}

// เหตุที่ต้องให้หัวหน้ายืนยัน (ตรงกับ needs_approval_reason ใน self_service.py, server ตรวจซ้ำ)
const problem = computed(() => {
	const d = draft.value;
	const location = data.value?.location;
	if (!d?.position || !location) return "";
	if (d.distance > location.radius)
		return `อยู่นอกพื้นที่ลงเวลา ห่าง ${num(Math.round(d.distance))} ม. (ไม่เกิน ${num(location.radius)} ม.)`;
	if (d.position.accuracy > data.value.accuracy_limit)
		return `GPS คลาดเคลื่อน ±${num(Math.round(d.position.accuracy))} ม.`;
	return "";
});
const outside = computed(() => !!problem.value);

function start() {
	draft.value = { log_type: data.value.next_log_type, photo: null, position: null, gps_error: "", reason: "" };
	camera_open.value = true;
	locate();
}

function locate() {
	if (!draft.value) return;
	draft.value.gps_error = "";
	draft.value.position = null;
	if (!navigator.geolocation) {
		draft.value.gps_error = "อุปกรณ์นี้ไม่รองรับ GPS";
		return;
	}
	navigator.geolocation.getCurrentPosition(
		(pos) => {
			if (!draft.value) return;
			const position = {
				latitude: pos.coords.latitude,
				longitude: pos.coords.longitude,
				accuracy: pos.coords.accuracy,
			};
			draft.value.position = position;
			draft.value.distance = distance_m(data.value.location, position);
		},
		(error) => {
			if (!draft.value) return;
			draft.value.gps_error =
				error.code === error.PERMISSION_DENIED
					? "ไม่ได้รับอนุญาตให้ใช้ตำแหน่ง เปิดสิทธิ์ตำแหน่งของเบราว์เซอร์แล้วลองใหม่"
					: "หาตำแหน่งไม่ได้ ลองออกไปที่โล่งแล้วลองใหม่";
		},
		{ enableHighAccuracy: true, timeout: 20000, maximumAge: 0 }
	);
}

function on_capture(photo) {
	camera_open.value = false;
	if (draft.value) draft.value.photo = photo;
}

function cancel() {
	if (busy.value) return;
	draft.value = null;
	camera_open.value = false;
}

async function submit() {
	const d = draft.value;
	busy.value = true;
	try {
		const result = await post(`${API}check_in`, {
			log_type: d.log_type,
			latitude: d.position.latitude,
			longitude: d.position.longitude,
			accuracy: d.position.accuracy,
			photo: d.photo,
			reason: problem.value ? d.reason : undefined,
		});
		draft.value = null;
		vibrate(30);
		celebrate(
			d.log_type === "IN" ? "ลงเวลาเข้างานแล้ว" : "ลงเวลาออกงานแล้ว",
			result.pending ? `${time_of(result.time)} น. · รอหัวหน้ายืนยัน` : `${time_of(result.time)} น.`
		);
		await load();
	} catch (error) {
		show_error(error);
	} finally {
		busy.value = false;
	}
}

// ---------------------------------------------------------------- ลืมลงเวลาออก

const missing = ref(null);
function open_missing(m) {
	day.value = null;
	missing.value = { ...m, time: "17:00", reason: "" };
}
async function send_missing() {
	busy.value = true;
	try {
		await post(`${API}request_checkout`, {
			date: missing.value.date,
			time: missing.value.time,
			reason: missing.value.reason,
		});
		missing.value = null;
		toast("ส่งแจ้งเวลาออกให้หัวหน้ายืนยันแล้ว", "success");
		await load();
	} catch (error) {
		show_error(error);
	} finally {
		busy.value = false;
	}
}
load();
</script>
