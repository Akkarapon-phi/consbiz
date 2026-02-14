// Script for DocType: Transmittal Entry

frappe.ui.form.on('Transmittal Entry', {
    refresh: function(frm) {
        // แสดงปุ่มเสมอถ้ามีเลขที่เอกสาร
        if (frm.doc.document_no) {
             frm.add_custom_button(__('Create Transmittal Note'), function() {
                 create_transmittal_note(frm);
             }, __('Action'));
        }
    }
});

function create_transmittal_note(frm) {
    if (!frm.doc.document_no) {
        frappe.msgprint(__('กรุณาระบุ Document No ในส่วนหัวก่อน'));
        return;
    }

    // เตรียมข้อมูลสำหรับการสร้างเอกสารใหม่ 'Transmittal Note'
    frappe.model.with_doctype('Transmittal Note', function() {
        
        // 1. สร้างเอกสารใหม่ใน Memory
        var new_doc = frappe.model.get_new_doc('Transmittal Note');
        
        // 2. Map ข้อมูล Header (Type -> Type)
        new_doc.type = frm.doc.type;
        
        // Map ข้อมูลพื้นฐานอื่นๆ
        if(frm.doc.company) new_doc.company = frm.doc.company;
        if(frm.doc.customer) new_doc.customer = frm.doc.customer;
        if(frm.doc.project) new_doc.project = frm.doc.project;

        // 3. Map ข้อมูลลง Child Table
        var target_table_field = 'transmittal_item'; 
        var target_child_doctype = 'Transmittal Item';

        // เพิ่มแถวใหม่ในเอกสารใหม่
        var row = frappe.model.add_child(new_doc, target_child_doctype, target_table_field);
        
        // --- Set Reference ---
        row.reference = frm.doc.name; 

        // --- แก้ไข: Force Map ข้อมูลลงไปตรงๆ (ไม่ต้องรอ Fetch) ---
        // สาเหตุ: การ Fetch อัตโนมัติมักไม่ทำงานตอนสร้าง Doc แบบ Programmatic
        // เราจึงใส่ค่าจากต้นทาง (frm.doc) ลงไปเลยเพื่อให้ข้อมูลขึ้นทันที
        row.document_no = frm.doc.document_no;
        row.receipt = frm.doc.receipt;
        row.tax = frm.doc.tax;
        row.wht = frm.doc.wht;
        row.retention = frm.doc.retention;

        // 4. เปิดหน้าจอสร้างเอกสารใหม่
        frappe.set_route('Form', 'Transmittal Note', new_doc.name);
    });
}