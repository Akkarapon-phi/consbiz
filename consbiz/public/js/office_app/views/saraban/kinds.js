// เอกสารของหมวดสารบรรณ (API consbiz/saraban.py, key = ชื่อหน้ารายการใน sections.js และ KINDS ของ saraban.py)
// kind เป็นชื่อหน้ารายการด้วย เพราะหน้าดู/ฟอร์มไฮไลต์เมนูตาม params.kind (kind_pages ของ office_app.bundle.js)
// สถานะในแถว: status_label / status_tone มาจาก server (saraban.status_of)

export const API = "consbiz.saraban";

// สถานะของหนังสือเข้า (ค่าใน DocType เป็นภาษาไทย ตรงกับ LI_* ใน saraban.py)
export const LI = {
	WAIT: "รอเสนอ",
	PROPOSE: "เสนออนุมัติ",
	APPROVED: "อนุมัติ",
	REJECTED: "ไม่อนุมัติ",
};

export const LETTER_OUT_STATUS = [
	{ value: "ดำเนินการ", label: "ดำเนินการ" },
	{ value: "พิจารณา", label: "พิจารณา" },
	{ value: "อนุมัติ", label: "อนุมัติ" },
	{ value: "ไม่อนุมัติ", label: "ไม่อนุมัติ" },
];

export const RECIPIENT_TYPES = [
	{ value: "Customer", label: "ลูกค้า" },
	{ value: "Supplier", label: "ผู้ขาย / ผู้รับเหมา" },
	{ value: "Accounting Office", label: "สำนักงานบัญชี" },
	{ value: "Other", label: "อื่นๆ" },
];
export const recipient_label = (value) =>
	RECIPIENT_TYPES.find((r) => r.value === value)?.label || value || "";
// ประเภทผู้รับที่เป็นคู่ค้า (ตรงกับ PARTY_TYPES ใน transmittal.py)
export const PARTY_TYPES = { Customer: "Customer", Supplier: "Supplier" };

// ชื่อเอกสารที่ดึงเข้าใบนำส่งได้ (transmittal.SOURCES)
export const SOURCE_LABELS = {
	"Sales Tax Invoice": "ใบกำกับภาษีขาย",
	"Purchase Tax Invoice": "ใบกำกับภาษีซื้อ",
	"Withholding Tax Cert": "หนังสือรับรองหัก ณ ที่จ่าย",
	"Sales Invoice": "ใบแจ้งหนี้ขาย",
	"Purchase Invoice": "ใบแจ้งหนี้ซื้อ",
	"Retention Invoice": "ใบเบิกเงินประกันผลงาน",
};

const is = (status) => (row) => row.docstatus === 1 && row.status === status;
const draft = (row) => row.docstatus === 0;

// filters: แท็บของหน้ารายการ (ตัวแรก = ค่าตั้งต้น) test(row) = แถวที่อยู่ในแท็บ
// date / party / title: ช่องที่แสดงในรายการ
export const SARABAN_KINDS = {
	"letters-in": {
		doctype: "Letter In",
		label: "หนังสือเข้า",
		icon: "inbox",
		title: (row) => row.title,
		party: (row) => row.document_no,
		party_label: "เลขที่หนังสือ",
		date: "receive_date",
		date_label: "ลงรับ",
		search: ["name", "title", "document_no", "receiver_name", "approver_name", "project"],
		filters: [
			{
				value: "todo",
				label: "รอดำเนินการ",
				test: (r) =>
					draft(r) || (r.docstatus === 1 && [LI.WAIT, LI.REJECTED].includes(r.status)),
			},
			{
				value: "mine",
				label: "รอฉันอนุมัติ",
				test: (r, me) => is(LI.PROPOSE)(r) && r.approver === me,
			},
			{ value: "waiting", label: "รออนุมัติ", test: is(LI.PROPOSE) },
			{ value: "approved", label: "อนุมัติแล้ว", test: is(LI.APPROVED) },
			{ value: "all", label: "ทั้งหมด", test: () => true },
		],
	},
	"letters-out": {
		doctype: "Letter Out",
		label: "หนังสือออก",
		icon: "send",
		title: (row) => row.title,
		party: (row) => row.receiver,
		party_label: "ผู้รับ",
		date: "sent_date",
		date_label: "วันที่ส่ง",
		search: ["name", "title", "receiver", "sender_name", "project"],
		filters: [
			{
				value: "open",
				label: "ดำเนินการ",
				test: (r) =>
					draft(r) ||
					(r.docstatus === 1 && !["อนุมัติ", "ไม่อนุมัติ"].includes(r.document_status)),
			},
			{
				value: "done",
				label: "ได้คำตอบแล้ว",
				test: (r) =>
					r.docstatus === 1 && ["อนุมัติ", "ไม่อนุมัติ"].includes(r.document_status),
			},
			{ value: "all", label: "ทั้งหมด", test: () => true },
		],
	},
	transmittals: {
		doctype: "Transmittal",
		label: "ใบนำส่งเอกสาร",
		icon: "layers",
		title: (row) => row.title,
		party: (row) => row.recipient_name || recipient_label(row.recipient_type),
		party_label: "ผู้รับ",
		date: "date",
		date_label: "วันที่",
		search: ["name", "title", "recipient_name", "project"],
		filters: [
			{ value: "draft", label: "ร่าง", test: draft },
			{ value: "to-send", label: "รอส่ง", test: is("To Send") },
			{ value: "sent", label: "ส่งแล้ว", test: is("Sent") },
			{ value: "received", label: "รับแล้ว", test: is("Received") },
			{ value: "all", label: "ทั้งหมด", test: () => true },
		],
	},
	envelopes: {
		doctype: "Envelope",
		label: "ใบปะหน้าซอง",
		icon: "mail",
		title: (row) => row.remark || row.to || row.name,
		party: (row) => row.to,
		party_label: "ถึง",
		date: "send_date",
		date_label: "วันที่ส่ง",
		search: ["name", "to", "receiver", "remark", "reference_name"],
		filters: [
			{ value: "draft", label: "ร่าง", test: draft },
			{ value: "sent", label: "ส่งแล้ว", test: (r) => r.docstatus === 1 },
			{ value: "all", label: "ทั้งหมด", test: () => true },
		],
	},
};

// ค่าที่หน้ารายการกลาง (common/KindList.vue) ใช้: API, สิทธิ์ใน boot, หน้าดู/ฟอร์ม, ข้อความใต้สถานะ
for (const [key, kind] of Object.entries(SARABAN_KINDS)) {
	Object.assign(kind, {
		api: API,
		boot: "saraban",
		open: (row) => ["saraban-doc", { kind: key, name: row.name }],
		create: () => ["saraban-form", { kind: key, name: "new" }],
	});
}
SARABAN_KINDS["letters-in"].note = (row) => (row.status === LI.PROPOSE ? row.approver_name : null);
