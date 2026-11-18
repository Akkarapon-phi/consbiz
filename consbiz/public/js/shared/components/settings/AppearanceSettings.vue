<!-- ตั้งค่าส่วนตัว > การแสดงผล (avatar > ตั้งค่า, ตกลง 2026-11-18): โหมดสี ตามเครื่อง / สว่าง / มืด (shared/theme.js จำในเครื่องนี้) -->
<template>
	<div class="ss-settings-form">
		<div class="ss-settings-form-inner">
			<header class="as-head">
				<h2>การแสดงผล</h2>
				<p>ค่าที่เลือกใช้กับเครื่องนี้เท่านั้น</p>
			</header>
			<div class="as-row">
				<div class="as-label">
					<b>โหมดสี</b>
					<small>ตามเครื่อง = สว่าง/มืดตามที่ตั้งในโทรศัพท์หรือคอมพิวเตอร์</small>
				</div>
				<div class="as-themes" role="radiogroup" aria-label="โหมดสี">
					<button
						v-for="t in OPTIONS"
						:key="t.value"
						type="button"
						class="as-theme"
						:class="{ 'is-active': theme === t.value }"
						role="radio"
						:aria-checked="theme === t.value"
						@click="pick(t.value)"
					>
						<span class="as-swatch" :class="`as-swatch--${t.value}`"></span>
						<span>{{ t.label }}</span>
					</button>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { ref } from "vue";
import { get_theme, set_theme } from "../../theme.js";

const OPTIONS = [
	{ value: "auto", label: "ตามเครื่อง" },
	{ value: "light", label: "สว่าง" },
	{ value: "dark", label: "มืด" },
];
const theme = ref(get_theme());
function pick(value) {
	theme.value = value;
	set_theme(value);
}
</script>

<style scoped>
.as-head h2 { margin: 0; font-size: var(--ss-fs-xl); font-weight: 650; }
.as-head p { margin: 4px 0 0; color: var(--ss-muted); font-size: var(--ss-fs); }
.as-row {
	display: flex;
	align-items: center;
	gap: 14px;
	padding: 14px 0;
	border-bottom: 1px solid var(--ss-border);
}
.as-label { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 3px; }
.as-label b { font-weight: 600; }
.as-label small { color: var(--ss-muted); font-size: var(--ss-fs-sm); }
.as-themes { display: flex; gap: 10px; flex: none; }
.as-theme {
	display: flex;
	flex-direction: column;
	align-items: center;
	gap: 6px;
	padding: 6px;
	border: 1.5px solid var(--ss-border);
	border-radius: 14px;
	background: transparent;
	color: var(--ss-text-2);
	font-size: var(--ss-fs-sm);
	cursor: pointer;
}
.as-theme.is-active { border-color: var(--ss-brand); color: var(--ss-text); font-weight: 600; }
.as-swatch { display: block; width: 72px; height: 44px; border-radius: 9px; border: 1px solid var(--ss-border); }
.as-swatch--light { background: linear-gradient(#17233f 0 30%, #f2f4f8 30%); }
.as-swatch--dark { background: linear-gradient(#17233f 0 30%, #0b1020 30%); }
.as-swatch--auto { background: linear-gradient(90deg, transparent 50%, #0b1020 50%), linear-gradient(#17233f 0 30%, #f2f4f8 30%); }
@media (max-width: 767px) {
	.as-row { flex-direction: column; align-items: stretch; }
	.as-themes { justify-content: space-between; }
	.as-theme { flex: 1; }
	.as-swatch { width: 100%; }
}
</style>
