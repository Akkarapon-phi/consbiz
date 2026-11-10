// ฟังก์ชันที่ desk มีให้แต่แอป ConsERP (/conserp ไม่โหลด desk) ไม่มี print.js / columns.js ใช้ผ่านไฟล์นี้จึงทำงานได้ทั้งสองที่
export function __(text, args) {
	if (globalThis.__) return globalThis.__(text, args);
	return String(text).replace(/\{(\d+)\}/g, (_, i) => args?.[i] ?? "");
}

export function format_number(value, format, decimals) {
	if (globalThis.format_number) return globalThis.format_number(value, format, decimals);
	const digits = decimals ?? 0;
	return Number(value || 0).toLocaleString("en-US", {
		minimumFractionDigits: digits,
		maximumFractionDigits: digits,
	});
}

export function str_to_user(value) {
	if (globalThis.frappe?.datetime) return globalThis.frappe.datetime.str_to_user(value);
	const [year, month, day] = String(value).slice(0, 10).split("-");
	return `${day}-${month}-${year}`;
}
