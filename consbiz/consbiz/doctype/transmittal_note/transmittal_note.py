import frappe
from frappe.model.document import Document

class TransmittalNote(Document):
    def on_submit(self):
        """
        เมื่อ Submit Transmittal Note:
        เปลี่ยนสถานะของ Transmittal Entry ที่อ้างอิงอยู่ให้เป็น 'Prepare'
        """
        self.update_linked_entry_status("Prepare")

    def on_cancel(self):
        """
        เมื่อ Cancel Transmittal Note:
        คืนสถานะของ Transmittal Entry กลับเป็น 'Submitted' (สถานะตั้งต้นก่อนถูกดึงมา)
        """
        self.update_linked_entry_status("Submitted")

    def update_linked_entry_status(self, new_status):
        updated_count = 0
        
        # วนลูปรายการใน Child Table 'transmittal_item'
        for item in self.transmittal_item:
            # reference คือเลขที่ของ Transmittal Entry (Link Field)
            if item.reference:
                if frappe.db.exists("Transmittal Entry", item.reference):
                    # อัปเดตสถานะ
                    frappe.db.set_value("Transmittal Entry", item.reference, "status", new_status)
                    updated_count += 1
        
        # (Optional) แสดงข้อความแจ้งเตือนเล็กๆ เพื่อให้ User รู้ว่ามีการอัปเดตเอกสารลูก
        # frappe.msgprint(f"Updated {updated_count} Transmittal Entries to '{new_status}'", alert=True)