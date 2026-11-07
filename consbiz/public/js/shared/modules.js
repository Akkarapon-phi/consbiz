// หมวดงาน (module) ของทุกแอปใน ConsERP ที่ติดตั้งตัวเดียว: ชื่อ/ไอคอน/สีของหมวด อยู่ที่นี่ที่เดียว
// sections.js ของแต่ละแอปดึงค่าจากที่นี่ (หน้า/เมนูย่อย/ตัวเลข อยู่ใน sections.js)
// หน้า Desktop และ Dock แสดงหมวดของแอปอื่นด้วย (ลิงก์ไป bundle ของแอปนั้น โหลดหน้าใหม่)
// รายการหมวดที่ผู้ใช้มีสิทธิ์ของทุกแอปมาจาก server: boot.modules (site_app.app_modules)
import { app } from "./app.js";
import { boot } from "./api.js";

export const APP_LABELS = { site: "หน้างาน", office: "ออฟฟิศ" };

export const MODULE_META = {
	site: {
		store: {
			label: "สโตร์",
			title: "สโตร์หน้างาน",
			note: "รับของ เบิก ยืม-คืน คลัง",
			icon: "package",
			theme: "#1f6feb",
			colors: ["#1f6feb", "#5b3df5"],
		},
		work: {
			label: "ควบคุมงาน",
			title: "ควบคุมงาน",
			note: "ความคืบหน้า รายงานประจำวัน คอนกรีต ตรวจงาน",
			icon: "hardhat",
			theme: "#e8590c",
			colors: ["#e8590c", "#d6336c"],
		},
		pm: {
			label: "บริหารโครงการ",
			title: "บริหารโครงการ",
			note: "ภาพรวม แผนงาน Look-ahead ทรัพยากร เอกสาร",
			icon: "gantt",
			theme: "#6d4cf6",
			colors: ["#6d4cf6", "#2563eb"],
		},
		buy: {
			label: "ขอซื้อ",
			title: "ขอซื้อ",
			note: "ขอซื้อวัสดุ ติดตามการสั่งซื้อ/รับของ",
			icon: "cart",
			theme: "#0d9488",
			colors: ["#0d9488", "#0284c7"],
		},
	},
	office: {
		purchase: {
			label: "จัดซื้อ",
			title: "จัดซื้อ",
			note: "ขอซื้อ สั่งซื้อ ใบแจ้งหนี้ซื้อ",
			icon: "cart",
			theme: "#0d9488",
			colors: ["#0d9488", "#0284c7"],
		},
		sales: {
			label: "ขาย",
			title: "ขาย",
			note: "ใบเสนอราคา ใบสั่งขาย ใบแจ้งหนี้",
			icon: "trending",
			theme: "#c026d3",
			colors: ["#c026d3", "#7c3aed"],
		},
	},
};

// หน้าแรก (Desktop) เป็นหมวดพิเศษที่ทุกแอปมี (configure ใส่ให้) ไม่ต้องเลือกโครงการ
export const DESKTOP = {
	key: "desktop",
	label: "หน้าแรก",
	title: "ConsERP",
	note: "เลือกงาน",
	icon: "grid",
	home: "desktop",
	theme: "#2e3754",
	colors: ["#2e3754", "#475569"],
	tabs: [{ view: "desktop", label: "หน้าแรก", icon: "grid" }],
};

// หมวดที่ผู้ใช้เปิดได้ของทุกแอป (ไม่มี boot.modules = เฉพาะหมวดของแอปนี้)
// local = อยู่ใน bundle นี้ (สลับในแอป) / ไม่ใช่ = ลิงก์ไปแอปอื่น
export function module_list() {
	const list = boot.modules?.length
		? boot.modules
		: boot.sections.map((section) => ({ app: app.key, section, url: `${app.base}/${section}` }));
	return list
		.filter((m) => MODULE_META[m.app]?.[m.section])
		.map((m) => ({
			...MODULE_META[m.app][m.section],
			...m,
			key: `${m.app}:${m.section}`,
			local: m.app === app.key && boot.sections.includes(m.section),
		}));
}

// จัดกลุ่มตามแอป (หัวข้อในหน้า Desktop / เส้นคั่นใน Dock)
export function module_groups() {
	const groups = [];
	for (const m of module_list()) {
		let group = groups.find((g) => g.app === m.app);
		if (!group) groups.push((group = { app: m.app, label: APP_LABELS[m.app] || m.app, modules: [] }));
		group.modules.push(m);
	}
	return groups;
}

// ตัวเลขงานค้างของหมวด (เฉพาะหมวดของแอปนี้ ข้อมูลจาก summary ที่โหลดแล้ว)
export function module_badge(module, state) {
	if (!module.local) return 0;
	return app.sections[module.section]?.badge?.(state.summaries[module.section]) || 0;
}
