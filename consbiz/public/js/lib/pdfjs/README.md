# PDF.js 4.10.38 (legacy build)

จาก npm `pdfjs-dist@4.10.38` (`legacy/build/pdf.min.mjs`, `legacy/build/pdf.worker.min.mjs`) ไม่ได้แก้ไขเนื้อไฟล์
เปลี่ยนนามสกุลเป็น `.js` เพราะ nginx บางรุ่นส่ง `.mjs` เป็น `application/octet-stream` แล้วเบราว์เซอร์ไม่ยอมโหลดเป็น module
ใช้ใน `public/js/site_app/components/PdfViewer.vue` (โหลดจาก `/assets/consbiz/js/lib/pdfjs/`) (แสดง PDF ในแอปหน้างาน) ลิขสิทธิ์ Apache-2.0 ดู `LICENSE`
