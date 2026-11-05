// แอปหน้างาน (/site) โหลดจาก consbiz/www/site.html แบ่งหมวดงาน (sections.js) สลับในแอป
// สโตร์ (views/store, API consbiz/store_app.py): รับของ / เบิก / คอนกรีต / ยืม-คืน / คลัง
// ควบคุมงาน (views/work, API consbiz/site_app.py): ความคืบหน้า / รายงานประจำวัน / ตรวจงาน
import { createApp } from "vue";
import App from "./App.vue";

const app = createApp(App);
app.config.errorHandler = (error) => {
	// ไม่ให้หน้าค้างขาวทั้งหน้าเมื่อ component ใดพัง
	console.error(error);
};
app.mount("#site-app");
