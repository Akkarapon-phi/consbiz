<!-- จุดลงเวลา (Shift Location) ของโครงการ/พนักงาน (ตกลง 2026-11-17): ปุ่มใต้ช่องจุดลงเวลาใน MasterPage
     ตั้งจุดใหม่หรือแก้จุดที่เลือก ใช้ GPS ของเครื่องที่หน้างาน (หรือวางพิกัดจาก Google Maps) + รัศมี
     บันทึก = master_data.save_checkin_location แล้วคืนชื่อจุดให้ฟอร์มใส่ช่อง (บันทึกพร้อมฟอร์ม) จุดที่ใช้ร่วมกับเอกสารอื่น = สร้างจุดใหม่ -->
<template>
	<div class="md-loc-actions">
		<button type="button" class="ss-link" :disabled="loading" @click="open_sheet">
			<Icon :name="modelValue ? 'pen' : 'crosshair'" :size="14" />
			{{ modelValue ? "แก้พิกัด/รัศมีของจุดนี้" : "ตั้งจุดใหม่ด้วย GPS" }}
		</button>
		<a v-if="current && maps_url(current)" class="ss-link" :href="maps_url(current)" target="_blank" rel="noopener">
			<Icon name="pin" :size="14" /> ดูในแผนที่ · รัศมี {{ num(current.radius) }} ม.
		</a>
	</div>

	<Sheet :open="!!form" :title="modelValue && !form?.copy ? 'แก้จุดลงเวลา' : 'ตั้งจุดลงเวลา'" :subtitle="label" form @close="form = null">
		<template v-if="form">
			<p v-if="form.copy" class="ss-note ss-note--warn">
				จุด {{ modelValue }} ใช้ร่วมกับอีก {{ form.copy }} รายการ บันทึกแล้วจะสร้างจุดใหม่ให้{{ label }}นี้ จุดเดิมไม่เปลี่ยน
			</p>
			<label class="ss-field">
				<span class="ss-field-label">ชื่อจุด<em>*</em></span>
				<input v-model="form.label" class="ss-input" :disabled="form.existing" placeholder="เช่น ไซต์งานบางนา ประตู 1" />
				<small v-if="form.existing" class="md-loc-hint">ชื่อจุดเดิมเปลี่ยนไม่ได้</small>
			</label>

			<div class="ss-field">
				<span class="ss-field-label">ตำแหน่ง<em>*</em></span>
				<button type="button" class="ss-btn ss-btn--soft ss-btn--block" :disabled="locating" @click="locate">
					<span v-if="locating" class="ss-spinner"></span>
					<Icon v-else name="crosshair" :size="18" />
					<span>{{ locating ? "กำลังหาตำแหน่ง…" : "ใช้ตำแหน่งปัจจุบันของเครื่องนี้" }}</span>
				</button>
				<small v-if="gps_error" class="ss-field-error">{{ gps_error }}</small>
				<small v-else-if="form.accuracy != null" class="md-loc-hint" :class="{ 'is-warn': form.accuracy > GOOD_ACCURACY }">
					ความแม่นยำ ±{{ num(Math.round(form.accuracy)) }} ม.
					<template v-if="form.accuracy > GOOD_ACCURACY"> ค่อนข้างคลาด ลองออกไปที่โล่งแล้วกดอีกครั้ง</template>
				</small>
			</div>
			<div class="ss-leave-dates">
				<label class="ss-field">
					<span class="ss-field-label">ละติจูด</span>
					<input v-model="form.latitude" class="ss-input" inputmode="decimal" placeholder="13.7563" @paste="paste_coords" />
				</label>
				<label class="ss-field">
					<span class="ss-field-label">ลองจิจูด</span>
					<input v-model="form.longitude" class="ss-input" inputmode="decimal" placeholder="100.5018" @paste="paste_coords" />
				</label>
			</div>
			<small class="md-loc-hint">วางพิกัดจาก Google Maps (เช่น 13.7563, 100.5018) ลงช่องไหนก็ได้ ระบบแยกให้</small>

			<div class="ss-field">
				<span class="ss-field-label">รัศมีที่ลงเวลาได้ (เมตร)<em>*</em></span>
				<div class="md-loc-radius">
					<Segmented v-model="radius_choice" :options="RADIUS_OPTIONS" />
					<input v-model="form.radius" class="ss-input" inputmode="numeric" aria-label="รัศมี (เมตร)" />
				</div>
				<small class="md-loc-hint">นอกรัศมียังลงเวลาได้ แต่ต้องให้หัวหน้ายืนยัน ไซต์ใหญ่ควรครอบทั้งพื้นที่ + เผื่อ GPS คลาด 50 ม.</small>
			</div>
			<a v-if="maps_url(form)" class="ss-link" :href="maps_url(form)" target="_blank" rel="noopener">
				<Icon name="external" :size="14" /> ตรวจตำแหน่งใน Google Maps
			</a>
		</template>
		<template #footer>
			<button type="button" class="ss-btn ss-btn--primary ss-btn--block ss-btn--lg" :disabled="busy || !can_save" @click="save">
				<span v-if="busy" class="ss-spinner"></span>
				<span>บันทึกจุดลงเวลา</span>
			</button>
		</template>
	</Sheet>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import Icon from "../../../shared/components/Icon.vue";
import Sheet from "../../../shared/components/Sheet.vue";
import Segmented from "../../../shared/components/Segmented.vue";
import { call, num, post, show_error, toast } from "../../../shared/api.js";
import { API } from "./kinds.js";

