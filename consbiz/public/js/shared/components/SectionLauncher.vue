<!-- เลือกหมวดงาน (มือถือ): หมวดของกลุ่มแอปนี้ เปิดจากชิปบน hero กลุ่มอื่น/ระบบเต็มอยู่ที่หน้าแรก -->
<template>
	<Sheet :open="open" title="หมวดงาน" subtitle="เลือกงานที่จะทำ" @close="$emit('close')">
		<ModuleGrid local_only @choose="choose" />
		<button type="button" class="ss-btn ss-btn--ghost ss-btn--block ss-launcher-home" @click="choose('desktop')">
			<Icon name="grid" :size="18" />
			หน้าแรก (ทุกแอป)
		</button>
	</Sheet>
</template>

<script setup>
import Icon from "./Icon.vue";
import Sheet from "./Sheet.vue";
import ModuleGrid from "./ModuleGrid.vue";
import { switch_section } from "../api.js";

defineProps({ open: Boolean });
const emit = defineEmits(["close"]);

function choose(key) {
	emit("close");
	// ปิด sheet ก่อนแล้วค่อยเปลี่ยนหน้า (ไม่ให้ 2 animation ชนกัน)
	setTimeout(() => switch_section(key), 160);
}
</script>
