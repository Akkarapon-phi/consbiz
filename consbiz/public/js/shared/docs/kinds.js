// ชนิดเอกสารจัดซื้อ/ขาย ใช้ร่วมทุกแอป (ตรงกับ DOCS ใน consbiz/site_docs.py)
// section = หมวดที่มีหน้า <section>-doc / <section>-form ของชนิดนั้น
import { app } from "../app.js";
import { boot, go } from "../api.js";
export const DOC_KINDS = {
	mr: {
		doctype: "Material Request",
		section: "buy",
		label: "ใบขอซื้อ",
		icon: "clipboard",
		tone: "teal",
		project: true,
		todo: "รอสั่งซื้อ",
		progress: [
			["per_ordered", "สั่งซื้อ"],
			["per_received", "รับของ"],
		],
	},
	po: {
		doctype: "Purchase Order",
		section: "buy",
		label: "ใบสั่งซื้อ",
		icon: "cart",
		tone: "blue",
		project: true,
		party: "ผู้ขาย",
		todo: "รอรับ/วางบิล",
		due: "กำหนดส่ง",
		progress: [
			["per_received", "รับของ"],
			["per_billed", "วางบิล"],
		],
	},
	pi: {
		doctype: "Purchase Invoice",
		section: "buy",
		label: "ใบแจ้งหนี้ซื้อ",
		icon: "file",
		tone: "violet",
		project: true,
		party: "ผู้ขาย",
		todo: "ค้างจ่าย",
		due: "ครบกำหนดจ่าย",
	},
	qtn: {
		doctype: "Quotation",
		section: "sell",
		label: "ใบเสนอราคา",
		icon: "file",
		tone: "violet",
		project: false,
		party: "ลูกค้า",
		todo: "รอตอบรับ",
		due: "ยืนราคาถึง",
	},
	so: {
		doctype: "Sales Order",
		section: "sell",
		label: "ใบสั่งขาย",
		icon: "clipboard-check",
		tone: "blue",
		project: true,
		party: "ลูกค้า",
		todo: "รอส่งมอบ/วางบิล",
		due: "กำหนดส่งมอบ",
		progress: [
			["per_delivered", "ส่งมอบ"],
			["per_billed", "วางบิล"],
		],
	},
	si: {
		doctype: "Sales Invoice",
		section: "sell",
		label: "ใบแจ้งหนี้ขาย",
		icon: "receive",
		tone: "green",
		project: true,
		party: "ลูกค้า",
		todo: "ค้างรับ",
		due: "ครบกำหนดรับ",
	},
};

// แอปที่ดูแลเอกสารทุกชนิด (สั่งซื้อ แจ้งหนี้ ขาย) แอปหน้างานดูแลเฉพาะใบขอซื้อ (app.doc_kinds)
const DOC_APP = "office";

// แอปนี้เปิด/สร้างเอกสารชนิดนี้เองได้ไหม
export const in_app = (kind) => app.doc_kinds.includes(kind);

// URL หน้าดูเอกสารในแอปที่ดูแล (ผู้ใช้ไม่มีแอปนั้น = ระบบเต็ม)
export function doc_url(kind, name) {
	const config = DOC_KINDS[kind];
	const owner = (boot.apps || []).find((a) => a.key === DOC_APP);
	if (owner)
		return `${owner.url}/${config.section}/${config.section}-doc/${kind}/${encodeURIComponent(name)}`;
	return `/app/${config.doctype.toLowerCase().replace(/ /g, "-")}/${encodeURIComponent(name)}`;
}

// เปิดเอกสาร: ชนิดที่แอปนี้ดูแลเปิดในแอป ที่เหลือไปแอปที่ดูแล
export function open_doc(kind, name) {
	if (in_app(kind)) go(`${DOC_KINDS[kind].section}-doc`, { kind, name });
	else window.location.href = doc_url(kind, name);
}
