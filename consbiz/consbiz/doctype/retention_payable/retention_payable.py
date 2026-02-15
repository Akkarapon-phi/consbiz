import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, nowdate

class RetentionPayable(Document):
    def validate(self):
        # 1. ระบบป้องกันการสร้างซ้ำ (Hard Block)
        self.check_duplicate_invoice()
        
        # 2. คำนวณสถานะ (Logic เดิม)
        self.set_status()

    def check_duplicate_invoice(self):
        """
        ตรวจสอบว่า Purchase Invoice ในรายการนี้ เคยถูกเอาไปสร้าง Retention Payable ใบอื่นหรือยัง
        (ต้องเช็คทั้งแบบ Draft และ Submit แต่ไม่เช็ค Cancel)
        """
        for item in self.retention_items:
            # แก้ไข: เปลี่ยนจาก item.purchase_invoice เป็น item.purchase_invoice_no
            ref_no = item.purchase_invoice_no
            
            if ref_no:
                # แก้ไข: SQL WHERE t1.purchase_invoice_no ให้ตรงกับฐานข้อมูล
                duplicate = frappe.db.sql("""
                    SELECT t2.name 
                    FROM `tabRetention Items` t1
                    LEFT JOIN `tabRetention Payable` t2 ON t1.parent = t2.name
                    WHERE t1.purchase_invoice_no = %s
                    AND t1.parenttype = 'Retention Payable'
                    AND t2.docstatus < 2
                    AND t2.name != %s
                """, (ref_no, self.name or "New Document"))
                
                # ถ้าเจอ -> โวยวายทันที และห้ามบันทึก
                if duplicate:
                    frappe.throw(_("ไม่สามารถสร้างได้: Purchase Invoice {0} ถูกใช้งานแล้วในเอกสาร <a href='/app/retention-payable/{1}'>{1}</a>").format(ref_no, duplicate[0][0]))

    def set_status(self):
        if self.docstatus == 0:
            self.status = "Draft"
            return
        elif self.docstatus == 2:
            self.status = "Cancelled"
            return
        
        if self.status == "Billed":
            return

        if self.due_date and getdate(self.due_date) < getdate(nowdate()):
            self.status = "Overdue"
        else:
            self.status = "Active"

    def on_submit(self):
        self.set_status()
        self.db_set("status", self.status)

    def update_overdue_status(self):
        if self.docstatus == 1 and self.status == "Active":
            if self.due_date and getdate(self.due_date) < getdate(nowdate()):
                self.db_set("status", "Overdue")

    @staticmethod
    def update_overdue_status_all():
        active_docs = frappe.get_all("Retention Payable", filters={"status": "Active", "docstatus": 1})
        for d in active_docs:
            doc = frappe.get_doc("Retention Payable", d.name)
            doc.update_overdue_status()