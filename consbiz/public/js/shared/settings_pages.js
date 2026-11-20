// หัวข้อของหน้าตั้งค่า (SettingsDialog.vue) ที่เดียวทั้งแอป แยก 2 ชุด (ตกลง 2026-11-18)
// - ตั้งค่าส่วนตัว (เมนู avatar → ตั้งค่า): ข้อมูลส่วนตัว การแสดงผล + ของผู้ดูแลระบบ (สิทธิ์การใช้งาน ไม่ใช่ของหมวดใด)
// - ตั้งค่าของหมวด (เมนู ⋯ ในหัวรายการ ListHead): section.settings / groups[].settings = key ของหัวข้อแรกที่เปิด
//   หน้าต่างของหมวดแสดงทุกหัวข้อที่ module ตรงกัน (เช่น บุคคล = 4 หัวข้อตามกลุ่มเมนู)
// หัวข้อใหม่: เพิ่มที่ PERSONAL หรือ MODULE (group = หัวข้อหลักในเมนูซ้าย, props = ส่งให้ component, when = เห็นตามสิทธิ์)
import PermissionSettings from "./components/settings/PermissionSettings.vue";
import LabourSettings from "./components/settings/LabourSettings.vue";
import HrSettings from "./components/settings/HrSettings.vue";
import ProfileSettings from "./components/settings/ProfileSettings.vue";
import AppearanceSettings from "./components/settings/AppearanceSettings.vue";
import ContractTemplates from "./components/settings/ContractTemplates.vue";
import PrintSettings from "./components/settings/PrintSettings.vue";
import ApprovalSettings from "./components/settings/ApprovalSettings.vue";
import { boot } from "./api.js";

const has_hr = () => (boot.sections || []).includes("hr");

const PERSONAL = [
	{ key: "profile", group: "บัญชีของฉัน", label: "ข้อมูลส่วนตัว", icon: "user", component: ProfileSettings, when: () => !boot.guest },
	{ key: "appearance", group: "บัญชีของฉัน", label: "การแสดงผล", icon: "sun", component: AppearanceSettings },
	{
		key: "permissions",
		group: "ผู้ดูแลระบบ",
		label: "สิทธิ์การใช้งาน",
		icon: "shield",
		component: PermissionSettings,
		when: () => boot.can?.settings,
	},
];

// หมวดบุคคล: 1 หัวข้อต่อกลุ่มเมนู (module ตรงกับ hr_setup.MODULES)
const HR = [
	{ key: "hr-time", label: "เวลาทำงาน", icon: "clock", module: "time" },
	{ key: "hr-pay", label: "เงินเดือน", icon: "wallet", module: "pay" },
	{ key: "hr-expense", label: "ค่าใช้จ่าย", icon: "receive", module: "expense" },
	{ key: "hr-people", label: "พนักงาน", icon: "users", module: "people" },
];

const MODULE = [
	...HR.map((p) => ({
		key: p.key,
		module: "hr",
		group: "บุคคล",
		label: p.label,
		icon: p.icon,
		component: HrSettings,
		props: { module: p.module, label: p.label },
		when: has_hr,
	})),
	// แม่แบบสัญญาจ้าง (ตกลง 2026-11-18, consbiz/contract_terms.py) อยู่ท้ายหัวข้อของหมวดบุคคล
	{
		key: "hr-contract-templates",
		module: "hr",
		group: "บุคคล",
		label: "แม่แบบสัญญาจ้าง",
		icon: "file",
		component: ContractTemplates,
		when: () => has_hr() && !!boot.hr_docs?.["hr-contracts"],
	},
	// หมวดจัดซื้อ: แบบฟอร์มพิมพ์ของใบขอซื้อ/สั่งซื้อ/แจ้งหนี้ (ตกลง 2026-11-18, consbiz/print_settings.py)
	{
		key: "purchase-print",
		module: "purchase",
		group: "จัดซื้อ",
		label: "แบบฟอร์มพิมพ์",
		icon: "printer",
		component: PrintSettings,
		props: { section: "buy" },
		when: () => (boot.sections || []).includes("purchase"),
	},
	// หมวดจัดซื้อ: Role ที่อนุมัติใบขอซื้อ / ลงนามใบสั่งซื้อ-ใบแจ้งหนี้ซื้อ + บันทึกการลงนามแทน (ตกลง 2026-11-19, consbiz/doc_approval.py)
	{
		key: "purchase-approval",
		module: "purchase",
		group: "จัดซื้อ",
		label: "การอนุมัติ/ลงนาม",
		icon: "check",
		component: ApprovalSettings,
		when: () => (boot.sections || []).includes("purchase"),
	},
	{
		key: "labour",
		module: "labour",
		group: "คนงาน",
		label: "บัญชีค่าแรง",
		icon: "calculator",
		component: LabourSettings,
		when: () => boot.can?.labour_settings,
	},
];

const allowed = (p) => !p.when || p.when();

export const personal_pages = () => PERSONAL.filter(allowed);

// หัวข้อของหมวดที่มี key นี้ (ทุกหัวข้อ module เดียวกัน) ไม่มีสิทธิ์ = []
export function module_pages(key) {
	const first = MODULE.find((p) => p.key === key);
	if (!first || !allowed(first)) return [];
	return MODULE.filter((p) => p.module === first.module && allowed(p));
}
