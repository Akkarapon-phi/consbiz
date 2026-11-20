// หมวดงาน (module) ของทุกแอปใน ConsERP ที่ติดตั้งตัวเดียว: ชื่อ/ไอคอน/สีของหมวด อยู่ที่นี่ที่เดียว
// sections.js ของแต่ละแอปดึงค่าจากที่นี่ (หน้า/เมนูย่อย/ตัวเลข อยู่ใน sections.js)
// หน้า Desktop และ Dock แสดงหมวดของแอปอื่นด้วย (ลิงก์ไป bundle ของแอปนั้น โหลดหน้าใหม่)
// รายการหมวดที่ผู้ใช้มีสิทธิ์ของทุกแอปมาจาก server: boot.modules (site_app.app_modules)
import { app, app_of, local_apps } from "./app.js";
import { boot } from "./api.js";

export const APP_LABELS = { site: "หน้างาน", office: "ออฟฟิศ", self: "พนักงาน", contractor: "ผู้รับเหมา" };

// กลุ่มที่แสดง (หัวข้อในหน้า Desktop / หมวดใน Dock) ไม่จำเป็นต้องตรงกับแอป (bundle)
// หมวดไม่ระบุ group = กลุ่มชื่อเดียวกับแอป, ลำดับหมวดในกลุ่มตาม order (key "แอป:หมวด") หมวดที่ไม่อยู่ใน order ต่อท้าย
// ธุรการโครงการ รวมหมวดจากแอปหน้างาน (คนงาน) และแอปออฟฟิศ (สารบรรณ ผู้รับเหมา) หมวดของแอปอื่นเป็นลิงก์
export const GROUPS = [
	{ key: "site", label: "หน้างาน", order: ["site:pm", "site:work", "site:store", "site:buy", "site:rebar"] },
	{ key: "project_admin", label: "ธุรการโครงการ", order: ["office:labour", "office:saraban", "office:subcontract"] },
	{
		key: "office",
		label: "ออฟฟิศ",
		order: ["office:purchase", "office:sales", "office:accounting", "office:hr", "office:boq", "office:master"],
	},
	{ key: "self", label: "พนักงาน" },
	{ key: "contractor", label: "ผู้รับเหมา" },
];

