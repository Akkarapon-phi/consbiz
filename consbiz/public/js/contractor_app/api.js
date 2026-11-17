// เรียก API ของแอปผู้รับเหมา (consbiz/contractor_app.py) ทุกคำขอส่ง token ของลิงก์ไปด้วย (เปิดจาก /contractor/k/<token>)
// ไม่มี token = เข้าด้วยบัญชีผู้ใช้ server ตรวจขอบเขตจาก token/ผู้ใช้ทุกคำขอ
import { ApiError, boot, call, post } from "../shared/api.js";

const API = "consbiz.contractor_app.";
const with_token = (args = {}) => (boot.token ? { ...args, token: boot.token } : args);

export const capi = (method, args) => call(API + method, with_token(args));
export const cpost = (method, args) => post(API + method, with_token(args));

// รูปหลักฐานผลงาน: ด้านยาวไม่เกิน 1600px (อ่านรายละเอียดหน้างานได้) JPEG คุณภาพ 0.85
// ใช้ JPEG ไม่ใช้ WebP (ตกลง 2026-11-15): ไฟล์จะส่งต่อไป SharePoint/Office ซึ่งโปรแกรมเก่าเปิด WebP ไม่ได้ และ WebP เล็กกว่าไม่มาก
// ผลใหญ่กว่าไฟล์เดิม = ใช้ไฟล์เดิม PDF / GIF ส่งตามเดิม
const MAX_SIDE = 1600;
function encode(canvas, type, quality) {
	return new Promise((resolve) => canvas.toBlob((b) => resolve(b), type, quality));
}
export async function compress_photo(file) {
	if (!file.type?.startsWith("image/") || file.type === "image/gif") return { blob: file, name: file.name };
	let bitmap;
	try {
		bitmap = await createImageBitmap(file);
	} catch {
		return { blob: file, name: file.name }; // เช่น HEIC ที่เบราว์เซอร์อ่านไม่ได้
	}
	const scale = Math.min(1, MAX_SIDE / Math.max(bitmap.width, bitmap.height));
	const canvas = document.createElement("canvas");
	canvas.width = Math.round(bitmap.width * scale);
	canvas.height = Math.round(bitmap.height * scale);
	canvas.getContext("2d").drawImage(bitmap, 0, 0, canvas.width, canvas.height);
	bitmap.close?.();
	const blob = await encode(canvas, "image/jpeg", 0.85);
	if (!blob || blob.size >= file.size) return { blob: file, name: file.name };
	const base = (file.name || `photo-${Date.now()}`).replace(/\.[^.]+$/, "");
	return { blob, name: `${base}.jpg` };
}

// แนบไฟล์กับใบเบิก (คนที่ไม่ได้ login ใช้ upload_file ของ Frappe ไม่ได้) รูปย่อก่อนส่ง คืนหน้าใบเบิกใหม่
export async function upload_claim_file(name, file) {
	const photo = await compress_photo(file);
	const form = new FormData();
	form.append("file", photo.blob, photo.name || `photo-${Date.now()}.jpg`);
	form.append("name", name);
	if (boot.token) form.append("token", boot.token);
	const response = await fetch(`/api/method/${API}upload_file`, {
		method: "POST",
		body: form,
		headers: { Accept: "application/json", "X-Frappe-CSRF-Token": window.frappe?.csrf_token || "" },
		credentials: "same-origin",
	});
	const data = await response.json().catch(() => ({}));
	if (!response.ok || data.exc) {
		let message = "อัปโหลดไฟล์ไม่สำเร็จ";
		try {
			message = JSON.parse(JSON.parse(data._server_messages)[0]).message || message;
		} catch {
			// ใช้ข้อความกลาง
		}
		throw new ApiError(message);
	}
	return data.message;
}

export const file_url = (claim, file) =>
	`/api/method/${API}open_file?${new URLSearchParams(with_token({ name: claim, file }))}`;
