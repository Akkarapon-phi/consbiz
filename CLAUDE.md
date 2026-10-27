# ConsBiz

แอป Frappe สำหรับธุรกิจก่อสร้าง (โมดูลเดียว: `ConsBiz`) ทำงานบน Frappe/ERPNext v16 ร่วมกับ `hrms`, `erpnext_thailand`, `print_designer`
ครอบคลุม: BOQ, เงินประกันผลงาน (Retention), หนังสือเข้า-ออก/Transmittal, แผนงานก่อสร้าง + Daily Report,
แผนตัดเหล็ก (Bar Cut Plan), ภาษีหัก ณ ที่จ่ายพนักงาน (WHT Employee), สัญญาจ้างและสัญญาผู้รับเหมาช่วง

ค่าเฉพาะเครื่อง (ชื่อไซต์, path, พอร์ต) อยู่ใน `CLAUDE.local.md` ซึ่งไม่ commit
ในไฟล์นี้ `<dev-site>` = ไซต์พัฒนา, `<test-site>` = ไซต์สำหรับรันเทสต์ (แยกจากไซต์พัฒนา)

**repo นี้เป็น public** ห้าม commit รหัสผ่าน, token, `site_config.json`, ไฟล์ backup, ข้อมูลลูกค้า/พนักงานจริง หรือราคาทุน

## คำสั่งประจำ (รันจากโฟลเดอร์ `frappe-bench`)

```bash
bench --site <dev-site> migrate                          # หลังแก้ DocType, patch, fixtures, hooks
bench build --app consbiz                                # หลังแก้ไฟล์ใน public/
bench --site <dev-site> clear-cache                      # หลัง build หรือแก้ hooks.py
bench --site <dev-site> export-fixtures --app consbiz    # หลังแก้ Custom Field/Property Setter/Client Script/Print Format ผ่านหน้าเว็บ
bench --site <test-site> run-tests --app consbiz         # ทั้งแอป
bench --site <test-site> run-tests --doctype "Daily Report"   # DocType เดียว
pre-commit run --all-files                               # ruff + prettier (ต้องติดตั้ง pre-commit ก่อน)
```

- `<test-site>` ต้องติดตั้ง consbiz และเปิด `bench --site <test-site> set-config allow_tests true`
  ห้ามรันเทสต์บน `<dev-site>` เพราะเทสต์เขียนข้อมูลลงฐานข้อมูล
- ไฟล์ใน `app_include_js` / `app_include_css` ไม่มีเลขเวอร์ชันใน URL หลัง build ต้อง Ctrl+Shift+R ในเบราว์เซอร์

## ข้อห้าม

- ห้ามแก้โค้ด, DocType, Sidebar, Dock ของ frappe/erpnext/hrms/erpnext_thailand/print_designer
  ให้ทำผ่าน consbiz เท่านั้น (`hooks.py`, Custom Field, Property Setter, `doctype_js`, override)
  ถ้าแก้ของแอปอื่นในเครื่อง dev ไฟล์จะไปเขียนลงแอปนั้นแล้วหายตอนอัปเดต
- ห้ามติดป้าย Module `ConsBiz` ให้ field ที่แอปอื่นสร้าง เพราะจะชนกันตอนอัปเกรด
- ห้ามแก้ patch ที่อยู่ใน `patches.txt` แล้ว (patch รันครั้งเดียวต่อไซต์ แก้แล้วไม่รันซ้ำ) ให้เขียน patch ชื่อใหม่แทน
- ห้ามแก้ไฟล์ใน `consbiz/fixtures/` ด้วยมือ ให้แก้ในหน้าเว็บแล้ว export ใหม่
- ห้าม commit ตรงเข้า `main` และห้ามแก้ DocType/customization บนเซิร์ฟเวอร์จริง

## ขั้นตอนที่ต้องทำเสมอ

- แก้ DocType, patch หรือ fixtures แล้วต้อง `migrate` บน `<dev-site>` ให้ผ่านโดยไม่มี error
- เพิ่มฟีเจอร์หรือแก้ logic ต้องมีเทสต์ใน `test_<doctype>.py` ของ DocType นั้น และ `run-tests` ต้องผ่าน
- DocType ที่ Link ไป DocType ของ ERPNext (เช่น Project) ต้องใส่ชื่อนั้นใน `IGNORE_TEST_RECORD_DEPENDENCIES`
  ไม่งั้นเทสต์จะสร้าง test record ของ ERPNext ทั้งชุดแล้วชนข้อมูลเดิม
