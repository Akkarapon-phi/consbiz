// คีย์ลัดของแอปที่เปิด app.shortcuts (ออฟฟิศ, จอใช้คีย์บอร์ด) เรียกใน setup ของหน้า: use_shortcuts({ "/": fn, n: fn })
// ไม่ทำงานขณะพิมพ์ในช่องกรอก, กดคู่ Ctrl/Alt/⌘ หรือมีหน้าต่าง (sheet) เปิดอยู่
import { onBeforeUnmount, onMounted } from "vue";
import { app } from "./app.js";

const typing = (el) =>
	el?.closest?.("input, textarea, select, [contenteditable=''], [contenteditable='true']");

export function use_shortcuts(keys) {
	if (!app.shortcuts) return;
	const handler = (event) => {
		if (event.ctrlKey || event.metaKey || event.altKey || event.defaultPrevented) return;
		if (typing(event.target) || document.querySelector(".ss-sheet")) return;
		const run = keys[event.key];
		if (!run) return;
		event.preventDefault();
		run(event);
	};
	onMounted(() => window.addEventListener("keydown", handler));
	onBeforeUnmount(() => window.removeEventListener("keydown", handler));
}
