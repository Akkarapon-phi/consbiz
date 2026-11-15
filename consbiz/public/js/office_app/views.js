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
import KindList from "./views/common/KindList.vue";
import SarabanView from "./views/saraban/SarabanView.vue";
import SarabanForm from "./views/saraban/SarabanForm.vue";
import AgreementPage from "./views/subcontract/AgreementPage.vue";
import ClaimPage from "./views/subcontract/ClaimPage.vue";
import VariationPage from "./views/subcontract/VariationPage.vue";
import RetentionPage from "./views/retention/RetentionPage.vue";
import HrDocPage from "./views/hr/HrDocPage.vue";
import PaymentPage from "./views/accounting/PaymentPage.vue";
import WhtPage from "./views/accounting/WhtPage.vue";
import TaxInvoicePage from "./views/accounting/TaxInvoicePage.vue";
import TaxReport from "./views/accounting/TaxReport.vue";
import MasterPage from "./views/master/MasterPage.vue";

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
	"letters-in": KindList,
	"letters-out": KindList,
	transmittals: KindList,
	envelopes: KindList,
	"saraban-doc": SarabanView,
	"saraban-form": SarabanForm,
	agreements: KindList,
	claims: KindList,
	agreement: AgreementPage,
	claim: ClaimPage,
	variations: KindList,
	variation: VariationPage,
	"acc-receipts": KindList,
	"acc-payments": KindList,
	"acc-wht": KindList,
	"acc-sales-tax": KindList,
	"acc-purchase-tax": KindList,
	"acc-payment": PaymentPage,
	"acc-wht-doc": WhtPage,
	"acc-tax-doc": TaxInvoicePage,
	"acc-tax-report": TaxReport,
	"acc-retention-in": KindList,
	"acc-retention-out": KindList,
	"sell-retention": KindList,
	"buy-retention": KindList,
	"acc-retention-in-doc": RetentionPage,
	"acc-retention-out-doc": RetentionPage,
	"sell-retention-doc": RetentionPage,
	"buy-retention-doc": RetentionPage,
	"hr-contracts": KindList,
	"hr-wht": KindList,
	"hr-doc": HrDocPage,
	"md-employees": KindList,
	"md-items": KindList,
	"md-customers": KindList,
	"md-suppliers": KindList,
	"md-projects": KindList,
	"md-doc": MasterPage,
};
