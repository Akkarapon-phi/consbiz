// Tab "ภาพรวม", "ทรัพยากร", "Look-ahead", "การเงิน" และ "เอกสารโครงการ" ในฟอร์ม Construction Management (โหลดจาก construction_management.js ด้วย frappe.require)
// ฝั่ง server: consbiz/consbiz/doctype/construction_management/dashboard.py (ทรัพยากร: resources.py)
import { createApp } from "vue";
import Dashboard from "./Dashboard.vue";
import Documents from "./Documents.vue";
import Finance from "./Finance.vue";
import LookAhead from "./LookAhead.vue";
import Resources from "./Resources.vue";

class ProjectView {
	constructor({ wrapper, name }, component) {
		this.name = name;
		this.app = createApp(component, { name });
		SetVueGlobals(this.app);
		this.view = this.app.mount(wrapper);
	}

	reload() {
		this.view.load();
	}

	destroy() {
		this.app.unmount();
	}
}

frappe.provide("consbiz");
consbiz.ProjectDashboard = class extends ProjectView {
	constructor(options) {
		super(options, Dashboard);
	}
};
consbiz.ProjectLookAhead = class extends ProjectView {
	constructor(options) {
		super(options, LookAhead);
	}
};
consbiz.ProjectResources = class extends ProjectView {
	constructor(options) {
		super(options, Resources);
	}
};
consbiz.ProjectFinance = class extends ProjectView {
	constructor(options) {
		super(options, Finance);
	}
};
consbiz.ProjectDocuments = class extends ProjectView {
	constructor(options) {
		super(options, Documents);
	}
};
