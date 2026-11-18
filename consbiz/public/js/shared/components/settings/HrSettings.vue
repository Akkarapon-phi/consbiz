<!-- หัวข้อหมวดบุคคลในหน้าตั้งค่ารวม (settings_pages.js) 1 หัวข้อต่อกลุ่มเมนู module = time / pay / expense / people
     บน = ค่าตั้งของกลุ่ม (hr_setup.PARAMS ช่องของ Company แก้แล้วบันทึกทันที) แถวละ 1 ค่า ชื่อ+คำอธิบายซ้าย ค่าขวา (แบบหน้าตั้งค่าของ Frappe)
     ล่าง = ตรวจความพร้อม (hr_setup.MODULES) ปุ่มแก้ให้ (HR Manager) / ลิงก์ไปที่ตั้ง (ในแอป = ปิดหน้าต่างแล้วไปหน้านั้น) -->
<template>
	<div class="ss-settings-form">
		<div class="ss-settings-form-inner hrs">
			<header class="hrs-head">
				<h2>{{ label }}</h2>
				<p>ค่าตั้งและความพร้อมของ{{ label }}<template v-if="data"> · {{ data.company }}</template></p>
			</header>
			<Skeleton v-if="!data" :rows="5" />
			<template v-else>
				<p v-if="!data.can_fix" class="hrs-note">แก้ค่าได้เฉพาะ HR Manager / System Manager</p>

				<div v-for="p in data.params" :key="p.fieldname" class="hrs-row">
					<div class="hrs-label">
						<b>{{ p.label }}</b>
						<small v-if="p.note">{{ p.note }}</small>
					</div>
					<div class="hrs-control">
						<SelectBox
							v-if="p.type === 'link'"
							:model-value="p.value || ''"
							:options="[{ value: '', label: 'ไม่ระบุ' }, ...p.options.map((o) => ({ value: o, label: o }))]"
							:disabled="!data.can_fix || busy === p.fieldname"
							@update:model-value="(v) => save_param(p, v)"
						/>
						<input
							v-else
							class="ss-input"
							inputmode="decimal"
							:value="p.value"
							:disabled="!data.can_fix || busy === p.fieldname"
							@change="(e) => save_param(p, e.target.value)"
						/>
					</div>
				</div>

				<div class="hrs-section">
					<h3>ตรวจความพร้อม</h3>
					<span>ผ่าน {{ ok_count }} / {{ data.checks.length }}</span>
					<button
						v-if="data.can_fix && fixable.length"
						type="button"
						class="ss-btn ss-btn--soft hrs-fix-all"
						:disabled="!!busy"
						@click="fix_all"
					>
						<Icon name="check" :size="14" :stroke="2.6" /> แก้อัตโนมัติ {{ fixable.length }} ข้อ
					</button>
				</div>
				<div v-for="c in data.checks" :key="c.key" class="hrs-row hrs-check" :class="`is-${c.status}`">
					<span class="hrs-icon"><Icon :name="ICON[c.status]" :size="14" :stroke="2.6" /></span>
					<div class="hrs-label">
						<b>{{ c.title }}</b>
						<small :class="{ 'is-open': open.has(c.key) }" @click="toggle(c.key)">{{ c.detail }}</small>
						<small v-if="c.fix && data.can_fix && c.status !== 'ok'" class="hrs-fix-text">แก้อัตโนมัติ: {{ c.fix }}</small>
					</div>
					<div v-if="c.status !== 'ok'" class="hrs-actions">
						<button v-if="c.fix && data.can_fix" type="button" class="ss-btn ss-btn--soft" :disabled="!!busy" @click="fix(c)">
							<span v-if="busy === c.key" class="ss-spinner"></span>
							<span>แก้ให้</span>
						</button>
						<a v-if="c.link" class="ss-btn ss-btn--ghost" :href="c.link" :target="in_app(c.link) ? undefined : '_blank'" @click="follow($event, c.link)">
							{{ c.link_label || "เปิดฟอร์ม" }}
						</a>
					</div>
					<span v-else class="ss-tag tone-green">ผ่าน</span>
				</div>
			</template>
		</div>
	</div>
</template>

<script setup>
import { computed, inject, ref, watch } from "vue";
import Icon from "../Icon.vue";
import Skeleton from "../Skeleton.vue";
import SelectBox from "../SelectBox.vue";
import { call, go, parse_path, post, show_error, state, toast } from "../../api.js";

const props = defineProps({ module: { type: String, required: true }, label: { type: String, default: "" } });
const close_settings = inject("close_settings", null);
const API = "consbiz.hr_setup";
const ICON = { ok: "check", warn: "info", error: "alert" };

const data = ref(null);
const busy = ref(null);
const open = ref(new Set());
const ok_count = computed(() => (data.value?.checks || []).filter((c) => c.status === "ok").length);
const fixable = computed(() => (data.value?.checks || []).filter((c) => c.fix && c.status !== "ok"));

