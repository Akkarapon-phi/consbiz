<!-- กะ (กลุ่มเวลาทำงานของหมวดบุคคล, API consbiz/hr_shifts.py, ตกลง 2026-11-17) แท็บ:
     ตารางกะ = พนักงาน x 7 วันของสัปดาห์ (กะของวัน / หยุด / ลา ชุดเดียวกับหน้าเวลาทำงาน) เลือกคนหรือแตะช่อง → กำหนดกะเป็นช่วง (Shift Assignment)
     ประเภทกะ = Shift Type (เวลาเข้า-ออก พัก ผ่อนผันสาย) + กะเริ่มต้นของบริษัท
     จุดลงเวลา = Shift Location ทั้งหมด + ใครใช้ แก้พิกัด/รัศมีในที่ (CheckinLocation.vue in_place)
     สาย/ชั่วโมงทำงานในหน้าเวลาทำงานคิดตามกะของแต่ละวัน (hr_attendance.shift_of) -->
<template>
	<div>
		<TopBar title="กะ" />

		<div class="ss-content">
			<ListHead
				v-model="tab"
				:tabs="TABS"
				:loading="loading"
				:create="tab === 'types' ? 'เพิ่มกะ' : undefined"
				:search="tab === 'board' ? txt : undefined"
				search_placeholder="ค้นหาชื่อ"
				@update:search="txt = $event"
				@refresh="load"
				@create="open_type(null)"
			>
				<template v-if="tab === 'board'" #filters>
					<div class="hr-week-nav">
						<button type="button" class="ss-icon-btn" aria-label="สัปดาห์ก่อน" @click="move(-7)">
							<Icon name="chevron-left" :size="18" />
						</button>
						<b>{{ week_label }}</b>
						<button type="button" class="ss-icon-btn" aria-label="สัปดาห์ถัดไป" @click="move(7)">
							<Icon name="chevron-right" :size="18" />
						</button>
						<button v-if="week !== this_week" type="button" class="ss-btn ss-btn--soft ss-list-create" @click="week = this_week">
							สัปดาห์นี้
						</button>
					</div>
					<SelectBox v-model="project" :options="project_options" class="hr-shift-project" />
				</template>
			</ListHead>

			<!-- จอ ≥768: เนื้อหาทุกแท็บอยู่ในการ์ดต่อจากหัวรายการ (ListCard) -->
			<ListCard :on="wide">
			<Skeleton v-if="data === null" :rows="6" />

			<!-- ตารางกะ -->
			<template v-else-if="tab === 'board'">
				<p class="hr-shift-note">
					วันที่ไม่ได้กำหนดกะใช้กะประจำของพนักงาน ถ้าไม่มีใช้กะเริ่มต้นของบริษัท
					({{ data.company_shift || `ปกติ ${data.default_hours}` }}) เลือกพนักงานหรือแตะช่องเพื่อกำหนดกะ
				</p>
				<Empty v-if="!rows.length" icon="users" title="ไม่มีพนักงาน" />
				<div v-else-if="wide" class="hr-shift-grid-wrap ss-list-scroll">
					<table class="hr-shift-grid">
						<thead>
							<tr>
								<th class="hr-shift-check">
									<input type="checkbox" :checked="all_checked" aria-label="เลือกทั้งหมด" @change="toggle_all" />
								</th>
								<th class="hr-shift-person">พนักงาน</th>
								<th v-for="d in days" :key="d.iso" :class="{ 'is-today': d.iso === data.today, 'is-weekend': d.weekend }">
									{{ d.dow }} <small>{{ d.day }}</small>
								</th>
							</tr>
						</thead>
						<tbody>
							<tr v-for="r in rows" :key="r.employee" :class="{ 'is-selected': selected.has(r.employee) }">
								<td class="hr-shift-check">
									<input type="checkbox" :checked="selected.has(r.employee)" :aria-label="r.employee_name" @change="toggle(r.employee)" />
								</td>
								<td class="hr-shift-person">
									<b>{{ r.employee_name }}</b>
									<small>{{ project_name(r.project) || "ไม่ประจำโครงการ" }}<template v-if="r.default_shift"> · ประจำ {{ r.default_shift }}</template></small>
								</td>
								<td v-for="d in days" :key="d.iso" class="hr-shift-cell">
									<button type="button" :class="`is-${cell(r, d.iso).tone}`" :title="cell(r, d.iso).title" @click="open_assign([r.employee], d.iso)">
										{{ cell(r, d.iso).text }}
									</button>
								</td>
							</tr>
						</tbody>
					</table>
				</div>
				<div v-else class="ss-list">
					<div v-for="r in rows" :key="r.employee" class="ss-card hr-shift-card" :class="{ 'is-selected': selected.has(r.employee) }">
						<label class="hr-shift-card-head">
							<input type="checkbox" :checked="selected.has(r.employee)" @change="toggle(r.employee)" />
							<span>
								<b>{{ r.employee_name }}</b>
								<small>{{ project_name(r.project) || "ไม่ประจำโครงการ" }}</small>
							</span>
						</label>
						<div class="hr-shift-week">
							<button
								v-for="d in days"
								:key="d.iso"
								type="button"
								class="hr-shift-cell"
								:class="`is-${cell(r, d.iso).tone}`"
								:title="cell(r, d.iso).title"
								@click="open_assign([r.employee], d.iso)"
							>
								<small>{{ d.dow }}</small>
								<span>{{ cell(r, d.iso).short }}</span>
							</button>
						</div>
					</div>
				</div>
			</template>

			<!-- ประเภทกะ -->
			<template v-else-if="tab === 'types'">
				<p class="hr-shift-note">
					สาย = เข้าหลังเวลาเข้า + ผ่อนผัน (นับนาทีจากเวลาเข้า) ชั่วโมงทำงานนับเฉพาะในเวลากะ หักเวลาพัก
					ไม่ได้ตั้งกะเริ่มต้น = 08:00-17:00 พักเที่ยง 12:00-13:00 ผ่อนผัน 5 นาที
				</p>
				<Empty v-if="!data.types.length" icon="sun" title="ยังไม่มีประเภทกะ" text="กด เพิ่มกะ เพื่อสร้างกะแรก" />
				<div v-else class="hr-type-grid hr-in-card">
					<section v-for="t in data.types" :key="t.name" class="ss-work-card hr-type">
						<div class="hr-type-head">
							<i class="hr-type-dot" :style="{ background: color_of(t.color) }"></i>
							<b>{{ t.name }}</b>
							<span v-if="t.name === data.company_shift" class="ss-tag tone-blue">กะเริ่มต้นบริษัท</span>
							<span v-if="!t.usable" class="ss-tag tone-rose">ใช้ไม่ได้</span>
						</div>
						<div class="hr-type-time">{{ t.start || "--:--" }} – {{ t.end || "--:--" }}</div>
						<dl class="hr-type-facts">
							<div><dt>พัก</dt><dd>{{ t.break_start ? `${t.break_start}–${t.break_end}` : "ไม่มี" }}</dd></div>
							<div><dt>ชั่วโมงงาน</dt><dd>{{ t.hours != null ? `${t.hours} ชม.` : "—" }}</dd></div>
							<div><dt>ผ่อนผันสาย</dt><dd>{{ t.grace }} นาที</dd></div>
							<div><dt>ใช้อยู่</dt><dd>{{ t.default_people + t.assigned_people }} คน</dd></div>
						</dl>
						<p v-if="t.usable && !t.break_start" class="hr-type-warn">ไม่มีเวลาพัก: ชั่วโมงทำงานจะไม่หักพักเที่ยง</p>
						<div class="hr-type-actions">
							<button type="button" class="ss-btn ss-btn--soft" @click="open_type(t)"><Icon name="pen" :size="14" /> แก้ไข</button>
							<button v-if="t.usable && t.name !== data.company_shift" type="button" class="ss-btn ss-btn--ghost" :disabled="busy" @click="set_company_shift(t.name)">
								ตั้งเป็นกะเริ่มต้น
							</button>
							<button v-else-if="t.name === data.company_shift" type="button" class="ss-btn ss-btn--ghost" :disabled="busy" @click="set_company_shift(null)">
								เลิกใช้เป็นกะเริ่มต้น
							</button>
						</div>
					</section>
				</div>
			</template>

			<!-- จุดลงเวลา -->
			<template v-else>
				<p class="hr-shift-note">จุดที่ใช้ร่วมกันแก้ที่นี่มีผลกับทุกโครงการ/พนักงานที่ใช้ เลือกจุดให้โครงการที่ฟอร์มโครงการ (หมวดข้อมูลหลัก)</p>
				<section class="ss-work-card hr-loc-new">
					<b>จุดใหม่</b>
					<CheckinLocation :model-value="null" kind="md-projects" label="" @saved="load_locations" />
				</section>
				<Skeleton v-if="locations === null" :rows="3" />
				<Empty v-else-if="!locations.length" icon="pin" title="ยังไม่มีจุดลงเวลา" />
				<div v-else class="hr-type-grid hr-in-card">
					<section v-for="l in locations" :key="l.name" class="ss-work-card hr-type">
						<div class="hr-type-head">
							<Icon name="pin" :size="16" />
							<b>{{ l.location_name || l.name }}</b>
							<span v-if="!l.radius || !(l.latitude || l.longitude)" class="ss-tag tone-rose">ยังลงเวลาไม่ได้</span>
						</div>
						<dl class="hr-type-facts">
							<div><dt>รัศมี</dt><dd>{{ l.radius ? `${l.radius} ม.` : "ไม่ได้ตั้ง" }}</dd></div>
							<div><dt>ใช้อยู่</dt><dd>{{ l.projects.length }} โครงการ · {{ l.people.length }} คน</dd></div>
						</dl>
						<p v-if="l.projects.length || l.people.length" class="hr-loc-users">
							{{ [...l.projects, ...l.people].map((x) => x.label).join(", ") }}
						</p>
						<CheckinLocation :model-value="l.name" kind="md-projects" :label="l.location_name" in_place @saved="load_locations" />
					</section>
				</div>
			</template>
			</ListCard>
		</div>

		<!-- แถบล่าง: ทำกับพนักงานที่เลือก -->
		<Teleport to="#ss-layer">
			<div v-if="tab === 'board' && selected.size" class="ss-bottom-bar hr-shift-bar">
				<span>เลือก {{ selected.size }} คน</span>
				<button type="button" class="ss-btn ss-btn--ghost" @click="selected = new Set()">ล้าง</button>
				<button type="button" class="ss-btn ss-btn--soft" @click="open_default([...selected])">กะประจำ</button>
				<button type="button" class="ss-btn ss-btn--primary" @click="open_assign([...selected], days[0].iso)">กำหนดกะเป็นช่วง</button>
			</div>
		</Teleport>

		<!-- กำหนดกะเป็นช่วง -->
		<Sheet :open="!!assign" title="กำหนดกะ" :subtitle="assign && people_label(assign.employees)" form @close="assign = null">
			<template v-if="assign">
				<div class="ss-field">
					<span class="ss-field-label">กะ<em>*</em></span>
					<SelectBox v-model="assign.shift_type" :options="assign_options" />
				</div>
				<div class="ss-leave-dates">
					<div class="ss-field">
						<span class="ss-field-label">ตั้งแต่วันที่<em>*</em></span>
						<DateInput v-model="assign.from_date" />
					</div>
					<div class="ss-field">
						<span class="ss-field-label">ถึงวันที่</span>
						<DateInput v-model="assign.to_date" :min="assign.from_date" clearable placeholder="ไม่มีกำหนด" />
					</div>
				</div>
				<p class="ss-note">
					กะที่กำหนดไว้เดิมในช่วงนี้ถูกแทนที่ ช่วงหลังวันสิ้นสุดคงกะเดิมไว้
					<template v-if="!assign.to_date"> · ไม่ระบุวันสิ้นสุด = ใช้กะนี้ไปเรื่อยๆ</template>
				</p>
			</template>
			<template #footer>
				<button type="button" class="ss-btn ss-btn--primary ss-btn--block ss-btn--lg" :disabled="busy || !assign?.from_date" @click="save_assign">
					<span v-if="busy" class="ss-spinner"></span>
					<span>บันทึก</span>
				</button>
			</template>
		</Sheet>

		<!-- กะประจำ (Employee.default_shift) -->
		<Sheet :open="!!default_form" title="กะประจำ" :subtitle="default_form && people_label(default_form.employees)" form @close="default_form = null">
			<template v-if="default_form">
				<div class="ss-field">
					<span class="ss-field-label">กะประจำ</span>
					<SelectBox v-model="default_form.shift_type" :options="default_options" />
				</div>
				<p class="ss-note">ใช้ทุกวันที่ไม่ได้กำหนดกะเป็นช่วง ไม่ระบุ = ใช้กะเริ่มต้นของบริษัท</p>
			</template>
			<template #footer>
				<button type="button" class="ss-btn ss-btn--primary ss-btn--block ss-btn--lg" :disabled="busy" @click="save_default">
					<span v-if="busy" class="ss-spinner"></span>
					<span>บันทึก</span>
				</button>
			</template>
		</Sheet>

		<!-- ประเภทกะ -->
		<Sheet :open="!!type_form" :title="type_form?.original ? `แก้กะ ${type_form.original}` : 'เพิ่มกะ'" form @close="type_form = null">
			<template v-if="type_form">
				<label v-if="!type_form.original" class="ss-field">
					<span class="ss-field-label">ชื่อกะ<em>*</em></span>
					<input v-model="type_form.name" class="ss-input" placeholder="เช่น กะเช้า, กะบ่าย" />
				</label>
				<div class="ss-leave-dates">
					<label class="ss-field">
						<span class="ss-field-label">เวลาเข้า<em>*</em></span>
						<input v-model="type_form.start" class="ss-input" type="time" />
					</label>
					<label class="ss-field">
						<span class="ss-field-label">เวลาออก<em>*</em></span>
						<input v-model="type_form.end" class="ss-input" type="time" />
					</label>
				</div>
				<div class="ss-leave-dates">
					<label class="ss-field">
						<span class="ss-field-label">เริ่มพัก</span>
						<input v-model="type_form.break_start" class="ss-input" type="time" />
					</label>
					<label class="ss-field">
						<span class="ss-field-label">สิ้นสุดพัก</span>
						<input v-model="type_form.break_end" class="ss-input" type="time" />
					</label>
				</div>
				<div class="ss-leave-dates">
					<label class="ss-field">
						<span class="ss-field-label">ผ่อนผันสาย (นาที)</span>
						<input v-model="type_form.grace" class="ss-input" inputmode="numeric" />
					</label>
					<div class="ss-field">
						<span class="ss-field-label">สี</span>
						<SelectBox v-model="type_form.color" :options="COLOR_OPTIONS" />
					</div>
				</div>
				<p class="ss-note">ชั่วโมงงาน {{ form_hours }} · กะข้ามเที่ยงคืนยังไม่รองรับ</p>
			</template>
			<template #footer>
				<button type="button" class="ss-btn ss-btn--primary ss-btn--block ss-btn--lg" :disabled="busy" @click="save_type">
					<span v-if="busy" class="ss-spinner"></span>
					<span>บันทึกกะ</span>
				</button>
			</template>
		</Sheet>
	</div>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import Icon from "../../../shared/components/Icon.vue";
