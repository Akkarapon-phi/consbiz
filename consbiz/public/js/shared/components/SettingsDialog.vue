<!-- หน้าต่างตั้งค่า ใช้ 2 ที่ (ตกลง 2026-11-18, หัวข้ออยู่ shared/settings_pages.js):
     ตั้งค่าส่วนตัว (เมนู avatar: personal_pages) / ตั้งค่าของหมวด (เมนู ⋯ ในหัวรายการ: module_pages) initial = หัวข้อที่เปิดก่อน
     ซ้าย = เมนูแบ่งตามหัวข้อหลัก (group) ขวา = การตั้งค่า หัวข้อเดียว = ไม่มีเมนูซ้าย -->
<template>
	<Sheet :open="open && !!page" :title="title" wide @close="emit('close')">
		<div v-if="open && page" class="ss-settings" :class="{ 'is-single': pages.length < 2 }">
			<nav v-if="pages.length > 1" class="ss-settings-menu" aria-label="หัวข้อการตั้งค่า">
				<template v-for="g in groups" :key="g.label">
					<div class="ss-settings-group">{{ g.label }}</div>
					<button
						v-for="p in g.pages"
						:key="p.key"
						type="button"
						class="ss-settings-link"
						:class="{ 'is-active': p.key === page.key }"
						@click="active = p.key"
					>
						<Icon :name="p.icon" :size="16" />
						<span>{{ p.label }}</span>
					</button>
				</template>
			</nav>
			<div class="ss-settings-body">
				<component :is="page.component" :key="page.key" v-bind="page.props || {}" />
			</div>
		</div>
	</Sheet>
</template>

<script setup>
import { computed, provide, ref, watch } from "vue";
import Sheet from "./Sheet.vue";
import Icon from "./Icon.vue";

const props = defineProps({
	open: Boolean,
	pages: { type: Array, required: true },
	title: { type: String, default: "ตั้งค่า" },
	initial: { type: String, default: null },
});
const emit = defineEmits(["close"]);
// หัวข้อที่พาไปหน้าอื่นในแอป ปิดหน้าต่างก่อน (HrSettings ลิงก์ในแอป)
provide("close_settings", () => emit("close"));

const groups = computed(() =>
	props.pages.reduce((out, p) => {
		let g = out.find((x) => x.label === p.group);
		if (!g) out.push((g = { label: p.group, pages: [] }));
		g.pages.push(p);
		return out;
	}, [])
);
const active = ref(null);
const page = computed(() => props.pages.find((p) => p.key === active.value) || props.pages[0]);
// เปิดจากปุ่มตั้งค่าของหมวด = ไปหัวข้อนั้น (ไม่ระบุ = หัวข้อที่เปิดล่าสุด)
watch(
	() => [props.open, props.initial],
	([open, initial]) => {
		if (open && initial && props.pages.some((p) => p.key === initial)) active.value = initial;
	},
	{ immediate: true }
);
</script>
