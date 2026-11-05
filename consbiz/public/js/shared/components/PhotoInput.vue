<template>
	<div class="ss-photos">
		<TransitionGroup name="ss-pop">
			<div v-for="(photo, i) in modelValue" :key="photo.name || photo.preview" class="ss-photo">
				<img :src="photo.preview || photo.file_url" alt="" />
				<div v-if="photo.uploading" class="ss-photo-progress"><span class="ss-spinner"></span></div>
				<button type="button" class="ss-photo-remove" aria-label="ลบรูป" @click="remove(i)">
					<Icon name="x" :size="14" :stroke="3" />
				</button>
			</div>
		</TransitionGroup>
		<label v-if="modelValue.length < max" class="ss-photo-add">
			<input type="file" accept="image/*" capture="environment" :multiple="max > 1" @change="add" />
			<Icon name="camera" :size="24" />
			<span>{{ label }}</span>
		</label>
	</div>
</template>

<script setup>
// ถ่าย/เลือกรูป อัปโหลดทันที (ไฟล์ยังไม่ผูกเอกสาร) v-model = [{name, file_url}]
import Icon from "./Icon.vue";
import { show_error, upload } from "../api.js";

const props = defineProps({
	modelValue: { type: Array, default: () => [] },
	max: { type: Number, default: 4 },
	label: { type: String, default: "ถ่ายรูป" },
});
const emit = defineEmits(["update:modelValue"]);

async function add(event) {
	const files = [...event.target.files].slice(0, props.max - props.modelValue.length);
	event.target.value = "";
	for (const file of files) {
		const photo = { preview: URL.createObjectURL(file), uploading: true };
		let list = [...props.modelValue, photo];
		emit("update:modelValue", list);
		try {
			const saved = await upload(file);
			list = props.modelValue.map((p) =>
				p === photo || p.preview === photo.preview ? { ...p, ...saved, uploading: false } : p
			);
			emit("update:modelValue", list);
		} catch (error) {
			show_error(error);
			emit(
				"update:modelValue",
				props.modelValue.filter((p) => p.preview !== photo.preview)
			);
		}
	}
}

function remove(index) {
	const list = [...props.modelValue];
	list.splice(index, 1);
	emit("update:modelValue", list);
}
</script>