import TopBar from "../../../shared/components/TopBar.vue";
import Skeleton from "../../../shared/components/Skeleton.vue";
import Empty from "../../../shared/components/Empty.vue";
import Sheet from "../../../shared/components/Sheet.vue";
import SelectBox from "../../../shared/components/SelectBox.vue";
import DateInput from "../../../shared/components/DateInput.vue";
import ListHead from "../../../shared/components/ListHead.vue";
import ListCard from "../../../shared/components/ListCard.vue";
import CheckinLocation from "../master/CheckinLocation.vue";
import { use_wide } from "../../../shared/table.js";
import { call, post, remember_tab, show_error, state, thai_date, toast } from "../../../shared/api.js";

const API = "consbiz.hr_shifts";
const TABS = [
	{ value: "board", label: "ตารางกะ" },
	{ value: "types", label: "ประเภทกะ" },
	{ value: "locations", label: "จุดลงเวลา" },
];
const DOW = ["จ", "อ", "พ", "พฤ", "ศ", "ส", "อา"];
// สีของ Shift Type (ค่าของ Frappe) → สีที่แสดง
const COLORS = { Blue: "#2563eb", Cyan: "#0891b2", Gray: "#64748b", Green: "#16a34a", Orange: "#ea580c", Pink: "#db2777", Purple: "#7c3aed", Red: "#dc2626", Yellow: "#ca8a04" };
const COLOR_OPTIONS = Object.keys(COLORS).map((c) => ({ value: c, label: c }));
const color_of = (c) => COLORS[c] || COLORS.Blue;

