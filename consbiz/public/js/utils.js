//================================================================
// Bahttext Fuction
//================================================================

window.thai_baht_text = function(num) {
    if (num === null || num === undefined || num === '') return '';
    
    num = parseFloat(num).toFixed(2);
    let parts = num.split('.');
    let baht = parseInt(parts[0]);
    let satang = parseInt(parts[1]);

    let result = text_num_thai(baht);
    if (result === '') result = 'ศูนย์';
    result += 'บาท';

    if (satang === 0) {
        result += 'ถ้วน';
    } else {
        result += text_num_thai(satang) + 'สตางค์';
    }
    return result;
};

window.text_num_thai = function(num) {
    const thai_num = ["ศูนย์", "หนึ่ง", "สอง", "สาม", "สี่", "ห้า", "หก", "เจ็ด", "แปด", "เก้า"];
    const thai_unit = ["", "สิบ", "ร้อย", "พัน", "หมื่น", "แสน", "ล้าน"];
    
    let res = "";
    let num_str = num.toString();
    let len = num_str.length;

    for (let i = 0; i < len; i++) {
        let n = parseInt(num_str[i]);
        let pos = len - i - 1;
        let unit_pos = pos % 6;

        if (n !== 0) {
            // Logic "เอ็ด"
            if (unit_pos === 0 && n === 1 && i > 0) { 
                res += 'เอ็ด'; 
            } else if (unit_pos === 1 && n === 2) {
                res += 'ยี่';
            } else if (unit_pos === 1 && n === 1) {
                // สิบ
            } else {
                res += thai_num[n];
            }
            res += thai_unit[unit_pos];
        }
        
        // เติม "ล้าน"
        if (pos > 0 && pos % 6 === 0) {
            res += 'ล้าน';
        }
    }
    return res;
};

//================================================================
// BOQ Item price trend (BOQ Item form)
//================================================================

window.consbiz = window.consbiz || {};

// ราคาของรายการใน BOQ แต่ละใบ: สรุปราคามาตรฐาน/ต่ำสุด/สูงสุด + กราฟเส้น + ตาราง 10 ใบล่าสุด
consbiz.render_price_history = function (wrapper, item_code) {
    const $wrapper = $(wrapper).html(`<p class="text-muted">${__("กำลังโหลด...")}</p>`);
    return frappe
        .call("consbiz.consbiz.doctype.boq_item.boq_item.get_price_history", { item_code })
        .then(({ message: data }) => {
            const money = (value) => format_number(value, null, 2);
            const history = data.history;
            if (!history.length) {
                $wrapper.html(`<p class="text-muted">${__("ยังไม่มีรายการนี้ใน BOQ")}</p>`);
                return;
            }

            const summary = (label, field) => {
                const values = history.map((row) => flt(row[field]));
                return `<div class="col-sm-6">
                    <div class="text-muted">${label}</div>
                    <div>${__("มาตรฐาน")} <b>${money(data[field])}</b>
                        <span class="text-muted ml-2">${__("ต่ำสุด")} ${money(Math.min(...values))}
                        · ${__("สูงสุด")} ${money(Math.max(...values))}</span></div>
                </div>`;
            };
            const recent = history
                .slice(-10)
                .reverse()
                .map(
                    (row) => `<tr>
                        <td>${frappe.datetime.str_to_user(row.date)}</td>
                        <td><a href="/app/boq/${encodeURIComponent(row.boq)}">${frappe.utils.escape_html(row.boq)}</a></td>
                        <td>${frappe.utils.escape_html(row.project || "")}</td>
                        <td class="text-right">${money(row.material_rate)}</td>
                        <td class="text-right">${money(row.labour_rate)}</td>
                    </tr>`
                )
                .join("");

            $wrapper.html(`
                <div class="row small mb-3">
                    ${summary(__("ค่าวัสดุต่อหน่วย"), "material_rate")}
                    ${summary(__("ค่าแรงต่อหน่วย"), "labour_rate")}
                </div>
                <div class="price-history-chart"></div>
                <table class="table table-sm small mt-2 mb-0">
                    <thead><tr>
                        <th>${__("วันที่")}</th><th>${__("BOQ")}</th><th>${__("โครงการ")}</th>
                        <th class="text-right">${__("ค่าวัสดุ")}</th><th class="text-right">${__("ค่าแรง")}</th>
                    </tr></thead>
                    <tbody>${recent}</tbody>
                </table>`);

            new frappe.Chart($wrapper.find(".price-history-chart")[0], {
                type: "line",
                height: 220,
                data: {
                    labels: history.map((row) => frappe.datetime.str_to_user(row.date)),
                    datasets: [
                        { name: __("ค่าวัสดุ"), values: history.map((row) => flt(row.material_rate)) },
                        { name: __("ค่าแรง"), values: history.map((row) => flt(row.labour_rate)) },
                    ],
                },
                lineOptions: { dotSize: 5 },
                axisOptions: { xIsSeries: 1 },
                tooltipOptions: { formatTooltipY: (value) => money(value) },
            });
        });
};