// หน้าตาใหม่ (กรมท่า + ทอง, Design.md "สิ่งที่ตกลงแล้ว" 2026-11-16) ใช้ทุกหมวดทุกแอป
// CSS ใช้ [data-look="new"] (api.js set_section / AppShell) หมวดที่ยังต้องใช้หน้าตาเดิมใส่ใน OLD_LOOK
const OLD_LOOK = new Set([]);
export const NEW_LOOK = { has: (section) => !OLD_LOOK.has(section) };

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
			label: "แผนงาน",
			title: "แผนงาน",
			note: "ภาพรวม แผนงาน Look-ahead ทรัพยากร การเงิน เอกสาร",
			icon: "gantt",
			theme: "#1e3a8a",
			colors: ["#1e3a8a", "#0369a1"],
		},
		// ขอซื้อ: หน้างานขอวัสดุ/สิ่งของไปยังออฟฟิศ (หน้าใบขอซื้อชุดเดียวกับจัดซื้อ)
		buy: {
			label: "ขอซื้อ",
			title: "ขอซื้อ",
			note: "ขอวัสดุ/สิ่งของที่ต้องการจากออฟฟิศ ติดตามการสั่งซื้อ/รับของ",
			icon: "cart",
			theme: "#0d9488",
			colors: ["#0d9488", "#0284c7"],
		},
		// แผนตัดเหล็ก (เดิมเป็นเมนูในควบคุมงาน) consbiz/bar_cut_app.py
		rebar: {
			label: "แผนการตัด",
			title: "แผนการตัดเหล็ก",
			note: "แผนตัดเหล็ก ผลการตัด",
			icon: "scissors",
			theme: "#9333ea",
			colors: ["#9333ea", "#4f46e5"],
		},
	},
	office: {
		// คนงาน (bundle ออฟฟิศ, URL เดิม /conserp/admin เด้งมา /conserp/labour) อยู่กลุ่มธุรการโครงการ
		labour: {
			label: "คนงาน",
			title: "คนงาน",
			group: "project_admin",
			note: "ลงเวลาคนงานรายวัน เบิกล่วงหน้า ทะเบียนคนงาน",
			icon: "briefcase",
			theme: "#475569",
			colors: ["#475569", "#0f766e"],
		},
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
		boq: {
			label: "BOQ",
			title: "BOQ",
			note: "ประมาณราคา รายการงานและราคาต่อหน่วย",
			icon: "calculator",
			theme: "#b45309",
			colors: ["#b45309", "#a16207"],
		},
		// ฝ่ายบุคคล: สรุปวันทำงาน → Attendance (consbiz/hr_attendance.py) เฉพาะ HR
		hr: {
			label: "บุคคล",
			title: "ฝ่ายบุคคล",
			note: "สรุปวันทำงาน บันทึก Attendance",
			icon: "users",
			theme: "#be123c",
			colors: ["#be123c", "#c2410c"],
		},
		// สารบรรณ: หนังสือเข้า-ออก ใบนำส่งเอกสาร ใบปะหน้าซอง (consbiz/saraban.py)
		saraban: {
			label: "สารบรรณ",
			group: "project_admin",
			title: "งานสารบรรณ",
			note: "หนังสือเข้า-ออก ใบนำส่งเอกสาร ใบปะหน้าซอง",
			icon: "send",
			theme: "#0e7490",
			colors: ["#0e7490", "#4f46e5"],
		},
		// ผู้รับเหมาช่วง: สัญญาจ้างเหมาช่วง + ใบเบิกงวด (consbiz/subcontract_app.py)
		subcontract: {
			label: "ผู้รับเหมา",
			group: "project_admin",
			title: "ผู้รับเหมาช่วง",
			note: "สัญญาจ้างเหมาช่วง ใบเบิกงวด",
			icon: "hardhat",
			theme: "#9a3412",
			colors: ["#9a3412", "#b45309"],
		},
		// บัญชี: รับ-จ่ายชำระ ภาษี หัก ณ ที่จ่าย (consbiz/accounting_app.py) + เงินประกันผลงาน (consbiz/retention_app.py)
		accounting: {
			label: "บัญชี",
			title: "บัญชี",
			note: "รับ-จ่ายชำระ ภาษีซื้อ-ขาย หัก ณ ที่จ่าย เงินประกันผลงาน",
			icon: "wallet",
			theme: "#1d4ed8",
			colors: ["#1d4ed8", "#0f766e"],
		},
		// ข้อมูลหลัก: พนักงาน สินค้า/วัสดุ ลูกค้า ผู้ขาย โครงการ (consbiz/master_data.py)
		master: {
			label: "ข้อมูลหลัก",
			title: "ข้อมูลหลัก",
			note: "พนักงาน สินค้า/วัสดุ ลูกค้า ผู้ขาย โครงการ",
			icon: "grid",
			theme: "#4d7c0f",
			colors: ["#4d7c0f", "#0f766e"],
		},
	},
	self: {
		self: {
			label: "Self Service",
			title: "Self Service",
			note: "ลงเวลา ขอลา สลิปเงินเดือน",
			icon: "user",
			theme: "#15803d",
			colors: ["#15803d", "#0f766e"],
		},
		// รวมเอกสารที่รออนุมัติทุกชนิดไว้ที่เดียว (ตอนนี้งาน HR) consbiz/approvals.py
		approve: {
			label: "อนุมัติ",
			title: "อนุมัติ",
			note: "ใบลา ลงเวลา เบิกเงิน เคลียร์ค่าใช้จ่าย",
			icon: "clipboard-check",
			theme: "#4338ca",
			colors: ["#4338ca", "#7c3aed"],
		},
	},
	// แอปผู้รับเหมาช่วง (/contractor, คนนอก) consbiz/contractor_app.py สีเดียวกับหมวด ผรม. ของออฟฟิศ
	contractor: {
		contractor: {
			label: "ผู้รับเหมา",
			title: "ผู้รับเหมาช่วง",
			note: "สัญญา ใบเบิกงวด",
			icon: "hardhat",
			theme: "#9a3412",
			colors: ["#9a3412", "#b45309"],
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
	const rank = (m) => {
		const g = GROUPS.findIndex((x) => x.key === m.group);
		const at = GROUPS[g]?.order?.indexOf(m.key) ?? -1;
		return [g < 0 ? GROUPS.length : g, at < 0 ? 999 : at];
	};
	return list
		.filter((m) => MODULE_META[m.app]?.[m.section])
		.map((m, i) => {
			const meta = MODULE_META[m.app][m.section];
			return {
				...meta,
				...m,
				group: meta.group || m.app,
				key: `${m.app}:${m.section}`,
				local: local_apps().includes(m.app) && boot.sections.includes(m.section),
				i,
			};
		})
		.sort((a, b) => {
			const [ga, oa] = rank(a);
			const [gb, ob] = rank(b);
			return ga - gb || oa - ob || a.i - b.i;
		});
}

// กลุ่มของหมวด (ไม่ระบุ = กลุ่มชื่อเดียวกับแอป) หน้าแรก/หมวดที่ไม่รู้จัก = กลุ่มของแอปนี้
export function group_of(section, app_key = app_of(section)) {
	return MODULE_META[app_key]?.[section]?.group || app_key;
}

// กลุ่มออฟฟิศ: ดูแลเอกสารทุกโครงการ แถบบนเป็นตัวเลือกบริษัท (ไม่มีปุ่มโครงการ)
// กรองโครงการได้เฉพาะหน้าที่มีตัวกรองโครงการในหัวรายการ (ProjectFilter) (ตกลง 2026-11-17)
export const is_company_section = (section) => group_of(section) === "office";

// จัดกลุ่มตาม GROUPS (หัวข้อในหน้า Desktop / หมวดใน Dock)
export function module_groups() {
	const groups = [];
	for (const m of module_list()) {
		let group = groups.find((g) => g.key === m.group);
		if (!group) {
			const label = GROUPS.find((g) => g.key === m.group)?.label || APP_LABELS[m.group] || m.group;
			groups.push((group = { key: m.group, label, modules: [] }));
		}
		group.modules.push(m);
	}
	return groups;
}

// ตัวเลขงานค้างของหมวด (เฉพาะหมวดของแอปนี้ ข้อมูลจาก summary ที่โหลดแล้ว)
export function module_badge(module, state) {
	if (!module.local) return 0;
	return app.sections[module.section]?.badge?.(state.summaries[module.section]) || 0;
}
