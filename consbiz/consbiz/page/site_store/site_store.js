// หน้าสโตร์หน้างานย้ายไปเป็นแอปเต็มจอที่ /store (consbiz/www/store.html, public/js/site_store/)
// หน้านี้คงไว้ให้เมนู Sidebar "สโตร์หน้างาน" และลิงก์เดิมยังใช้ได้
frappe.pages["site-store"].on_page_load = () => {
	window.location.href = "/store";
};
frappe.pages["site-store"].on_page_show = () => {
	window.location.href = "/store";
};