- งานที่เปลี่ยน DocType, fixtures, Sidebar หรือ Dock: restore backup ล่าสุดของเซิร์ฟเวอร์จริงลงไซต์ทดสอบ แล้ว migrate
  ตรวจ log ว่าไม่มีบรรทัด "Orphaned ... found" และข้อมูลไม่หาย

## Branch และการขึ้นระบบ

- พัฒนาบน `develop` แล้วเปิด PR `develop` → `main` เซิร์ฟเวอร์จริงดึงจาก `main`
- อัปเดตเซิร์ฟเวอร์จริง: backup → `git pull` → `bench --site <site> migrate` → `bench build --app consbiz` → `bench restart`
- `apps/print_designer` บนเซิร์ฟเวอร์จริงต้องดึงจาก fork `Akkarapon-phi/print_designer` (มีฟอนต์ไทย)

## ของที่สร้างผ่านหน้าเว็บ ต้องเข้า git อย่างไร (เครื่อง dev ต้องเปิด `developer_mode`)

| ของ | วิธี | ไฟล์ที่ได้ |
|---|---|---|
| DocType | standard (ไม่ติ๊ก Is Custom), Module = `ConsBiz`, Save | `consbiz/consbiz/doctype/<name>/` |
| Custom Field, Property Setter, Client Script, Print Format (ไม่ standard) | Module = `ConsBiz` แล้ว `export-fixtures` (ตัวกรองอยู่ใน `fixtures` ของ `hooks.py`) | `consbiz/fixtures/` |
| Report ที่ไม่ใช่ standard | เพิ่มชื่อในรายการ `Report` ของ `fixtures` แล้ว export | `consbiz/fixtures/` |
| Sidebar, Dock, Workspace | ติ๊ก Standard, Module/App = ConsBiz, Save | `consbiz/consbiz/sidebar/<name>/`, `consbiz/dock/consbiz/`, `consbiz/consbiz/workspace/<name>/` |

กับดักที่เคยเจอ:

- DocType standard ห้ามมี `default_print_format` ให้ใช้ Property Setter แทน (แบบที่ Customize Form ทำ)
- โฟลเดอร์ DocType ใหม่ต้องมี `__init__.py`
- ของ standard ที่อยู่ในฐานข้อมูลแต่ไม่มีไฟล์ใน repo จะถูก `migrate` ลบเป็น orphan (เคยเกิดกับ WHT Employee, Dock, Sidebar "Docs")
- migrate ข้ามการ import ไฟล์ DocType ถ้าฐานข้อมูลมี `modified` ใหม่กว่าไฟล์
- ชื่อ record บนเซิร์ฟเวอร์ต่างจากในไฟล์ (เช่น Dock ชื่อ hash กับ `consbiz`) migrate จะชน unique key
  ให้เขียน patch ใน `[pre_model_sync]` ลบหรือเปลี่ยนชื่อตัวเก่าก่อน ดู `consbiz/patches/remove_hash_named_dock.py`
- เพิ่มโมดูลใหม่ใน `modules.txt` แล้ว migrate รอบแรกจะข้าม DocType/Page ของโมดูลนั้น (redis จำรายชื่อโมดูลเก่า)
  ต้องมี patch ใหม่ใน `[pre_model_sync]` ที่เรียก `frappe.cache.delete_value("app_modules")` แล้ว `frappe.setup_module_map()`

## โครงสร้าง

- `consbiz/hooks.py`: `doc_events`, `doctype_js`, `fixtures`, `scheduler_events`, `jinja`, `naming_series_variables`
- `consbiz/api.py`: logic ที่ผูกกับ doc_events (Retention, Transmittal)
- `consbiz/utils.py`: ตัวแปร naming series `ABBR` และ `thai_date()` (วันที่ไทย พ.ศ. ใช้ใน Print Format)
- `consbiz/consbiz/doctype/`: DocType ของแอป แต่ละตัวมี `test_<name>.py`
- `consbiz/consbiz/page/construction_gantt/`: หน้า Gantt (ใช้ชื่อนี้เพราะ `construction-management` ชนกับ list ของ DocType)
- `consbiz/consbiz/print_format/<name>/`: Print Format standard แก้ HTML ที่ `<name>.html` ไม่ใช่ช่อง HTML บนเว็บ (Frappe อ่านไฟล์ก่อน)
- `consbiz/templates/print/print_style.html`: CSS กลางของ Print Format ใช้ผ่าน `{% include %}` class ขึ้นต้น `pf-`
- `consbiz/consbiz/sidebar/`, `consbiz/consbiz/workspace/`, `consbiz/workspace_sidebar/`, `consbiz/dock/`, `consbiz/desktop_icon/`: เมนูและหน้าแรกของแอป
- `consbiz/patches/` + `consbiz/patches.txt`: patch ที่รันตอน migrate
- `consbiz/fixtures/`: ผลจาก `export-fixtures`
- `consbiz/translations/th.csv`: คำแปลไทย
- `consbiz/public/js/`: สคริปต์ฟอร์ม (`doctype_js`), helper กลาง `utils.js` (เช่น `thai_baht_text()`), Vue bundle ของหน้า Gantt ใน `construction_management/`
- `consbiz/public/css/style.css`: ฟอนต์และสีของ desk แบ่งเป็นส่วนมีหมายเลข
- `consbiz/public/fonts/`: Noto Sans Thai (OFL)

