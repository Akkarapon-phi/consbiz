<!-- ยืนยันลบเอกสาร (ใช้ทุกหน้าดูเอกสารของแอป) ปุ่มที่เปิดแผงนี้ต้องแสดงตามสิทธิ์ (can_delete จาก server)
     method / args = API ลบ เสร็จแล้ว emit deleted ให้หน้าเรียกใช้พาออกจากเอกสาร -->
<template>
	<Sheet :open="open" :title="`ลบ${label}`" @close="$emit('close')">
		<p class="ss-muted">ลบ {{ name }} ถาวร ย้อนกลับไม่ได้</p>
		<template #footer>
			<button type="button" class="ss-btn ss-btn--danger ss-btn--block ss-btn--lg" :disabled="busy" @click="remove">
				<span v-if="busy" class="ss-spinner"></span>
				<template v-else>ยืนยันลบ</template>
			</button>
		</template>
	</Sheet>
</template>

<script setup>
import { ref } from "vue";
import Sheet from "./Sheet.vue";
import { post, show_error, toast } from "../api.js";

const props = defineProps({
	open: Boolean,
	label: { type: String, default: "เอกสาร" },
	name: { type: String, default: "" },
	method: { type: String, required: true },
	args: { type: Object, required: true },
});
const emit = defineEmits(["close", "deleted"]);
const busy = ref(false);

async function remove() {
	busy.value = true;
	try {
		await post(props.method, props.args);
		toast(`ลบ ${props.name} แล้ว`, "success");
		emit("close");
		emit("deleted");
	} catch (error) {
		show_error(error);
	} finally {
		busy.value = false;
	}
}
</script>
