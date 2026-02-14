import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, nowdate, flt, add_days

class RetentionInvoice(Document):
    def before_insert(self):
        # ตั้งค่าเริ่มต้น
        self.status = "Draft"
        
        # เงื่อนไข: เมื่อทำการ Amend (แก้ไขเอกสารที่ยกเลิก) ไม่ให้ copy ค่าการจ่ายเงินมาด้วย
        if self.amended_from:
            self.mode_of_payment = None
            self.account = None
            self.bank = None
            self.bank_account_no = None

    def validate(self):
        # ถ้า Amend แต่ยังเป็น Draft ให้สถานะเป็น Draft
        if self.amended_from and self.docstatus == 0:
            self.status = "Draft"
        
        # 1. คำนวณ Due Date (Server-side)
        self.calculate_due_date()

        # 2. ดึงข้อมูลธนาคาร (อัปเดตเมื่อมีการเปลี่ยนแปลง หรือก่อน Submit)
        # เช็คว่าถ้ายังไม่มีข้อมูลธนาคาร ให้ดึง Default ของบริษัทมาใส่
        if not self.bank or not self.bank_account_no:
            self.fetch_bank_details()

    def calculate_due_date(self):
        """
        คำนวณ Due Date จาก Credit Day (Server-side Validation)
        """
        if self.credit_day and self.posting_date:
            # คำนวณใหม่เสมอเพื่อความถูกต้อง (Posting Date + Credit Day)
            self.due_date = add_days(self.posting_date, int(self.credit_day))
        
        # ถ้ายังไม่มี Due Date (เช่น ไม่ได้ใส่ Credit Day และไม่ได้เลือกวันที่) ให้แจ้งเตือน
        if not self.due_date:
             frappe.throw(_("กรุณาระบุวันครบกำหนดชำระ (Due Date) หรือจำนวนวันเครดิต (Credit Day)"))

    def fetch_bank_details(self):
        """
        ดึงข้อมูลบัญชีธนาคาร Default ของบริษัทมาใส่
        """
        bank_account = frappe.db.get_value("Bank Account", 
            {"company": self.company, "is_default": 1}, 
            ["bank", "bank_account_no"], 
            as_dict=True
        )
        if bank_account:
            self.bank = bank_account.bank
            self.bank_account_no = bank_account.bank_account_no

    def on_submit(self):
        """
        เมื่อ Submit Retention Invoice:
        1. เปลี่ยนสถานะเอกสารนี้เป็น Unpaid หรือ Overdue
        2. ให้ไปเปลี่ยนสถานะของ Retention Receivable ที่เกี่ยวข้องเป็น 'Billed'
        """
        # Ensure we have the latest state
        self.reload()
        
        # 1. อัปเดตสถานะของตัวเอง
        self.update_status_on_submit()
        
        # 2. ส่ง Action "Billed" เพื่อไปอัปเดต Retention Receivable ต้นทาง
        self.update_receivable_status("Billed")

    def update_status_on_submit(self):
        # เมื่อกดปุ่ม Submit ให้เปลี่ยนสถานะเป็น Unpaid แต่ถ้าเกิน Due Date ให้เปลี่ยนเป็น Overdue
        new_status = "Unpaid"
        if self.due_date and getdate(self.due_date) < getdate(nowdate()):
            new_status = "Overdue"
        
        self.db_set("status", new_status)

    def on_cancel(self):
        """
        เมื่อ Cancel Retention Invoice:
        ให้คืนสถานะ Retention Receivable ที่เกี่ยวข้องกลับเป็น 'Active' หรือ 'Overdue'
        โดยเช็คจาก Due Date เทียบกับวันปัจจุบัน
        """
        self.db_set("status", "Cancelled") # เปลี่ยนสถานะตัวเอง
        self.update_receivable_status("Revert") # คืนสถานะเอกสารต้นทาง
        self.cancel_linked_journal_entry() # ยกเลิก JV ที่ผูกอยู่ (ถ้ามี)

    def cancel_linked_journal_entry(self):
        # Find linked JE (via User Remark or Direct Reference)
        je_name = None
        
        # 1. Try User Remark
        je_name = frappe.db.get_value("Journal Entry Account", 
            {"user_remark": ("like", f"%Retention Payment for {self.name}%"), "docstatus": 1}, 
            "parent"
        )
        
        # 2. Try Reference (if enabled later)
        if not je_name:
             je_name = frappe.db.get_value("Journal Entry Account", 
                {"reference_type": "Retention Invoice", "reference_name": self.name, "docstatus": 1}, 
                "parent"
            )
            
        if je_name:
            je = frappe.get_doc("Journal Entry", je_name)
            if je.docstatus == 1:
                je.cancel()
                frappe.msgprint(f"Cancelled linked Journal Entry: {je_name}", indicator="green", alert=True)

    def update_receivable_status(self, action):
        """
        อัปเดตสถานะของ Retention Receivable (RR) ต้นทาง
        """
        updated_rrs = []
        
        # วนลูปทุกรายการใน Child Table ของ Retention Invoice
        for item in self.retention_items:
            # reference_no ในตารางนี้ เราเก็บ 'ชื่อ Retention Receivable' ไว้ (จาก JS)
            rr_name = item.reference_no 

            if not rr_name:
                continue

            # ป้องกันการอัปเดตซ้ำใน loop เดียวกัน (กรณีมีหลาย Item มาจาก RR เดียวกัน)
            if rr_name in updated_rrs:
                continue

            # ตรวจสอบว่าเอกสาร RR มีอยู่จริง
            if frappe.db.exists("Retention Receivable", rr_name):
                if action == "Billed":
                    # กรณี Submit: เปลี่ยนเป็น Billed (วางบิลแล้ว)
                    frappe.db.set_value("Retention Receivable", rr_name, "status", "Billed")
                
                elif action == "Revert":
                    # กรณี Cancel: คำนวณสถานะใหม่กลับคืน
                    self.revert_status(rr_name)
                
                updated_rrs.append(rr_name)

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

