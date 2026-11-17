// หมวดของแอปผู้รับเหมาช่วง (/contractor/<หน้า>/<params...>) ตั้งค่าแอปที่ contractor_app.bundle.js
// หมวดเดียว ชื่อหน้าห้ามซ้ำกับแอปอื่น (ขึ้นต้น contractor)

import { MODULE_META } from "../shared/modules.js";

export const SECTIONS = {
	contractor: {
		key: "contractor",
		...MODULE_META.contractor.contractor,
		home: "contractor",
		tabs: [
			{ view: "contractor", label: "สัญญา", icon: "file" },
			{
				view: "contractor-claims",
				label: "ใบเบิกงวด",
				icon: "receive",
				badge: (s) => s?.returned,
				alert: (s) => s?.returned,
			},
		],
		badge: (s) => s?.returned,
	},
};

// view → หมวด + ชื่อ params ตามลำดับใน URL
export const ROUTES = {
	contractor: { section: "contractor", params: [] },
	"contractor-claims": { section: "contractor", params: [] },
	"contractor-agreement": { section: "contractor", params: ["name"] },
	// name = "new" + agreement = ใบเบิกใหม่ของสัญญานั้น
	"contractor-claim": { section: "contractor", params: ["name", "agreement"] },
};

// หน้าย่อย → เมนูที่ไฮไลต์
export const PARENT_TAB = {
	"contractor-agreement": "contractor",
	"contractor-claim": "contractor-claims",
};