const wide = use_wide();
const tab = ref(TABS.some((t) => t.value === state.route.params.tab) ? state.route.params.tab : "board");
const data = ref(null);
const locations = ref(null);
const loading = ref(false);
const busy = ref(false);
const txt = ref("");
const project = ref("");
const selected = ref(new Set());

const pad = (n) => String(n).padStart(2, "0");
const iso = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
function monday(d = new Date()) {
	const x = new Date(d);
	x.setDate(x.getDate() - ((x.getDay() + 6) % 7));
	return iso(x);
}
const this_week = monday();
const week = ref(this_week);
function move(n) {
	const d = new Date(`${week.value}T00:00:00`);
	d.setDate(d.getDate() + n);
	week.value = iso(d);
}
const days = computed(() =>
	Array.from({ length: 7 }, (_, i) => {
		const d = new Date(`${week.value}T00:00:00`);
		d.setDate(d.getDate() + i);
		return { iso: iso(d), day: d.getDate(), dow: DOW[i], weekend: i >= 5 };
	})
);
const week_label = computed(() => `${thai_date(days.value[0].iso)} – ${thai_date(days.value[6].iso, { year: true })}`);

const project_name = (p) => (p && data.value?.projects?.[p]) || p;
const project_options = computed(() => [
	{ value: "", label: "ทุกโครงการ" },
	...Object.entries(data.value?.projects || {}).map(([value, label]) => ({ value, label: label || value })),
]);
const rows = computed(() =>
	(data.value?.rows || []).filter(
		(r) => (!project.value || r.project === project.value) && (!txt.value || r.employee_name.includes(txt.value.trim()))
	)
);
const all_checked = computed(() => rows.value.length && rows.value.every((r) => selected.value.has(r.employee)));
function toggle(employee) {
	const next = new Set(selected.value);
	next.has(employee) ? next.delete(employee) : next.add(employee);
	selected.value = next;
}
function toggle_all() {
	selected.value = all_checked.value ? new Set() : new Set(rows.value.map((r) => r.employee));
}
const people_label = (list) => {
	if (list.length !== 1) return `${list.length} คน`;
	return data.value.rows.find((r) => r.employee === list[0])?.employee_name || list[0];
};

