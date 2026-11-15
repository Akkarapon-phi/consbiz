// หมวดงานของแอปออฟฟิศ (/conserp/purchase, /conserp/sales: /conserp/<หมวด>/<หน้า>/<params...>) ตั้งค่าแอปที่ office_app.bundle.js (configure)
// งานออฟฟิศบนจอใหญ่: จัดซื้อ (ขอซื้อ → สั่งซื้อ → แจ้งหนี้) / ขาย (เสนอราคา → สั่งขาย → แจ้งหนี้)
// บัญชี: รับ/จ่ายชำระ ภาษี หัก ณ ที่จ่าย + เงินประกันผลงาน (หมวดขาย/จัดซื้อมีเมนูเงินประกันของฝั่งตัวเองด้วย) เพิ่มหมวดใหม่: SECTIONS + ROUTES + views.js + สิทธิ์ใน site_app.office_sections
// ชื่อหน้า (view) ห้ามซ้ำข้ามหมวด เพราะ go("<view>") หาหมวดจากชื่อหน้า

import { boot } from "../shared/api.js";
import { MODULE_META } from "../shared/modules.js";

export const SECTIONS = {
	// docs = ชุดเอกสาร (DOC_KINDS[].section) ของหมวด เมื่อชื่อหมวดใน URL ต่างจากชุดเอกสาร
	purchase: {
		key: "purchase",
		...MODULE_META.office.purchase,
		docs: "buy",
		home: "buy",
		tabs: [
			{ view: "buy", label: "หน้าหลัก", icon: "home" },
			{
				view: "mr",
				label: "ขอซื้อ",
				icon: "clipboard",
				badge: (s) => s?.mr_todo?.count,
				when: (b) => b.docs?.mr?.read,
			},
			{ view: "po", label: "สั่งซื้อ", icon: "cart", when: (b) => b.docs?.po?.read },
			{
				view: "pi",
				label: "แจ้งหนี้",
				when: (b) => b.docs?.pi?.read,
				icon: "file",
				alert: (s) => s?.pi_overdue?.count,
				badge: (s) => s?.pi_overdue?.count,
			},
			// เงินประกันที่หัก ผรม. (retention_app, สิทธิ์ของ Retention Payable / Release)
			{
				view: "buy-retention",
				label: "เงินประกัน",
				icon: "shield",
				when: (b) => b.retention?.sides?.out,
				badge: (s) => s?.retention_out?.count,
				alert: (s) => s?.retention_out?.late,
			},
		],
		badge: (s) => s?.mr_todo?.count,
	},
	sales: {
		key: "sales",
		...MODULE_META.office.sales,
		docs: "sell",
		home: "sell",
		tabs: [
			{ view: "sell", label: "หน้าหลัก", icon: "home" },
			{
				view: "qtn",
				label: "เสนอราคา",
				icon: "file",
				badge: (s) => s?.qtn_open?.count,
				when: (b) => b.docs?.qtn?.read,
			},
			{
				view: "so",
				label: "สั่งขาย",
				icon: "clipboard-check",
				when: (b) => b.docs?.so?.read,
			},
			{
				view: "si",
				label: "แจ้งหนี้",
				when: (b) => b.docs?.si?.read,
				icon: "receive",
				alert: (s) => s?.si_overdue?.count,
				badge: (s) => s?.si_overdue?.count,
			},
			// เงินประกันที่ผู้ว่าจ้างหัก (retention_app, สิทธิ์ของ Retention Receivable / Invoice)
			{
				view: "sell-retention",
				label: "เงินประกัน",
				icon: "shield",
				when: (b) => b.retention?.sides?.in,
				badge: (s) => s?.retention_in?.count,
				alert: (s) => s?.retention_in?.late,
			},
		],
		badge: (s) => s?.si_overdue?.count,
	},
	boq: {
		key: "boq",
		...MODULE_META.office.boq,
		home: "boq",
		tabs: [{ view: "boq", label: "BOQ", icon: "calculator" }],
	},
	hr: {
		key: "hr",
		...MODULE_META.office.hr,
		home: "hr-attendance",
		tabs: [
			{
				view: "hr-attendance",
				label: "สรุปวันทำงาน",
				icon: "calendar",
				badge: (s) => s?.flag,
				alert: (s) => s?.flag,
			},
			{
				view: "hr-adjustments",
				label: "เพิ่ม/หัก",
				icon: "list",
				when: (b) => b.can?.payroll,
			},
			{
				view: "hr-payroll",
				label: "เงินเดือน",
				icon: "receive",
				when: (b) => b.can?.payroll,
			},
			{
				view: "hr-salaries",
				label: "ค่าจ้างพนักงาน",
				icon: "users",
				when: (b) => b.can?.payroll,
			},
			{ view: "hr-advances", label: "เบิกเงิน", icon: "swap" },
			{ view: "hr-setup", label: "ตั้งค่า HR", icon: "sliders" },
		],
		badge: (s) => s?.flag,
	},
	// สารบรรณ: 1 ชนิดเอกสาร = 1 เมนู (views/saraban/kinds.js, API consbiz/saraban.py)
	saraban: {
		key: "saraban",
		...MODULE_META.office.saraban,
		// หน้าแรกของหมวด = เมนูแรกที่ผู้ใช้เปิดได้ (สิทธิ์แยกตามชนิดเอกสาร)
		get home() {
			return (this.tabs.find((t) => t.when(boot)) || this.tabs[0]).view;
		},
		tabs: [
			{
				view: "letters-in",
				label: "หนังสือเข้า",
				icon: "inbox",
				when: (b) => b.saraban?.["letters-in"],
				badge: (s) => s?.to_approve?.count,
				alert: (s) => s?.to_approve?.count,
			},
			{
				view: "letters-out",
				label: "หนังสือออก",
				icon: "send",
				when: (b) => b.saraban?.["letters-out"],
			},
			{
				view: "transmittals",
				label: "ใบนำส่งเอกสาร",
				icon: "layers",
				when: (b) => b.saraban?.transmittals,
				badge: (s) => s?.to_send?.count,
			},
			{
				view: "envelopes",
				label: "ใบปะหน้าซอง",
				icon: "mail",
				when: (b) => b.saraban?.envelopes,
			},
		],
		badge: (s) => s?.to_approve?.count,
	},
	// ผู้รับเหมาช่วง: สัญญา + ใบเบิกงวด + ใบงานเพิ่ม (views/subcontract, API consbiz/subcontract_app.py)
	subcontract: {
		key: "subcontract",
		...MODULE_META.office.subcontract,
		get home() {
			return (this.tabs.find((t) => t.when(boot)) || this.tabs[0]).view;
		},
		tabs: [
			{
				view: "agreements",
				label: "สัญญา",
				icon: "file",
				when: (b) => b.subcontract?.agreements,
			},
			{
				view: "claims",
				label: "ใบเบิกงวด",
				icon: "receive",
				when: (b) => b.subcontract?.claims,
				badge: (s) => (s?.claims_draft?.count || 0) + (s?.to_invoice?.count || 0),
				alert: (s) => s?.claims_draft?.count,
			},
			{
				view: "variations",
				label: "ใบงานเพิ่ม",
				icon: "plus",
				when: (b) => b.subcontract?.variations,
				badge: (s) => s?.variations_draft?.count,
				alert: (s) => s?.variations_draft?.count,
			},
		],
		badge: (s) => s?.claims_draft?.count,
	},
	// บัญชี: รับ/จ่ายชำระ, หัก ณ ที่จ่าย, ภาษีขาย/ซื้อ, รายงานภาษี (views/accounting, API consbiz/accounting_app.py)
	// + เงินประกันผลงาน 2 ฝั่ง (views/retention, API consbiz/retention_app.py)
	accounting: {
		key: "accounting",
		...MODULE_META.office.accounting,
		get home() {
			return (this.tabs.find((t) => t.when(boot)) || this.tabs[0]).view;
		},
		tabs: [
			{
				view: "acc-receipts",
				label: "รับชำระ",
				icon: "receive",
				when: (b) => b.accounting?.["acc-receipts"],
				badge: (s) => s?.receipts_draft?.count,
			},
			{
				view: "acc-payments",
				label: "จ่ายชำระ",
				icon: "send",
				when: (b) => b.accounting?.["acc-payments"],
				badge: (s) => s?.payments_draft?.count,
			},
			{
				view: "acc-wht",
				label: "หัก ณ ที่จ่าย",
				icon: "file",
				when: (b) => b.accounting?.["acc-wht"],
				badge: (s) => s?.wht_to_issue?.count,
				alert: (s) => s?.wht_to_issue?.count,
			},
			{
				view: "acc-sales-tax",
				label: "ภาษีขาย",
				icon: "trending",
				when: (b) => b.accounting?.["acc-sales-tax"],
			},
			{
				view: "acc-purchase-tax",
				label: "ภาษีซื้อ",
				icon: "cart",
				when: (b) => b.accounting?.["acc-purchase-tax"],
			},
			{
				view: "acc-tax-report",
				label: "รายงานภาษี",
				icon: "list",
				when: (b) => b.accounting?.reports?.length,
			},
			{
				view: "acc-retention-in",
				label: "ประกันรับ",
				icon: "shield",
				when: (b) => b.retention?.sides?.in,
				badge: (s) => s?.retention_in?.count,
				alert: (s) => s?.retention_in?.late,
			},
			{
				view: "acc-retention-out",
				label: "ประกันจ่าย",
				icon: "shield",
				when: (b) => b.retention?.sides?.out,
				badge: (s) => s?.retention_out?.count,
				alert: (s) => s?.retention_out?.late,
			},
		],
		badge: (s) =>
			(s?.wht_to_issue?.count || 0) +
			(s?.retention_in?.count || 0) +
			(s?.retention_out?.count || 0),
	},
};

