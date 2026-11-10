// ของกลางสำหรับหน้าที่แสดงเป็นตารางบนแท็บเล็ต/จอใหญ่ และการ์ดบนมือถือ
import { nextTick, onBeforeUnmount, ref, watch } from "vue";

export function use_wide() {
	const mq = window.matchMedia("(min-width: 768px)");
	const wide = ref(mq.matches);
	const update = () => (wide.value = mq.matches);
	mq.addEventListener("change", update);
	onBeforeUnmount(() => mq.removeEventListener("change", update));
	return wide;
}

export function matches(query, ...values) {
	const q = (query || "").trim().toLowerCase();
	return !q || values.filter(Boolean).join(" ").toLowerCase().includes(q);
}

// แถวเดียวแบบ flex-wrap: ลูกที่ตกลงบรรทัดถัดไปถูกซ่อน (visibility ไม่เปลี่ยนเลย์เอาต์ จึงไม่เกิดวนวัด)
// คืน ref: มีลูกถูกซ่อนหรือไม่ sources = ค่าที่เปลี่ยนความกว้างของลูก (เช่น ข้อความของตัวกรอง)
export function use_overflow_row(box, sources = []) {
	const hidden = ref(false);
	function measure() {
		const children = [...(box.value?.children || [])];
		if (!children.length) {
			hidden.value = false;
			return;
		}
		const first = Math.min(...children.map((el) => el.offsetTop));
		const left = box.value.getBoundingClientRect().left;
		let any = false;
		for (const el of children) {
			// ล้นซ้าย = กล่องแคบกว่าลูกตัวแรก (ลูกตัวเดียวในบรรทัดจึงไม่ตกบรรทัด)
			const over = el.offsetTop > first || el.getBoundingClientRect().left < left - 1;
			el.style.visibility = over ? "hidden" : "";
			any ||= over;
		}
		hidden.value = any;
	}
	const observer = new ResizeObserver(measure);
	watch(box, (el, old) => {
		if (old) observer.unobserve(old);
		if (el) observer.observe(el);
	});
	watch(sources, () => nextTick(measure));
	onBeforeUnmount(() => observer.disconnect());
	return hidden;
}