// ช่องของวัน: วันหยุด/ลา ก่อน แล้วจึงกะ
function cell(r, day) {
	const c = r.days[day] || {};
	const shift = c.shift || "";
	const type = data.value.types.find((t) => t.name === shift);
	const time = type ? `${type.start}-${type.end}` : data.value.default_hours;
	if (c.s === "inactive") return { tone: "none", text: "–", short: "–", title: "ยังไม่เริ่มงาน/ลาออก" };
	if (c.s === "holiday") return { tone: "holiday", text: "นักขัตฯ", short: "ห", title: "วันหยุด" };
	if (c.s === "day_off") return { tone: "off", text: "หยุด", short: "ย", title: c.note || "วันหยุดประจำสัปดาห์" };
	if (c.leave_type || c.status === "On Leave") return { tone: "leave", text: "ลา", short: "ล", title: `ลา${c.leave_type ? ` (${c.leave_type})` : ""}` };
	return { tone: shift ? "shift" : "default", text: shift ? `${shift}` : "ปกติ", short: shift ? shift.slice(0, 2) : "ป", title: `${shift || "กะเริ่มต้น"} ${time}` };
}

async function load() {
	loading.value = true;
	try {
		data.value = await call(`${API}.get_shifts`, { week_start: week.value, company: state.company || undefined });
		if (tab.value === "locations") await load_locations();
	} catch (error) {
		show_error(error);
		data.value ??= { rows: [], types: [], projects: {} };
	} finally {
		loading.value = false;
	}
}
async function load_locations() {
	try {
		locations.value = await call(`${API}.get_locations`);
	} catch (error) {
		show_error(error);
		locations.value ??= [];
	}
}

