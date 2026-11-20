<!-- ตั้งค่าการอนุมัติ/ลงนามของเอกสารจัดซื้อ (ตกลง 2026-11-19, หมวดจัดซื้อ เมนู ⋯ > ตั้งค่า) API consbiz/doc_approval.py
     แถวละ 1 เอกสาร: Role ที่อนุมัติ/ลงนามได้ (+ Role ที่บันทึกการลงนามแทนได้ ของใบสั่งซื้อ/ใบแจ้งหนี้ซื้อ)
     มีผลทุกทาง (แอป + ระบบเต็ม) แก้ได้เฉพาะ Purchase Manager / System Manager -->
<template>
	<div class="ss-settings-form">
		<div class="ss-settings-form-inner aps">
			<header class="aps-head">
				<h2>การอนุมัติ/ลงนาม</h2>
				<p>
					เลือก Role ที่อนุมัติหรือลงนามเอกสารได้ คนอื่นกด "ส่งอนุมัติ/ส่งลงนาม" ให้ผู้มีสิทธิ์
					(มีผลทั้งแอปและระบบเต็ม ผู้มีสิทธิ์อนุมัติเอกสารของตัวเองได้)
				</p>
			</header>
			<Skeleton v-if="!data" :rows="3" />
			<template v-else>
				<p v-if="!data.can_edit" class="aps-note">แก้ได้เฉพาะ Purchase Manager / System Manager</p>
				<section v-for="d in data.docs" :key="d.doctype" class="aps-doc">
					<div class="aps-title">
						<b>{{ d.label }}</b>
						<span class="ss-tag">{{ d.words.send }} → {{ d.words.do }}</span>
						<button
							v-if="d.custom && data.can_edit"
							type="button"
							class="ss-btn ss-btn--ghost ss-btn--sm"
							:disabled="busy === d.doctype"
							@click="reset(d)"
						>
							ใช้ค่าเริ่มต้น
						</button>
					</div>
					<div class="aps-row">
						<div class="aps-label">
							<span>{{ d.words.who }}</span>
							<small>{{ people_text(d) }}</small>
						</div>
						<RolePicker
							:roles="d.roles"
							:options="data.roles"
							:disabled="!data.can_edit || busy === d.doctype"
							@change="(roles) => save(d, { roles })"
						/>
					</div>
					<div v-if="d.mode === 'sign'" class="aps-row">
						<div class="aps-label">
							<span>บันทึกการลงนามแทน</span>
							<small>ผู้ลงนามเซ็นบนกระดาษ แล้วเจ้าหน้าที่บันทึกในระบบแทน (เมนู ⋯ ของเอกสาร)</small>
						</div>
						<RolePicker
							:roles="d.proxy_roles"
							:options="data.roles"
							:disabled="!data.can_edit || busy === d.doctype"
							@change="(proxy_roles) => save(d, { proxy_roles })"
						/>
					</div>
				</section>
			</template>
		</div>
	</div>
</template>

<script setup>
import { defineComponent, h, ref } from "vue";
import Skeleton from "../Skeleton.vue";
import SelectBox from "../SelectBox.vue";
import Icon from "../Icon.vue";
import { call, post, show_error, toast } from "../../api.js";

// Role ที่เลือก = ชิปลบได้ + ช่องเลือกเพิ่ม
const RolePicker = defineComponent({
	props: { roles: Array, options: Array, disabled: Boolean },
	emits: ["change"],
	setup(props, { emit }) {
		return () =>
			h("div", { class: "aps-roles" }, [
				...props.roles.map((r) =>
					h("span", { class: "aps-chip", key: r }, [
						r,
						!props.disabled &&
							h(
								"button",
								{
									type: "button",
									"aria-label": `เอา ${r} ออก`,
									onClick: () => emit("change", props.roles.filter((x) => x !== r)),
								},
								[h(Icon, { name: "x", size: 13 })]
							),
					])
				),
				!props.disabled &&
					h(SelectBox, {
						modelValue: null,
						label: "เพิ่ม Role",
						placeholder: "+ เพิ่ม Role",
						options: props.options.filter((r) => !props.roles.includes(r)).map((r) => ({ value: r, label: r })),
						"onUpdate:modelValue": (v) => v && emit("change", [...props.roles, v]),
					}),
			]);
	},
});

const data = ref(null);
const busy = ref(null);

const people_text = (d) =>
	d.people.length ? `${d.people.length} คน: ${d.people.slice(0, 6).join(", ")}${d.people.length > 6 ? " ..." : ""}` : "ยังไม่มีผู้ใช้ที่มี Role นี้";

async function load() {
	try {
		data.value = await call("consbiz.doc_approval.get_settings");
	} catch (error) {
		show_error(error);
	}
}

async function save(d, change) {
	busy.value = d.doctype;
	try {
		data.value = await post("consbiz.doc_approval.set_roles", {
			doctype: d.doctype,
			roles: change.roles || d.roles,
			proxy_roles: change.proxy_roles || d.proxy_roles,
		});
		toast(`บันทึกการตั้งค่า${d.label}แล้ว`, "success");
	} catch (error) {
		show_error(error);
	} finally {
		busy.value = null;
	}
}

async function reset(d) {
	busy.value = d.doctype;
	try {
		data.value = await post("consbiz.doc_approval.set_roles", { doctype: d.doctype, reset: 1 });
		toast("ใช้ค่าเริ่มต้นแล้ว", "success");
	} catch (error) {
		show_error(error);
	} finally {
		busy.value = null;
	}
}

load();
</script>

<style scoped>
.aps-head h2 { margin: 0; font-size: var(--ss-fs-xl); font-weight: 650; }
.aps-head p { margin: 4px 0 12px; color: var(--ss-muted); font-size: var(--ss-fs); }
.aps-note { margin: 0 0 8px; color: var(--ss-muted); font-size: var(--ss-fs-sm); }
.aps-doc { padding: 12px 0; border-bottom: 1px solid var(--ss-border); }
.aps-title { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.aps-title b { font-weight: 650; }
.aps-title .ss-btn { margin-left: auto; }
.aps-row { display: flex; align-items: flex-start; gap: 14px; padding: 8px 0; }
.aps-label { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 3px; }
.aps-label small { color: var(--ss-muted); font-size: var(--ss-fs-sm); line-height: 1.6; }
.aps-roles { flex: none; width: 320px; display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
.aps-roles :deep(.ss-select) { flex: 1 1 100%; }
.aps-chip {
	display: inline-flex;
	align-items: center;
	gap: 4px;
	padding: 2px 6px 2px 10px;
	border-radius: 999px;
	background: var(--ss-surface-2);
	border: 1px solid var(--ss-border);
	font-size: var(--ss-fs-sm);
}
.aps-chip button { display: inline-flex; padding: 2px; border: 0; background: none; color: var(--ss-muted); cursor: pointer; }
@media (max-width: 640px) {
	.aps-row { flex-direction: column; align-items: stretch; }
	.aps-roles { width: auto; }
}
</style>
