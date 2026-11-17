// ปุ่มของหัวฟอร์ม (FormHead.vue) ทุกหน้าเอกสารใช้ชุดนี้ ให้ป้ายและลำดับขั้นตรงกันทั้งแอป (ตกลง 2026-11-17)
//
// ขั้นตอน (แสดงทีละขั้น ไม่ขึ้นพร้อมกัน):
//   ร่างใหม่ / ร่างที่ยังไม่บันทึก        → บันทึก
//   ร่างที่บันทึกแล้ว                    → ส่งอนุมัติ / อนุมัติ / ยืนยัน (ตามชนิดเอกสาร)
//   รออนุมัติ                            → ผู้ส่ง: ดึงกลับ  ผู้อนุมัติ: ไม่อนุมัติ + อนุมัติ
//   อนุมัติ/ยืนยันแล้ว                   → ยกเลิก (+ ขั้นถัดไปของเอกสาร เช่น สร้างใบแจ้งหนี้)
//   ยกเลิกแล้ว                           → แก้ไขฉบับใหม่ (เฉพาะชนิดที่แอปทำ amend ได้)
// ป้ายปุ่มยืนยันขั้นตอน:
//   SEND    = ผู้กรอกส่งให้คนอื่นอนุมัติ (มีขั้นรออนุมัติ ดึงกลับได้)
//   APPROVE = ผู้มีสิทธิ์อนุมัติกดเอง (Submit = อนุมัติ)
//   CONFIRM = เอกสารไม่ต้องอนุมัติ (Submit = ยืนยันว่าถูกต้อง ลงบัญชี/ตัดสต็อก)
import { boot, desk_url, go, post, show_error, toast } from "./api.js";

export const LABELS = {
	save: "บันทึก",
	send: "ส่งอนุมัติ",
	approve: "อนุมัติ",
	reject: "ไม่อนุมัติ",
	confirm: "ยืนยัน",
	withdraw: "ดึงกลับ",
	cancel: "ยกเลิก",
	amend: "แก้ไขฉบับใหม่",
	duplicate: "ทำซ้ำ",
	refresh: "โหลดใหม่",
	desk: "เปิดในระบบเต็ม",
	remove: "ลบ",
};

const ICONS = { save: "save", send: "send", approve: "check", confirm: "check", amend: "copy" };
const ORDER = { danger: 0, soft: 1, primary: 2 };

// step = ฟังก์ชัน หรือ { run, label?, disabled?, title?, icon? } ไม่ส่ง/null = ไม่มีปุ่มนั้น
function action(key, step, tone, label) {
	if (!step) return null;
	const o = typeof step === "function" ? { run: step } : step;
	if (o.when === false) return null;
	return {
		key,
		label: o.label || label,
		icon: o.icon === undefined ? (tone === "primary" ? ICONS[key] : null) : o.icon,
		tone: o.tone || tone,
		disabled: !!o.disabled,
		title: o.title || "",
		onClick: o.run,
		href: o.href,
	};
}