// ---------------------------------------------------------------- กำหนดกะ

const assign = ref(null);
const usable_types = computed(() => (data.value?.types || []).filter((t) => t.usable));
const assign_options = computed(() => [
	{ value: "", label: "ใช้กะประจำ/กะเริ่มต้น (ล้างที่กำหนด)" },
	...usable_types.value.map((t) => ({ value: t.name, label: t.name, description: `${t.start}-${t.end}` })),
]);
const default_options = computed(() => [{ value: "", label: "ไม่ระบุ (กะเริ่มต้นของบริษัท)" }, ...assign_options.value.slice(1)]);
function open_assign(employees, day) {
	const first = data.value.rows.find((r) => r.employee === employees[0]);
	assign.value = { employees, shift_type: first?.days[day]?.shift || usable_types.value[0]?.name || "", from_date: day, to_date: day };
}
async function save_assign() {
	busy.value = true;
	try {
		const a = assign.value;
		await post(`${API}.assign_shift`, { employees: JSON.stringify(a.employees), from_date: a.from_date, to_date: a.to_date || undefined, shift_type: a.shift_type || undefined });
		assign.value = null;
		selected.value = new Set();
		toast("บันทึกกะแล้ว", "success");
		await load();
	} catch (error) {
		show_error(error);
	} finally {
		busy.value = false;
	}
}

