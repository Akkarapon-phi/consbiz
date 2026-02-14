import frappe
from frappe.model.document import Document

class TransmittalNote(Document):
    def validate(self):
        # เก็บรายการ Reference เดิมที่มีอยู่ใน Database ก่อนที่จะถูกบันทึกทับ
        # เพื่อใช้ตรวจสอบว่ารายการไหนถูกลบออกไปบ้างในขั้นตอน on_update
        if not self.is_new():
            self.flags.old_refs = frappe.db.sql(
                "SELECT reference FROM `tabTransmittal Item` WHERE parent=%s", 
                self.name, pluck=True
            ) or []

    def on_update(self):
        """
        ทำงานเมื่อกดปุ่ม Save/Update:
        1. เปลี่ยนสถานะของรายการปัจจุบันในตารางเป็น 'Prepared'
        2. คืนสถานะรายการที่ถูกลบออกจากตารางกลับเป็น 'Submitted'
        """
        if self.docstatus < 2: # Draft หรือ Submitted
            self.sync_entry_status()

    def on_submit(self):
        # เมื่อ Submit: ย้ำสถานะเป็น 'Prepared'
        self.update_linked_entry_status("Prepared")

    def on_cancel(self):
        # เมื่อ Cancel: คืนสถานะทั้งหมดกลับเป็น 'Submitted'
        self.update_linked_entry_status("Submitted")

    def on_trash(self):
        # เมื่อ Delete: คืนสถานะทั้งหมดกลับเป็น 'Submitted'
        self.update_linked_entry_status("Submitted")

    def sync_entry_status(self):
        # 1. รายการปัจจุบันในตาราง -> บังคับ Set เป็น 'Prepared'
        current_refs = [d.reference for d in self.transmittal_item if d.reference]
        
        if current_refs:
            # ใช้ SQL Update โดยตรงเพื่อความแน่นอน (ข้าม Permission/Validations)
            # แก้เฉพาะตัวที่ยังไม่เป็น Sent (เพื่อไม่ให้ไปแตะต้องตัวที่ส่งจริงไปแล้ว)
            frappe.db.sql("""
                UPDATE `tabTransmittal Entry` 
                SET status = 'Prepared' 
                WHERE name IN %s AND status != 'Sent'
            """, (tuple(current_refs),))

        # 2. รายการที่ถูกลบออก -> Revert เป็น 'Submitted'
        # ดึงค่าเก่าที่เราเก็บไว้ใน validate
        old_refs = self.flags.old_refs if hasattr(self.flags, 'old_refs') else []
        removed_refs = set(old_refs) - set(current_refs)
        
        if removed_refs:
            frappe.db.sql("""
                UPDATE `tabTransmittal Entry` 
                SET status = 'Submitted' 
                WHERE name IN %s
            """, (tuple(removed_refs),))

    def update_linked_entry_status(self, new_status):
        refs = [d.reference for d in self.transmittal_item if d.reference]
        if refs:
            frappe.db.sql("""
                UPDATE `tabTransmittal Entry` 
                SET status = %s 
                WHERE name IN %s
            """, (new_status, tuple(refs)))

    @frappe.whitelist()
    def set_status_sent(self):
        """
        Custom Action: เปลี่ยนสถานะตัวเองและลูกๆ เป็น 'Sent'
        """
        # 1. เปลี่ยนสถานะเอกสารลูก (Entries) -> Sent
        self.update_linked_entry_status("Sent")
        
        # 2. เปลี่ยนสถานะตัวเอง (Note) -> Sent
        # ใช้ db_set เพื่อเปลี่ยนค่าใน DB โดยตรง (ไม่ต้องผ่าน validate อีก)
        self.db_set("status", "Sent")