function toggle(key) {
	const next = new Set(open.value);
	next.has(key) ? next.delete(key) : next.add(key);
	open.value = next;
}
const in_app = (link) => String(link).startsWith("/conserp/");
// ลิงก์ในแอป: ปิดหน้าต่างตั้งค่าแล้วไปหน้านั้น (ไม่โหลดหน้าใหม่)
function follow(event, link) {
	if (!in_app(link)) return;
	event.preventDefault();
	const route = parse_path(link);
	close_settings?.();
	if (route?.view) go(route.view, route.params || {}, { section: route.section });
}

async function load() {
	try {
		data.value = await call(`${API}.get_checks`, { company: state.company || undefined, module: props.module });
	} catch (error) {
		show_error(error);
	}
}

async function save_param(p, value) {
	if (String(value ?? "") === String(p.value ?? "")) return;
	busy.value = p.fieldname;
	try {
		data.value.params = await post(`${API}.save_param`, {
			company: data.value.company,
			module: props.module,
			fieldname: p.fieldname,
			value,
		});
		toast(`${p.label}: บันทึกแล้ว`, "success");
		await load();
	} catch (error) {
		show_error(error);
		data.value = { ...data.value };
	} finally {
		busy.value = null;
	}
}

async function fix(c, quiet = false) {
	busy.value = c.key;
	try {
		const r = await post(`${API}.apply_fix`, { key: c.key, company: data.value.company });
		Object.assign(c, { status: r.status, detail: r.detail, fix: r.fix, link: r.link, link_label: r.link_label });
		if (!quiet) toast(`${c.title}: แก้แล้ว`, "success");
		return true;
	} catch (error) {
		show_error(error);
		return false;
	} finally {
		busy.value = null;
	}
}
// บางข้อแก้ได้หลังข้ออื่นผ่าน (โควตาวันลาต้องมีนโยบายก่อน) จึงตรวจใหม่แล้ววนอีกรอบ
async function fix_all() {
	let done = 0;
	for (let pass = 0; pass < 3 && fixable.value.length; pass += 1) {
		for (const c of [...fixable.value]) {
			if (!(await fix(c, true))) return load();
			done += 1;
		}
		await load();
	}
	toast(`แก้แล้ว ${done} ข้อ`, "success");
}

watch(() => state.company, load);
load();
</script>

<style scoped>
.hrs-head h2 { margin: 0; font-size: var(--ss-fs-xl); font-weight: 650; }
.hrs-head p { margin: 4px 0 12px; color: var(--ss-muted); font-size: var(--ss-fs); }
.hrs-note { margin: 0 0 8px; color: var(--ss-muted); font-size: var(--ss-fs-sm); }
.hrs-row {
	display: flex;
	align-items: center;
	gap: 14px;
	padding: 14px 0;
	border-bottom: 1px solid var(--ss-border);
}
.hrs-label { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 3px; }
.hrs-label b { font-weight: 600; }
.hrs-label small {
	color: var(--ss-muted);
	font-size: var(--ss-fs-sm);
	line-height: 1.5;
	overflow-wrap: anywhere;
	display: -webkit-box;
	-webkit-line-clamp: 2;
	-webkit-box-orient: vertical;
	overflow: hidden;
	cursor: pointer;
}
.hrs-label small.is-open { display: block; }
.hrs-label .hrs-fix-text { cursor: default; }
.hrs-control { flex: none; width: 240px; }
.hrs-section {
	display: flex;
	align-items: center;
	gap: 10px;
	margin-top: 24px;
	padding-bottom: 6px;
	border-bottom: 1px solid var(--ss-border);
}
.hrs-section h3 { margin: 0; font-size: var(--ss-fs); font-weight: 650; }
.hrs-section span { color: var(--ss-muted); font-size: var(--ss-fs-sm); }
.hrs-fix-all { margin-left: auto; height: 30px; padding: 0 12px; border-radius: 999px; gap: 4px; }
.hrs-check { align-items: flex-start; }
.hrs-icon {
	display: grid;
	place-items: center;
	flex: none;
	width: 22px;
	height: 22px;
	margin-top: 1px;
	border-radius: 50%;
	color: var(--tone);
	background: var(--tone-bg);
}
.hrs-check.is-ok .hrs-icon { --tone: var(--tone-green); --tone-bg: var(--tone-green-bg); }
.hrs-check.is-warn .hrs-icon { --tone: var(--tone-amber); --tone-bg: var(--tone-amber-bg); }
.hrs-check.is-error .hrs-icon { --tone: var(--tone-rose); --tone-bg: var(--tone-rose-bg); }
.hrs-actions { flex: none; display: flex; flex-direction: column; align-items: stretch; gap: 6px; }
.hrs-actions .ss-btn { height: 30px; padding: 0 12px; border-radius: 999px; justify-content: center; }
@media (max-width: 767px) {
	.hrs-row { flex-wrap: wrap; }
	.hrs-control { width: 100%; }
	.hrs-actions { flex-direction: row; width: 100%; padding-left: 36px; }
}
</style>