const default_form = ref(null);
function open_default(employees) {
	const first = data.value.rows.find((r) => r.employee === employees[0]);
	default_form.value = { employees, shift_type: first?.default_shift || "" };
}
async function save_default() {
	busy.value = true;
	try {
		const f = default_form.value;
		await post(`${API}.set_default_shift`, { employees: JSON.stringify(f.employees), shift_type: f.shift_type || undefined });
		default_form.value = null;
		selected.value = new Set();
		toast("บันทึกกะประจำแล้ว", "success");
		await load();
	} catch (error) {
		show_error(error);
	} finally {
		busy.value = false;
	}
}

// ---------------------------------------------------------------- ประเภทกะ

const type_form = ref(null);
function open_type(t) {
	type_form.value = t
		? { original: t.name, start: t.start, end: t.end, break_start: t.break_start || "", break_end: t.break_end || "", grace: t.grace, color: t.color || "Blue" }
		: { original: null, name: "", start: "08:00", end: "17:00", break_start: "12:00", break_end: "13:00", grace: 5, color: "Blue" };
}
const minutes = (t) => (t ? Number(t.slice(0, 2)) * 60 + Number(t.slice(3, 5)) : null);
const form_hours = computed(() => {
	const f = type_form.value;
	const span = minutes(f?.end) - minutes(f?.start);
	if (!f || !(span > 0)) return "—";
	const rest = f.break_start && f.break_end ? Math.max(0, minutes(f.break_end) - minutes(f.break_start)) : 0;
	return `${((span - rest) / 60).toFixed(1)} ชม.`;
});
async function save_type() {
	busy.value = true;
	try {
		data.value.types = await post(`${API}.save_shift_type`, { data: JSON.stringify(type_form.value) });
		type_form.value = null;
		toast("บันทึกกะแล้ว", "success");
	} catch (error) {
		show_error(error);
	} finally {
		busy.value = false;
	}
}
async function set_company_shift(name) {
	busy.value = true;
	try {
		await post(`${API}.set_company_shift`, { company: data.value.company, shift_type: name || undefined });
		toast(name ? `กะเริ่มต้นบริษัท: ${name}` : "เลิกใช้กะเริ่มต้น (กลับเป็น 08:00-17:00)", "success");
		await load();
	} catch (error) {
		show_error(error);
	} finally {
		busy.value = false;
	}
}

watch(tab, (value) => {
	remember_tab("hr-shifts", value, "board");
	if (value === "locations" && locations.value === null) load_locations();
});
watch(week, load);
watch(() => state.company, load);
load();
</script>

<style scoped>
/* ในการ์ด (ListCard ≥768): คำอธิบาย/การ์ดกะ เว้นขอบใน ตารางชิดกรอบการ์ด */
.ss-list-main > .hr-shift-note { margin: 0; padding: 10px 14px; border-bottom: 1px solid var(--ss-work-line, var(--ss-border)); }
.ss-list-main > .hr-in-card { padding: 14px; overflow-y: auto; min-height: 0; }
.ss-list-main > .hr-loc-new { margin: 14px 14px 0; }

