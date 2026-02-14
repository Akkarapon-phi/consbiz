// Script for DocType: Transmittal Note

frappe.ui.form.on('Transmittal Note', {
    refresh: function(frm) {
        // ------------------------------------------------
        // กรณีสถานะ Draft
        // ------------------------------------------------
        if (frm.doc.docstatus === 0) {
            frm.add_custom_button(__('Get Submitted Entries'), function() {
                show_date_filter_dialog(frm);
            }, __('Get Items'));

            frm.add_custom_button(__('Get All Submitted Entries'), function() {
                get_submitted_entries(frm, null, null);
            }, __('Get Items'));

            frm.add_custom_button(__('Check & Remove Invalid'), function() {
                validate_and_cleanup_entries(frm);
            }, __('Get Items'));
        }

        // ------------------------------------------------
        // กรณีสถานะ Submitted
        // ------------------------------------------------
        if (frm.doc.docstatus === 1) {
            // ** เงื่อนไข: แสดงปุ่ม Add เฉพาะตอนที่สถานะ *ไม่ใช่* Sent **
            if (frm.doc.status !== 'Sent') {
                frm.add_custom_button(__('Add Submitted Entry'), function() {
                    add_submitted_entry_custom_dialog(frm);
                }, __('Get Items'));
            }

            // ปุ่ม SEND (แสดงเมื่อยังไม่ Sent)
            if (frm.doc.status !== 'Sent') {
                frm.add_custom_button(__('Send'), function() {
                    frappe.confirm(
                        __('ยืนยันการส่งเอกสาร? สถานะของ Transmittal Entry ทั้งหมดจะถูกเปลี่ยนเป็น "Sent"'),
                        function() {
                            frm.call({
                                method: 'set_status_sent',
                                doc: frm.doc,
                                freeze: true,
                                freeze_message: __('Sending...'),
                                callback: function(r) {
                                    if (!r.exc) {
                                        // รีโหลดหน้าจอเพื่อให้เห็นสถานะ Sent และปุ่มต่างๆ หายไป
                                        frm.reload_doc();
                                        frappe.show_alert({message: __('เอกสารถูกส่งเรียบร้อยแล้ว (Sent)'), indicator: 'green'});
                                    }
                                }
                            });
                        }
                    );
                }).addClass('btn-primary'); 
            }
        }
    },
    
    validate: function(frm) {
        renumber_items(frm);

        if (!frm.doc.flags) frm.doc.flags = {};
        
        if (frm.doc.transmittal_item && frm.doc.transmittal_item.length > 0) {
            if (frm.doc.flags.ignore_validate_references) return;

            let refs = frm.doc.transmittal_item.map(d => d.reference).filter(d => d);
            if (refs.length > 0) {
                frappe.validated = false; 
                
                frappe.call({
                    method: 'frappe.client.get_list',
                    args: {
                        doctype: 'Transmittal Entry',
                        filters: {
                            name: ['in', refs],
                            // อนุญาต: Submitted, Prepared, Sent
                            status: ['not in', ['Submitted', 'Prepared', 'Sent']] 
                        },
                        fields: ['name', 'status']
                    },
                    callback: function(r) {
                        if (r.message && r.message.length > 0) {
                            let invalid_docs = r.message.map(d => d.name + " (" + d.status + ")").join(', ');
                            frappe.msgprint({
                                title: __('พบเอกสารไม่พร้อมใช้งาน'),
                                message: __('มีเอกสารบางรายการที่สถานะผิดปกติ:<br><b>{0}</b><br><br>กรุณากดปุ่ม <b>"Check & Remove Invalid"</b> เพื่อตรวจสอบ', [invalid_docs]),
                                indicator: 'red'
                            });
                        } else {
                            frm.doc.flags.ignore_validate_references = true;
                            // ถ้าเป็น Draft ให้ Save, ถ้า Submitted ให้ผ่าน Validation (เพราะเราจะ Save ในฟังก์ชัน Add)
                            if (frm.doc.docstatus === 0) frm.save();
                            else frappe.validated = true; 
                        }
                    }
                });
            }
        }
    },

    customer: function(frm) {
        if(frm.doc.transmittal_item && frm.doc.transmittal_item.length > 0) {
            frappe.msgprint(__('คำแนะนำ: คุณเปลี่ยนชื่อลูกค้า อย่าลืมตรวจสอบรายการในตารางใหม่'));
        }
    }
});

