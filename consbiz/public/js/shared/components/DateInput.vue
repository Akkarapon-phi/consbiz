<!-- ช่องวันที่ของแอป: แสดงวันที่ไทย (พ.ศ.) เปิดปฏิทินเลือกวัน (แทน <input type="date"> ของเบราว์เซอร์)
     ค่า = "YYYY-MM-DD" (ค.ศ. แบบที่ server ใช้) variant: field / cell
     กดชื่อเดือน = เลือกเดือน, กดปี = เลือกปี (ลูกศรเลื่อนทีละเดือน / ปี / ทศวรรษตามหน้าที่เปิด)
     คีย์บอร์ด: Enter/Space/↓ เปิด, ลูกศรเลื่อนวัน, PageUp/PageDown เลื่อนเดือน, Enter เลือก, Esc ปิด -->
<template>
	<button
		ref="trigger"
		type="button"
		class="ss-select ss-date"
		:class="[`ss-select--${variant}`, { 'is-open': open, 'is-empty': !modelValue }]"
		:disabled="disabled"
		aria-haspopup="dialog"
		:aria-expanded="open"
		:aria-label="label"
		@click="toggle"
		@keydown="on_key"
	>
		<Icon name="calendar" :size="variant === 'cell' ? 14 : 16" class="ss-date-icon" />
		<span class="ss-select-value">{{ modelValue ? display(modelValue) : placeholder }}</span>
	</button>
	<Teleport to="body">
		<Transition name="ss-pop-menu">
			<div
				v-if="open"
				ref="panel"
				class="ss-cal-pop"
				role="dialog"
				:aria-label="label"
				:style="pop_style"
			>
				<div class="ss-cal-pop-head">
					<button
						type="button"
						class="ss-icon-btn ss-icon-btn--sm"
						aria-label="ก่อนหน้า"
						@click="page(-1)"
					>
						<Icon name="chevron-left" :size="17" />
					</button>
					<div class="ss-cal-pop-title">
						<b v-if="mode === 'years'">{{ decade + 543 }} – {{ decade + 552 }}</b>
						<template v-else>
							<button
								v-if="mode === 'days'"
								type="button"
								class="ss-cal-pop-part"
								aria-label="เลือกเดือน"
								@mousedown.prevent="mode = 'months'"
							>
								{{ MONTHS[view.getMonth()] }}
							</button>
							<button
								type="button"
								class="ss-cal-pop-part"
								aria-label="เลือกปี"
								@mousedown.prevent="mode = 'years'"
							>
								{{ view.getFullYear() + 543 }}
							</button>
						</template>
					</div>
					<button
						type="button"
						class="ss-icon-btn ss-icon-btn--sm"
						aria-label="ถัดไป"
						@click="page(1)"
					>
						<Icon name="chevron-right" :size="17" />
					</button>
				</div>
				<div v-if="mode === 'months'" class="ss-cal-pop-pick">
					<button
						v-for="c in month_cells"
						:key="c.month"
						type="button"
						class="ss-cal-pop-day"
						:class="{
							'is-today': c.today,
							'is-selected': c.selected,
							'is-focus': c.month === view.getMonth(),
							'is-off': c.off,
						}"
						:aria-label="MONTHS[c.month]"
						:aria-pressed="c.selected"
						:disabled="c.off"
						@mousedown.prevent="pick_month(c.month)"
					>
						{{ SHORT[c.month] }}
					</button>
				</div>
				<div v-else-if="mode === 'years'" class="ss-cal-pop-pick">
					<button
						v-for="c in year_cells"
						:key="c.year"
						type="button"
						class="ss-cal-pop-day"
						:class="{
							'is-other': c.other,
							'is-today': c.today,
							'is-selected': c.selected,
							'is-focus': c.year === view.getFullYear(),
							'is-off': c.off,
						}"
						:aria-pressed="c.selected"
						:disabled="c.off"
						@mousedown.prevent="pick_year(c.year)"
					>
						{{ c.year + 543 }}
					</button>
				</div>
				<div v-else class="ss-cal-pop-grid" role="grid">
					<span v-for="d in DAYS" :key="d" class="is-dow">{{ d }}</span>
					<button
						v-for="c in cells"
						:key="c.iso"
						type="button"
						class="ss-cal-pop-day"
						:class="{
							'is-other': c.other,
							'is-today': c.iso === today_iso,
							'is-selected': c.iso === modelValue,
							'is-focus': c.iso === focus_iso,
							'is-off': c.off,
						}"
						:aria-label="display(c.iso)"
						:aria-pressed="c.iso === modelValue"
						:disabled="c.off"
						@mousedown.prevent="choose(c.iso)"
					>
						{{ c.day }}
					</button>
				</div>
				<div class="ss-cal-pop-foot">
					<button type="button" class="ss-link" @mousedown.prevent="choose(today_iso)">
						วันนี้
					</button>
					<button
						v-if="clearable && modelValue"
						type="button"
						class="ss-link is-muted"
						@mousedown.prevent="choose(null)"
					>
						ล้าง
					</button>
				</div>
			</div>
		</Transition>
	</Teleport>
