<!-- ข้อมูลส่วนตัวของผู้ใช้ที่ล็อกอิน (เปิดจากเมนู avatar ท้าย Dock) หัวข้อตามฟอร์ม User ของระบบเต็ม ดูอย่างเดียว แก้ไขที่ระบบเต็ม -->
<template>
	<Sheet :open="open" title="ข้อมูลส่วนตัว" @close="emit('close')">
		<div class="ss-profile-head">
			<span class="ss-avatar ss-profile-avatar" :class="`tone-${tone(boot.user || '')}`">
				<img v-if="boot.user_image && !broken" :src="boot.user_image" alt="" @error="broken = true" />
				<template v-else>{{ initials(boot.full_name || boot.user || "") }}</template>
			</span>
			<div class="ss-profile-name">
				<strong>{{ boot.full_name }}</strong>
				<span>{{ boot.user }}</span>
			</div>
		</div>

		<Skeleton v-if="!profile" />
		<template v-else>
			<section v-for="group in groups" :key="group.title" class="ss-profile-group">
				<div class="ss-section-title">{{ group.title }}</div>
				<dl class="ss-kv">
					<template v-for="row in group.rows" :key="row.label">
						<dt>{{ row.label }}</dt>
						<dd>{{ row.value || "-" }}</dd>
					</template>
				</dl>
			</section>
		</template>

		<template v-if="boot.desk" #footer>
			<a class="ss-btn ss-btn--soft" :href="`/app/user/${encodeURIComponent(boot.user)}`">แก้ไขในระบบเต็ม</a>
		</template>
	</Sheet>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import Sheet from "./Sheet.vue";
import Skeleton from "./Skeleton.vue";
import { boot, call, initials, show_error, thai_date, tone } from "../api.js";

const props = defineProps({ open: Boolean });
const emit = defineEmits(["close"]);

const profile = ref(null);
const broken = ref(false);

const groups = computed(() => {
	const p = profile.value;
	return [
		{
			title: "ข้อมูลผู้ใช้",
			rows: [
				{ label: "ชื่อ", value: p.first_name },
				{ label: "ชื่อกลาง", value: p.middle_name },
				{ label: "นามสกุล", value: p.last_name },
				{ label: "อีเมล", value: p.email },
				{ label: "ชื่อผู้ใช้", value: p.username },
				{ label: "ภาษา", value: p.language },
				{ label: "เขตเวลา", value: p.time_zone },
			],
		},
		{
			title: "ข้อมูลเพิ่มเติม",
			rows: [
				{ label: "เพศ", value: p.gender },
				{ label: "วันเกิด", value: p.birth_date && thai_date(p.birth_date, { year: true }) },
				{ label: "โทรศัพท์", value: p.phone },
				{ label: "มือถือ", value: p.mobile_no },
				{ label: "สถานที่", value: p.location },
				{ label: "ความสนใจ", value: p.interest },
				{ label: "เกี่ยวกับฉัน", value: p.bio },
			],
		},
	];
});

watch(
	() => props.open,
	async (open) => {
		if (!open) return;
		profile.value = null;
		try {
			profile.value = await call("consbiz.site_app.get_my_profile");
		} catch (error) {
			show_error(error);
			emit("close");
		}
	}
);
</script>