// ... (ฟังก์ชัน Get / Show Dialog / Validate เดิม คงไว้เหมือนเดิม) ...

function show_date_filter_dialog(frm) {
    let d = new frappe.ui.Dialog({
        title: __('Select Date Range'),
        fields: [
            {
                label: 'From Date', fieldname: 'from_date', fieldtype: 'Date',
                default: frappe.datetime.add_months(frappe.datetime.get_today(), -1), reqd: 1,
                change: function() {
                    let from_date = d.get_value('from_date');
                    if (from_date) {
                        let date_obj = frappe.datetime.str_to_obj(from_date);
                        let last_day = new Date(date_obj.getFullYear(), date_obj.getMonth() + 1, 0);
                        d.set_value('to_date', frappe.datetime.obj_to_str(last_day));
                    }
                }
            },
            {
                label: 'To Date', fieldname: 'to_date', fieldtype: 'Date',
                default: frappe.datetime.get_today(), reqd: 1
            }
        ],
        primary_action_label: __('Get Entries'),
        primary_action: function(values) {
            get_submitted_entries(frm, values.from_date, values.to_date);
            d.hide();
        }
    });
    d.show();
}

function get_submitted_entries(frm, from_date, to_date) {
    fetch_entries_from_server(frm, from_date, to_date);
}

function fetch_entries_from_server(frm, from_date, to_date) {
    var filters = [
        ['docstatus', '=', 1],
        ['status', '=', 'Submitted']
    ];

    if (frm.doc.type) filters.push(['type', '=', frm.doc.type]);
    if (from_date) filters.push(['posting_date', '>=', from_date]);
    if (to_date) filters.push(['posting_date', '<=', to_date]);
    if (frm.doc.customer) filters.push(['customer', '=', frm.doc.customer]);
    if (frm.doc.project) filters.push(['project', '=', frm.doc.project]);
    if (frm.doc.company) filters.push(['company', '=', frm.doc.company]);

    var existing_refs = (frm.doc.transmittal_item || []).map(d => d.reference);

    frappe.call({
        method: 'frappe.client.get_list',
        args: {
            doctype: 'Transmittal Entry',
            filters: filters,
            fields: ['name', 'document_no', 'type', 'receipt', 'tax', 'wht', 'retention'],
            limit_page_length: 0
        },
        freeze: true,
        freeze_message: __('กำลังดึงข้อมูล...'),
        callback: function(r) {
            if (r.message && r.message.length > 0) {
                var added_count = 0;
                r.message.forEach(function(entry) {
                    if (!existing_refs.includes(entry.name)) {
                        var row = frm.add_child('transmittal_item');
                        row.reference = entry.name;
                        row.document_no = entry.document_no;
                        row.receipt = entry.receipt;
                        row.tax = entry.tax;
                        row.wht = entry.wht;
                        row.retention = entry.retention;
                        existing_refs.push(entry.name);
                        added_count++;
                    }
                });

                if (added_count > 0) {
                    renumber_items(frm);
                    frm.refresh_field('transmittal_item');
                    frappe.show_alert({message: __('เพิ่มรายการใหม่ ' + added_count + ' รายการ'), indicator: 'green'});
                } else {
                    frappe.msgprint(__('ไม่พบรายการใหม่ (รายการที่มีสถานะ Submitted ถูกเพิ่มไปหมดแล้ว)'));
                }
            } else {
                frappe.msgprint(__('ไม่พบเอกสาร Transmittal Entry ที่มีสถานะ Submitted (ตามเงื่อนไข)'));
            }
        }
    });
}

