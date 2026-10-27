<script setup>
// ห่อ Frappe control (Date, Int, Float ...) ให้ใช้ใน Vue ด้วย v-model
// ใช้ control ของ Frappe เพื่อให้ date picker และรูปแบบวันที่ตรงกับหน้าฟอร์มอื่น
import { onMounted, ref, watch } from "vue";

const props = defineProps({
	df: { type: Object, required: true },
	modelValue: { default: null },
	autofocus: Boolean,
});
const emit = defineEmits(["update:modelValue"]);

const wrapper = ref(null);
let control;

onMounted(() => {
	control = frappe.ui.form.make_control({
		parent: wrapper.value,
		df: {
			fieldname: "value",
			...props.df,
			change(event) {
				// Data ส่ง change ทุกครั้งที่หยุดพิมพ์ (event input) ช่องจะปิดกลางคัน รอ Enter หรือออกจากช่องแทน
				if (event?.type === "input") return;
				const value = control.get_value();
				if (value !== props.modelValue) emit("update:modelValue", value);
			},
		},
		render_input: true,
		only_input: true,
	});
	control.set_value(props.modelValue ?? "");
	// Frappe เปิด date picker ชิดซ้ายของช่องเสมอ ช่องที่อยู่ขวาของจอจะล้นขอบ ให้สลับไปชิดขวาเมื่อที่ไม่พอ
	if (control.update_datepicker_position) {
		const update_position = control.update_datepicker_position.bind(control);
		control.update_datepicker_position = () => {
			update_position();
			const picker = control.datepicker;
			const right = control.$input.offset().left + picker.$datepicker.outerWidth();
			if (right > $(window).width() - 8) {
				picker.update("position", picker.opts.position.replace("left", "right"));
			}
		};
	}
	if (props.autofocus) {
		// รอให้ control ตั้งค่าเสร็จก่อน ไม่งั้นโฟกัสหลุดและ date picker ไม่เปิด
		setTimeout(() => {
			control.$input.get(0)?.focus();
			control.$input.get(0)?.select?.();
		}, 50);
	}
});

watch(
	() => props.modelValue,
	(value) => {
		if (control && value !== control.get_value()) control.set_value(value ?? "");
	}
);

defineExpose({ get_control: () => control });
</script>

<template>
	<div ref="wrapper" class="cs-control" />
</template>

<style scoped>
.cs-control :deep(.form-control) {
	height: 26px;
	padding: 2px 8px;
	font-size: var(--text-sm);
}
.cs-control :deep(.form-group) {
	margin: 0;
}
</style>
