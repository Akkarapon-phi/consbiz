import frappe
from frappe.model.document import Document
from frappe.utils import getdate, nowdate

class RetentionInvoice(Document):
    def on_submit(self):
        """
        เมื่อ Submit Retention Claim:
        ให้ไปเปลี่ยนสถานะของ Retention Receivable ที่เกี่ยวข้องเป็น 'Billed'
        """
        self.update_receivable_status("Billed")

    def on_cancel(self):
        """
        เมื่อ Cancel Retention Claim:
        ให้คืนสถานะ Retention Receivable ที่เกี่ยวข้องกลับเป็น 'Active' หรือ 'Overdue'
        โดยเช็คจาก Due Date เทียบกับวันปัจจุบัน
        """
        self.update_receivable_status("Revert")

    def update_receivable_status(self, action):
        # วนลูปทุกรายการใน Retention Claim
        for item in self.retention_items:
            if not item.sales_invoice:
                continue

            # 1. ค้นหาใบ Retention Receivable ต้นทาง
            # โดยดูว่า Sales Invoice นี้ถูกอ้างอิงอยู่ใน Retention Receivable ใบไหนบ้าง (เฉพาะที่ Submit แล้ว)
            receivables = frappe.db.sql("""
                SELECT DISTINCT parent 
                FROM `tabRetention Items`
                WHERE sales_invoice = %s 
                AND parenttype = 'Retention Receivable'
                AND docstatus = 1
            """, (item.sales_invoice,), as_dict=True)

            # 2. อัปเดตสถานะเอกสารต้นทาง
            for rr in receivables:
                if action == "Billed":
                    # กรณี Submit: เปลี่ยนเป็น Billed (ถูกเรียกเก็บเงินแล้ว)
                    frappe.db.set_value("Retention Receivable", rr.parent, "status", "Billed")
                
                elif action == "Revert":
                    # กรณี Cancel: คำนวณสถานะใหม่
                    self.revert_status(rr.parent)

    def revert_status(self, receivable_name):
        # ดึง Due Date ของเอกสารต้นทางมาตรวจสอบ
        due_date = frappe.db.get_value("Retention Receivable", receivable_name, "due_date")
        
        # ตั้งค่าเริ่มต้นเป็น Active
        new_status = "Active"
        
        # ถ้ามี Due Date และ วันนี้เลยกำหนดจ่ายแล้ว -> ให้เป็น Overdue
        if due_date and getdate(due_date) < getdate(nowdate()):
            new_status = "Overdue"
            
        # อัปเดตสถานะลงฐานข้อมูล
        frappe.db.set_value("Retention Receivable", receivable_name, "status", new_status)