ระบบย่อยที่ต้องรู้:

- แผนงาน: `Construction Management` (+ Task) ความคืบหน้าจริงเก็บใน `Construction Progress Entry`
  ซึ่งระบบสร้างเองจากการ Submit `Daily Report` หรือการกรอกในหน้า Gantt ห้ามให้ผู้ใช้กรอกตรง
  `Daily Request` (ขออนุมัติปฏิบัติงานล่วงหน้า) ไม่สร้าง Progress Entry Submit = อนุมัติ แล้วสร้าง Daily Report ต่อได้ 1 ฉบับ
  การคำนวณ %แผน/S-Curve ใน `public/js/construction_management/schedule.js` ต้องตรงกับฝั่ง Python เสมอ
  งานก่อนหน้า (`predecessors` FS/SS/FF/SF + lag) เป็นแบบ ASAP: `apply_dependencies` มีทั้ง Python และ `schedule.js` ต้องตรงกัน
  ลาก/แก้วันเริ่มของงานที่มีงานก่อนหน้าในหน้า Gantt = ปรับ lag (`hold_start`) ส่วน Excel อยู่ใน `schedule_excel.py`
  (นำเข้าแค่อ่านไฟล์ หน้า Gantt เป็นคนใส่ค่าและ Undo ได้)
- งานลด-งานเพิ่ม: `Variation Order` Submit แล้วมีผลกับแผน (`apply_variations` ใน CM) งานลดลดปริมาณงานเดิม
  งานเพิ่มเป็นแถว `VO.n` ใต้กลุ่ม `VO` ท้ายตาราง แต่นับในมูลค่าสัญญาและ % เมื่อ `employer_status = Approved` เท่านั้น
  % ความคืบหน้า = มูลค่างานที่ทำแล้ว ÷ มูลค่าสัญญาปรับปรุง (`revised_amount`) S-Curve จริงใช้ตัวหาร ณ วันที่อนุมัติแต่ละ VO
- แผนตัดเหล็ก: `Bar Cut Plan` ใช้ `Rebar Type` และ `Bar Shape` (สูตรความยาว + รูป SVG) ตัวจัดตัดอยู่ใน `bar_cut_plan/optimizer.py`
  ด้าน A-F, R (มม.), N (รอบ), T (องศา) สูตรใช้ `sqrt` และ `sin`/`cos`/`tan` (องศา) ได้
  ข้อมูลมาตรฐานสร้างด้วย patch `seed_bar_cut_masters`, `seed_more_bar_shapes`, `seed_more_rebar_types` (ข้ามที่มีอยู่แล้ว) รหัสรูปทรงไม่ใช่รหัส BS 8666
  ไซต์ใหม่ `install-app` ข้าม patch ทั้งหมด จึงเรียก seed ซ้ำใน `consbiz/install.py` (`after_install`) seed ใหม่ต้องเพิ่มที่นั่นด้วย
  น้ำหนักต่อเมตรใช้มวลระบุจากตาราง มอก. 20/24 (`rebar_type.nominal_mass`)
- ปุ่มเปลี่ยนบริษัท (`public/js/company_switcher.js`) มี 2 ที่ ใช้ avatar และเมนูชุดเดียวกัน
  - Dock: กล่อง `.dock-company` เหนือ `.dock-user` ห้ามใส่ใน `.dock-user` (Frappe ผูกคลิกทั้งกล่องกับเมนูผู้ใช้)
  - Sidebar: ใช้ class `.dropdown-navbar-user` ของ Frappe จึงซ่อนตอน Dock แบบ Pinned และแสดงตอน Floating

## การตั้งชื่อ

