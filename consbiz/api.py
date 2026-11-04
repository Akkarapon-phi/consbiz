import frappe
from frappe import _

# เงินประกันผลงาน (Retention) อยู่ที่ consbiz/retention.py


# ---------------------------------------------------------
# Update Tax No. to Sales Invoice
# ---------------------------------------------------------

def update_si_tax(doc, method):
    # รอ 1 วินาที เพื่อให้ระบบ Gen เลขเสร็จ (ถ้าจำเป็น)
    # time.sleep(1) 
    
    # สั่งโหลดข้อมูลตัวเองใหม่จากฐานข้อมูล เพื่อให้ได้เลขที่เพิ่งเจนสดๆ
    doc.reload() 

    if doc.tax_invoice_number:
        for reference in doc.references:
            if reference.reference_doctype == "Sales Invoice":
                frappe.db.set_value("Sales Invoice", reference.reference_name, {
                    "tax_invoice_number": doc.tax_invoice_number,
                    "tax_invoice_date": doc.tax_invoice_date
                }, update_modified=False) # ไม่ให้วันที่แก้ไขใน SI เปลี่ยน
                
                # แสดงข้อความแจ้งเตือน
            frappe.msgprint(
                msg=f"อัปเดตเลขที่ {doc.tax_invoice_number} ไปยัง {reference.reference_name} แล้ว",
                alert=True,    # บรรทัดนี้จะทำให้มันแสดงผลเป็น Alert/Toast เหมือน show_alert
                indicator="green"
            )


@frappe.whitelist()
def set_user_default_company(company):
    # ตรวจสอบว่าบริษัทมีจริงหรือไม่เพื่อความปลอดภัย
    if frappe.db.exists("Company", company):
        # บันทึกค่า Default แยกตาม User ที่กำลังใช้งาน
        frappe.defaults.set_user_default("company", company)
        frappe.clear_cache(user=frappe.session.user)
        return True
    return False