// view → หมวด + ชื่อ params ตามลำดับใน URL
export const ROUTES = {
	// จัดซื้อ / ขาย: รายการ (filter) และรายละเอียด (kind = mr/po/pi/qtn/so/si)
	buy: { section: "purchase", params: [] },
	mr: { section: "purchase", params: ["filter"] },
	po: { section: "purchase", params: ["filter"] },
	pi: { section: "purchase", params: ["filter"] },
	"buy-doc": { section: "purchase", params: ["kind", "name"] },
	// สร้าง/แก้ไขร่าง: name = new (ใหม่) หรือเลขที่ร่าง, source = เอกสารต้นทาง (สร้างเอกสารถัดไป)
	"buy-form": { section: "purchase", params: ["kind", "name", "source"] },
	sell: { section: "sales", params: [] },
	qtn: { section: "sales", params: ["filter"] },
	so: { section: "sales", params: ["filter"] },
	si: { section: "sales", params: ["filter"] },
	"sell-doc": { section: "sales", params: ["kind", "name"] },
	"sell-form": { section: "sales", params: ["kind", "name", "source"] },
	boq: { section: "boq", params: ["filter"] },
	"boq-form": { section: "boq", params: ["name"] },
	// month = YYYY-MM (ว่าง = เดือนนี้)
	"hr-attendance": { section: "hr", params: ["month"] },
	"hr-payroll": { section: "hr", params: ["month"] },
	"hr-setup": { section: "hr", params: [] },
	"hr-adjustments": { section: "hr", params: ["month"] },
	"hr-salaries": { section: "hr", params: ["filter"] },
	"hr-advances": { section: "hr", params: ["filter"] },
	// สารบรรณ: รายการ (tab = แท็บสถานะ) / ดู / ฟอร์ม (kind = letter_in/letter_out/transmittal/envelope)
	// source ของฟอร์ม = ใบนำส่งต้นทางของใบปะหน้าใหม่
	"letters-in": { section: "saraban", params: ["tab"] },
	"letters-out": { section: "saraban", params: ["tab"] },
	transmittals: { section: "saraban", params: ["tab"] },
	envelopes: { section: "saraban", params: ["tab"] },
	"saraban-doc": { section: "saraban", params: ["kind", "name"] },
	"saraban-form": { section: "saraban", params: ["kind", "name", "source"] },
	// ผรม.: name = new (ใหม่) หรือเลขที่ / ใบเบิกใหม่: agreement = สัญญาที่จะเบิก
	agreements: { section: "subcontract", params: ["tab"] },
	claims: { section: "subcontract", params: ["tab"] },
	agreement: { section: "subcontract", params: ["name"] },
	claim: { section: "subcontract", params: ["name", "agreement"] },
	variations: { section: "subcontract", params: ["tab"] },
	variation: { section: "subcontract", params: ["name", "agreement"] },
	// บัญชี: รายการ (tab) / หน้าเอกสาร kind = ชื่อหน้ารายการ (ไฮไลต์เมนูผ่าน kind_pages): รับ/จ่ายชำระ (acc-receipts/acc-payments),
	// ใบกำกับภาษี (acc-sales-tax/acc-purchase-tax) / หนังสือรับรอง: name = new + source = จ่ายชำระต้นทาง
	// รายงานภาษี: report = sales/purchase/pnd3/pnd53, month = YYYY-MM
	"acc-receipts": { section: "accounting", params: ["tab"] },
	"acc-payments": { section: "accounting", params: ["tab"] },
	"acc-wht": { section: "accounting", params: ["tab"] },
	"acc-sales-tax": { section: "accounting", params: ["tab"] },
	"acc-purchase-tax": { section: "accounting", params: ["tab"] },
	"acc-payment": { section: "accounting", params: ["kind", "name"] },
	"acc-wht-doc": { section: "accounting", params: ["name", "source"] },
	"acc-tax-doc": { section: "accounting", params: ["kind", "name"] },
	"acc-tax-report": { section: "accounting", params: ["report", "month"] },
	// เงินประกันผลงาน: รายการ (tab) / หน้าเอกสาร `<รายการ>-doc` (type = rr/ri/rp/rl, name = new = ใบขอคืน/ใบคืนใหม่,
	// source = เงินประกันต้นทางของใบใหม่)
	"acc-retention-in": { section: "accounting", params: ["tab"] },
	"acc-retention-out": { section: "accounting", params: ["tab"] },
	"acc-retention-in-doc": { section: "accounting", params: ["type", "name", "source"] },
	"acc-retention-out-doc": { section: "accounting", params: ["type", "name", "source"] },
	"sell-retention": { section: "sales", params: ["tab"] },
	"sell-retention-doc": { section: "sales", params: ["type", "name", "source"] },
	"buy-retention": { section: "purchase", params: ["tab"] },
	"buy-retention-doc": { section: "purchase", params: ["type", "name", "source"] },
};
