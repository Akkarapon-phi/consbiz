import frappe
from frappe import _
from frappe.utils import getdate, nowdate

# ---------------------------------------------------------
# Retention Receivable Logic
# ---------------------------------------------------------

def create_retention_receivable(doc, method):
    """
    ฟังก์ชันนี้จะถูกเรียกเมื่อ Sales Invoice ถูก Submit
    สร้างเอกสาร Retention Receivable หากเงื่อนไขเป็นจริง
    """
    if not doc.custom_subject_to_retention:
        return

    if doc.custom_retention_amount <= 0:
        return

    try:
        # Check duplicate
        existing_rr = frappe.db.sql("""
            SELECT parent FROM `tabRetention Items` 
            WHERE sales_invoice_no = %s AND docstatus != 2
        """, (doc.name,))

        if existing_rr:
            frappe.msgprint(
                msg=_("เอกสาร Retention ถูกสร้างไปแล้ว: {0}").format(existing_rr[0][0]),
                title=_("แจ้งเตือน"),
                indicator='orange',
                alert=True
            )
            return

        # Find SO No
        so_no = doc.get("so_no")
        if not so_no and doc.items:
             for item in doc.items:
                 if item.sales_order:
                     so_no = item.sales_order
                     break

        # Prepare Parent
        rr_doc = frappe.get_doc({
            "doctype": "Retention Receivable",
            "company": doc.company,
            "customer": doc.customer,
            "posting_date": doc.posting_date,
            "due_date": doc.due_date,
            "project": doc.project,
            "customer_po": doc.po_no,
            "so_no": so_no,
            "status": "Draft",
            "retention_items": []
        })

        # Prepare Child
        rr_doc.append("retention_items", {
            "sales_invoice_no": doc.name,
            "posting_date": doc.posting_date,
            "due_date": doc.due_date,
            "description": f"Retention from Invoice {doc.name}",
            "base_amount": doc.net_total,
            "retention_percent": doc.custom_retention_percent,
            "amount": doc.custom_retention_amount
        })

        # Insert & Submit
        rr_doc.insert(ignore_permissions=True)
        rr_doc.submit()

        frappe.msgprint(
            msg=f"สร้างใบประกันผลงาน <a href='/app/retention-receivable/{rr_doc.name}'><b>{rr_doc.name}</b></a> เรียบร้อยแล้ว",
            title=_("สำเร็จ"),
            indicator='green',
            alert=True
        )

    except Exception as e:
        frappe.log_error(message=frappe.get_traceback(), title="Retention Creation Error")
        frappe.msgprint(
            msg=_("เกิดข้อผิดพลาดในการสร้าง Retention Receivable (ดู Error Log)"),
            indicator='red',
            alert=True
        )

def cancel_linked_retention_receivable(doc, method):
    """
    ฟังก์ชันนี้จะถูกเรียกเมื่อ Sales Invoice ถูก Cancel (เรียกผ่าน before_cancel)
    """
    try:
        # ค้นหา Retention Receivable ที่อ้างอิงถึง SI ใบนี้
        linked_rrs = frappe.db.sql("""
            SELECT DISTINCT t1.parent 
            FROM `tabRetention Items` t1
            JOIN `tabRetention Receivable` t2 ON t1.parent = t2.name
            WHERE t1.sales_invoice_no = %s
            AND t1.parenttype = 'Retention Receivable'
            AND t2.docstatus < 2
        """, (doc.name,), pluck=True)

        for rr_name in linked_rrs:
            rr_doc = frappe.get_doc("Retention Receivable", rr_name)
            
            # --- Smart Check ---
            # ถ้าถูกนำไปวางบิลแล้ว (Billed/Paid) ให้หยุดและแจ้งเตือน User
            if rr_doc.status in ["Billed", "Paid"]:
                linked_inv = frappe.db.sql("""
                    SELECT DISTINCT t1.name 
                    FROM `tabRetention Invoice` t1
                    JOIN `tabRetention Items` t2 ON t1.name = t2.parent
                    WHERE t2.reference_no = %s AND t1.docstatus < 2
                """, (rr_name,), pluck=True)
                
                inv_msg = ", ".join(linked_inv) if linked_inv else "Unknown"
                
                frappe.throw(
                    _("ไม่สามารถยกเลิก Sales Invoice นี้ได้<br>เนื่องจากใบประกันผลงาน <b>{0}</b> ถูกนำไปวางบิลแล้วในเอกสาร: <b>{1}</b><br><br>กรุณายกเลิกเอกสารปลายทางเหล่านั้นก่อน").format(rr_name, inv_msg)
                )

            # --- Auto Cancel ---
            # ข้าม permission check เพื่อให้ระบบทำงานได้แม้ user ไม่มีสิทธิ์ลบ RR โดยตรง
            rr_doc.flags.ignore_permissions = True 
            
            if rr_doc.docstatus == 1:
                rr_doc.cancel()
                frappe.msgprint(
                    msg=_("ยกเลิกใบประกันผลงาน {0} ที่เกี่ยวข้องแล้ว").format(rr_name),
                    indicator='green',
                    alert=True
                )
            
            elif rr_doc.docstatus == 0:
                frappe.delete_doc("Retention Receivable", rr_name, ignore_permissions=True)
                frappe.msgprint(
                    msg=_("ลบใบประกันผลงานร่าง {0} ที่เกี่ยวข้องแล้ว").format(rr_name),
                    indicator='green',
                    alert=True
                )

    except Exception as e:
        if isinstance(e, frappe.ValidationError):
            raise e
        frappe.log_error(frappe.get_traceback(), "Cancel Linked RR Error")
        frappe.throw(_("เกิดข้อผิดพลาดในการยกเลิก Retention Receivable ที่เกี่ยวข้อง"))