function validate_and_cleanup_entries(frm) {
    if (!frm.doc.transmittal_item || frm.doc.transmittal_item.length === 0) {
        frappe.msgprint(__('ไม่มีรายการในตารางให้ตรวจสอบ'));
        return;
    }

    let refs = frm.doc.transmittal_item.map(d => d.reference).filter(d => d);

    frappe.call({
        method: 'frappe.client.get_list',
        args: {
            doctype: 'Transmittal Entry',
            filters: {
                name: ['in', refs],
                status: ['not in', ['Submitted', 'Prepared', 'Sent']] 
            },
            fields: ['name']
        },
        freeze: true,
        freeze_message: __('กำลังตรวจสอบสถานะเอกสาร...'),
        callback: function(r) {
            let remove_list = [];
            if (r.message && r.message.length > 0) {
                remove_list = r.message.map(d => d.name);
            }

            if (remove_list.length > 0) {
                let rows = frm.doc.transmittal_item;
                for (let i = rows.length - 1; i >= 0; i--) {
                    if (remove_list.includes(rows[i].reference)) {
                        rows.splice(i, 1);
                    }
                }
                
                renumber_items(frm);
                frm.refresh_field('transmittal_item');
                
                frappe.msgprint({
                    title: __('อัปเดตเรียบร้อย'),
                    message: __('ลบรายการที่ไม่พร้อมใช้งานออกจำนวน <b>{0}</b> รายการ', [remove_list.length]),
                    indicator: 'green'
                });
            } else {
                frappe.msgprint({
                    title: __('ตรวจสอบเรียบร้อย'),
                    message: __('เอกสารทั้งหมดสถานะปกติ'),
                    indicator: 'green'
                });
            }
        }
    });
}

// ... (ฟังก์ชัน Custom Dialog และ Add Entry เหมือนเดิม) ...