</template>

<script setup>
import { computed, onBeforeUnmount, ref } from "vue";
import Icon from "./Icon.vue";
import { iso_date } from "../api.js";

const props = defineProps({
	modelValue: { type: String, default: null },
	placeholder: { type: String, default: "เลือกวันที่" },
	variant: { type: String, default: "field" },
	label: String,
	disabled: Boolean,
	clearable: Boolean,
	// วันแรกที่เลือกได้ ("YYYY-MM-DD") ก่อนหน้านั้นกดไม่ได้
	min: String,
});
const emit = defineEmits(["update:modelValue", "change"]);

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
const SHORT = [
	"ม.ค.",
	"ก.พ.",
	"มี.ค.",
	"เม.ย.",
	"พ.ค.",
	"มิ.ย.",
	"ก.ค.",
	"ส.ค.",
	"ก.ย.",
	"ต.ค.",
	"พ.ย.",
	"ธ.ค.",
];
const DAYS = ["อา", "จ", "อ", "พ", "พฤ", "ศ", "ส"];

const trigger = ref(null);
const panel = ref(null);
const open = ref(false);
const mode = ref("days"); // days | months | years
const view = ref(new Date());
const focus_iso = ref(null);
const pop_style = ref({});
const today_iso = iso_date(new Date());

const parse = (iso) => {
	const [y, m, d] = String(iso).slice(0, 10).split("-").map(Number);
	return new Date(y, m - 1, d);
};
const display = (iso) => {
	const d = parse(iso);
	return `${d.getDate()} ${SHORT[d.getMonth()]} ${d.getFullYear() + 543}`;
};

// ตาราง 6 สัปดาห์ เริ่มวันอาทิตย์
const cells = computed(() => {
	const y = view.value.getFullYear();
	const m = view.value.getMonth();
	const start = new Date(y, m, 1 - new Date(y, m, 1).getDay());
	return Array.from({ length: 42 }, (_, i) => {
		const d = new Date(start.getFullYear(), start.getMonth(), start.getDate() + i);
		const iso = iso_date(d);
		return { iso, day: d.getDate(), other: d.getMonth() !== m, off: !!props.min && iso < props.min };
	});
});

const selected_date = computed(() => (props.modelValue ? parse(props.modelValue) : null));
const today_date = parse(today_iso);
const min_date = computed(() => (props.min ? parse(props.min) : null));

const month_cells = computed(() => {
	const y = view.value.getFullYear();
	return Array.from({ length: 12 }, (_, month) => ({
		month,
		today: today_date.getFullYear() === y && today_date.getMonth() === month,
		selected: selected_date.value?.getFullYear() === y && selected_date.value?.getMonth() === month,
		off: !!min_date.value && new Date(y, month + 1, 0) < min_date.value,
	}));
});

// ทศวรรษ พ.ศ. + ปีก่อน/หลังอย่างละปี 12 ช่องเท่าปฏิทินของ Frappe
const decade = computed(() => Math.floor((view.value.getFullYear() + 543) / 10) * 10 - 543);
const year_cells = computed(() =>
	Array.from({ length: 12 }, (_, i) => {
		const year = decade.value - 1 + i;
		return {
			year,
			other: i === 0 || i === 11,
			today: today_date.getFullYear() === year,
			selected: selected_date.value?.getFullYear() === year,
			off: !!min_date.value && year < min_date.value.getFullYear(),
		};
	})
);