# ---------------------------------------------------------
# Retention Payable Logic (PI) - แก้ไข purchase_invoice_no
# ---------------------------------------------------------
def create_retention_payable(doc, method):
    if not doc.custom_subject_to_retention: return
    if doc.custom_retention_amount <= 0: return

    try:
        # แก้ไข: ใช้ purchase_invoice_no
        existing_rp = frappe.db.sql("""
            SELECT parent FROM `tabRetention Items` 
            WHERE purchase_invoice_no = %s AND docstatus != 2
        """, (doc.name,))

        if existing_rp:
            frappe.msgprint(msg=_("เอกสาร Retention ถูกสร้างไปแล้ว: {0}").format(existing_rp[0][0]), title=_("แจ้งเตือน"), indicator='orange', alert=True)
            return

        rp_doc = frappe.get_doc({
            "doctype": "Retention Payable",
            "company": doc.company,
            "supplier": doc.supplier,
            "posting_date": doc.posting_date,
            "due_date": doc.due_date,
            "project": doc.project,
            "bill_no": doc.bill_no,
            "status": "Draft",
            "retention_items": []
        })

        # แก้ไข: ใช้ key 'purchase_invoice_no'
        rp_doc.append("retention_items", {
            "purchase_invoice_no": doc.name,
            "posting_date": doc.posting_date,
            "due_date": doc.due_date,
            "description": f"Retention from Invoice {doc.name}",
            "base_amount": doc.net_total,
            "retention_percent": doc.custom_retention_percent,
            "amount": doc.custom_retention_amount
        })

        rp_doc.insert(ignore_permissions=True)
        rp_doc.submit()

        frappe.msgprint(msg=f"สร้างใบเจ้าหนี้ประกันผลงาน <a href='/app/retention-payable/{rp_doc.name}'><b>{rp_doc.name}</b></a> เรียบร้อยแล้ว", title=_("สำเร็จ"), indicator='green', alert=True)

    except Exception as e:
        frappe.log_error(message=frappe.get_traceback(), title="Retention Payable Creation Error")
        frappe.msgprint(msg=_("เกิดข้อผิดพลาดในการสร้าง Retention Payable (ดู Error Log)"), indicator='red', alert=True)

def cancel_linked_retention_payable(doc, method):
    try:
        # แก้ไข: ใช้ purchase_invoice_no
        linked_rps = frappe.db.sql("""
            SELECT DISTINCT t1.parent 
            FROM `tabRetention Items` t1
            JOIN `tabRetention Payable` t2 ON t1.parent = t2.name
            WHERE t1.purchase_invoice_no = %s
            AND t1.parenttype = 'Retention Payable'
            AND t2.docstatus < 2
        """, (doc.name,), pluck=True)

        for rp_name in linked_rps:
            rp_doc = frappe.get_doc("Retention Payable", rp_name)
            
            # Logic เช็คสถานะก่อนลบ (ถ้ามี)
            # if rp_doc.status == "Paid": ...

            rp_doc.flags.ignore_permissions = True 
            if rp_doc.docstatus == 1:
                rp_doc.cancel()
                frappe.msgprint(msg=_("ยกเลิกใบเจ้าหนี้ประกันผลงาน {0} ที่เกี่ยวข้องแล้ว").format(rp_name), indicator='green', alert=True)
            elif rp_doc.docstatus == 0:
                frappe.delete_doc("Retention Payable", rp_name, ignore_permissions=True)
                frappe.msgprint(msg=_("ลบใบเจ้าหนี้ประกันผลงานร่าง {0} ที่เกี่ยวข้องแล้ว").format(rp_name), indicator='green', alert=True)

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Cancel Linked RP Error")
        frappe.throw(_("เกิดข้อผิดพลาดในการยกเลิก Retention Payable ที่เกี่ยวข้อง"))

