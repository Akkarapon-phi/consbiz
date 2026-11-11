// หน้า (view) ของแอปออฟฟิศ → component (ชื่อตรงกับ ROUTES ใน sections.js)
// จัดซื้อ / ขาย (ชุดเดียวกับแอปหน้างาน แยกตาม kind)
import DocsHome from "../shared/docs/DocsHome.vue";
import DocList from "../shared/docs/DocList.vue";
import DocView from "../shared/docs/DocView.vue";
import DocForm from "../shared/docs/DocForm.vue";
import BoqList from "./views/boq/BoqList.vue";
import BoqForm from "./views/boq/BoqForm.vue";
import HrAttendance from "./views/hr/HrAttendance.vue";
import HrPayroll from "./views/hr/HrPayroll.vue";
import HrSetup from "./views/hr/HrSetup.vue";
import HrAdjustments from "./views/hr/HrAdjustments.vue";
import HrSalaries from "./views/hr/HrSalaries.vue";
import HrAdvances from "./views/hr/HrAdvances.vue";

export default {
	buy: DocsHome,
	sell: DocsHome,
	mr: DocList,
	po: DocList,
	pi: DocList,
	qtn: DocList,
	so: DocList,
	si: DocList,
	"buy-doc": DocView,
	"sell-doc": DocView,
	"buy-form": DocForm,
	"sell-form": DocForm,
	boq: BoqList,
	"boq-form": BoqForm,
	"hr-attendance": HrAttendance,
	"hr-payroll": HrPayroll,
	"hr-setup": HrSetup,
	"hr-adjustments": HrAdjustments,
	"hr-salaries": HrSalaries,
	"hr-advances": HrAdvances,
};
