<!-- ถ่ายรูปสดจากกล้อง (getUserMedia) เลือกไฟล์จากเครื่องไม่ได้ ใช้กับเซลฟี่ลงเวลา
     ภาพตัวอย่างกลับซ้าย-ขวาแบบกระจก แต่รูปที่ได้ไม่กลับ ย่อเหลือด้านยาว max px เป็น JPEG (quality)
     emit("capture", dataURL) ปิดแล้วหยุดกล้องทันที (ไฟกล้องดับ) ต้องเป็น HTTPS หรือ localhost -->
<template>
	<Teleport to="body">
		<Transition name="ss-backdrop">
			<div v-if="open" class="ss-camera" role="dialog" aria-modal="true" :aria-label="title">
				<div class="ss-camera-head">
					<b>{{ title }}</b>
					<button type="button" class="ss-icon-btn" aria-label="ปิด" @click="$emit('close')">
						<Icon name="x" />
					</button>
				</div>
				<div class="ss-camera-view">
					<video
						v-show="ready"
						ref="video"
						class="ss-camera-video"
						:class="{ 'is-mirror': facing === 'user' }"
						autoplay
						playsinline
						muted
					></video>
					<div v-if="!ready" class="ss-camera-note">
						<template v-if="error">
							<Icon name="camera" :size="32" />
							<span>{{ error }}</span>
							<button type="button" class="ss-btn ss-btn--soft" @click="start">ลองอีกครั้ง</button>
						</template>
						<span v-else class="ss-spinner"></span>
					</div>
				</div>
				<div class="ss-camera-foot">
					<span></span>
					<button
						type="button"
						class="ss-camera-shutter"
						aria-label="ถ่ายรูป"
						:disabled="!ready"
						@click="capture"
					></button>
					<button
						v-if="can_switch"
						type="button"
						class="ss-icon-btn ss-camera-switch"
						aria-label="สลับกล้อง"
						@click="switch_camera"
					>
						<Icon name="refresh" :size="22" />
					</button>
					<span v-else></span>
				</div>
			</div>
		</Transition>
	</Teleport>
</template>

<script setup>
import { nextTick, onBeforeUnmount, ref, watch } from "vue";
import Icon from "./Icon.vue";

const props = defineProps({
	open: Boolean,
	title: { type: String, default: "ถ่ายรูป" },
	// user = กล้องหน้า, environment = กล้องหลัง
	facing_mode: { type: String, default: "user" },
	max: { type: Number, default: 480 },
	quality: { type: Number, default: 0.6 },
});
const emit = defineEmits(["capture", "close"]);

const video = ref(null);
const ready = ref(false);
const error = ref("");
const facing = ref(props.facing_mode);
const can_switch = ref(false);
let stream = null;

function stop() {
	stream?.getTracks().forEach((track) => track.stop());
	stream = null;
	ready.value = false;
}

async function start() {
	stop();
	error.value = "";
	if (!navigator.mediaDevices?.getUserMedia) {
		error.value = window.isSecureContext
			? "เบราว์เซอร์นี้เปิดกล้องไม่ได้"
			: "เปิดกล้องได้เฉพาะเว็บที่เป็น HTTPS";
		return;
	}
	try {
		stream = await navigator.mediaDevices.getUserMedia({
			video: { facingMode: facing.value, width: { ideal: 960 }, height: { ideal: 960 } },
			audio: false,
		});
		if (!props.open) return stop();
		await nextTick();
		if (!video.value) return stop();
		video.value.srcObject = stream;
		await video.value.play().catch(() => {});
		ready.value = true;
		const devices = await navigator.mediaDevices.enumerateDevices().catch(() => []);
		can_switch.value = devices.filter((d) => d.kind === "videoinput").length > 1;
	} catch (e) {
		stop();
		error.value =
			e?.name === "NotAllowedError"
				? "ไม่ได้รับอนุญาตให้ใช้กล้อง เปิดสิทธิ์กล้องของเบราว์เซอร์แล้วลองใหม่"
				: e?.name === "NotFoundError" || e?.name === "OverconstrainedError"
				? "ไม่พบกล้องในอุปกรณ์นี้"
				: e?.name === "NotReadableError"
				? "กล้องถูกใช้งานโดยแอปอื่นอยู่"
				: "เปิดกล้องไม่ได้";
	}
}

function switch_camera() {
	facing.value = facing.value === "user" ? "environment" : "user";
	start();
}

function capture() {
	const el = video.value;
	if (!el?.videoWidth) return;
	const scale = Math.min(1, props.max / Math.max(el.videoWidth, el.videoHeight));
	const canvas = document.createElement("canvas");
	canvas.width = Math.round(el.videoWidth * scale);
	canvas.height = Math.round(el.videoHeight * scale);
	canvas.getContext("2d").drawImage(el, 0, 0, canvas.width, canvas.height);
	emit("capture", canvas.toDataURL("image/jpeg", props.quality));
}

watch(
	() => props.open,
	(open) => {
		if (open) {
			facing.value = props.facing_mode;
			start();
		} else stop();
	},
	{ immediate: true }
);
onBeforeUnmount(stop);
</script>
