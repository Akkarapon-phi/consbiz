// ชนิดเอกสารที่อนุมัติได้ + โมดูลเจ้าของ (ตรงกับ KINDS / MODULES ใน consbiz/approvals.py)
// โมดูลอนุมัติ (/conserp/approve) เป็นแค่ที่รวม: แต่ละโมดูลอนุมัติในหน้าของตัวเองได้ด้วย ApprovalSheet.vue ชุดเดียวกัน
// ชนิดใหม่: เพิ่มที่ KINDS (+ module) และ to_item / ApprovalSheet ถ้าแสดงต่างจากเดิม
import { thai_date } from "../api.js";
import { advance_status, claim_status, TYPE } from "./status.js";

// method = API อนุมัติของชนิดนั้น reason = ชื่อช่องเหตุผลของ API
export const KINDS = {
	leave: { label: "ใบลา", tone: "teal", module: "hr", method: "consbiz.approvals.review_leave", reason: "reason" },
	checkin: { label: "ลงเวลา", tone: "amber", module: "hr", method: "consbiz.self_service.review_checkin", reason: "note" },
	advance: { label: "ใบเบิก", tone: "green", module: "hr", method: "consbiz.self_advance.review_advance", reason: "reason" },
	claim: { label: "เคลียร์/เบิกคืน", tone: "violet", module: "hr", method: "consbiz.self_advance.review_claim", reason: "reason" },
};
// โมดูลเจ้าของเอกสาร = เมนูย่อยของโมดูลอนุมัติ (view = approve-<key>)
export const MODULES = {
	hr: { label: "บุคคล", icon: "users" },
};
export const kinds_of = (module) => Object.keys(KINDS).filter((k) => !module || KINDS[k].module === module);

const DONE = {
	Approved: { label: "อนุมัติ", tone: "green" },
	Rejected: { label: "ไม่อนุมัติ", tone: "rose" },
};

export const time_of = (value) => String(value || "").slice(11, 16);
export const days = (value) => {
	const n = Number(value) || 0;
	return Number.isInteger(n) ? String(n) : n.toFixed(1);
};
export function leave_range(row) {
	const from = thai_date(row.from_date, { year: true });
	const text = row.from_date === row.to_date ? from : `${from} – ${thai_date(row.to_date, { year: true })}`;
	return row.half_day ? `${text} (ครึ่งวัน)` : text;
}
// ช่วงวันที่ของเอกสาร (ใช้หาคนในโครงการที่ลาชนวัน)
export function context_dates(item) {
	if (item.kind === "leave") return [item.row.from_date, item.row.to_date];
	if (item.kind === "checkin") return [String(item.row.time).slice(0, 10), String(item.row.time).slice(0, 10)];
	return [undefined, undefined];
}

// แปลงแต่ละชนิดเป็นรายการรูปแบบเดียวกัน history = รายการที่พิจารณาแล้ว (มีป้ายผล)
export function to_item(kind, row, history = false) {
	const item = { kind, row, key: `${kind}:${row.name}`, amount: null, status: null };
	if (kind === "leave") {
		Object.assign(item, { title: `ลา${row.leave_type}`, sub: `${leave_range(row)} · ${days(row.total_leave_days)} วัน`, date: row.from_date });
		if (history) item.status = DONE[row.status];
	} else if (kind === "checkin") {
		Object.assign(item, {
			title: row.manual ? "แจ้งลืมลงเวลาออก" : "ลงเวลานอกพื้นที่",
			sub: `${row.log_type === "IN" ? "เข้า" : "ออก"} ${thai_date(row.time)} ${time_of(row.time)} น.`,
			date: row.time,
		});
		if (history) item.status = DONE[row.approval];
	} else if (kind === "advance") {
		Object.assign(item, { title: TYPE[row.advance_type], sub: row.purpose, amount: row.advance_amount, date: row.posting_date });
		item.status = history ? advance_status(row) : row.over_limit ? { label: "เกินวงเงิน", tone: "violet" } : null;
	} else {
		Object.assign(item, {
			title: row.total_advance_amount ? "เคลียร์เงินสำรองจ่าย" : "เบิกค่าใช้จ่ายคืน",
			sub: thai_date(row.posting_date, { year: true }),
			amount: row.total_claimed_amount,
			date: row.posting_date,
		});
		if (history) item.status = claim_status(row);
	}
	return item;
}

// รายการจากผลของ get_inbox / get_history เรียงตามวันที่ (รอ = เก่าก่อน, พิจารณาแล้ว = ใหม่ก่อน)
export function inbox_items(data, { history = false, module = null } = {}) {
	if (!data) return [];
	const out = kinds_of(module).flatMap((kind) => (data[kind] || []).map((row) => to_item(kind, row, history)));
	return out.sort((a, b) => (history ? -1 : 1) * String(a.date).localeCompare(String(b.date)));
}

// หาเอกสารนี้ในกล่องอนุมัติของผู้ใช้ (มี = อนุมัติได้) ใช้ในหน้าของแต่ละโมดูล
export async function find_pending(call, kind, name) {
	const data = await call("consbiz.approvals.get_inbox", { module: KINDS[kind].module, quiet: 1 });
	const row = (data?.[kind] || []).find((r) => r.name === name);
	return row ? to_item(kind, row) : null;
}