.hr-shift-note {
	margin: 10px 0;
	color: var(--ss-muted);
	font-size: var(--ss-fs-sm);
	line-height: 1.5;
}
.hr-week-nav {
	display: inline-flex;
	align-items: center;
	gap: 4px;
	white-space: nowrap;
}
.hr-shift-project { flex: none; width: 220px; }
.hr-shift-search { max-width: 200px; }
.hr-shift-grid-wrap {
	overflow-x: auto;
	border: 1px solid var(--ss-work-line, var(--ss-border));
	border-radius: 14px;
	background: var(--ss-work-card, var(--ss-surface));
}
.hr-shift-grid {
	width: 100%;
	border-collapse: collapse;
	font-size: var(--ss-fs);
}
.hr-shift-grid th,
.hr-shift-grid td {
	padding: 6px 8px;
	border-bottom: 1px solid var(--ss-work-line, var(--ss-border));
	text-align: center;
}
.hr-shift-grid th {
	color: var(--ss-muted);
	font-size: var(--ss-fs-sm);
	font-weight: 500;
	white-space: nowrap;
}
.hr-shift-grid th small { margin-left: 2px; }
.hr-shift-grid th.is-today { color: var(--ss-brand); font-weight: 700; }
.hr-shift-grid th.is-weekend { color: #b4323b; }
.hr-shift-grid tr:last-child td { border-bottom: 0; }
.hr-shift-grid tr.is-selected td { background: var(--ss-brand-soft); }
.hr-shift-check { width: 36px; }
.hr-shift-person {
	min-width: 180px;
	text-align: left !important;
}
.hr-shift-person b { display: block; font-weight: 600; }
.hr-shift-person small { color: var(--ss-muted); font-size: var(--ss-fs-sm); }
.hr-shift-cell button,
button.hr-shift-cell {
	width: 100%;
	min-width: 64px;
	min-height: 30px;
	padding: 2px 6px;
	border: 0;
	border-radius: 8px;
	font-size: var(--ss-fs-sm);
	font-weight: 600;
	cursor: pointer;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}
.is-shift { color: #1d4ed8; background: #dbeafe; }
.is-default { color: var(--ss-text-2); background: color-mix(in srgb, var(--ss-text) 5%, transparent); }
.is-off { color: var(--ss-muted); background: transparent; border: 1px dashed var(--ss-border) !important; }
.is-holiday { color: #b4323b; background: #fbe6e7; }
.is-leave { color: #7c3aed; background: #ede9fe; }
.is-none { color: var(--ss-muted); background: transparent; cursor: default; }
.hr-shift-card { display: flex; flex-direction: column; gap: 10px; padding: 12px; }
.hr-shift-card.is-selected { outline: 2px solid var(--ss-brand); }
.hr-shift-card-head { display: flex; align-items: center; gap: 10px; }
.hr-shift-card-head b { display: block; }
.hr-shift-card-head small { color: var(--ss-muted); font-size: var(--ss-fs-sm); }
.hr-shift-week { display: grid; grid-template-columns: repeat(7, 1fr); gap: 4px; }
.hr-shift-week .hr-shift-cell {
	display: flex;
	flex-direction: column;
	align-items: center;
	gap: 2px;
	min-width: 0;
	padding: 4px 0;
}
.hr-shift-week .hr-shift-cell small { font-weight: 500; opacity: 0.8; }
.hr-shift-bar { display: flex; align-items: center; gap: 8px; justify-content: flex-end; }
.hr-shift-bar > span { margin-right: auto; font-weight: 600; }
.hr-type-grid {
	display: grid;
	grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
	gap: 12px;
}
.hr-type { gap: 8px; }
.hr-type-head { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.hr-type-head b { font-weight: 650; }
.hr-type-dot { width: 10px; height: 10px; border-radius: 50%; }
.hr-type-time { font-size: var(--ss-fs-xl); font-weight: 700; font-variant-numeric: tabular-nums; }
.hr-type-facts {
	display: grid;
	grid-template-columns: 1fr 1fr;
	gap: 6px 12px;
	margin: 0;
}
.hr-type-facts dt { color: var(--ss-muted); font-size: var(--ss-fs-sm); }
.hr-type-facts dd { margin: 0; font-weight: 600; }
.hr-type-warn { margin: 0; color: var(--tone-amber); font-size: var(--ss-fs-sm); }
.hr-type-actions { display: flex; flex-wrap: wrap; gap: 8px; margin-top: auto; padding-top: 6px; }
.hr-type-actions .ss-btn { height: 32px; padding: 0 12px; border-radius: 999px; gap: 4px; }
.hr-loc-new { margin-bottom: 12px; gap: 4px; }
.hr-loc-users { margin: 0; color: var(--ss-muted); font-size: var(--ss-fs-sm); }
</style>
