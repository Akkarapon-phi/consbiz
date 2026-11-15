// หมวดบัญชี (API consbiz/accounting_app.py): รับชำระ / จ่ายชำระ (Payment Entry), หนังสือรับรองหัก ณ ที่จ่าย (Withholding Tax Cert),
// ภาษีขาย / ภาษีซื้อ (Sales / Purchase Tax Invoice ของ erpnext_thailand) รายการใช้ KindList, key = ชื่อหน้ารายการใน sections.js
// รับ/จ่ายชำระสร้างจากหน้าใบแจ้งหนี้ (PaymentSheet.vue) ใบกำกับภาษีระบบสร้างเอง หนังสือรับรองออกจากหน้าจ่ายชำระ จึงไม่มีปุ่มสร้างในรายการ

export const API = "consbiz.accounting_app";

const posted = (r) => r.docstatus === 1;

function payment_kind(view, side) {
	const receive = side === "receive";
	return {
		api: API,
		boot: "accounting",
		label: receive ? "รับชำระ" : "จ่ายชำระ",
		icon: receive ? "receive" : "send",
		title: (r) => r.refs || r.remarks || "—",
		title_label: "ใบแจ้งหนี้",
		party: (r) => r.party_name || r.party,
		party_label: receive ? "ลูกค้า" : "ผู้ขาย / ผรม.",
		date: "posting_date",
		date_label: receive ? "วันที่รับ" : "วันที่จ่าย",
		amount: "amount",
		amount_label: receive ? "ยอดรับ" : "ยอดจ่าย",
		note: (r) =>
			[r.mode_of_payment, r.tax_invoice_number ? `ใบกำกับ ${r.tax_invoice_number}` : null]
				.filter(Boolean)
				.join(" · ") || null,
		search: [
			"name",
			"refs",
			"party",
			"party_name",
			"project",
			"reference_no",
			"tax_invoice_number",
		],
		filters: [
			{ value: "all", label: "ทั้งหมด", test: (r) => r.docstatus < 2 },
			...(receive
				? []
				: [
						{
							value: "wht",
							label: "รอออกหนังสือหัก ณ ที่จ่าย",
							test: (r) => posted(r) && r.has_wht && r.wht_status !== "Issued",
						},
				  ]),
			{ value: "draft", label: "ร่าง", test: (r) => r.docstatus === 0 },
			{ value: "cancelled", label: "ยกเลิก", test: (r) => r.docstatus === 2 },
		],
		open: (r) => ["acc-payment", { kind: view, name: r.name }],
	};
}

function tax_kind(view, side) {
	const sales = side === "sales";
	return {
		api: API,
		boot: "accounting",
		label: sales ? "ภาษีขาย" : "ภาษีซื้อ",
		icon: sales ? "trending" : "cart",
		title: (r) => (sales ? r.voucher_no : r.number) || r.voucher_no || "—",
		title_label: sales ? "เอกสารอ้างอิง" : "เลขที่ใบกำกับผู้ขาย",
		party: (r) => r.party_name || r.party,
		party_label: sales ? "ลูกค้า" : "ผู้ขาย",
		date: "report_date",
		date_label: "เดือนที่ยื่น",
		amount: "amount",
		amount_label: "ภาษี",
		note: (r) => (r.tax_base ? `ฐาน ${Number(r.tax_base).toLocaleString("th-TH")}` : null),
		search: ["name", "number", "voucher_no", "party", "party_name", "tax_id"],
		filters: [
			{ value: "all", label: "ทั้งหมด", test: (r) => r.docstatus === 1 },
			{
				value: "month",
				label: "เดือนนี้",
				test: (r) =>
					r.docstatus === 1 && (r.report_date || "").slice(0, 7) === this_month(),
			},
			{ value: "draft", label: "ร่าง", test: (r) => r.docstatus === 0 },
		],
		open: (r) => ["acc-tax-doc", { kind: view, name: r.name }],
	};
}

function this_month() {
	const d = new Date();
	return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

export const ACCOUNTING_KINDS = {
	"acc-receipts": payment_kind("acc-receipts", "receive"),
	"acc-payments": payment_kind("acc-payments", "pay"),
	"acc-wht": {
		api: API,
		boot: "accounting",
		label: "หนังสือรับรองหัก ณ ที่จ่าย",
		icon: "file",
		title: (r) =>
			`${r.income_tax_form === "PND3" ? "ภ.ง.ด.3" : "ภ.ง.ด.53"}${
				r.refs ? ` · ${r.refs}` : ""
			}`,
		title_label: "แบบ / จ่ายชำระ",
		party: (r) => r.party_name || r.party,
		party_label: "ผู้ถูกหัก",
		date: "date",
		date_label: "วันที่จ่าย",
		amount: "amount",
		amount_label: "ภาษีที่หัก",
		note: (r) => (r.tax_base ? `ฐาน ${Number(r.tax_base).toLocaleString("th-TH")}` : null),
		search: ["name", "refs", "party", "party_name"],
		filters: [
			{ value: "all", label: "ทั้งหมด", test: (r) => r.docstatus < 2 },
			{
				value: "pnd3",
				label: "ภ.ง.ด.3",
				test: (r) => r.docstatus < 2 && r.income_tax_form === "PND3",
			},
			{
				value: "pnd53",
				label: "ภ.ง.ด.53",
				test: (r) => r.docstatus < 2 && r.income_tax_form === "PND53",
			},
			{ value: "draft", label: "ร่าง", test: (r) => r.docstatus === 0 },
			{ value: "cancelled", label: "ยกเลิก", test: (r) => r.docstatus === 2 },
		],
		open: (r) => ["acc-wht-doc", { name: r.name }],
	},
	"acc-sales-tax": tax_kind("acc-sales-tax", "sales"),
	"acc-purchase-tax": tax_kind("acc-purchase-tax", "purchase"),
};

// หน้าเอกสารที่ไม่มี kind ใน URL → หน้ารายการ (ปุ่มย้อนกลับ + ไฮไลต์เมนู)
export const DOC_PAGES = { "acc-wht-doc": "acc-wht" };

export const FORM_LABEL = { PND3: "ภ.ง.ด.3", PND53: "ภ.ง.ด.53" };
