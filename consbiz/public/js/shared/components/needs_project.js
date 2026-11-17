// หน้าที่ต้องมีโครงการ ในแอปที่โครงการเป็นแค่ตัวกรอง (ออฟฟิศ: ว่าง = ทุกโครงการ) เช่น ลงเวลาคนงาน (1 ใบต่อโครงการต่อรอบ)
// ยังไม่เลือกโครงการ = แถบบน + ปุ่มเลือกโครงการ เลือกแล้ว AppShell สร้างหน้าใหม่เอง (route_key มีโครงการ)
import { h, inject } from "vue";
import { state } from "../api.js";
import TopBar from "./TopBar.vue";
import Empty from "./Empty.vue";
import Icon from "./Icon.vue";

export function needs_project(view, title) {
	return {
		name: `NeedsProject${view.name || view.__name || ""}`,
		setup() {
			const open_picker = inject("open_project_picker", null);
			return () =>
				state.project
					? h(view)
					: h("div", [
							h(TopBar, { title }),
							h("div", { class: "ss-content" }, [
								h(
									Empty,
									{
										icon: "layers",
										title: "เลือกโครงการก่อน",
										text: "ข้อมูลหน้านี้แยกตามโครงการ",
									},
									() =>
										open_picker &&
										h(
											"button",
											{ type: "button", class: "ss-btn ss-btn--primary", onClick: open_picker },
											[h(Icon, { name: "layers", size: 16 }), h("span", "เลือกโครงการ")]
										)
								),
							]),
					  ]);
		},
	};
}
