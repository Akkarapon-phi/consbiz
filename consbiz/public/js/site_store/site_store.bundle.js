// แอปสโตร์หน้างาน (/store) โหลดจาก consbiz/www/store.html ข้อมูลจาก consbiz/store_app.py
// รับของ (PO → Purchase Receipt, ผู้ว่าจ้างจัดหา → Stock Entry) / เบิก / คอนกรีต / ยืม-คืน / คลัง
import { createApp } from "vue";
import App from "./App.vue";

const app = createApp(App);
app.config.errorHandler = (error) => {
	// ไม่ให้หน้าค้างขาวทั้งหน้าเมื่อ component ใดพัง
	console.error(error);
};
app.mount("#store-app");
