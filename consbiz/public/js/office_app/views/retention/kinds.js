// เงินประกันผลงาน (API consbiz/retention_app.py): หมวดบัญชี 2 ฝั่ง + เมนูในหมวดขาย (ฝั่งรับ) / จัดซื้อ (ฝั่งจ่าย)
// รายการของฝั่ง = เงินประกันที่ถูกหัก (rr / rp) + ใบขอคืน / ใบคืน (ri / rl) รวมกัน แยกด้วย row.type
// key = ชื่อหน้ารายการใน sections.js หน้าเอกสารของแต่ละรายการ = `<key>-doc` (RetentionPage.vue)

export const API = "consbiz.retention_app";

// ข้อความตามฝั่ง (in = ผู้ว่าจ้างหักเรา, out = เราหัก ผรม.)
export const SIDE_TEXT = {
	in: {
		party: "ผู้ว่าจ้าง",
		party_doctype: "Customer",
		source: "เงินประกันที่ผู้ว่าจ้างหัก",
		claim: "ใบขอคืนเงินประกัน",
		claim_short: "ขอคืน",
		pay: "บันทึกรับเงิน",
		paid: "รับเงินแล้ว",
		ref: "เลขที่ PO ผู้ว่าจ้าง",
		invoice: "ใบแจ้งหนี้ขาย",
		source_type: "rr",
		claim_type: "ri",
	},
	out: {
		party: "ผู้รับเหมา / ผู้ขาย",
		party_doctype: "Supplier",
		source: "เงินประกันที่หัก ผรม.",
		claim: "ใบคืนเงินประกัน",
		claim_short: "คืน",
		pay: "บันทึกจ่ายเงิน",
		paid: "จ่ายเงินแล้ว",
		ref: "ใบสั่งซื้อ",
		invoice: "ใบแจ้งหนี้ซื้อ",
		source_type: "rp",
		claim_type: "rl",
	},
};
export const SIDE_OF_TYPE = { rr: "in", ri: "in", rp: "out", rl: "out" };
export const is_source = (type) => type === "rr" || type === "rp";

const source = (r) => r.role === "source";
const claim = (r) => r.role === "claim";

function side_kind(view, side, label) {
	const t = SIDE_TEXT[side];
	return {
		api: API,
		boot: "retention",
		label,
		// ปุ่มสร้างของรายการ = ใบขอคืน / ใบคืน (เงินประกันที่ถูกหักระบบสร้างจากใบแจ้งหนี้)
		create_label: t.claim,
		icon: "shield",
		title: (r) =>
			source(r)
				? `${t.source}${r.refs ? ` · ${r.refs}` : ""}`
				: `${t.claim}${r.refs ? ` · ${r.refs}` : ""}`,
		title_label: "รายการ",
		party: (r) => r.party_name,
		party_label: t.party,
		date: "due_date",
		date_label: "ครบกำหนด",
		amount: "amount",
		amount_label: "ยอด",
		note: (r) =>
			source(r) && r.docstatus === 1 && !r.due_date
				? "ยังไม่ระบุวันคืน"
				: source(r) && r.billed_amount > 0 && r.amount > 0
				? `ทำใบ${t.claim_short}แล้ว ${r.billed_amount.toLocaleString("th-TH")}`
				: null,
		search: ["name", "refs", "party_name", "party", "project"],
		filters: [
			{
				value: "due",
				label: side === "in" ? "ถึงกำหนดขอคืน" : "ถึงกำหนดคืน",
				test: (r) => source(r) && r.status === "Overdue",
			},
			{
				value: "unpaid",
				label: side === "in" ? "รอรับเงิน" : "รอจ่ายเงิน",
				test: (r) => claim(r) && ["Unpaid", "Overdue"].includes(r.status),
			},
			{
				value: "held",
				label: "ยังไม่ถึงกำหนด",
				test: (r) => source(r) && ["Active", "Partly Billed"].includes(r.status),
			},
			{ value: "draft", label: "ร่าง", test: (r) => r.docstatus === 0 },
			{
				value: "done",
				label: side === "in" ? "รับคืนแล้ว" : "คืนแล้ว",
				test: (r) => r.status === "Paid",
			},
			{ value: "all", label: "ทั้งหมด", test: () => true },
		],
		open: (r) => [`${view}-doc`, { type: r.type, name: r.name }],
		create: () => [`${view}-doc`, { type: t.claim_type, name: "new" }],
	};
}

export const RETENTION_KINDS = {
	"acc-retention-in": side_kind("acc-retention-in", "in", "เงินประกันรับ (ผู้ว่าจ้าง)"),
	"acc-retention-out": side_kind("acc-retention-out", "out", "เงินประกันจ่าย (ผรม.)"),
	"sell-retention": side_kind("sell-retention", "in", "เงินประกันผลงาน"),
	"buy-retention": side_kind("buy-retention", "out", "เงินประกันผลงาน"),
};
// หน้าเอกสาร → หน้ารายการ (ปุ่มย้อนกลับ + ไฮไลต์เมนู)
export const DOC_PAGES = Object.fromEntries(
	Object.keys(RETENTION_KINDS).map((view) => [`${view}-doc`, view])
);
