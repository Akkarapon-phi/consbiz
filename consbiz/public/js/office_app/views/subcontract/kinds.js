// เอกสารของหมวดผู้รับเหมาช่วง (API consbiz/subcontract_app.py) key = ชื่อหน้ารายการใน sections.js
// หน้าดู/แก้ = 1 หน้าต่อเอกสาร (agreement, claim) แบบ BOQ

export const API = "consbiz.subcontract_app";

export const BILLING_METHODS = [
	{ value: "Measured", label: "ตามปริมาณงานจริง" },
	{ value: "Milestone", label: "ตามงวดงาน" },
];
export const billing_label = (value) =>
	BILLING_METHODS.find((m) => m.value === value)?.label || value;

const status_is =
	(...values) =>
	(row) =>
		values.includes(row.status);

export const SUBCONTRACT_KINDS = {
	agreements: {
		api: API,
		boot: "subcontract",
		doctype: "Subcontract Agreement",
		label: "สัญญาจ้างเหมาช่วง",
		icon: "file",
		title: (row) => row.title,
		title_label: "งานที่จ้าง",
		party: (row) => row.supplier_name || row.supplier,
		party_label: "ผู้รับเหมา",
		date: "contract_date",
		date_label: "วันทำสัญญา",
		amount: "total_amount",
		amount_label: "มูลค่าสัญญา",
		note: (row) =>
			row.docstatus === 1 ? `เบิกแล้ว ${Math.round(row.progress_percent || 0)}%` : null,
		search: ["name", "title", "supplier_name", "project"],
		filters: [
			{ value: "active", label: "ดำเนินการ", test: status_is("Active") },
			{ value: "draft", label: "ร่าง", test: status_is("Draft") },
			{ value: "completed", label: "เบิกครบ", test: status_is("Completed") },
			{ value: "closed", label: "ปิดสัญญา", test: status_is("Closed") },
			{ value: "all", label: "ทั้งหมด", test: () => true },
		],
		open: (row) => ["agreement", { name: row.name }],
		create: () => ["agreement", { name: "new" }],
	},
	claims: {
		api: API,
		boot: "subcontract",
		doctype: "Subcontract Claim",
		label: "ใบเบิกงวด",
		icon: "receive",
		title: (row) => `งวดที่ ${row.claim_no || "-"} · ${row.title || ""}`,
		title_label: "งวด / งาน",
		party: (row) => row.supplier_name,
		party_label: "ผู้รับเหมา",
		date: "posting_date",
		date_label: "วันที่เบิก",
		amount: "gross_amount",
		amount_label: "มูลค่างวด",
		search: ["name", "title", "supplier_name", "project", "subcontract_agreement"],
		filters: [
			{ value: "draft", label: "รออนุมัติ", test: (r) => r.docstatus === 0 },
			{
				value: "to-invoice",
				label: "รอตั้งหนี้",
				test: (r) => r.docstatus === 1 && !r.purchase_invoice,
			},
			{
				value: "invoiced",
				label: "ตั้งหนี้แล้ว",
				test: (r) => r.docstatus === 1 && !!r.purchase_invoice,
			},
			{ value: "all", label: "ทั้งหมด", test: () => true },
		],
		open: (row) => ["claim", { name: row.name }],
		create: () => ["claim", { name: "new" }],
	},
	variations: {
		api: API,
		boot: "subcontract",
		doctype: "Subcontract Variation",
		label: "ใบงานเพิ่ม ผรม.",
		icon: "plus",
		title: (row) => `แก้ไขครั้งที่ ${row.revision_no || "-"} · ${row.title || ""}`,
		title_label: "ครั้งที่ / งาน",
		party: (row) => row.supplier_name,
		party_label: "ผู้รับเหมา",
		date: "posting_date",
		date_label: "วันที่",
		amount: "addition_amount",
		amount_label: "มูลค่างานเพิ่ม",
		search: ["name", "title", "supplier_name", "project", "subcontract_agreement"],
		filters: [
			{ value: "draft", label: "รออนุมัติ", test: (r) => r.docstatus === 0 },
			{ value: "approved", label: "อนุมัติแล้ว", test: (r) => r.docstatus === 1 },
			{ value: "all", label: "ทั้งหมด", test: () => true },
		],
		open: (row) => ["variation", { name: row.name }],
		create: () => ["variation", { name: "new" }],
	},
};
