<template>
	<!-- เลือกหมวดงาน: ตารางไอคอน (เพิ่มหมวดได้ไม่จำกัด) เปิดจากชิปบน hero (มือถือ) หรือชื่อแอปบนแถบข้าง -->
	<Sheet
		:open="open"
		title="หมวดงาน"
		subtitle="เลือกงานที่จะทำ ข้อมูลเป็นของโครงการที่เลือก"
		@close="$emit('close')"
	>
		<div class="ss-launcher">
			<button
				v-for="(s, i) in sections"
				:key="s.key"
				type="button"
				class="ss-app-tile"
				:class="{ 'is-active': s.key === state.section }"
				:style="{ '--i': i, '--sw': s.colors[0], '--sw2': s.colors[1] }"
				@click="choose(s.key)"
			>
				<span class="ss-app-tile-icon">
					<Icon :name="s.icon" :size="28" :stroke="2" />
					<span v-if="badge(s)" class="ss-app-tile-badge">{{ badge(s) }}</span>
				</span>
				<span class="ss-app-tile-label">{{ s.title }}</span>
				<span class="ss-app-tile-note">{{ s.note }}</span>
				<span v-if="s.key === state.section" class="ss-app-tile-check"
					><Icon name="check" :size="14" :stroke="3"
				/></span>
			</button>
			<a
				v-if="boot.desk"
				class="ss-app-tile is-desk"
				href="/app"
				:style="{ '--i': sections.length, '--sw': '#64748b', '--sw2': '#334155' }"
			>
				<span class="ss-app-tile-icon"><Icon name="monitor" :size="28" :stroke="2" /></span>
				<span class="ss-app-tile-label">ระบบเต็ม</span>
				<span class="ss-app-tile-note">เอกสารและรายงานทั้งหมด</span>
			</a>
		</div>
	</Sheet>
</template>

<script setup>
import { computed } from "vue";
import Icon from "./Icon.vue";
import Sheet from "./Sheet.vue";
import { SECTIONS } from "../sections.js";
import { boot, state, switch_section, vibrate } from "../api.js";

defineProps({ open: Boolean });
const emit = defineEmits(["close"]);

const sections = computed(() => boot.sections.map((key) => SECTIONS[key]));
const badge = (section) => section.badge?.(state.summaries[section.key]) || 0;

function choose(key) {
	vibrate(10);
	emit("close");
	// ปิด sheet ก่อนแล้วค่อยเปลี่ยนหน้า (ไม่ให้ 2 animation ชนกัน)
	setTimeout(() => switch_section(key), 160);
}
</script>
