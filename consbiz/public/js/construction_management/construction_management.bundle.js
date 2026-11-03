// หน้า Gantt + S-Curve ของ Construction Schedule (โหลดด้วย frappe.require)
// จาก page/construction_gantt (เต็มจอ) หรือ Tab "Gantt" ของฟอร์ม (embedded: ดูอย่างเดียว ใช้ page จำลองแทน Header ของฟอร์ม)
import { createApp } from "vue";
import App from "./App.vue";
import "./toolbar.css";
import { make_embedded_page } from "./embedded_page";

class ConstructionGantt {
	constructor({ wrapper, page, schedule, embedded = false, is_active, on_saved }) {
		this.name = schedule;
		this.app = createApp(App, {
			page: embedded ? make_embedded_page() : page,
			schedule,
			embedded,
			isActive: is_active,
			onSaved: on_saved,
		});
		SetVueGlobals(this.app);
		this.view = this.app.mount(wrapper);
	}

	// เปิด Tab หรือกลับมาที่ฟอร์ม: คำนวณความสูงใหม่ (ตอนสร้างใน Tab ที่ซ่อนอยู่วัดตำแหน่งไม่ได้)
	// และโหลดใหม่ถ้าแผนถูกแก้ (เช่น เพิ่งแก้ในหน้าเต็มจอ) ไม่เปลี่ยนก็ไม่โหลด ตำแหน่งที่เลื่อนไว้ไม่หาย
	activate() {
		this.view.fit_height();
		this.view.check_remote();
	}

	destroy() {
		this.app.unmount();
	}
}

frappe.provide("consbiz");
consbiz.ConstructionGantt = ConstructionGantt;
