<!-- ตั้งค่าส่วนตัว > ข้อมูลส่วนตัว (avatar > ตั้งค่า, ตกลง 2026-11-18 แบบหน้า Settings > Profile ของ Frappe)
     หัว = avatar + ชื่อ + อีเมล + ปุ่มเปลี่ยนรหัสผ่าน แก้ชื่อได้ (site_app.update_my_profile) ชื่อผู้ใช้/อีเมลดูอย่างเดียว
     เปลี่ยนรหัสผ่าน = update_password ของ Frappe (ตรวจรหัสเดิม + ความยาก) สำเร็จแล้ว session ใหม่ จึงโหลดหน้าใหม่ -->
<template>
	<div class="ss-settings-form">
		<div class="ss-settings-form-inner">
			<header class="ps-head">
				<div>
					<h2>ข้อมูลส่วนตัว</h2>
					<p>ชื่อที่แสดงในระบบและรหัสผ่าน</p>
				</div>
				<button type="button" class="ss-btn ss-btn--primary" :disabled="!dirty || busy" @click="save">บันทึก</button>
			</header>
			<Skeleton v-if="!form" :rows="4" />
			<template v-else>
				<div class="ps-user">
					<span class="ss-avatar ps-avatar" :class="`tone-${tone(boot.user || '')}`">
						<img v-if="boot.user_image && !broken" :src="boot.user_image" alt="" @error="broken = true" />
						<template v-else>{{ initials(full_name || boot.user || "") }}</template>
					</span>
					<div class="ps-name">
						<strong>{{ full_name }}</strong>
						<span>{{ profile.email || boot.user }}</span>
					</div>
					<button type="button" class="ss-btn ss-btn--soft" @click="pw_open = true">เปลี่ยนรหัสผ่าน</button>
				</div>
				<div class="ps-grid">
					<label class="ss-field">
						<span class="ss-field-label">ชื่อ<em>*</em></span>
						<input v-model="form.first_name" class="ss-input" maxlength="140" />
					</label>
					<label class="ss-field">
						<span class="ss-field-label">ชื่อกลาง</span>
						<input v-model="form.middle_name" class="ss-input" maxlength="140" />
					</label>
					<label class="ss-field">
						<span class="ss-field-label">นามสกุล</span>
						<input v-model="form.last_name" class="ss-input" maxlength="140" />
					</label>
					<label class="ss-field">
						<span class="ss-field-label">ชื่อผู้ใช้</span>
						<input :value="profile.username || '-'" class="ss-input" disabled />
					</label>
				</div>
				<a v-if="boot.desk" class="ps-link" :href="`/app/user/${encodeURIComponent(boot.user)}`"
					>ข้อมูลอื่น (โทรศัพท์ ภาษา เขตเวลา) แก้ในระบบเต็ม <Icon name="external" :size="13"
				/></a>
			</template>
		</div>

		<Sheet :open="pw_open" title="เปลี่ยนรหัสผ่าน" form @close="close_pw">
			<label class="ss-field">
				<span class="ss-field-label">รหัสผ่านเดิม</span>
				<input v-model="pw.old" class="ss-input" type="password" autocomplete="current-password" />
			</label>
			<label class="ss-field">
				<span class="ss-field-label">รหัสผ่านใหม่</span>
				<input v-model="pw.new" class="ss-input" type="password" autocomplete="new-password" />
			</label>
			<label class="ss-field">
				<span class="ss-field-label">ยืนยันรหัสผ่านใหม่</span>
				<input v-model="pw.confirm" class="ss-input" type="password" autocomplete="new-password" />
			</label>
			<p v-if="pw.confirm && pw.confirm !== pw.new" class="ps-error">รหัสผ่านใหม่ไม่ตรงกัน</p>
			<template #footer>
				<button type="button" class="ss-btn ss-btn--ghost" @click="close_pw">ยกเลิก</button>
				<button
					type="button"
					class="ss-btn ss-btn--primary"
					:disabled="!pw.old || !pw.new || pw.new !== pw.confirm || busy"
					@click="change_password"
				>
					เปลี่ยนรหัสผ่าน
				</button>
			</template>
		</Sheet>
	</div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import Icon from "../Icon.vue";
import Sheet from "../Sheet.vue";
import Skeleton from "../Skeleton.vue";
import { boot, call, initials, show_error, toast, tone } from "../../api.js";

const profile = ref(null);
const form = ref(null);
const busy = ref(false);
const broken = ref(false);
const pw_open = ref(false);
const pw = reactive({ old: "", new: "", confirm: "" });

const NAMES = ["first_name", "middle_name", "last_name"];
const full_name = computed(() =>
	form.value ? NAMES.map((f) => (form.value[f] || "").trim()).filter(Boolean).join(" ") : boot.full_name
);
const dirty = computed(
	() => form.value && NAMES.some((f) => (form.value[f] || "").trim() !== (profile.value[f] || ""))
);

onMounted(async () => {
	try {
		profile.value = await call("consbiz.site_app.get_my_profile");
		form.value = Object.fromEntries(NAMES.map((f) => [f, profile.value[f] || ""]));
	} catch (error) {
		show_error(error);
	}
});

async function save() {
	if (!form.value.first_name.trim()) return toast("กรุณากรอกชื่อ", "warning");
	busy.value = true;
	try {
		const res = await call("consbiz.site_app.update_my_profile", form.value, { post: true });
		for (const f of NAMES) profile.value[f] = form.value[f].trim();
		boot.full_name = res.full_name;
		toast("บันทึกข้อมูลส่วนตัวแล้ว", "success");
	} catch (error) {
		show_error(error);
	} finally {
		busy.value = false;
	}
}

function close_pw() {
	pw_open.value = false;
	Object.assign(pw, { old: "", new: "", confirm: "" });
}

async function change_password() {
	busy.value = true;
	try {
		await call(
			"frappe.core.doctype.user.user.update_password",
			{ old_password: pw.old, new_password: pw.new, logout_all_sessions: 0 },
			{ post: true }
		);
		toast("เปลี่ยนรหัสผ่านแล้ว", "success");
		// Frappe ล็อกอินให้ใหม่ (session/CSRF ใหม่) หน้าเดิมเรียก API ต่อไม่ได้
		setTimeout(() => location.reload(), 900);
	} catch (error) {
		show_error(error);
		busy.value = false;
	}
}
</script>

<style scoped>
.ps-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }
.ps-head h2 { margin: 0; font-size: var(--ss-fs-xl); font-weight: 650; }
.ps-head p { margin: 4px 0 0; color: var(--ss-muted); font-size: var(--ss-fs); }
.ps-user { display: flex; align-items: center; gap: 12px; padding: 8px 0; }
.ps-avatar { width: 52px; height: 52px; flex: none; font-size: var(--ss-fs-lg); }
.ps-name { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.ps-name strong { font-size: var(--ss-fs-lg); font-weight: 650; }
.ps-name span { color: var(--ss-muted); font-size: var(--ss-fs-sm); overflow-wrap: anywhere; }
.ps-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px 24px; }
.ps-link { display: inline-flex; align-items: center; gap: 4px; color: var(--ss-muted); font-size: var(--ss-fs-sm); }
.ps-error { margin: 0; color: var(--ss-danger); font-size: var(--ss-fs-sm); }
@media (max-width: 767px) {
	.ps-grid { grid-template-columns: minmax(0, 1fr); }
	.ps-user { flex-wrap: wrap; }
	.ps-user .ss-btn { width: 100%; }
}
</style>
