import frappe
from frappe.model.document import Document

class TransmittalNote(Document):
    def on_update(self):
        """
        ทำงานเมื่อกดปุ่ม Save (Draft)
        """
        if self.docstatus < 2: 
            self.sync_entry_status()

    def on_update_after_submit(self):
        """
        ทำงานเมื่อกดปุ่ม Save (Submitted)
        """
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

    @frappe.whitelist() # เพิ่มบรรทัดนี้เพื่อให้ JavaScript เรียกใช้ได้
    def sync_entry_status(self):
        """
        ฟังก์ชันหลักในการเปลี่ยนสถานะ:
        1. รายการที่เหลืออยู่ -> 'Prepared'
        2. รายการที่หายไป (ถูกลบ) -> 'Submitted'
        """
        # 1. รายการปัจจุบัน (Current Items)
        items = self.get("transmittal_item") or []
        current_refs = set(d.reference for d in items if d.reference)
        
        # 1.1 อัปเดตรายการปัจจุบันเป็น 'Prepared' (จองไว้)
        if current_refs:
            placeholders = ', '.join(['%s'] * len(current_refs))
            # อัปเดตเป็น Prepared (เฉพาะที่ยังไม่ Sent เพื่อไม่ให้ทับสถานะส่งแล้ว)
            frappe.db.sql(f"""
                UPDATE `tabTransmittal Entry` 
                SET status = 'Prepared' 
                WHERE name IN ({placeholders}) AND status != 'Sent'
            """, tuple(current_refs))

        # 2. หาความแตกต่างเพื่อดูว่ามีอะไรถูกลบไปบ้าง (Removed Items)
        # ใช้ get_doc_before_save() เพื่อดึงข้อมูลก่อนบันทึก (แม่นยำกว่า before_save hook)
        old_doc = self.get_doc_before_save()
        old_refs = set()
        if old_doc and old_doc.get("transmittal_item"):
            old_refs = set(d.reference for d in old_doc.transmittal_item if d.reference)
        
        removed_refs = old_refs - current_refs
        
        # 2.1 คืนสถานะรายการที่ถูกลบเป็น 'Submitted' (ปล่อยจอง)
        if removed_refs:
            placeholders_rm = ', '.join(['%s'] * len(removed_refs))
            # คืนสถานะเป็น Submitted เฉพาะตัวที่เป็น Prepared (ถ้า Cancelled อยู่แล้วก็ปล่อยไว้)
            frappe.db.sql(f"""
                UPDATE `tabTransmittal Entry` 
                SET status = 'Submitted' 
                WHERE name IN ({placeholders_rm}) AND status = 'Prepared'
            """, tuple(removed_refs))

    def update_linked_entry_status(self, new_status):
        items = self.get("transmittal_item") or []
        refs = [d.reference for d in items if d.reference]
        if refs:
            placeholders = ', '.join(['%s'] * len(refs))
            params = (new_status,) + tuple(refs)
            frappe.db.sql(f"""
                UPDATE `tabTransmittal Entry` 
                SET status = %s 
                WHERE name IN ({placeholders})
            """, params)

    @frappe.whitelist()
    def set_status_sent(self):
        """
        Custom Action: เปลี่ยนสถานะตัวเองและลูกๆ เป็น 'Sent'
        """
        self.update_linked_entry_status("Sent")
        self.db_set("status", "Sent")