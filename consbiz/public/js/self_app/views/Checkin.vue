<!-- ลงเวลาเข้า-ออกงาน: กดปุ่ม = เปิดกล้องถ่ายสด (LiveCamera, เลือกไฟล์ไม่ได้) + ขอตำแหน่ง GPS พร้อมกัน แล้วยืนยันใน sheet
     รูป 480px JPEG 0.6 ส่งพร้อมพิกัดในคำขอเดียว server ตรวจรัศมีจุดลงเวลาและใช้เวลาของ server
     นอกรัศมี / GPS คลาดเกิน accuracy_limit = ลงได้แต่ต้องมีเหตุผล แล้วรอหัวหน้ายืนยัน (โมดูลอนุมัติ หน้า approve)
     ลืมลงเวลาออก (ย้อนหลังไม่เกิน 7 วัน) = แถบเตือนบนหน้า แจ้งเวลาออก + เหตุผล รอหัวหน้ายืนยัน
     ประวัติ 31 วัน จัดกลุ่มตามวัน กดรายการ = ดูรูปเซลฟี่ (ลบอัตโนมัติเมื่อสลิปงวดนั้นผ่านไป 90 วัน) -->
<template>
	<div>
		<TopBar title="ลงเวลา" no_project>
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
			<Skeleton v-if="data === null" :rows="3" />
			<template v-else>
				<section class="ss-card ss-clock" :class="{ 'is-out': data.next_log_type === 'OUT' }">
					<div class="ss-clock-date">{{ long_date(clock) }}</div>
					<div class="ss-clock-time">{{ clock_text }}</div>
					<div class="ss-clock-place">
						<Icon name="pin" :size="14" />
						<span v-if="data.location">
							{{ data.location.location_name || data.location.name }}
							<small v-if="data.location.radius">· รัศมี {{ num(data.location.radius) }} ม.</small>
						</span>
						<span v-else class="ss-text-danger">{{ data.location_issue }}</span>
					</div>
					<button
						type="button"
						class="ss-btn ss-btn--primary ss-btn--block ss-btn--lg ss-clock-btn"
						:disabled="!data.location || busy"
						@click="start"
					>
						<Icon name="camera" :size="20" />
						<span>{{ data.next_log_type === "OUT" ? "ลงเวลาออกงาน" : "ลงเวลาเข้างาน" }}</span>
					</button>
				</section>

				<button
					v-for="m in data.missing_out"
					:key="m.date"
					type="button"
					class="ss-card ss-card--row ss-missing-out"
					@click="open_missing(m)"
				>
					<span class="ss-avatar tone-amber"><Icon name="alert" :size="18" /></span>
					<span class="ss-card-main">
						<span class="ss-card-title">ยังไม่ได้ลงเวลาออก {{ relative_date(m.date) }}</span>
						<span class="ss-card-meta">เข้างาน {{ time_of(m.check_in) }} น. · แตะเพื่อแจ้งเวลาออก</span>
					</span>
					<Icon name="chevron-right" :size="18" />
				</button>

				<div class="ss-stats ss-stats--3">
					<div class="ss-stat tone-green" style="--i: 0">
						<span class="ss-stat-icon"><Icon name="log-out" :size="20" class="ss-flip" /></span>
						<span class="ss-stat-value">{{ today_summary.first_in || "—" }}</span>
						<span class="ss-stat-label">เข้างานวันนี้</span>
					</div>
					<div class="ss-stat tone-green" style="--i: 1">
						<span class="ss-stat-icon"><Icon name="log-out" :size="20" /></span>
						<span class="ss-stat-value">{{ today_summary.last_out || "—" }}</span>
						<span class="ss-stat-label">ออกงานวันนี้</span>
					</div>
					<div class="ss-stat tone-green" style="--i: 2">
						<span class="ss-stat-icon"><Icon name="clock" :size="20" /></span>
						<span class="ss-stat-value">{{ today_summary.hours }}</span>
						<span class="ss-stat-label">ชั่วโมงวันนี้</span>
					</div>
				</div>

				<h2 class="ss-section-title">ประวัติ 31 วัน</h2>
				<Empty
					v-if="!days.length"
					icon="clock"
					title="ยังไม่มีการลงเวลา"
					text="กดปุ่มด้านบนเพื่อลงเวลาเข้างาน"
				/>
				<template v-for="day in days" :key="day.date">
					<div class="ss-day">{{ relative_date(day.date) }}</div>
					<div class="ss-list">
						<button
							v-for="(log, i) in day.logs"
							:key="log.name"
							type="button"
							class="ss-card ss-card--row"
							:style="{ '--i': i }"
							@click="open_log(log)"
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
									<template v-if="log.shift"> · {{ log.shift }}</template>
								</span>
							</span>
							<span class="ss-qty"><b>{{ time_of(log.time) }}</b><small>น.</small></span>
						</button>
					</div>
				</template>
			</template>
		</div>

		<Sheet
			:open="!!draft"
			:title="draft?.log_type === 'OUT' ? 'ลงเวลาออกงาน' : 'ลงเวลาเข้างาน'"
			:subtitle="data?.location?.location_name || data?.location?.name"
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
import Empty from "../../shared/components/Empty.vue";
import Sheet from "../../shared/components/Sheet.vue";
import LiveCamera from "../../shared/components/LiveCamera.vue";
import {
	call,
	celebrate,
	num,
	post,
	relative_date,
	show_error,
	thai_date,
	toast,
	vibrate,
} from "../../shared/api.js";

