// โหมดสี (ตกลง 2026-11-18): auto = ตามเครื่อง / light / dark จำในเครื่อง (คีย์เดียวกับ script ใน www/*.html ที่ตั้งก่อนวาดหน้า)
const KEY = "consbiz.theme";
export const THEMES = ["auto", "light", "dark"];

export function get_theme() {
	try {
		const value = localStorage.getItem(KEY);
		return THEMES.includes(value) ? value : "auto";
	} catch {
		return "auto";
	}
}

export function set_theme(value) {
	try {
		if (value === "auto") localStorage.removeItem(KEY);
		else localStorage.setItem(KEY, value);
	} catch {
		// เก็บไม่ได้ (โหมดส่วนตัว) ใช้เฉพาะหน้านี้
	}
	if (window.__consbiz_theme) window.__consbiz_theme();
	if (value !== "auto") {
		document.documentElement.setAttribute("data-theme", value);
		document.documentElement.style.colorScheme = value;
	}
}