# ---------------------------------------------------------
# Transmittal Entry Logic (Shared)
# ---------------------------------------------------------
def create_transmittal_entry(doc, method):
    # สำหรับ Sales Invoice (รายรับ)
    _create_transmittal(doc, "รายรับ", doc.customer, "customer")

def create_transmittal_entry_for_pi(doc, method):
    # สำหรับ Purchase Invoice (รายจ่าย)
    _create_transmittal(doc, "รายจ่าย", doc.supplier, "supplier")

def _create_transmittal(doc, type_val, party_val, party_field):
    try:
        if frappe.db.exists("Transmittal Entry", {"document_no": doc.name, "docstatus": 1}):
            return

        is_tax = 1 if doc.total_taxes_and_charges > 0 else 0
        is_wht = 1 if doc.get("custom_subject_to_wht") else 0
        is_retention = 1 if doc.get("custom_subject_to_retention") else 0

        te_doc = frappe.get_doc({
            "doctype": "Transmittal Entry",
            "type": type_val,
            "posting_date": doc.posting_date,
            "document_no": doc.name,
            "receipt": 1,
            "tax": is_tax,
            "wht": is_wht,
            "retention": is_retention,
            "company": doc.company,
            party_field: party_val, # customer or supplier
            "project": doc.project,
            "subject": f"นำส่งเอกสาร {doc.name}",
            "status": "Draft"
        })

        te_doc.insert(ignore_permissions=True)
        te_doc.submit()
        te_doc.db_set("status", "Submitted")

        frappe.msgprint(msg=f"สร้างใบนำส่งเอกสาร <a href='/app/transmittal-entry/{te_doc.name}'><b>{te_doc.name}</b></a> เรียบร้อยแล้ว", indicator='green', alert=True)

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Transmittal Entry Creation Error")
        frappe.msgprint(msg=_("ไม่สามารถสร้าง Transmittal Entry ได้ (ดู Error Log)"), indicator='orange', alert=True)

def cancel_transmittal_entry(doc, method):
    try:
        te_name = frappe.db.get_value("Transmittal Entry", {"document_no": doc.name, "docstatus": 1}, "name")
        if te_name:
            te_doc = frappe.get_doc("Transmittal Entry", te_name)
            te_doc.flags.ignore_permissions = True
            te_doc.cancel()
            te_doc.db_set("status", "Cancelled")
            frappe.msgprint(msg=f"ยกเลิกใบนำส่งเอกสาร {te_name} เรียบร้อยแล้ว", indicator='green', alert=True)
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Transmittal Entry Cancellation Error")
        frappe.msgprint(msg=_("เกิดข้อผิดพลาดในการยกเลิก Transmittal Entry"), indicator='red', alert=True)


@frappe.whitelist()
def check_retention_exists(invoice_name):
    existing = frappe.db.sql("""
        SELECT t1.parent 
        FROM `tabRetention Items` t1
        JOIN `tabRetention Receivable` t2 ON t1.parent = t2.name
        WHERE t1.sales_invoice_no = %s AND t1.parenttype = 'Retention Receivable' AND t2.docstatus < 2 LIMIT 1
    """, (invoice_name,))
    if existing: return existing[0][0]
    return None

@frappe.whitelist()
def check_retention_payable_exists(invoice_name):
    # แก้ไข: ใช้ purchase_invoice_no ให้ถูกต้อง (สำคัญมาก)
    existing = frappe.db.sql("""
        SELECT t1.parent 
        FROM `tabRetention Items` t1
        JOIN `tabRetention Payable` t2 ON t1.parent = t2.name
        WHERE t1.purchase_invoice_no = %s AND t1.parenttype = 'Retention Payable' AND t2.docstatus < 2 LIMIT 1
    """, (invoice_name,))
    if existing: return existing[0][0]
    return None

@frappe.whitelist()
def check_transmittal_exists(document_no):
    existing = frappe.db.get_value("Transmittal Entry", {"document_no": document_no, "docstatus": ["<", 2]}, "name")
    return existing

# ---------------------------------------------------------
# Transmittal Entry Logic for Retention Invoice (เพิ่มใหม่)
# ---------------------------------------------------------