- DocType: ชื่ออังกฤษ Title Case คำเต็ม (เช่น `Daily Report`, `Retention Release`)
- เอกสารที่ submit ได้: `autoname = naming_series:` ใช้ `.ABBR.` ถ้าต้องการตัวย่อบริษัท/โครงการ
- prefix ที่ใช้แล้ว ห้ามใช้ซ้ำ: `BCP-` Bar Cut Plan, `CM-` Construction Management, `DR-` Daily Report, `DRQ-` Daily Request, `VO-` Variation Order, `WHTE-` WHT Employee
- master ที่ตั้งชื่อตามค่า field ใช้ `field:<fieldname>` (เช่น Rebar Type, Bar Shape)
- fieldname ของ Custom Field ขึ้นต้นด้วย `custom_`
- CSS ของ Print Format ใช้ class ขึ้นต้น `pf-` สีใหม่ใน `style.css` ใช้ตัวแปร `--consbiz-*`

## แนวทางเขียนโค้ด

- Python: indent ด้วย tab, เครื่องหมายคำพูดคู่, ruff ตาม `pyproject.toml`
- JS: prettier ตาม `.pre-commit-config.yaml`
- ข้อความที่ผู้ใช้เห็นเป็นภาษาไทย ครอบด้วย `_()` / `__()`
- ใช้ `frappe.qb` หรือ `frappe.db.get_*` ก่อน `frappe.db.sql` และส่งค่าผ่าน parameter เสมอ
- ก่อนแตะ UI ของ Frappe (Dock, sidebar, เมนู) ให้อ่านซอร์สใน `apps/frappe/frappe/public/js/frappe/ui/` ก่อน
  และใช้ component ของ Frappe (`frappe.ui.Dropdown`, `frappe.ui.Tooltip`, class ของ Frappe) แทนการเขียนเอง

## คำแปลภาษาไทย

- consbiz ติดตั้งท้ายสุด คำแปลใน `th.csv` จึงทับคำแปลของ frappe/erpnext/hrms ได้ (ข้อความเดียวกันได้คำแปลเดียวกันทั้งระบบ)
- แก้ `th.csv` ต้องคงตัวแปร (`{0}`, `%s`, แท็ก HTML) ให้ครบเหมือนต้นฉบับ
- คำแปลใน DocType `Translation` (ฐานข้อมูล) ทับไฟล์ทุกไฟล์

## หน้าตา (UI และเอกสารพิมพ์)

- ฟอนต์: Inter สำหรับอังกฤษ (Frappe ส่งมาเอง), Noto Sans Thai สำหรับไทย (`@font-face` จาก `public/fonts`)
- เปลี่ยนฟอนต์ทั้งระบบด้วยตัวแปร `--font-stack` ใน `:root` เท่านั้น ห้ามใส่ `font-family ... !important` ทุก element
  (จะทับฟอนต์ที่ Print Designer และ Print Format เลือกไว้)
- ใน font stack วาง `"Noto Sans Thai"` ก่อน `system-ui` และห้ามใส่เครื่องหมายคำพูดรอบ `system-ui` / `-apple-system`
- สีที่ใช้: หัวข้อ `#383838`, แท็บ `#525252`, เส้นตารางเอกสารพิมพ์ `#BFBFBF`, พื้นไฮไลต์ `#E8F0FE`
- สีใหม่ประกาศเป็น `--consbiz-*` ใน `:root` ของ `style.css` แล้วอ้างตัวแปร ห้ามใส่รหัสสีตรงซ้ำหลายที่
- สถานะใช้ indicator มาตรฐานของ Frappe (green/orange/red/blue/gray) ห้ามสร้างสีสถานะเอง

## PDF

- Print Format ทำหัว/ท้ายกระดาษซ้ำด้วย `<thead>`/`<tfoot>` เพราะ wkhtmltopdf แบบไม่ patch ไม่รองรับ `--header-html`,
  `@media print` และตัวหนาของ variable font วิธีนี้ใช้ได้ทั้งพิมพ์จากเบราว์เซอร์และ Chrome PDF
- ขอบหน้า PDF: Frappe อ่านจากกฎ `.print-format { margin-* }` (เขียนตรงตัว) ไม่อ่าน `@page`
- Jinja ใน Print Format ใช้ `frappe.get_cached_value` ไม่ได้ ให้ใช้ `frappe.db.get_value`
- ตั้งเครื่องให้สร้าง PDF ได้:
  - wkhtmltopdf โหลด CSS/ฟอนต์จาก URL ของไซต์ ชื่อไซต์ต้องอยู่ใน `/etc/hosts` (`127.0.0.1 <dev-site>`) ไม่งั้นได้ `HostNotFoundError`
  - PDF Generator แบบ `chrome` ใช้ `frappe-bench/chromium` ต้องติดตั้ง `libnss3 libasound2t64` ไม่งั้นได้ "Chromium took too long to start"