const props = defineProps({
	modelValue: { type: String, default: null },
	kind: { type: String, required: true },
	// ชื่อเอกสารที่กำลังแก้ (ว่าง = เอกสารใหม่)
	docname: { type: String, default: null },
	// ชื่อที่แสดง/ตั้งเป็นชื่อจุดเริ่มต้น (ชื่อโครงการ/พนักงาน)
	label: { type: String, default: "" },
	// แก้จุดเดิมในที่แม้ใช้ร่วมกัน (หน้ากะของ HR) ไม่สร้างจุดใหม่
	in_place: Boolean,
});
const emit = defineEmits(["update:modelValue", "saved"]);

const RADIUS_OPTIONS = [100, 200, 300, 500].map((r) => ({ value: String(r), label: `${r} ม.` }));
const GOOD_ACCURACY = 50;
const radius_choice = computed({
	get: () => String(form.value?.radius ?? ""),
	set: (v) => (form.value.radius = Number(v)),
});
const current = ref(null);
const loading = ref(false);
const form = ref(null);
const busy = ref(false);
const locating = ref(false);
const gps_error = ref("");

const maps_url = (p) => {
	const lat = Number(p?.latitude);
	const lng = Number(p?.longitude);
	return lat || lng ? `https://www.google.com/maps?q=${lat},${lng}` : "";
};
const can_save = computed(() => {
	const f = form.value;
	const lat = Number(f?.latitude);
	const lng = Number(f?.longitude);
	const r = Number(f?.radius);
	return f && f.label?.trim() && (lat || lng) && Math.abs(lat) <= 90 && Math.abs(lng) <= 180 && r >= 10;
});

async function load_current() {
	current.value = null;
	if (!props.modelValue) return;
	loading.value = true;
	try {
		current.value = await call(`${API}.get_checkin_location`, { kind: props.kind, location: props.modelValue, name: props.docname || undefined });
	} catch (error) {
		show_error(error);
	} finally {
		loading.value = false;
	}
}
watch(() => props.modelValue, load_current, { immediate: true });

function open_sheet() {
	const c = current.value;
	gps_error.value = "";
	const shared = props.in_place ? 0 : c?.shared;
	form.value = c
		? {
				label: shared ? `${props.label || c.location_name}` : c.location_name,
				latitude: c.latitude,
				longitude: c.longitude,
				radius: c.radius || 200,
				accuracy: null,
				existing: !shared,
				copy: shared || 0,
			}
		: { label: props.label || "", latitude: "", longitude: "", radius: 200, accuracy: null, existing: false, copy: 0 };
}

function locate() {
	gps_error.value = "";
	if (!navigator.geolocation) {
		gps_error.value = "อุปกรณ์นี้ไม่รองรับ GPS";
		return;
	}
	locating.value = true;
	navigator.geolocation.getCurrentPosition(
		(pos) => {
			locating.value = false;
			if (!form.value) return;
			form.value.latitude = pos.coords.latitude.toFixed(6);
			form.value.longitude = pos.coords.longitude.toFixed(6);
			form.value.accuracy = pos.coords.accuracy;
		},
		(error) => {
			locating.value = false;
			gps_error.value =
				error.code === error.PERMISSION_DENIED
					? "ไม่ได้รับอนุญาตให้ใช้ตำแหน่ง เปิดสิทธิ์ตำแหน่งของเบราว์เซอร์แล้วลองใหม่"
					: "หาตำแหน่งไม่ได้ ลองออกไปที่โล่งแล้วลองใหม่";
		},
		{ enableHighAccuracy: true, timeout: 20000, maximumAge: 0 }
	);
}

// วาง "13.7563, 100.5018" (คัดลอกจาก Google Maps) = แยกลงสองช่อง
function paste_coords(event) {
	const text = event.clipboardData?.getData("text") || "";
	const match = text.match(/(-?\d{1,3}\.\d+)\s*,\s*(-?\d{1,3}\.\d+)/);
	if (!match) return;
	event.preventDefault();
	form.value.latitude = match[1];
	form.value.longitude = match[2];
	form.value.accuracy = null;
}

async function save() {
	const f = form.value;
	busy.value = true;
	try {
		const result = await post(`${API}.save_checkin_location`, {
			kind: props.kind,
			label: f.label,
			latitude: f.latitude,
			longitude: f.longitude,
			radius: f.radius,
			location: props.modelValue || undefined,
			name: props.docname || undefined,
			in_place: props.in_place ? 1 : undefined,
		});
		form.value = null;
		emit("update:modelValue", result.name);
		emit("saved", result);
		await load_current();
		toast(result.created ? `สร้างจุด ${result.location_name} แล้ว กดบันทึกฟอร์มเพื่อใช้จุดนี้` : "แก้จุดลงเวลาแล้ว มีผลทันที", "success");
	} catch (error) {
		show_error(error);
	} finally {
		busy.value = false;
	}
}
</script>

<style scoped>
.md-loc-actions {
	display: flex;
	flex-wrap: wrap;
	gap: 6px 16px;
	margin-top: 6px;
}
.md-loc-actions .ss-link,
.ss-sheet-body .ss-link {
	display: inline-flex;
	align-items: center;
	gap: 4px;
	font-size: var(--ss-fs-sm);
}
.md-loc-hint {
	color: var(--ss-muted);
	font-size: var(--ss-fs-sm);
	line-height: 1.5;
}
.md-loc-hint.is-warn {
	color: var(--tone-amber);
}
.md-loc-radius {
	display: flex;
	align-items: center;
	gap: 6px;
	flex-wrap: wrap;
}
.md-loc-radius > :first-child {
	flex: 1;
	min-width: 220px;
}
.md-loc-radius .ss-input {
	width: 88px;
	flex: none;
}
</style>
