// หน้า (view) ของแอปผู้รับเหมา → component (ชื่อตรงกับ ROUTES ใน sections.js)
import Agreements from "./views/Agreements.vue";
import Claims from "./views/Claims.vue";
import AgreementView from "./views/AgreementView.vue";
import ClaimForm from "./views/ClaimForm.vue";

import { boot } from "../shared/api.js";

// เปิดจากลิงก์ของสัญญา (boot.agreement): หน้าแรก = สัญญานั้น
export default {
	contractor: boot.agreement ? AgreementView : Agreements,
	"contractor-claims": Claims,
	"contractor-agreement": AgreementView,
	"contractor-claim": ClaimForm,
};
