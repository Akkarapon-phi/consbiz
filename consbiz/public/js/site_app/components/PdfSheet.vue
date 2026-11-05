<template>
	<!-- PDF ของเอกสาร: เปิดดู / แชร์ไฟล์ไปแอปอื่น (LINE, อีเมล) / ดาวน์โหลด  url จาก site_app.pdf_url -->
	<Sheet :open="open" title="เอกสาร PDF" :subtitle="`${title} ${name}`" @close="$emit('close')">
		<div class="ss-options">
			<a class="ss-option" :href="url" target="_blank" rel="noopener" @click="$emit('close')">
				<span class="ss-avatar tone-blue"><Icon name="file" :size="18" /></span>
				<span class="ss-option-main">
					<span class="ss-option-label">เปิด PDF</span>
					<span class="ss-option-desc">ดูหรือพิมพ์จากเบราว์เซอร์</span>
				</span>
			</a>
			<button v-if="can_share" type="button" class="ss-option" :disabled="busy" @click="share">
				<span class="ss-avatar tone-green">
					<span v-if="busy" class="ss-spinner"></span>
					<Icon v-else name="send" :size="18" />
				</span>
				<span class="ss-option-main">
					<span class="ss-option-label">แชร์ไฟล์ PDF</span>
					<span class="ss-option-desc">ส่งไฟล์ต่อทาง LINE อีเมล หรือแอปอื่น</span>
				</span>
			</button>
			<button type="button" class="ss-option" :disabled="busy" @click="download">
				<span class="ss-avatar tone-violet"><Icon name="receive" :size="18" /></span>
				<span class="ss-option-main">
					<span class="ss-option-label">ดาวน์โหลด</span>
					<span class="ss-option-desc">บันทึกไฟล์ {{ name }}.pdf ลงเครื่อง</span>
				</span>
			</button>
		</div>
	</Sheet>
</template>

<script setup>
import { ref } from "vue";
import Icon from "./Icon.vue";
import Sheet from "./Sheet.vue";
import { show_error } from "../api.js";

const props = defineProps({ open: Boolean, url: String, name: String, title: String });
const emit = defineEmits(["close"]);

const busy = ref(false);
// แชร์ไฟล์ได้ (มือถือส่วนใหญ่) ไม่ได้ = ดาวน์โหลดแทน
const can_share = typeof navigator !== "undefined" && !!navigator.canShare;

async function pdf_file() {
	const response = await fetch(props.url, { credentials: "same-origin" });
	if (!response.ok) throw new Error("สร้าง PDF ไม่สำเร็จ ลองเปิด PDF แทน");
	const blob = await response.blob();
	return new File([blob], `${props.name}.pdf`, { type: "application/pdf" });
}

function save_file(file) {
	const href = URL.createObjectURL(file);
	const link = Object.assign(document.createElement("a"), { href, download: file.name });
	document.body.appendChild(link);
	link.click();
	link.remove();
	setTimeout(() => URL.revokeObjectURL(href), 2000);
}

async function share() {
	busy.value = true;
	try {
		const file = await pdf_file();
		if (navigator.canShare?.({ files: [file] })) {
			await navigator.share({ files: [file], title: `${props.title} ${props.name}` });
			emit("close");
		} else {
			save_file(file);
		}
	} catch (error) {
		// ผู้ใช้ปิดหน้าต่างแชร์เอง ไม่ใช่ข้อผิดพลาด
		if (error?.name !== "AbortError") show_error(error);
	} finally {
		busy.value = false;
	}
}

async function download() {
	busy.value = true;
	try {
		save_file(await pdf_file());
		emit("close");
	} catch (error) {
		show_error(error);
	} finally {
		busy.value = false;
	}
}
</script>
