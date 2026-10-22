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
- **Sidebar, Dock, Workspace**: ติ๊ก Standard และ Module/App = ConsBiz แล้วกด Save ระบบเขียนไฟล์เอง
  (`consbiz/consbiz/sidebar/<name>/`, `consbiz/dock/consbiz/`, `consbiz/consbiz/workspace/<name>/`)
- ห้ามแก้ Sidebar/Dock/DocType ของแอปอื่น (frappe, erpnext, hrms) ในเครื่อง dev ไฟล์จะไปเขียนในแอปนั้นและหายตอนอัปเดต
- ห้ามติดป้าย `ConsBiz` ให้ field ที่แอปอื่นสร้าง (hrms, erpnext_thailand, print_designer) ไม่งั้นจะชนกันตอนอัปเกรด

สิ่งที่เคยพลาด:

- DocType แบบ standard ห้ามมี `default_print_format` ให้ย้ายไปเป็น Property Setter (เหมือนที่ Customize Form ทำ)
- โฟลเดอร์ DocType ใหม่ต้องมี `__init__.py`
- ของแบบ standard (DocType, Sidebar, Dock, Workspace, Report) ที่อยู่ในฐานข้อมูลแต่ไม่มีไฟล์ใน repo
  จะถูก `migrate` ลบทิ้งเป็น orphan (เคยเกิดกับ WHT Employee, Dock และ Sidebar "Docs")
- การ import ไฟล์ DocType ตอน migrate จะข้ามถ้าฐานข้อมูลมี `modified` ใหม่กว่าไฟล์
- ถ้าชื่อ record บนเซิร์ฟเวอร์ต่างจากชื่อในไฟล์ (เช่น Dock ชื่อ hash กับ Dock ชื่อ `consbiz`) migrate จะชน unique key
  ให้เขียน patch ใน `[pre_model_sync]` ลบหรือเปลี่ยนชื่อตัวเก่าก่อน ดู `consbiz/patches/remove_hash_named_dock.py`

## โครงสร้าง

- `consbiz/hooks.py`: `doc_events`, `doctype_js`, `fixtures`, `scheduler_events`
- `consbiz/api.py`: logic ที่ผูกกับ doc_events (Retention, Transmittal)
- `consbiz/utils.py`: ตัวแปร naming series `ABBR`
- `consbiz/public/js/`: สคริปต์ฝั่งฟอร์ม (`doctype_js`) และ helper กลางใน `utils.js` เช่น `thai_baht_text()`
- `consbiz/public/js/company_switcher.js`: ปุ่มเปลี่ยนบริษัท 2 ที่ ใช้ avatar และเมนูชุดเดียวกัน
  - Dock: กล่อง `.dock-company` เหนือ `.dock-user` ห้ามใส่ใน `.dock-user` เพราะ Frappe ผูกคลิกทั้งกล่องกับเมนูผู้ใช้
  - Sidebar: แถวที่ใช้ class แถวผู้ใช้ของ Frappe (`.dropdown-navbar-user`) จึงซ่อนตอน Dock แบบ Pinned และแสดงตอน Floating
- `consbiz/public/css/style.css`: ฟอนต์และสีของหน้าจอ desk แบ่งเป็นส่วนมีหมายเลข
- `consbiz/public/fonts/`: ไฟล์ฟอนต์ที่แอปส่งเอง (Noto Sans Thai, OFL)
- `consbiz/patches/`: patch ที่รันตอน migrate (ลงทะเบียนใน `patches.txt`)
- `consbiz/fixtures/`: ไฟล์ที่ export จาก `export-fixtures` อย่าแก้ด้วยมือ ให้แก้ในหน้าเว็บแล้ว export ใหม่

## แนวทางเขียนโค้ด

- Python: indent ด้วย tab, เครื่องหมายคำพูดคู่, ruff ตาม `pyproject.toml`
- JS: prettier ตาม `.pre-commit-config.yaml`
- ข้อความที่แสดงผู้ใช้เป็นภาษาไทย และครอบด้วย `_()` / `__()`
- fieldname ของ Custom Field ขึ้นต้นด้วย `custom_`
- เอกสารที่ submit ได้ใช้ `autoname = naming_series:` และใช้ `.ABBR.` ได้ถ้าต้องการตัวย่อบริษัท/โครงการ
- ใช้ `frappe.qb` หรือ `frappe.db.get_*` ก่อน `frappe.db.sql` และใส่ค่าผ่าน parameter เสมอ

## หน้าตา (UI และเอกสารพิมพ์)

- ฟอนต์: Inter สำหรับอังกฤษ (Frappe ส่งมาเอง), Noto Sans Thai สำหรับไทย (`@font-face` จาก `public/fonts`)
- เปลี่ยนฟอนต์ทั้งระบบด้วยตัวแปร `--font-stack` ใน `:root` เท่านั้น ห้ามใส่ `font-family ... !important`
  ให้ทุก element เพราะจะทับฟอนต์ที่ Print Designer และ Print Format เลือกไว้
- ใน font stack ต้องวาง `"Noto Sans Thai"` ก่อน `system-ui` และห้ามใส่เครื่องหมายคำพูดรอบ `system-ui` / `-apple-system`
- ก่อนแตะ UI ของ Frappe (Dock, sidebar, เมนู) ให้เปิดซอร์สใน `apps/frappe/frappe/public/js/frappe/ui/` ดูโครงสร้างจริงก่อน
  และใช้ component ของ Frappe (`frappe.ui.Dropdown`, `frappe.ui.Tooltip`, class ของ Frappe) แทนการเขียนเอง
- สีที่ใช้อยู่: ตัวอักษรหัวข้อ `#383838`, แท็บ `#525252`, เส้นตารางในเอกสารพิมพ์ `#BFBFBF`, พื้นไฮไลต์ `#E8F0FE`
- สีใหม่ให้ประกาศเป็นตัวแปร `--consbiz-*` ใน `:root` ของ `style.css` แล้วอ้างถึงตัวแปร ไม่ใส่รหัสสีตรงๆ ซ้ำหลายที่
- ใช้ indicator สีมาตรฐานของ Frappe (green/orange/red/blue/gray) สำหรับสถานะ ไม่สร้างสีสถานะเอง

## ทดสอบก่อนขึ้นระบบ

- หลังแก้ ให้รัน `bench --site <dev-site> migrate` ในเครื่อง dev ต้องไม่มี error
- หลังแก้ไฟล์ใน `public/` ให้ `bench build --app consbiz` และ `clear-cache`
  ไฟล์ใน `app_include_js` / `app_include_css` ไม่มีเลขเวอร์ชันใน URL เบราว์เซอร์จะใช้ไฟล์เก่าจนกว่าจะ Ctrl+Shift+R
- งานที่เปลี่ยน DocType, fixtures, Sidebar หรือ Dock: restore backup ล่าสุดของเซิร์ฟเวอร์จริงลงไซต์ทดสอบ แล้ว migrate
  เพื่อดูว่าข้อมูลไม่หายและไม่มี record ถูกลบเป็น orphan (ดูบรรทัด "Orphaned ... found" ใน log)
- ตอนอัปเดตเซิร์ฟเวอร์จริง `apps/print_designer` ต้องดึงจาก fork `Akkarapon-phi/print_designer` (มีฟอนต์ไทย)