@frappe.whitelist()
def create_payment_entry(docname, mode_of_payment, account):
    # 1. ดึงข้อมูล Retention Invoice
    doc = frappe.get_doc("Retention Invoice", docname)
    
    # 2. อัปเดตข้อมูลลงใน Doctype นี้ (Mode of Payment, Account)
    doc.db_set("mode_of_payment", mode_of_payment)
    doc.db_set("account", account)

    # 3. เตรียมข้อมูลสำหรับ Journal Entry
    # ดึง account custom_retention_receivable จาก Company
    retention_receivable_account = frappe.get_value("Company", doc.company, "custom_retention_receivable")
    if not retention_receivable_account:
        frappe.throw(f"Please set 'Retention Receivable' account in Company {doc.company}")

    je = frappe.new_doc("Journal Entry")
    je.voucher_type = "Journal Entry"
    je.naming_series = "JV-.YYYY.-"
    je.company = doc.company
    je.posting_date = nowdate()
    # je.ref_no = doc.name # Optional: Link reference

    # Row 1: Retention Receivable Account (Debit)
    je.append("accounts", {
        "account": retention_receivable_account,
        "party_type": "Customer",
        "party": doc.customer,
        "debit_in_account_currency": doc.grand_total,
        "credit_in_account_currency": 0,
        "user_remark": f"Retention Payment for {doc.name}",
    })

    # Row 2: Payment Account (Credit) (จากที่เลือกใน Popup)
    je.append("accounts", {
        "account": account,
        "debit_in_account_currency": 0,
        "credit_in_account_currency": doc.grand_total,
        "user_remark": f"Payment for {doc.name}"
    })

    # Save to generate ID (but let user submit)
    je.save()
    
    return je