function add_submitted_entry_custom_dialog(frm) {
    let d = new frappe.ui.Dialog({
        title: __('Add Submitted Entry'),
        size: 'extra-large',
        fields: [
            {
                fieldtype: 'Section Break', label: __('Filters')
            },
            {
                fieldname: 'from_date', label: __('From Date'), fieldtype: 'Date',
                default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
                change: () => refresh_dialog_table()
            },
            {
                fieldname: 'to_date', label: __('To Date'), fieldtype: 'Date',
                default: frappe.datetime.get_today(),
                change: () => refresh_dialog_table()
            },
            {
                fieldtype: 'Column Break'
            },
            {
                fieldname: 'customer', label: __('Customer'), fieldtype: 'Link', options: 'Customer',
                default: frm.doc.customer, read_only: 1
            },
            {
                fieldname: 'project', label: __('Project'), fieldtype: 'Link', options: 'Project',
                default: frm.doc.project, read_only: 1
            },
            {
                fieldtype: 'Section Break', label: __('Select Documents')
            },
            {
                fieldname: 'html_results', fieldtype: 'HTML',
                label: 'Results'
            }
        ],
        primary_action_label: __('Add Selected'),
        primary_action: function() {
            let selected_entries = [];
            d.$wrapper.find('.entry-checkbox:checked').each(function() {
                selected_entries.push($(this).attr('data-name'));
            });

            if (selected_entries.length > 0) {
                fetch_and_add_entries(frm, selected_entries);
                d.hide();
            } else {
                frappe.msgprint(__('Please select at least one document.'));
            }
        }
    });

    let refresh_dialog_table = function() {
        let values = d.get_values();
        let existing_refs = (frm.doc.transmittal_item || []).map(d => d.reference);

        let filters = [
            ['docstatus', '=', 1],
            ['status', '=', 'Submitted'],
            ['name', 'not in', existing_refs]
        ];

        if (values.from_date) filters.push(['posting_date', '>=', values.from_date]);
        if (values.to_date) filters.push(['posting_date', '<=', values.to_date]);
        if (frm.doc.type) filters.push(['type', '=', frm.doc.type]);
        if (values.customer) filters.push(['customer', '=', values.customer]);
        if (values.project) filters.push(['project', '=', values.project]);
        if (frm.doc.company) filters.push(['company', '=', frm.doc.company]);

        frappe.call({
            method: 'frappe.client.get_list',
            args: {
                doctype: 'Transmittal Entry',
                filters: filters,
                fields: ['name', 'document_no', 'posting_date', 'receipt', 'tax', 'wht', 'retention'],
                limit_page_length: 50
            },
            freeze: true,
            callback: function(r) {
                let html = `
                    <div style="max-height: 400px; overflow-y: auto;">
                    <table class="table table-bordered table-hover">
                        <thead style="position: sticky; top: 0; background: white; z-index: 1;">
                            <tr>
                                <th width="5%" class="text-center"><input type="checkbox" id="select-all-entries"></th>
                                <th width="20%">${__('Ref No')}</th>
                                <th width="20%">${__('Doc No')}</th>
                                <th width="15%">${__('Date')}</th>
                                <th width="10%" class="text-center">Rcpt</th>
                                <th width="10%" class="text-center">Tax</th>
                                <th width="10%" class="text-center">WHT</th>
                                <th width="10%" class="text-center">Ret</th>
                            </tr>
                        </thead>
                        <tbody>`;

                if (r.message && r.message.length > 0) {
                    r.message.forEach(row => {
                        html += `
                            <tr>
                                <td class="text-center"><input type="checkbox" class="entry-checkbox" data-name="${row.name}"></td>
                                <td>${row.name}</td>
                                <td>${row.document_no || '-'}</td>
                                <td>${frappe.datetime.str_to_user(row.posting_date)}</td>
                                <td class="text-center">${row.receipt ? '✔' : ''}</td>
                                <td class="text-center">${row.tax ? '✔' : ''}</td>
                                <td class="text-center">${row.wht ? '✔' : ''}</td>
                                <td class="text-center">${row.retention ? '✔' : ''}</td>
                            </tr>
                        `;
                    });
                } else {
                    html += `<tr><td colspan="8" class="text-center text-muted">${__('No matching documents found')}</td></tr>`;
                }

                html += `</tbody></table></div>`;
                d.fields_dict.html_results.$wrapper.html(html);

                d.$wrapper.find('#select-all-entries').on('change', function() {
                    let checked = $(this).is(':checked');
                    d.$wrapper.find('.entry-checkbox').prop('checked', checked);
                });
            }
        });
    };

    d.show();
    refresh_dialog_table();
}

function fetch_and_add_entries(frm, selections) {
    frappe.call({
        method: 'frappe.client.get_list',
        args: {
            doctype: 'Transmittal Entry',
            filters: { name: ['in', selections] },
            fields: ['name', 'document_no', 'receipt', 'tax', 'wht', 'retention']
        },
        freeze: true,
        freeze_message: __('กำลังเพิ่มรายการ...'),
        callback: function(r) {
            if (r.message) {
                let added_count = 0;
                r.message.forEach(entry => {
                    let row = frm.add_child('transmittal_item');
                    row.reference = entry.name;
                    row.document_no = entry.document_no;
                    row.receipt = entry.receipt;
                    row.tax = entry.tax;
                    row.wht = entry.wht;
                    row.retention = entry.retention;
                    added_count++;
                });

                if (added_count > 0) {
                    renumber_items(frm);
                    frm.refresh_field('transmittal_item');
                    frm.save();
                    frappe.show_alert({message: __('เพิ่มเอกสาร ' + added_count + ' รายการและบันทึกแล้ว'), indicator: 'green'});
                }
            }
        }
    });
}

function renumber_items(frm) {
    if (frm.doc.transmittal_item && frm.doc.transmittal_item.length > 0) {
        frm.doc.transmittal_item.forEach((row, index) => {
            row.idx = index + 1;
        });
    }
}