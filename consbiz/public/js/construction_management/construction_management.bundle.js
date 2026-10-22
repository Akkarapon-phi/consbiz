// หน้า Gantt + S-Curve ของ Construction Schedule (โหลดจาก page/construction_gantt ด้วย frappe.require)
import { createApp } from "vue";
import App from "./App.vue";

class ConstructionGantt {
	constructor({ wrapper, page, schedule }) {
		this.app = createApp(App, { page, schedule });
		SetVueGlobals(this.app);
		this.app.mount(wrapper);
	}

	destroy() {
		this.app.unmount();
	}
}

frappe.provide("consbiz");
consbiz.ConstructionGantt = ConstructionGantt;