const API = "consbiz.self_service.";
// เซลฟี่: ด้านยาว 480px คุณภาพ 0.6 (~30-50 KB) ตกลงกับผู้ใช้ 2026-11-11
const SELFIE_MAX = 480;
const SELFIE_QUALITY = 0.6;
const APPROVAL = {
	Pending: { label: "รอยืนยัน", tone: "amber" },
	Approved: { label: "ยืนยันแล้ว", tone: "green" },
	Rejected: { label: "ไม่ยืนยัน", tone: "rose" },
};
const THAI_DAYS = ["อาทิตย์", "จันทร์", "อังคาร", "พุธ", "พฤหัสบดี", "ศุกร์", "เสาร์"];

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
const clock_text = computed(
	() => `${pad(clock.value.getHours())}:${pad(clock.value.getMinutes())}:${pad(clock.value.getSeconds())}`
);
const long_date = (d) =>
	`วัน${THAI_DAYS[d.getDay()]}ที่ ${thai_date(
		`${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`,
		{ year: true }
	)}`;
const time_of = (value) => String(value || "").slice(11, 16);
const selfie_url = (name) => `/api/method/${API}selfie?name=${encodeURIComponent(name)}`;

const days = computed(() => {
	const out = [];
	for (const log of data.value?.logs || []) {
		const date = String(log.time).slice(0, 10);
		let day = out.find((d) => d.date === date);
		if (!day) out.push((day = { date, logs: [] }));
		day.logs.push(log);
	}
	return out;
});

const today_summary = computed(() => {
	const today = data.value && String(data.value.now).slice(0, 10);
	const logs = (days.value.find((d) => d.date === today)?.logs || []).slice().reverse();
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
	};
});

async function load() {
	loading.value = true;
	try {
		data.value = await call(`${API}get_checkin_data`);
		offset.value = new Date(String(data.value.now).replace(" ", "T")).getTime() - Date.now();
		reload_summary?.("self");
	} catch (error) {
		show_error(error);
		data.value ??= { logs: [], location: null, next_log_type: "IN" };
	} finally {
		loading.value = false;
	}
}
load();

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

function open_log(log) {
	viewing.value = log;
}

// ---------------------------------------------------------------- ลืมลงเวลาออก

const missing = ref(null);
function open_missing(m) {
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
</script>
