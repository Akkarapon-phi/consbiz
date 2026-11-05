// หน้าสโตร์หน้างานย้ายไปเป็นหมวดสโตร์ของแอปหน้างาน /site/store (consbiz/www/site.html, public/js/site_app/)
// หน้านี้คงไว้ให้เมนู Sidebar "สโตร์หน้างาน" และลิงก์เดิมยังใช้ได้
frappe.pages["site-store"].on_page_load = () => {
	window.location.href = "/site/store";
};
frappe.pages["site-store"].on_page_show = () => {
	window.location.href = "/site/store";
};
