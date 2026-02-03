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
