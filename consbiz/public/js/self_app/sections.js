// หมวดของ Self Service (/conserp/self/<หน้า>/<params...>) ตั้งค่าแอปที่ self_app.bundle.js (configure)
// ชื่อหน้า (view) ห้ามซ้ำข้ามหมวด เพราะ go("<view>") หาหมวดจากชื่อหน้า

import { MODULE_META } from "../shared/modules.js";

export const SECTIONS = {
	self: {
		key: "self",
		...MODULE_META.self.self,
		home: "checkin",
		tabs: [
			// หน้าแรก (ตกลง 2026-11-17) = แดชบอร์ด + ลงเวลา (view ชื่อเดิม checkin ให้ลิงก์/การแจ้งเตือนเดิมใช้ได้)
			{
				view: "checkin",
				label: "หน้าแรก",
				icon: "home",
				badge: (s) => s?.missing_out,
				alert: (s) => s?.missing_out,
			},
			{ view: "leave", label: "ลา", icon: "calendar" },
			// จองกะ = Weekly Day Off เดิม เลือกวันเสาร์/อาทิตย์ที่มาทำงาน อีกวันเป็นวันหยุด (ตกลง 2026-11-17)
			{ view: "dayoff", label: "จองกะ", icon: "sun" },
			{ view: "advances", label: "เบิกเงิน", icon: "calculator", badge: (s) => s?.overdue_clearing, alert: (s) => s?.overdue_clearing },
			// เงินเดือน (เดิม สลิป) ค่าจ้าง + ที่จะปรับ + สะสมของปี + สลิป
			{ view: "pay", label: "เงินเดือน", icon: "wallet" },
		],
		badge: (s) => (s?.missing_out || 0) + (s?.overdue_clearing || 0),
	},
	// โมดูลอนุมัติ: เอกสารที่รอผู้ใช้อนุมัติทุกชนิด (API consbiz/approvals.py)
	approve: {
		key: "approve",
		...MODULE_META.self.approve,
		home: "approve",
		tabs: [
			// เมนูย่อย = โมดูล (ทั้งหมด + รายโมดูล) รออนุมัติ/พิจารณาแล้วสลับในหน้า (ApproveInbox.vue)
			{ view: "approve", label: "ทั้งหมด", icon: "inbox", badge: (s) => s?.total },
			// เมนูย่อยรายโมดูล (MODULES ใน shared/approvals/kinds.js) เห็นเมื่ออนุมัติชนิดในโมดูลนั้นได้
			{
				view: "approve-hr",
				label: "บุคคล",
				icon: "users",
				badge: (s) => s?.hr,
				when: (b) => ["leave", "checkin", "attendance", "advance", "claim"].some((k) => b.can?.[`approve_${k}`]),
			},
			// ใบขอซื้อ / ใบสั่งซื้อ / ใบแจ้งหนี้ซื้อ ที่รอผู้ใช้อนุมัติ/ลงนาม (consbiz/doc_approval.py)
			{
				view: "approve-purchase",
				label: "จัดซื้อ",
				icon: "cart",
				badge: (s) => s?.purchase,
				when: (b) => ["mr", "po", "pi"].some((k) => b.can?.[`approve_${k}`]),
			},
		],
		badge: (s) => s?.total,
	},
};

// view → หมวด + ชื่อ params ตามลำดับใน URL
export const ROUTES = {
	checkin: { section: "self", params: [] },
	// action = ทางลัดจากหน้าแรก (เปิดฟอร์มทันที): leave/new, advances/<ชนิด>
	leave: { section: "self", params: ["action"] },
	pay: { section: "self", params: [] },
	slips: { section: "self", params: [] },
	dayoff: { section: "self", params: [] },
	advances: { section: "self", params: ["action"] },
	// name = เปิดเอกสารนั้นทันที (จากการแจ้งเตือน)
	approve: { section: "approve", params: ["name"] },
	"approve-hr": { section: "approve", params: ["name"] },
	"approve-purchase": { section: "approve", params: ["name"] },
};
