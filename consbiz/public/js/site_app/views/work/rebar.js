// ตัวช่วยของแผนตัดเหล็ก (Rebar.vue / RebarPlan.vue)
// shape_svg / dim_label ตรงกับ bar_cut_plan.js (ระบบเต็ม) และ shape_svg ใน bar_cut_plan.py (Print Format)

export const API = "consbiz.bar_cut_app";
// ด้านเป็น มม. ยกเว้น n = จำนวนรอบ, t = มุม (ตรงกับ DIMENSIONS ใน bar_shape.py)
export const DIMS = ["a", "b", "c", "d", "e", "f", "r", "n", "t"];
export const DIM_UNITS = { n: "รอบ", t: "องศา" };
// ช่องตั้งค่าที่มีผลกับความยาวตัด (ตรงกับ SETTINGS ใน bar_cut_plan.py)
export const SETTINGS = [
	"use_bend_deduction",
	"bend_45",
	"bend_90",
	"bend_135",
	"bend_180",
	"hook_90",
	"hook_135",
	"hook_180",
	"round_up",
];

const number = new Intl.NumberFormat("th-TH", { maximumFractionDigits: 0 });
export const meters = (value, digits = 2) =>
	(Number(value) || 0).toLocaleString("th-TH", {
		minimumFractionDigits: digits,
		maximumFractionDigits: digits,
	});

export function dim_label(dim, value) {
	if (dim === "T") return `${value}°`;
	if (dim === "N") return `N=${value}`;
	return `${dim}=${number.format(value)}`;
}

// รูป SVG ของ Bar Shape ที่แทนป้ายด้านด้วยค่าจริง (ตัด script / on* ออกก่อนแสดงด้วย v-html)
export function shape_svg(svg, values = {}) {
	if (!svg) return "";
	const doc = new DOMParser().parseFromString(`<div>${svg}</div>`, "text/html");
	const root = doc.body.firstElementChild;
	root.querySelectorAll("script, foreignObject").forEach((el) => el.remove());
	root.querySelectorAll("*").forEach((el) => {
		for (const attr of [...el.attributes]) {
			if (/^on/i.test(attr.name) || /javascript:/i.test(attr.value))
				el.removeAttribute(attr.name);
		}
	});
	root.querySelectorAll("[data-dim]").forEach((el) => {
		const value = Number(values[el.dataset.dim.toLowerCase()]);
		if (!value) return;
		el.textContent = dim_label(el.dataset.dim, value);
		// ป้ายซ้าย/ขวาของรูปยาวขึ้นเมื่อมีค่า ชิดออกนอกรูปจะได้ไม่ทับเส้น
		const x = Number(el.getAttribute("x"));
		if (x < 40) {
			el.setAttribute("text-anchor", "end");
			el.setAttribute("x", x + 8);
		} else if (x > 120) {
			el.setAttribute("text-anchor", "start");
			el.setAttribute("x", x - 8);
		}
	});
	return root.innerHTML;
}
