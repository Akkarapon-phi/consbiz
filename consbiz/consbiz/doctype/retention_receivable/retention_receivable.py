import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, nowdate

class RetentionReceivable(Document):
    def validate(self):
        # 1. ระบบป้องกันการสร้างซ้ำ (Hard Block)
        self.check_duplicate_invoice()
        
        # 2. คำนวณสถานะ (Logic เดิม)
        self.set_status()

    def check_duplicate_invoice(self):
        """
        ตรวจสอบว่า Sales Invoice ในรายการนี้ เคยถูกเอาไปสร้าง Retention Receivable ใบอื่นหรือยัง
        (ต้องเช็คทั้งแบบ Draft และ Submit แต่ไม่เช็ค Cancel)
        """
        for item in self.retention_items:
            if item.sales_invoice:
                # Query หาว่ามีใบอื่น (t2) ที่ไม่ใช่ใบนี้ (self.name) ใช้อินวอยซ์เดียวกันไหม
                duplicate = frappe.db.sql("""
                    SELECT t2.name 
                    FROM `tabRetention Items` t1
                    LEFT JOIN `tabRetention Receivable` t2 ON t1.parent = t2.name
                    WHERE t1.sales_invoice = %s
                    AND t1.parenttype = 'Retention Receivable'
                    AND t2.docstatus < 2
                    AND t2.name != %s
                """, (item.sales_invoice, self.name or "New Document"))
                
                # ถ้าเจอ -> โวยวายทันที และห้ามบันทึก
                if duplicate:
                    frappe.throw(_("ไม่สามารถสร้างได้: Sales Invoice {0} ถูกใช้งานแล้วในเอกสาร <a href='/app/retention-receivable/{1}'>{1}</a>").format(item.sales_invoice, duplicate[0][0]))

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
        active_docs = frappe.get_all("Retention Receivable", filters={"status": "Active", "docstatus": 1})
        for d in active_docs:
            doc = frappe.get_doc("Retention Receivable", d.name)
            doc.update_overdue_status()