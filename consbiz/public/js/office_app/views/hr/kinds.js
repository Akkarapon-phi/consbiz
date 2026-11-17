// เอกสารพนักงานของหมวดบุคคล (API consbiz/hr_docs.py) key = ชื่อหน้ารายการ = KINDS ใน hr_docs.py
// หน้าเอกสาร = hr-doc/<kind>/<name> (HrDocPage.vue)

export const API = "consbiz.hr_docs";

const draft = (r) => r.docstatus === 0;
const done = (r) => r.docstatus === 1;

export const HR_DOC_KINDS = {
	"hr-contracts": {
		api: API,
		boot: "hr_docs",
		label: "สัญญาจ้าง",
		icon: "file",
		title: (r) => r.full_name || r.employee,
		title_label: "พนักงาน",
		party: (r) => r.employee,
		party_label: "รหัสพนักงาน",
		date: "date",
		date_label: "วันที่",
		amount: "base",
		amount_label: "เงินเดือน",
		note: (r) =>
			r.prob_end_date && done(r) && !r.probation
				? `ครบทดลองงาน ${new Date(r.prob_end_date).toLocaleDateString("th-TH", {
						day: "numeric",
						month: "short",
						year: "2-digit",
				  })}`
				: null,
		search: ["name", "full_name", "employee"],
		filters: [
			{
				value: "due",
				label: "รอประเมินทดลองงาน",
				test: (r) => done(r) && !r.probation && r.status_tone === "amber",
			},
			{
				value: "probation",
				label: "ทดลองงาน",
				test: (r) => done(r) && !r.probation,
			},
			{ value: "draft", label: "ร่าง", test: draft },
			{ value: "all", label: "ทั้งหมด", test: () => true },
		],
		open: (r) => ["hr-doc", { kind: "hr-contracts", name: r.name }],
		create: () => ["hr-doc", { kind: "hr-contracts", name: "new" }],
	},
	"hr-wht": {
		api: API,
		boot: "hr_docs",
		label: "หนังสือรับรองหัก ณ ที่จ่าย",
		icon: "receive",
		title: (r) => r.full_name || r.employee,
		title_label: "ผู้ถูกหักภาษี",
		party: (r) =>
			[
				r.income_tax_form,
				r.tax_payer === "Withholding" ? "หัก ณ ที่จ่าย" : "ออกให้ครั้งเดียว",
			]
				.filter(Boolean)
				.join(" · "),
		party_label: "แบบ / ผู้จ่ายภาษี",
		date: "date",
		date_label: "วันที่จ่าย",
		amount: "tax_amount",
		amount_label: "ภาษีที่หัก",
		search: ["name", "full_name", "employee"],
		filters: [
			{ value: "draft", label: "ร่าง", test: draft },
			{ value: "done", label: "ยืนยันแล้ว", test: done },
			{ value: "all", label: "ทั้งหมด", test: () => true },
		],
		open: (r) => ["hr-doc", { kind: "hr-wht", name: r.name }],
		create: () => ["hr-doc", { kind: "hr-wht", name: "new" }],
	},
};