def create_transmittal_from_retention(doc, method):
    """
    สร้าง Transmittal Entry อัตโนมัติเมื่อ Retention Invoice ถูก Submit
    """
    try:
        # ตรวจสอบว่าเคยสร้างไปแล้วหรือยัง
        if frappe.db.exists("Transmittal Entry", {"document_no": doc.name, "docstatus": 1}):
            return

        # สร้างเอกสาร Transmittal Entry
        te_doc = frappe.get_doc({
            "doctype": "Transmittal Entry",
            "type": "รายรับ",              # type = รายรับ
            "posting_date": doc.posting_date, # posting_date = posting_date
            "document_no": doc.name,        # document_no = doc.name
            "receipt": 1,                   # Receipt = 1
            "tax": 0,                       # Retention มักไม่มี Tax แยกในใบนี้ (หรือถ้ามีให้ปรับ logic)
            "wht": 0,                       # ปกติ Retention ไม่โดนหัก ณ ที่จ่ายซ้ำ
            "retention": 0,                 # ตัวมันเองคือ Retention (อาจจะไม่ต้องติ๊กช่อง Retention ซ้อน)
            
            # Map ข้อมูลเพิ่มเติมเพื่อให้เอกสารสมบูรณ์
            "company": doc.company,
            "customer": doc.customer,
            "project": doc.project,
            "subject": f"นำส่งเอกสารวางบิล Retention {doc.name}",
            "status": "Draft"
        })

        te_doc.insert(ignore_permissions=True)
        te_doc.submit()
        
        # อัปเดตสถานะเป็น Submitted
        te_doc.db_set("status", "Submitted")

        frappe.msgprint(
            msg=f"สร้างใบนำส่งเอกสาร <a href='/app/transmittal-entry/{te_doc.name}'><b>{te_doc.name}</b></a> เรียบร้อยแล้ว",
            indicator='green',
            alert=True
        )

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Retention Transmittal Creation Error")
        frappe.msgprint(
            msg=_("ไม่สามารถสร้าง Transmittal Entry สำหรับ Retention ได้ (ดู Error Log)"),
            indicator='orange',
            alert=True
        )

def cancel_transmittal_from_retention(doc, method):
    """
    ยกเลิก Transmittal Entry เมื่อ Retention Invoice ถูก Cancel
    """
    try:
        # ค้นหาเอกสารที่ Submit แล้วและอ้างอิงถึง Retention นี้
        te_name = frappe.db.get_value("Transmittal Entry", {"document_no": doc.name, "docstatus": 1}, "name")
        
        if te_name:
            te_doc = frappe.get_doc("Transmittal Entry", te_name)
            
            # ข้าม Permission Check
            te_doc.flags.ignore_permissions = True
            
            te_doc.cancel()
            
            # อัปเดตสถานะเป็น Cancelled
            te_doc.db_set("status", "Cancelled")
            
            frappe.msgprint(
                msg=f"ยกเลิกใบนำส่งเอกสาร {te_name} เรียบร้อยแล้ว",
                indicator='green',
                alert=True
            )

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Retention Transmittal Cancellation Error")
        frappe.msgprint(
            msg=_("เกิดข้อผิดพลาดในการยกเลิก Transmittal Entry"),
            indicator='red',
            alert=True
        )

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
    # แก้ไข: เปลี่ยนจาก reference_no เป็น sales_invoice_no
    existing = frappe.db.sql("""
        SELECT t1.parent 
        FROM `tabRetention Items` t1
        JOIN `tabRetention Receivable` t2 ON t1.parent = t2.name
        WHERE t1.sales_invoice_no = %s
        AND t1.parenttype = 'Retention Receivable'
        AND t2.docstatus < 2
        LIMIT 1
    """, (invoice_name,))

    if existing:
        return existing[0][0] # คืนค่าชื่อเอกสาร เช่น "RR-2024-001"
    
    return None

@frappe.whitelist()
def set_user_default_company(company):
    # ตรวจสอบว่าบริษัทมีจริงหรือไม่เพื่อความปลอดภัย
    if frappe.db.exists("Company", company):
        # บันทึกค่า Default แยกตาม User ที่กำลังใช้งาน
        frappe.defaults.set_user_default("company", company)
        frappe.clear_cache(user=frappe.session.user)
        return True
    return False

@frappe.whitelist()
def check_transmittal_exists(document_no):
    """
    ตรวจสอบว่ามี Transmittal Entry ที่ Active (ไม่ Cancelled) สำหรับเอกสารนี้หรือไม่
    """
    existing = frappe.db.get_value("Transmittal Entry", {"document_no": document_no, "docstatus": ["<", 2]}, "name")
    return existing

