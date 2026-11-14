// หน้า (view) ของแอปหน้างาน → component (ชื่อตรงกับ ROUTES ใน sections.js)
// สโตร์
import Home from "./views/store/Home.vue";
import Receive from "./views/store/Receive.vue";
import ReceiveForm from "./views/store/ReceiveForm.vue";
import ReceiptView from "./views/store/ReceiptView.vue";
import Issue from "./views/store/Issue.vue";
import Borrow from "./views/store/Borrow.vue";
import BorrowDetail from "./views/store/BorrowDetail.vue";
import BorrowNew from "./views/store/BorrowNew.vue";
import Stock from "./views/store/Stock.vue";
// ควบคุมงาน
import WorkHome from "./views/work/WorkHome.vue";
import ReportForm from "./views/work/ReportForm.vue";
import ReportView from "./views/work/ReportView.vue";
import Reports from "./views/work/Reports.vue";
import Inspections from "./views/work/Inspections.vue";
import Concrete from "./views/work/Concrete.vue";
import ConcreteForm from "./views/work/ConcreteForm.vue";
import Labour from "./views/admin/Labour.vue";
import Workers from "./views/admin/Workers.vue";
import Advances from "./views/admin/Advances.vue";
// แผนงาน
import PmHome from "./views/pm/PmHome.vue";
import Plan from "./views/pm/Plan.vue";
import PlanEdit from "./views/pm/PlanEdit.vue";
import Lookahead from "./views/pm/Lookahead.vue";
import PmDocs from "./views/pm/PmDocs.vue";
import ProjectDocForm from "./views/project_docs/ProjectDocForm.vue";
import ProjectDocView from "./views/project_docs/ProjectDocView.vue";
// ทรัพยากร
import Resources from "./views/resources/Resources.vue";
// การเงิน
import Finance from "./views/finance/Finance.vue";
// ขอซื้อ (ชุดเดียวกับแอปออฟฟิศ เฉพาะ kind = mr)
import DocsHome from "../shared/docs/DocsHome.vue";
import DocList from "../shared/docs/DocList.vue";
import DocView from "../shared/docs/DocView.vue";
import DocForm from "../shared/docs/DocForm.vue";

export default {
	home: Home,
	receive: Receive,
	"receive-form": ReceiveForm,
	receipt: ReceiptView,
	issue: Issue,
	concrete: Concrete,
	"concrete-form": ConcreteForm,
	labour: Labour,
	workers: Workers,
	advances: Advances,
	borrow: Borrow,
	"borrow-detail": BorrowDetail,
	"borrow-new": BorrowNew,
	stock: Stock,
	work: WorkHome,
	reports: Reports,
	"report-form": ReportForm,
	"report-view": ReportView,
	inspections: Inspections,
	pm: PmHome,
	plan: Plan,
	"plan-edit": PlanEdit,
	lookahead: Lookahead,
	"pm-docs": PmDocs,
	"pm-doc": ProjectDocView,
	"pm-doc-form": ProjectDocForm,
	"site-doc": ProjectDocView,
	"site-form": ProjectDocForm,
	resources: Resources,
	"resource-supply": Resources,
	"resource-people": Resources,
	"resource-gantt": Resources,
	"resource-monthly": Resources,
	finance: Finance,
	buy: DocsHome,
	mr: DocList,
	"buy-doc": DocView,
	"buy-form": DocForm,
};
