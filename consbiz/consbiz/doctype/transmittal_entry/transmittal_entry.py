import frappe
from frappe.model.document import Document

class TransmittalEntry(Document):
    def before_insert(self):
        # เมื่อทำการสร้างใหม่ หรือ Amend เอกสาร
        # ให้รีเซ็ตสถานะกลับเป็น "Draft" เสมอ ไม่ว่าจะ Copy ค่าเดิมมาหรือไม่
        self.status = "Draft"
        
    def validate(self):
        # ตรวจสอบสถานะทุกครั้งที่บันทึก (Save)
        # ถ้ายังเป็น Draft (docstatus=0) ให้สถานะเป็น Draft
        if self.docstatus == 0:
            self.status = "Draft"

    def on_submit(self):
        # เมื่อ Submit ให้เปลี่ยนสถานะเป็น Submitted
        self.db_set("status", "Submitted")

    def on_cancel(self):
        # เมื่อ Cancel ให้เปลี่ยนสถานะเป็น Cancelled
        self.db_set("status", "Cancelled")