// ปุ่มขั้นตอนของหัวฟอร์ม
// o = {
//   stage: "draft" | "pending" | "done" | "cancelled",
//   is_new, dirty,
//   save, save_after (บันทึกช่องที่แก้ได้หลังยืนยัน แสดงเมื่อ dirty), submit (label = LABELS.send/approve/confirm), reject, withdraw, cancel, amend,
//   next: [step] = ขั้นถัดไปหลังยืนยัน (ตัวแรก = ปุ่มหลักถ้าไม่ระบุ tone), extra: [step] = ปุ่มรองที่แสดงทุกขั้น
// }
export function step_actions(o) {
	const out = [];
	const add = (a) => a && out.push(a);
	if (o.stage === "draft") {
		const unsaved = o.is_new || o.dirty || !o.submit;
		if (unsaved && o.save) {
			const s = typeof o.save === "function" ? { run: o.save } : { ...o.save };
			if (!o.is_new && !o.dirty) s.disabled = true;
			add(action("save", s, "primary", LABELS.save));
		} else if (!unsaved) {
			add(action("reject", o.reject, "danger", LABELS.reject));
			add(action("submit", o.submit, "primary", LABELS.confirm));
		}
	} else if (o.stage === "pending") {
		add(action("withdraw", o.withdraw, "soft", LABELS.withdraw));
		add(action("reject", o.reject, "danger", LABELS.reject));
		add(action("submit", o.submit, "primary", LABELS.approve));
	} else if (o.stage === "done" && o.save_after && o.dirty) {
		// แก้ช่องที่แก้ได้หลังยืนยันค้างอยู่: บันทึกก่อน ขั้นอื่นซ่อน
		add(action("save", o.save_after, "primary", LABELS.save));
	} else if (o.stage === "done") {
		add(action("cancel", o.cancel, "danger", LABELS.cancel));
		(o.next || []).filter(Boolean).forEach((n, i) =>
			add(action(n.key || `next${i}`, n, i === 0 ? "primary" : "soft", n.label))
		);
	} else if (o.stage === "cancelled") {
		add(action("amend", o.amend, "primary", LABELS.amend));
	}
	(o.extra || []).filter(Boolean).forEach((n, i) => add(action(n.key || `extra${i}`, n, "soft", n.label)));
	out.sort((a, b) => ORDER[a.tone] - ORDER[b.tone]);
	// ปุ่มหลักมีได้ 1 ปุ่ม (ขวาสุด)
	const primaries = out.filter((a) => a.tone === "primary");
	primaries.slice(0, -1).forEach((a) => (a.tone = "soft"));
	out.sort((a, b) => ORDER[a.tone] - ORDER[b.tone]);
	return out;
}

// เมนู ⋯ ของหัวฟอร์ม ลำดับคงที่: (คำสั่งของหน้า) → ทำซ้ำ → โหลดใหม่ → เปิดในระบบเต็ม → ลบ
// o = { items: [{key,label,icon,run|href}], duplicate, refresh, desk: [doctype, name], remove }
export function doc_menu(o) {
	const out = [];
	for (const it of o.items || []) {
		if (!it || it.when === false) continue;
		out.push({ key: it.key || it.label, label: it.label, icon: it.icon, href: it.href, onClick: it.run, danger: it.danger });
	}
	if (o.duplicate) out.push({ key: "duplicate", label: LABELS.duplicate, icon: "copy", onClick: o.duplicate });
	if (o.refresh) out.push({ key: "refresh", label: LABELS.refresh, icon: "refresh", onClick: o.refresh });
	if (o.desk && o.desk[0] && o.desk[1]) {
		out.push({ key: "desk", label: LABELS.desk, icon: "external", href: desk_url(o.desk[0], o.desk[1]) });
	}
	if (o.remove) out.push({ key: "remove", label: LABELS.remove, icon: "trash", danger: true, onClick: o.remove });
	return out;
}

// ขั้นของเอกสารจาก docstatus (0 ร่าง, 1 ยืนยันแล้ว, 2 ยกเลิก)
export function stage_of(docstatus, pending = false) {
	if (pending) return "pending";
	return { 0: "draft", 1: "done", 2: "cancelled" }[docstatus || 0] || "draft";
}

// ทำซ้ำ (consbiz.form_actions.duplicate): server บันทึกร่างใหม่ แล้วเปิดหน้าของร่างนั้น (view + params)
// เห็นเมนูเมื่อชนิดเอกสารอยู่ใน boot.duplicate (ชนิดที่ทำซ้ำได้ และผู้ใช้มีสิทธิ์สร้าง)
export const can_duplicate = (doctype) => !!boot.duplicate?.includes(doctype);

export async function duplicate_doc(doctype, name, view, params = {}) {
	try {
		const result = await post("consbiz.form_actions.duplicate", { doctype, name });
		toast(`ทำซ้ำเป็นร่าง ${result.name} แล้ว`, "success");
		go(view, { ...params, name: result.name });
	} catch (error) {
		show_error(error);
	}
}
