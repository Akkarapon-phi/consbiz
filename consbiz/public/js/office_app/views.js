// หน้า (view) ของแอปออฟฟิศ → component (ชื่อตรงกับ ROUTES ใน sections.js)
// จัดซื้อ / ขาย (ชุดเดียวกับแอปหน้างาน แยกตาม kind)
import DocsHome from "../shared/docs/DocsHome.vue";
import DocList from "../shared/docs/DocList.vue";
import DocView from "../shared/docs/DocView.vue";
import DocForm from "../shared/docs/DocForm.vue";
import { needs_project } from "../shared/components/needs_project.js";
import Labour from "./views/labour/Labour.vue";
import Workers from "./views/labour/Workers.vue";
import Advances from "./views/labour/Advances.vue";
import BoqList from "./views/boq/BoqList.vue";
import BoqForm from "./views/boq/BoqForm.vue";
import HrAttendance from "./views/hr/HrAttendance.vue";
import HrPayroll from "./views/hr/HrPayroll.vue";
import HrSetup from "./views/hr/HrSetup.vue";
import HrAdjustments from "./views/hr/HrAdjustments.vue";
import HrSalaries from "./views/hr/HrSalaries.vue";
import HrAdvances from "./views/hr/HrAdvances.vue";
import HrShifts from "./views/hr/HrShifts.vue";
import HrEmployees from "./views/hr/HrEmployees.vue";
import HrEmployee from "./views/hr/HrEmployee.vue";
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
import BankList from "./views/accounting/BankList.vue";
import BankDetail from "./views/accounting/BankDetail.vue";
import TaxReport from "./views/accounting/TaxReport.vue";
import AccountDashboard from "./views/accounting/AccountDashboard.vue";
import ReceivedWht from "./views/accounting/ReceivedWht.vue";
import AccountChart from "./views/accounting/AccountChart.vue";
import AccountLedger from "./views/accounting/AccountLedger.vue";
import ComingSoon from "./views/accounting/ComingSoon.vue";
import MasterPage from "./views/master/MasterPage.vue";
import { ACCOUNTING_PLACEHOLDERS } from "./sections.js";

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
	// เบิกเงินแยกตามกลุ่มเมนู (HrAdvances.vue เลือกชนิดจากชื่อหน้า)
	"hr-salary-advances": HrAdvances,
	"hr-expense-advances": HrAdvances,
	"hr-claims": HrAdvances,
	"hr-shifts": HrShifts,
	"hr-employees": HrEmployees,
	"hr-employee": HrEmployee,
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
	...Object.fromEntries(Object.keys(ACCOUNTING_PLACEHOLDERS).map((view) => [view, ComingSoon])),
	"acc-dashboard": AccountDashboard,
	"acc-wht-received": ReceivedWht,
	"acc-general-ledger": AccountChart,
	"acc-ledger-account": AccountLedger,
	"acc-si": DocList,
	"acc-pi": DocList,
	"acc-invoice-doc": DocView,
	"acc-invoice-form": DocForm,
	"acc-expense-advances": HrAdvances,
	"acc-receipts": KindList,
	"acc-cheques-in": KindList,
	"acc-cheques-out": KindList,
	"acc-payments": KindList,
	"acc-wht": TaxReport,
	"acc-sales-tax": TaxReport,
	"acc-purchase-tax": TaxReport,
	"acc-payment": PaymentPage,
	"acc-wht-doc": WhtPage,
	"acc-tax-doc": TaxInvoicePage,
	"acc-tax-report": TaxReport,
	"acc-bank-accounts": BankList,
	"acc-bank-detail": BankDetail,
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
	"hr-warnings": KindList,
	"hr-doc": HrDocPage,
	"md-employees": KindList,
	"md-items": KindList,
	"md-customers": KindList,
	"md-suppliers": KindList,
	"md-projects": KindList,
	"md-doc": MasterPage,
	labour: needs_project(Labour, "ลงเวลาคนงาน"),
	advances: needs_project(Advances, "เบิกล่วงหน้า"),
	workers: needs_project(Workers, "ทะเบียนคนงาน"),
};