# hooks for Journal Entry
def update_retention_on_payment_submit(doc, method):
    _update_retention_status(doc, "Paid")

def update_retention_on_payment_cancel(doc, method):
    _update_retention_status(doc, "Revert")

def _update_retention_status(je_doc, action):
    retention_inv = None
    
    # 1. Try finding in Accounts table (Reference Link)
    if je_doc.accounts:
        for row in je_doc.accounts:
            if row.reference_type == "Retention Invoice" and row.reference_name:
                retention_inv = row.reference_name
                break
    
    # 2. If not found, try parsing Description (Fallback)
    if not retention_inv:
        # Pattern: "Retention Payment for INV-RET-2024-001"
        import re
        # Check accounts rows descriptions
        for row in je_doc.accounts:
            if row.user_remark and "Retention Payment for " in row.user_remark:
                parts = row.user_remark.split("Retention Payment for ")
                if len(parts) > 1:
                    retention_inv = parts[1].strip()
                    break

    if retention_inv:
        if action == "Paid":
            # 1. Update Retention Invoice -> Paid
            frappe.db.set_value("Retention Invoice", retention_inv, "status", "Paid")
            
            # 2. Find linked Retention Receivable and update to Paid
            linked_rrs = frappe.db.sql("""
                SELECT DISTINCT reference_no 
                FROM `tabRetention Items`
                WHERE parent = %s AND parenttype = 'Retention Invoice'
            """, (retention_inv,), as_dict=True)

            for rr in linked_rrs:
                if rr.reference_no and frappe.db.exists("Retention Receivable", rr.reference_no):
                    frappe.db.set_value("Retention Receivable", rr.reference_no, "status", "Paid")
            
        elif action == "Revert":
            # 1. Revert Retention Invoice Status (Unpaid or Overdue)
            if frappe.db.exists("Retention Invoice", retention_inv): 
                r_doc = frappe.get_doc("Retention Invoice", retention_inv)
                new_status = "Unpaid"
                if r_doc.due_date and getdate(r_doc.due_date) < getdate(nowdate()):
                    new_status = "Overdue"
                frappe.db.set_value("Retention Invoice", retention_inv, "status", new_status)
                
                # 2. Revert Retention Receivable -> Billed 
                # (Since Invoice is not cancelled, just unpaid, RR should be 'Billed')
                linked_rrs = frappe.db.sql("""
                    SELECT DISTINCT reference_no 
                    FROM `tabRetention Items`
                    WHERE parent = %s AND parenttype = 'Retention Invoice'
                """, (retention_inv,), as_dict=True)

                for rr in linked_rrs:
                    if rr.reference_no and frappe.db.exists("Retention Receivable", rr.reference_no):
                        frappe.db.set_value("Retention Receivable", rr.reference_no, "status", "Billed")

@frappe.whitelist()
def get_linked_journal_entry(retention_invoice):
    # 1. Try finding by direct Reference Link
    je_account = frappe.db.sql("""
        SELECT parent FROM `tabJournal Entry Account`
        WHERE reference_type = 'Retention Invoice' AND reference_name = %s
        AND parent IN (SELECT name FROM `tabJournal Entry` WHERE docstatus < 2)
        LIMIT 1
    """, (retention_invoice,))
    
    if je_account:
        return je_account[0][0]

    # 2. Fallback: Parse Description
    search_str = f"%Retention Payment for {retention_invoice}%"
    je_account_desc = frappe.db.sql("""
        SELECT parent FROM `tabJournal Entry Account`
        WHERE user_remark LIKE %s
        AND parent IN (SELECT name FROM `tabJournal Entry` WHERE docstatus < 2)
        LIMIT 1
    """, (search_str,))
    
    if je_account_desc:
        return je_account_desc[0][0]
        
    return None

@frappe.whitelist()
def get_retention_invoice_from_rr(rr_name):
    """
    เช็คว่า Retention Receivable ใบนี้ ถูกเอาไปเปิด Retention Invoice หรือยัง
    """
    # เช็คจาก Child table ของ Retention Invoice ที่มี reference_no ตรงกับ RR Name นี้
    # ตรวจสอบทั้ง reference_no ที่เป็น RR Name โดยตรง
    exists = frappe.db.sql("""
        SELECT t1.name
        FROM `tabRetention Invoice` t1
        JOIN `tabRetention Items` t2 ON t1.name = t2.parent
        WHERE t2.reference_no = %s
        AND t1.docstatus < 2
        LIMIT 1
    """, (rr_name,))
    
    if exists:
        return exists[0][0] # Return ชื่อ Retention Invoice
    return None

