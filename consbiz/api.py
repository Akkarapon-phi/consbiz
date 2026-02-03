import frappe
from frappe import _

def create_retention_receivable(doc, method):
    """
    ฟังก์ชันนี้จะถูกเรียกเมื่อ Sales Invoice ถูก Submit
    สร้างเอกสาร Retention Receivable หากเงื่อนไขเป็นจริง
    """
    
    # 1. ตรวจสอบเงื่อนไขว่าต้องหัก Retention หรือไม่
    if not doc.custom_subject_to_retention:
        return

    # 2. ตรวจสอบยอดเงิน (กันเหนียว) ถ้า Retention เป็น 0 ไม่ต้องสร้าง
    if doc.custom_retention_amount <= 0:
        return

    try:
        # 3. ตรวจสอบว่าเคยมีการสร้าง Retention สำหรับ Invoice ใบนี้ไปแล้วหรือยัง?
        # ป้องกันการสร้างซ้ำ (Duplicate)
        existing_rr = frappe.db.sql("""
            SELECT parent FROM `tabRetention Items` 
            WHERE sales_invoice = %s AND docstatus != 2
        """, (doc.name,))

        if existing_rr:
            frappe.msgprint(
                msg=_("เอกสาร Retention ถูกสร้างไปแล้ว: {0}").format(existing_rr[0][0]),
                title=_("แจ้งเตือน"),
                indicator='orange',
                alert=True
            )
            return

        # 4. เตรียมข้อมูลสำหรับ Retention Receivable (Parent)
        rr_doc = frappe.get_doc({
            "doctype": "Retention Receivable",
            "company": doc.company,
            "customer": doc.customer,
            "posting_date": doc.posting_date,
            "due_date": doc.due_date, # ควรใส่ Due Date ด้วยเพื่อให้ติดตามหนี้ได้
            "project": doc.project,
            "customer_po": doc.po_no, # Map field: po_no -> customer_po
            "status": "Draft",
            "retention_items": [] # เตรียม Child Table
        })

        # 5. เตรียมข้อมูลสำหรับ Child Table (retention_items)
        rr_doc.append("retention_items", {
            "sales_invoice": doc.name,       # เลขที่ SI
            "posting_date": doc.posting_date, # สำคัญ: ใส่เพื่อใช้อ้างอิง
            "due_date": doc.due_date,         # สำคัญ: ใส่เพื่อใช้อ้างอิง
            "description": f"Retention from Invoice {doc.name}",
            "base_amount": doc.net_total,    # Map field: net_total -> base_amount
            "retention_percent": doc.custom_retention_percent,
            "amount": doc.custom_retention_amount # Map field: custom_retention_amount -> amount
        })

        # 6. บันทึกเอกสาร (Insert)
        # ignore_permissions=True เพื่อให้ระบบสร้างได้แม้ User อาจไม่มีสิทธิ์ Create ตรงๆ
        rr_doc.insert(ignore_permissions=True)

        # 7. แจ้งเตือนผู้ใช้งาน (Realtime Alert)
        frappe.msgprint(
            msg=f"สร้างใบประกันผลงานร่าง <a href='/app/retention-receivable/{rr_doc.name}'><b>{rr_doc.name}</b></a> เรียบร้อยแล้ว",
            title=_("สำเร็จ"),
            indicator='green',
            alert=True
        )

    except Exception as e:
        # กรณีเกิด Error ให้บันทึก Log แต่ไม่ Block การ Submit ของ SI
        frappe.log_error(message=frappe.get_traceback(), title="Retention Creation Error")
        frappe.msgprint(
            msg=_("เกิดข้อผิดพลาดในการสร้าง Retention Receivable (ดู Error Log)"),
            indicator='red',
            alert=True
        )
#--------------------------------------------------#

# Update Tax No. to Sales Invoice
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


#--------------------------------------------------

@frappe.whitelist()
def check_retention_exists(invoice_name):
    """
    ตรวจสอบว่ามี Retention Receivable ที่ Active สำหรับ Invoice นี้หรือไม่
    คืนค่า: ชื่อเอกสาร (String) ถ้ามี, หรือ None ถ้าไม่มี
    """
    # ค้นหา Parent จากตารางลูก โดยเช็คเงื่อนไข:
    # 1. เป็น Retention Receivable
    # 2. สถานะ Parent ไม่ใช่ Cancelled (docstatus < 2)
    existing = frappe.db.sql("""
        SELECT t1.parent 
        FROM `tabRetention Items` t1
        JOIN `tabRetention Receivable` t2 ON t1.parent = t2.name
        WHERE t1.sales_invoice = %s
        AND t1.parenttype = 'Retention Receivable'
        AND t2.docstatus < 2
        LIMIT 1
    """, (invoice_name,))

    if existing:
        return existing[0][0] # คืนค่าชื่อเอกสาร เช่น "RR-2024-001"
    
    return None

#--------------------------------------------------

# ในไฟล์ api.py

@frappe.whitelist()
def check_retention_payable_exists(invoice_name):
    """
    ตรวจสอบว่ามี Retention Payable ที่ Active สำหรับ PI นี้หรือไม่
    """
    existing = frappe.db.sql("""
        SELECT t1.parent 
        FROM `tabRetention Items` t1
        JOIN `tabRetention Payable` t2 ON t1.parent = t2.name
        WHERE t1.purchase_invoice = %s
        AND t1.parenttype = 'Retention Payable'
        AND t2.docstatus < 2
        LIMIT 1
    """, (invoice_name,))

    if existing:
        return existing[0][0]
    
    return None