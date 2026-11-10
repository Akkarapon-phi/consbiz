// เอกสารโครงการที่สร้าง/แก้/ดูในแอป (API consbiz/project_docs.py, ช่องตรงกับ KINDS ของไฟล์นั้น)
// ขอตรวจงาน/Punch List อยู่หมวดควบคุมงาน (คนหน้างานบางคนไม่มีสิทธิ์เข้าหมวดแผนงาน) งานลด-เพิ่ม/EOT อยู่หมวดแผนงาน
const PM = { view: "pm-doc", form: "pm-doc-form", list: "pm-docs" };
const WORK = { view: "site-doc", form: "site-form", list: "inspections" };

export const PROJECT_KINDS = {
	vo: { ...PM, doctype: "Variation Order", label: "งานลด-เพิ่ม", icon: "swap", list_params: { tab: "vo" } },
	eot: { ...PM, doctype: "Extension of Time", label: "ขยายเวลา (EOT)", icon: "clock", list_params: { tab: "eot" } },
	inspection: { ...WORK, doctype: "Inspection Request", label: "ขอตรวจงาน", icon: "search-check", list_params: {}, quick: true },
	punch: { ...WORK, doctype: "Punch List", label: "Punch List", icon: "list-checks", list_params: { tab: "punch" }, quick: true },
};

export const CAUSES = [
	{ value: "Variation Order", label: "งานเพิ่ม-ลด" },
	{ value: "Employer Delay", label: "ผู้ว่าจ้างล่าช้า" },
	{ value: "Force Majeure", label: "เหตุสุดวิสัย" },
	{ value: "Other", label: "อื่นๆ" },
];
export const cause_label = (value) => CAUSES.find((c) => c.value === value)?.label || value;

export const EMPLOYER_STATUS = [
	{ value: "Pending", label: "รออนุมัติ" },
	{ value: "Approved", label: "อนุมัติแล้ว" },
	{ value: "Rejected", label: "ไม่อนุมัติ" },
];
export const RESULTS = [
	{ value: "Pending", label: "รอตรวจ" },
	{ value: "Passed", label: "ผ่าน" },
	{ value: "Passed with Comments", label: "ผ่าน (มีข้อแนะนำ)" },
	{ value: "Failed", label: "ไม่ผ่าน" },
];
export const VARIATION_TYPES = [
	{ value: "Addition", label: "งานเพิ่ม" },
	{ value: "Omission", label: "งานลด" },
];
