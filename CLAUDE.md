# ConsBiz

แอป Frappe v16 สำหรับธุรกิจก่อสร้าง (โมดูลเดียวชื่อ `ConsBiz`) ทำงานบน ERPNext ร่วมกับ `hrms`, `erpnext_thailand` และ `print_designer`

**repo นี้เป็น public** ห้าม commit รหัสผ่าน, token, `site_config.json`, ไฟล์ backup หรือข้อมูลลูกค้า/พนักงานจริง

## Branch และการขึ้นระบบ

- พัฒนาบน `develop` เท่านั้น ห้าม commit ตรงเข้า `main`
- ขึ้นระบบจริงด้วย PR `develop` → `main` เซิร์ฟเวอร์จริงดึงจาก `main`
- ห้ามแก้ DocType หรือ customization บนเซิร์ฟเวอร์จริง ทุกอย่างทำในเครื่อง dev แล้วผ่าน git
- อัปเดตเซิร์ฟเวอร์จริง: backup → `git pull` → `bench --site <site> migrate` → `bench build --app consbiz` → `bench restart`

## ของที่สร้างผ่านหน้าเว็บ ต้องเข้า git อย่างไร

เครื่อง dev เปิด `developer_mode` ไว้

- **DocType**: แก้ผ่านหน้าเว็บได้เลย ระบบจะเขียนไฟล์ลง `consbiz/consbiz/doctype/<name>/` เอง ต้องเป็น standard (ไม่ติ๊ก Is Custom) และ Module = `ConsBiz`
- **Custom Field, Property Setter, Client Script, Print Format**: ตั้ง Module = `ConsBiz` แล้วรัน
  `bench --site <dev-site> export-fixtures --app consbiz` (ตัวกรองอยู่ใน `fixtures` ของ `hooks.py`)
- **Report** ที่ไม่ใช่ standard: เพิ่มชื่อในรายการ `Report` ของ `fixtures`
- ห้ามติดป้าย `ConsBiz` ให้ field ที่แอปอื่นสร้าง (hrms, erpnext_thailand, print_designer) ไม่งั้นจะชนกันตอนอัปเกรด

สิ่งที่เคยพลาด:

- DocType แบบ standard ห้ามมี `default_print_format` ให้ย้ายไปเป็น Property Setter (เหมือนที่ Customize Form ทำ)
- โฟลเดอร์ DocType ใหม่ต้องมี `__init__.py`
- DocType แบบ standard ที่อยู่ในฐานข้อมูลแต่ไม่มีไฟล์ใน repo จะถูก `migrate` ลบทิ้งเป็น orphan
- การ import ไฟล์ DocType ตอน migrate จะข้ามถ้าฐานข้อมูลมี `modified` ใหม่กว่าไฟล์

## โครงสร้าง

- `consbiz/hooks.py`: `doc_events`, `doctype_js`, `fixtures`, `scheduler_events`
- `consbiz/api.py`: logic ที่ผูกกับ doc_events (Retention, Transmittal)
- `consbiz/utils.py`: ตัวแปร naming series `ABBR`
- `consbiz/public/js/`: สคริปต์ฝั่งฟอร์ม (`doctype_js`) และ helper กลางใน `utils.js` เช่น `thai_baht_text()`
- `consbiz/public/css/style.css`: ฟอนต์และสีของหน้าจอ desk
- `consbiz/fixtures/`: ไฟล์ที่ export จาก `export-fixtures` อย่าแก้ด้วยมือ ให้แก้ในหน้าเว็บแล้ว export ใหม่

## แนวทางเขียนโค้ด

- Python: indent ด้วย tab, เครื่องหมายคำพูดคู่, ruff ตาม `pyproject.toml`
- JS: prettier ตาม `.pre-commit-config.yaml`
- ข้อความที่แสดงผู้ใช้เป็นภาษาไทย และครอบด้วย `_()` / `__()`
- fieldname ของ Custom Field ขึ้นต้นด้วย `custom_`
- เอกสารที่ submit ได้ใช้ `autoname = naming_series:` และใช้ `.ABBR.` ได้ถ้าต้องการตัวย่อบริษัท/โครงการ
- ใช้ `frappe.qb` หรือ `frappe.db.get_*` ก่อน `frappe.db.sql` และใส่ค่าผ่าน parameter เสมอ

## หน้าตา (UI และเอกสารพิมพ์)

- ฟอนต์: Inter สำหรับอังกฤษ, Noto Sans Thai สำหรับไทย (กำหนดใน `style.css`)
- สีที่ใช้อยู่: ตัวอักษรหัวข้อ `#383838`, แท็บ `#525252`, เส้นตารางในเอกสารพิมพ์ `#BFBFBF`, พื้นไฮไลต์ `#E8F0FE`
- สีใหม่ให้ประกาศเป็นตัวแปร `--consbiz-*` ใน `:root` ของ `style.css` แล้วอ้างถึงตัวแปร ไม่ใส่รหัสสีตรงๆ ซ้ำหลายที่
- ใช้ indicator สีมาตรฐานของ Frappe (green/orange/red/blue/gray) สำหรับสถานะ ไม่สร้างสีสถานะเอง

## ทดสอบก่อนขึ้นระบบ

- หลังแก้ ให้รัน `bench --site <dev-site> migrate` ในเครื่อง dev ต้องไม่มี error
- งานที่เปลี่ยน DocType หรือ fixtures จำนวนมาก: restore backup ล่าสุดของเซิร์ฟเวอร์จริงลงไซต์ทดสอบ แล้ว migrate เพื่อดูว่าข้อมูลไม่หาย
