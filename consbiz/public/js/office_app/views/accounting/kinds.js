// หมวดบัญชี (API consbiz/accounting_app.py): รับชำระ / จ่ายชำระ (Payment Entry), หนังสือรับรองหัก ณ ที่จ่าย (Withholding Tax Cert),
// ภาษีขาย / ภาษีซื้อ (Sales / Purchase Tax Invoice ของ erpnext_thailand) รายการใช้ KindList, key = ชื่อหน้ารายการใน sections.js
// รับ/จ่ายชำระสร้างจากหน้าใบแจ้งหนี้ (PaymentSheet.vue) ใบกำกับภาษีระบบสร้างเอง หนังสือรับรองออกจากหน้าจ่ายชำระ จึงไม่มีปุ่มสร้างในรายการ

import { thai_date } from "../../../shared/api.js";

export const API = "consbiz.accounting_app";

const posted = (r) => r.docstatus === 1;
export const TAX_STATUS_FILTERS = [
	{ value: "submitted", label: "ยืนยันแล้ว", test: posted },
	{ value: "cancelled", label: "ยกเลิก", test: (r) => r.docstatus === 2 },
	{ value: "all", label: "ทั้งหมด", test: () => true },
];

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
		table_pair: {
			project: true,
			fields: [
				{ key: "refs", label: "ใบแจ้งหนี้" },
				{ key: "tax_invoice_number", label: "ใบกำกับภาษี" },
			],
			after_date: [{ key: "mode_of_payment", label: "วิธีชำระ" }],
		},
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

function cheque_kind(view, receive) {
	const bank = (r) => [r.bank_account || r.bank, r.account].filter(Boolean).join(" · ");
	const cleared = (r) => r.clearance_date && thai_date(r.clearance_date, { year: true });
	return {
		api: API,
		boot: "accounting",
		label: receive ? "เช็ครับ" : "เช็คจ่าย",
		icon: receive ? "receive" : "send",
		title: (r) => r.party_name || r.party || r.name,
		party: (r) => r.party_name || r.party,
		party_label: receive ? "ลูกค้า" : "ผู้รับเงิน",
		date: "reference_date",
		date_label: "วันที่หน้าเช็ค",
		amount: "amount",
		amount_label: "ยอด",
		amount_currency: true,
		overflow_tabs: true,
		table_pair: {
			project: true,
			fields: [
				{ key: "reference_no", label: "เลขที่เช็ค" },
				{ key: "account", label: "ธนาคาร/บัญชี", format: bank },
			],
			after_date: [{ key: "clearance_date", label: "วันที่เช็คผ่าน", format: cleared, class: "col-date is-date" }],
		},
		card_details: (r) => [
			r.reference_no && `เลขที่เช็ค ${r.reference_no}`, bank(r),
			r.clearance_date && `วันที่เช็คผ่าน ${cleared(r)}`,
		].filter(Boolean),
		status_note: (r) => r.postdated && "ลงวันที่ล่วงหน้า",
		search: ["name", "party", "party_name", "project", "project_name", "reference_no", "account", "bank_account", "bank"],
		filters: [
			{ value: "all", label: "ทั้งหมด", test: () => true },
			{ value: "waiting", label: "รอผ่าน", test: (r) => r.waiting },
			{ value: "postdated", label: "ลงวันที่ล่วงหน้า", test: (r) => r.postdated },
			{ value: "cleared", label: "ผ่านแล้ว", test: (r) => posted(r) && r.clearance_date },
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
		table_pair: {
			fields: [
				...(!sales ? [{ key: "number", label: "เลขที่ใบกำกับผู้ขาย" }] : []),
				{ key: "voucher_no", label: "เอกสารอ้างอิง" },
			],
		},
		note: (r) => (r.tax_base ? `ฐาน ${Number(r.tax_base).toLocaleString("th-TH")}` : null),
		search: ["name", "number", "voucher_no", "party", "party_name", "tax_id"],
		filters: TAX_STATUS_FILTERS,
		overflow_tabs: true,
		open: (r) => ["acc-tax-doc", { kind: view, name: r.name }],
	};
}

export const ACCOUNTING_KINDS = {
	"acc-cheques-in": cheque_kind("acc-cheques-in", true),
	"acc-cheques-out": cheque_kind("acc-cheques-out", false),
	"acc-receipts": payment_kind("acc-receipts", "receive"),
	"acc-payments": payment_kind("acc-payments", "pay"),
	"acc-wht": {
		api: API,
		boot: "accounting",
		label: "ภาษีหัก ณ ที่จ่าย",
		overflow_tabs: true,
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
		table_pair: {
			fields: [
				{
					key: "income_tax_form",
					label: "แบบ",
					format: (r) => FORM_LABEL[r.income_tax_form] || r.income_tax_form,
				},
				{ key: "refs", label: "จ่ายชำระ" },
			],
		},
		note: (r) => (r.tax_base ? `ฐาน ${Number(r.tax_base).toLocaleString("th-TH")}` : null),
		search: ["name", "refs", "party", "party_name"],
		filters: TAX_STATUS_FILTERS,
		open: (r) => ["acc-wht-doc", { name: r.name }],
	},
	"acc-sales-tax": tax_kind("acc-sales-tax", "sales"),
	"acc-purchase-tax": tax_kind("acc-purchase-tax", "purchase"),
};

// หน้าเอกสารที่ไม่มี kind ใน URL → หน้ารายการ (ปุ่มย้อนกลับ + ไฮไลต์เมนู)
export const DOC_PAGES = { "acc-ledger-account": "acc-general-ledger", "acc-bank-detail": "acc-bank-accounts", "acc-wht-doc": "acc-wht" };

export const FORM_LABEL = { PND3: "ภ.ง.ด.3", PND53: "ภ.ง.ด.53" };