function place() {
	const box = trigger.value?.getBoundingClientRect();
	if (!box) return;
	const height = 340;
	const width = 296;
	const up = window.innerHeight - box.bottom < height + 12 && box.top > height;
	pop_style.value = {
		left: `${Math.max(8, Math.min(box.left, window.innerWidth - width - 8))}px`,
		...(up ? { bottom: `${window.innerHeight - box.top + 4}px` } : { top: `${box.bottom + 4}px` }),
	};
}

function show() {
	if (props.disabled) return;
	const base = props.modelValue ? parse(props.modelValue) : new Date();
	view.value = new Date(base.getFullYear(), base.getMonth(), 1);
	focus_iso.value = props.modelValue || today_iso;
	mode.value = "days";
	place();
	open.value = true;
	window.addEventListener("pointerdown", outside, true);
	window.addEventListener("scroll", place, true);
	window.addEventListener("resize", place);
}

function hide(focus = true) {
	open.value = false;
	window.removeEventListener("pointerdown", outside, true);
	window.removeEventListener("scroll", place, true);
	window.removeEventListener("resize", place);
	if (focus) trigger.value?.focus();
}

const toggle = () => (open.value ? hide() : show());

function outside(event) {
	if (!panel.value?.contains(event.target) && !trigger.value?.contains(event.target)) hide(false);
}

function shift(months) {
	view.value = new Date(view.value.getFullYear(), view.value.getMonth() + months, 1);
}

// ลูกศรของหัวปฏิทิน: ทีละเดือน / ปี / ทศวรรษ ตามหน้าที่เปิด
const PAGE_MONTHS = { days: 1, months: 12, years: 120 };
const page = (step) => shift(step * PAGE_MONTHS[mode.value]);

function pick_month(month) {
	view.value = new Date(view.value.getFullYear(), month, 1);
	mode.value = "days";
}
function pick_year(year) {
	view.value = new Date(year, view.value.getMonth(), 1);
	mode.value = "days";
}

function choose(iso) {
	if (iso && props.min && iso < props.min) return;
	if (iso !== props.modelValue) {
		emit("update:modelValue", iso);
		emit("change", iso);
	}
	hide();
}

function move_focus(days) {
	const d = parse(focus_iso.value);
	d.setDate(d.getDate() + days);
	focus_iso.value = iso_date(d);
	view.value = new Date(d.getFullYear(), d.getMonth(), 1);
}

function on_key(event) {
	if (!open.value) {
		if (["Enter", " ", "ArrowDown"].includes(event.key)) {
			event.preventDefault();
			show();
		}
		return;
	}
	if (mode.value !== "days") return on_pick_key(event);
	const steps = { ArrowLeft: -1, ArrowRight: 1, ArrowUp: -7, ArrowDown: 7 };
	if (steps[event.key]) move_focus(steps[event.key]);
	else if (event.key === "PageUp") page(-1);
	else if (event.key === "PageDown") page(1);
	else if (event.key === "Enter" || event.key === " ") choose(focus_iso.value);
	else if (event.key === "Escape" || event.key === "Tab") return hide(event.key === "Escape");
	else return;
	event.preventDefault();
}

// หน้าเลือกเดือน/ปี: ลูกศรเลื่อนช่อง (ตาราง 3 คอลัมน์), Enter เลือก, Esc กลับหน้าวัน
function on_pick_key(event) {
	const unit = mode.value === "months" ? 1 : 12;
	const steps = { ArrowLeft: -unit, ArrowRight: unit, ArrowUp: -3 * unit, ArrowDown: 3 * unit };
	if (steps[event.key]) shift(steps[event.key]);
	else if (event.key === "PageUp") page(-1);
	else if (event.key === "PageDown") page(1);
	else if (event.key === "Enter" || event.key === " ") mode.value = "days";
	else if (event.key === "Escape") mode.value = "days";
	else if (event.key === "Tab") return hide(false);
	else return;
	event.preventDefault();
}

onBeforeUnmount(() => hide(false));
</script>
