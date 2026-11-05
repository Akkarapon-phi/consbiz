# ConsBiz

แอป Frappe สำหรับธุรกิจก่อสร้าง (โมดูลเดียว: `ConsBiz`) ทำงานบน Frappe/ERPNext v16 ร่วมกับ `hrms`, `erpnext_thailand`, `print_designer`
ครอบคลุม: BOQ, เงินประกันผลงาน (Retention), หนังสือเข้า-ออก/ใบนำส่งเอกสาร (Transmittal), แผนงานก่อสร้าง + Daily Report,
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
  (ไล่ไปถึง DocType ของแอปที่ไม่ได้ติดตั้ง เช่น `Payment Gateway` แล้วพัง) รวม Link ในตารางลูกด้วย
  ใส่ได้เฉพาะเทสต์ในโฟลเดอร์ DocType: ไฟล์เทสต์นอกโฟลเดอร์ DocType (รายงาน, `consbiz/test_*.py`, `consbiz/tests/`) ห้ามใส่ Frappe v16 ขึ้น `NotImplementedError`
- เทสต์ที่ต้องใช้ BOQ ใช้ `consbiz.tests.utils.insert_boq` (BOQ คำนวณ `total_amount` = ปริมาณ x ราคา เองทุกครั้ง)
- Frappe v16: `frappe.copy_doc` คง `docstatus` ต้นฉบับ ทำฉบับแก้ไข (amend) ในเทสต์ต้องตั้ง `docstatus = 0` เอง
  ระหว่างเทสต์ไม่มี Version (`ignore_version = in_test`) และ `cancel` ที่ไม่ผ่านเขียน docstatus ไปแล้ว ต้องย้อนด้วย savepoint เอง
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
- `consbiz/api.py`: เลขใบกำกับภาษีจาก Payment Entry
- `consbiz/retention.py`: เงินประกันผลงานทั้งระบบ (ดู "ระบบย่อยที่ต้องรู้")
- `consbiz/utils.py`: ตัวแปร naming series `ABBR`, `thai_date()` (วันที่ไทย พ.ศ. ใช้ใน Print Format) และ `thai_baht_text()` (ตรงกับ JS ใน `utils.js`)
- `consbiz/consbiz/doctype/`: DocType ของแอป แต่ละตัวมี `test_<name>.py`
- `consbiz/consbiz/page/construction_gantt/`: หน้า Gantt (ใช้ชื่อนี้เพราะ `construction-management` ชนกับ list ของ DocType)
- `consbiz/consbiz/print_format/<name>/`: Print Format standard แก้ HTML ที่ `<name>.html` ไม่ใช่ช่อง HTML บนเว็บ (Frappe อ่านไฟล์ก่อน)
- `consbiz/templates/print/print_style.html`: CSS กลางของ Print Format ใช้ผ่าน `{% include %}` class ขึ้นต้น `pf-`
- `consbiz/consbiz/sidebar/`, `consbiz/consbiz/workspace/`, `consbiz/workspace_sidebar/`, `consbiz/dock/`, `consbiz/desktop_icon/`: เมนูและหน้าแรกของแอป
- หน้าแรก (Workspace `ConsBiz`) = Custom HTML Block `ConsBiz Home` (fixtures) ที่เรียก `consbiz.render_home` ใน `public/js/home.js`
  รายการไอคอนแก้ที่ `HOME_GROUPS` block อยู่ใน shadow DOM: CSS ใส่ใน home.js และคัดลอก `<symbol>` ไอคอนเป็น `<svg>` เอง
  Workspace export ใช้ `title` เป็นชื่อไฟล์ถ้า title ต่างจาก label: ห้ามเปลี่ยน title ของ ConsBiz ไม่งั้นได้ Workspace ใหม่อีกตัว
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
  1 วันสร้าง DR / DRQ ได้หลายฉบับ (แบ่งกันลงหลายคน) ฟอร์มแจ้งว่าวันนั้นมีฉบับไหนแล้ว (`consbiz.show_same_day` ใน `utils.js`)
  การคำนวณ %แผน/S-Curve ใน `public/js/construction_management/schedule.js` ต้องตรงกับฝั่ง Python เสมอ
  งานก่อนหน้า (`predecessors` FS/SS/FF/SF + lag) เป็นแบบ ASAP: `apply_dependencies` มีทั้ง Python และ `schedule.js` ต้องตรงกัน
  Baseline เก็บได้หลายชุดใน `Construction Baseline` (สำเนาวันที่/% แผน/น้ำหนักของทุกแถว) เลือกดูในหน้า Gantt ได้ทีละชุด
  ชุดที่ใช้เทียบในรายงาน (`active_baseline`) ถูกคัดลอกลงช่อง `baseline_*` ของแถวงาน และลบไม่ได้
  Daily Report/Request เทียบ % จริงกับ Baseline (ไม่มี Baseline ใช้แผนปัจจุบัน: `target_progress`) แล้วเก็บค่าไว้ในเอกสาร
  ลาก/แก้วันเริ่มของงานที่มีงานก่อนหน้าในหน้า Gantt = ปรับ lag (`hold_start`) ส่วน Excel อยู่ใน `schedule_excel.py`
  (นำเข้าแค่อ่านไฟล์ หน้า Gantt เป็นคนใส่ค่าและ Undo ได้)
- งานลด-งานเพิ่ม: `Variation Order` Submit แล้วมีผลกับแผน (`apply_variations` ใน CM) งานลดลดปริมาณงานเดิม
  งานเพิ่มเป็นแถว `VO.n` ใต้กลุ่ม `VO` ท้ายตาราง แต่นับในมูลค่าสัญญาและ % เมื่อ `employer_status = Approved` เท่านั้น
  % ความคืบหน้า = มูลค่างานที่ทำแล้ว ÷ มูลค่าสัญญาปรับปรุง (`revised_amount`) S-Curve จริงใช้ตัวหาร ณ วันที่อนุมัติแต่ละ VO
- ขยายเวลา: `Extension of Time` ที่ `employer_status = Approved` เลื่อน `revised_finish_date` ของ CM (วันปฏิทิน)
  `finish_date` คงเป็นวันตามสัญญาเดิม และไม่เลื่อนวันของงานในแผน
- สายงานวิกฤต: `total_float` มีทั้ง Python และ `schedule.js` ต้องตรงกัน (backward pass จากวันจบหลังสุดของงานย่อย)
- ความล่าช้า/ค่าปรับ (`construction_management/delay.py`) และ EVM (`evm.py`, AC จาก GL Entry บัญชี Expense ที่ผูก Project)
  ใช้ในรายงาน `Construction Delay Analysis`, `Construction Earned Value` และ Tab ภาพรวมของ CM
- Tab "ภาพรวม" / "Gantt" / "ทรัพยากร" / "คลังวัสดุ" / "Look-ahead" / "การเงิน" / "เอกสารโครงการ" ของ CM เป็น Vue โหลดเมื่อเปิด Tab (`PROJECT_TABS` ใน `construction_management.js`)
  Look-ahead (แผนรายวันหลายสัปดาห์ จัดกลุ่มตาม WBS ระดับบน) ข้อมูลจาก `construction_management/lookahead.py` เทียบแผนปัจจุบัน
  แต่ละวันเป็นกล่องสีตามสถานะของวัน ณ วันที่ดู (ทำแล้ว / ไม่ได้ทำตามแผน / วันที่ดู / แผนข้างหน้า / ทำนอกแผน / เสร็จแล้ว)
  ภาพรวม/เอกสาร: `public/js/project_dashboard` (ข้อมูลจาก `construction_management/dashboard.py`) Header ของ CM ไม่มีปุ่มเพิ่ม
  การเงิน (`Finance.vue`, `construction_management/finance.py`): Cash Flow รายเดือน (Cash Plan ตรงกับตารางสรุปใต้ Gantt) + EVM
  ต้นทุนตามหมวด (`construction_management/cost.py`, ไม่ต้องกรอกเพิ่มในเอกสารซื้อ): หมวด = `Cost Category` (ข้อมูล ไม่ใช่โค้ด)
  ผูกผ่าน `custom_cost_category` บน Item Group / Account (ไม่ตั้ง = ใช้ของกลุ่มแม่) ใช้จริง = GL เดียวกับ AC ของ EVM
  แบ่งหมวดตาม Item Group ของบรรทัดเอกสาร (PI/PR/Stock Entry) ไม่มีบรรทัดใช้หมวดของบัญชี ผูกพัน = PO ส่วนที่ยังไม่ตั้งหนี้
  งบอยู่ในตาราง `cost_budgets` ของ CM (permlevel 1) ปุ่ม "เติมงบวัสดุจากแผน" = แผนวัสดุ x ราคาซื้อล่าสุด
  Gantt ในฟอร์มเป็นโหมด `embedded` = ดูอย่างเดียว (แถบบาง `ViewBar.vue`) ใช้ page จำลองที่ไม่ทำอะไร (`embedded_page.js`) ห้ามแตะ Header ของฟอร์ม
  แก้แผนที่หน้าเต็มจอ `/app/construction-gantt/<CM>` ที่เดียว (ปุ่ม "แก้ไขแผนงาน" ใน `ViewBar`, แถบเครื่องมือ `Toolbar.vue`)
  Tab โหลดใหม่เมื่อแผนเปลี่ยน (`activate` → `check_remote`) แผนเปลี่ยนแล้วฟอร์ม `reload_doc` เปิด Tab แล้วซ่อนแผงข้าง (`.consbiz-wide-form`)
  เมนู/แผงในแถบเครื่องมือใช้ `frappe.ui.Dropdown` / `frappe.ui.Popover` (ผ่าน `EsDropdown.vue` / `EsPopover.vue`) ห้ามใช้ dropdown ของ Bootstrap
  `budget_cost` ของ CM เป็น permlevel 1 (เฉพาะ Projects Manager) รายงาน EVM จึงให้สิทธิ์เฉพาะ Projects Manager
- แผนทรัพยากร/จัดซื้อ: `Construction Resource Plan`, `Construction Material Plan` (1 ฉบับต่อ CM ชื่อเดียวกับ CM)
  ชื่อทรัพยากรต้องตรงกับที่ลงใน Daily Report วันต้องสั่งวัสดุเลื่อนตามแผนผ่าน `refresh_dates` ใน `CM.on_update`
  หน้า Gantt เต็มจอ: คลิก WBS/ชื่องาน เปิดแผงขวา `TaskPanel.vue` แก้รายการของงาน (Undo ได้ บันทึกพร้อม `save_tasks`
  → `construction_management/resources.py` `save_plans` ตรวจ `modified` ของแผน) แก้/ลบแถววัสดุได้เสมอ
  วันต้องสั่ง/ต้องจอง (วันปฏิทิน) มีทั้ง `resources.py` และ `prep_by_task` ใน `schedule.js` ต้องตรงกัน คอลัมน์ "เตรียมล่วงหน้า (วัน)"
  Tab "ทรัพยากร" ของ CM (`project_dashboard/Resources.vue`, ข้อมูลจาก `resources.get_overview`) ดูอย่างเดียว
  สถานะวัสดุไม่ผูก MR ทีละแถว: `get_supply` รวมยอด MR (รวมร่าง) / PO / รับของ (PR, PI อัปเดตสต็อก, Stock Entry Material Receipt)
  ต่อ (โครงการ + Item) หน่วยสต็อก แยกซื้อเอง / ลูกค้าจัดหา (Customer Provided) แล้ว `allocate` ตัดให้แถวที่ต้องการก่อนก่อน
  มีทั้ง Python (`construction_material_plan.py`) และ `allocate_materials` ใน `schedule.js` ต้องตรงกัน
  โครงการของ MR = `custom_project` (doc_events `set_item_project` คัดลอกลงรายการให้ PO/PR ได้โครงการต่อ)
  มุมมอง "ทรัพยากร" ของหน้า Gantt (`ResourceGantt.vue`) แถวเป็นคน/เครื่องจักร/วัสดุ ดูอย่างเดียว
- วัสดุผู้ว่าจ้างจัดหา (= Customer Provided ของ ERPNext, ใช้คำ "ผู้ว่าจ้างจัดหา" ทั้งระบบ): `consbiz/employer_supplied.py`
  ผู้ว่าจ้างซื้อเองแล้วหักค่าวัสดุจากงวดงาน มูลค่าสต็อก 0 ไม่ลงบัญชีบริษัท ห้ามเปิด PO
  Customer Provided ตั้งที่ Item เท่านั้น จึงมี Item คู่ที่ระบบสร้างเอง (`custom_base_item` ชี้ Item หลัก, unique) ผู้ใช้ไม่สร้างเอง
  ชื่อ = ชื่อ Item หลัก + " (ผู้ว่าจ้างจัดหา)" กลุ่ม/หน่วย/UOM ตาม Item หลักเสมอ (doc_events ของ Item รวม merge)
  ผู้ใช้เลือก Item หลัก: MR ประเภท Customer Provided สลับเป็น Item คู่ (เลขชุด `OPO-`, ไม่มี VAT, Print Format `Employer Material Order`)
  แผนวัสดุ: ติ๊ก `employer_supplied` แล้วแถวเก็บ Item คู่ ยอดแยกตาม Item จึงไม่ต้องแก้ `get_supply` / `allocate`
- สต็อกหน้างาน (`consbiz/site_stock.py`) ใช้เอกสารสต็อกของ ERPNext:
  1 คลังต่อโครงการ: Project.after_insert สร้าง `All Warehouses / โครงการ (หรือกลุ่ม Project/Projects ที่มีอยู่) / <ชื่อคลัง>`
  ชื่อคลังผู้ใช้ตั้งเองตอนสร้างโครงการ (`Project.custom_warehouse_name`) เพราะ ERPNext ซ่อนช่องชื่อคลังหลังบันทึกและปิด Rename
  (`custom_project`) ฟอร์มรับของ/เบิก/MR/ใบยืมใส่คลังนี้ให้ (`consbiz.set_project_warehouse`) โครงการเดิมใช้ปุ่มในฟอร์ม Project
  วัสดุผู้ว่าจ้างแยกด้วย Item คู่ อยู่คลังเดียวกับของบริษัทได้ คลังผู้ว่าจ้างแยก (`custom_is_owner_warehouse`) ไม่บังคับ ถ้ามีรับได้เฉพาะ Item คู่
  เบิก (Stock Entry Material Issue) Item หลัก: บันทึกร่างแล้วแยกแถวตัด Item คู่ก่อน (คลังเดียวกัน แล้วคลังผู้ว่าจ้าง ตาม `Project.custom_issue_priority`)
  แถวที่ผ่านแล้ว `custom_employer_checked` = 1 ไม่แยกซ้ำ แถว Item คู่ไม่อ้าง MR (ERPNext บังคับ Item ตรงกับ MR)
  WBS ของรายการ (`custom_wbs` ใน Stock Entry Detail / Material Request Item) ตรวจกับงานย่อยของ CM ของโครงการ
  รับของ: Stock Entry Material Receipt มีเลขที่ใบส่งของ/ผู้ส่ง/ทะเบียนรถ รายงาน `Site Delivery Summary` รวมกับ Purchase Receipt
  Tab "คลังวัสดุ" ของ CM (`project_dashboard/Stock.vue`) และรายงาน `Project Stock Summary` ใช้ `construction_management/stock.py` ชุดเดียว
  1 แถวต่อ Item หลัก (Item คู่รวมเข้า Item หลัก) แยกซื้อเอง/ผู้ว่าจ้าง: ยังไม่ส่ง รับเข้า เบิกออก คงเหลือ (SLE ของคลังที่ผูกโครงการ) + ใช้ตามงาน + PO ค้างส่ง
- คอนกรีต: `Concrete Usage` 1 ใบต่อการเท 1 จุด (WBS + ตำแหน่ง) ตั๋วรถ 1 แถวต่อคัน ไม่ผ่านสต็อก
  ติ๊ก `employer_supplied` รายตั๋ว = หักงวดผู้ว่าจ้างตามปริมาณใช้จริง เศษไปเทที่อื่นเขียนหมายเหตุ รายงาน `Concrete Usage Summary` (แสดงรายตั๋วได้)
- ยืม-คืนอุปกรณ์: `Equipment Borrowing` สโตร์บันทึก ผู้ยืม = พนักงาน / ผรม. / คนงาน (คนงานของ ผรม. ระบุ ผรม. เป็นผู้รับผิดชอบ)
  Submit = โอนเข้าคลังอุปกรณ์ระหว่างยืม รับคืนผ่าน `record_return` (dialog `consbiz.equipment_return_dialog` ใน utils.js)
  ปกติ/ชำรุด โอนกลับ, สูญหาย Material Issue แถวคืนที่บันทึกแล้วแก้/ลบไม่ได้ รายงาน `Borrowed Equipment Outstanding`
- แอปหน้างาน `/site` (มือถือ, ติดตั้งลงหน้าจอได้) = หน้า www (`consbiz/www/site.html`) + Vue (`public/js/site_app/`) แอปเดียวแบ่งหมวดงาน
  หมวด (`sections.js`): สโตร์ (`views/store/`, API `consbiz/store_app.py`) / ควบคุมงาน (`views/work/`, รวมคอนกรีต) / บริหารโครงการ (`views/pm/`) API 2 หมวดนี้อยู่ `consbiz/site_app.py`
  จัดซื้อ (MR ประเภท Purchase → PO → PI) / ขาย (Quotation → SO → SI): `views/docs/` ชุดเดียวกันทั้ง 6 ชนิด (`DOC_KINDS` ใน sections.js ตรงกับ `DOCS` ใน `consbiz/site_docs.py`)
  ดูรายการ/รายละเอียด/เอกสารต้นทาง-ปลายทาง, ส่งเอกสารร่าง, PDF ขอบเขต โครงการนี้/ทุกโครงการ (`state.doc_scope`)
  สร้าง/แก้ไขร่างในแอป (`DocForm.vue`, หน้า `buy-form` / `sell-form`): ช่องที่กรอกได้อยู่ใน `FORM` ของ site_docs.py (รวมส่วนลดท้ายบิล %)
  หัก ณ ที่จ่าย/เงินประกันผลงานในแอป: `consbiz/deductions.py` (เรียกจาก `apply_form` เท่านั้น ไม่ได้ผูก validate)
  สูตรเดียวกับสคริปต์ฟอร์มระบบเต็ม (`purchase_order.js`, `quotation_cal.js`, `sales_order_cal.js`, `purchase_invoice.js`, `sales_invoice_cal.js`) แก้ที่หนึ่งต้องแก้อีกที่
  PI/SI ลงตาราง `custom_payment_entry_deduction` (บัญชีจาก Company) SI ติ๊ก `custom_edit_wht`/`custom_edit_retention` = ใช้ยอดที่กรอกเอง
  รายการ: `LineEditor.vue` จอ ≥1000 = ตารางแก้ไขในช่อง + แถวค้นหาเพิ่ม (↑↓/Enter, Enter จำนวน → ราคา → ค้นหา), แคบกว่า = การ์ด
  ลากที่จับย้ายลำดับแถว (ส่ง idx ตามลำดับ), ติ๊กหลายแถวแล้วลบ, ปากกา = รายละเอียดแถว (คำอธิบาย, WBS, ไม่คิดภาษี)
  ใบขอซื้อ: วัตถุประสงค์ ซื้อ / ผู้ว่าจ้างจัดหา (ผู้ว่าจ้างจัดหาห้ามสร้าง PO ต่อ), ผู้จัดทำ/ผู้อนุมัติ = Signature
  ยอด/ภาษีของ MR = `consbiz/request_totals.py` (doc_events validate) สูตรเดียวกับ `material_request.js` แก้ที่หนึ่งต้องแก้อีกที่
  MR ใหม่: ERPNext `update_item_rates` ทับราคาด้วย Price List ตอนบันทึกครั้งแรก `save_doc` ใส่ราคาที่ผู้ใช้กรอกคืน (`keep_request_rates`)
  ดูเอกสาร: แถบขั้นตอน (`steps_of`), สรุปยอด (`summary_of`: แถว + ยอดสุทธิ + ตัวอักษร) ใช้ทั้งหน้าดูและฟอร์ม
  sidebar ขวาของหน้าดู แยกจากเนื้อหา เปิด-ปิดที่ปุ่มบน TopBar: จอ ≥1480 กางค้าง (`html[data-rside]` → `--ss-rside` ดันเนื้อหา/แถบล่าง จำในเครื่อง), เล็กกว่า = เลื่อนทับ (z-index ต่ำกว่า sheet)
  เนื้อหา sidebar (`DocActivity.vue`, `site_docs.get_activity`): ถูกใจ, มอบหมาย (`frappe.desk.form.assign_to`), ไฟล์แนบ (`upload(file, {doctype, docname})` / `remove_attachment`),
  เอกสารที่เกี่ยวข้อง, ความคิดเห็น (`add_comment` ผ่าน `clean_html`, ลบได้เฉพาะของตัวเอง) + ความเคลื่อนไหวจาก Version/Comment แบบ timeline ของระบบเต็ม
  ช่องเลือก/วันที่ของแอปใช้ `components/SelectBox.vue` / `DateInput.vue` (ปฏิทิน พ.ศ.) ห้ามใช้ `<select>` / `<input type="date">` ของเบราว์เซอร์
  ช่องเงินใช้ `MoneyInput.vue` (แสดง 1,234.50 / โฟกัสแล้วเป็นตัวเลขดิบ) รายละเอียดรายการ (HTML ของ Quill) แสดงด้วย `RichText.vue` แก้ด้วย `RichEditor.vue`
  HTML จากระบบเต็มต้องผ่าน `sanitize_html` (api.js) ก่อน `v-html` ทุกครั้ง (ตัด `span.ql-ui`, Quill 2 ใช้ `li[data-list]` แยกลำดับเลข/หัวข้อย่อย)
  ดูเอกสาร (`DocView.vue`): หัวเอกสาร = คู่ค้า/สถานะ + ช่องข้อมูลเป็นตาราง, ≥768 = ตารางรายการ + สรุปยอดท้ายตาราง, ≥1180 = แผงข้าง (เอกสารที่เกี่ยวข้อง/หมายเหตุ)
  เอกสารถัดไป (`MAPPERS`: MR→PO, PO→PI, QTN→SO, SO→SI) ใช้ mapper ของ ERPNext ตอนบันทึกเรียก mapper ใหม่แล้วจับคู่แถวด้วย `key` (แถวบันทึกแล้ว = name, แถวจาก mapper = ลำดับ)
  ยอด/ภาษีคำนวณที่ server (`preview_doc`) แล้ว rollback เสมอ (ERPNext สร้าง Item Price อัตโนมัติระหว่างเติมค่า) PI มีเลขที่ใบกำกับภาษี (erpnext_thailand บังคับเมื่อมีภาษีซื้อ)
  ทางเข้าจากระบบเต็ม: Desktop Icon "ConsERP" (`consbiz/desktop_icon/conserp.json`, External → /site) ผู้ใช้ที่มี Desktop Layout ของตัวเองเห็นไอคอนใหม่เฉพาะที่อยู่ใน layout (patch `add_conserp_to_desktop_layouts`)
  บริหารโครงการ (สิทธิ์อ่าน CM) ดูอย่างเดียว: ภาพรวม (`dashboard.get_dashboard`), แผนงาน Gantt (`get_plan`), Look-ahead (`lookahead.get_lookahead` สถานะวันตรงกับ `LookAhead.vue`),
  ทรัพยากร + แผนจัดซื้อวัสดุ (`resources.get_overview`), เอกสาร (`get_documents`) แก้แผนที่หน้า Gantt ในระบบเต็ม
  Look-ahead: มือถือ = การ์ดทีละสัปดาห์, แท็บเล็ต = ตาราง 2 สัปดาห์, จอใหญ่ = ตารางทั้งช่วง (matchMedia ใน `Lookahead.vue`)
  summary ของหมวดที่ `lazy` (บริหารโครงการ) โหลดเมื่อเปิดหมวดนั้นเท่านั้น
  หมวดที่เห็นตามสิทธิ์ (`site_app.boot_data` → `sections`) สลับหมวด: มือถือ = ตารางไอคอน (`SectionLauncher.vue`) เปิดจากชิปบน hero (`Hero.vue`)
  แท็บเล็ต/จอใหญ่ = Dock คอลัมน์ซ้ายสุด (`SectionDock.vue`) + sidebar เมนูของหมวด ค่าเริ่มต้นพับ (ไอคอน)
  กางชั่วคราวทับเนื้อหา (`html[data-peek]`): ใช้เมาส์ = ชี้แล้วกาง, จอสัมผัส = ปุ่มล่างสุด เลือกเมนู/แตะนอกแถบแล้วพับ
  ปักหมุด (`html[data-side="expanded"]`, ปุ่มล่างสุดบนจอใช้เมาส์) = กางค้างและดันเนื้อหา จำในเครื่อง
  `html[data-dock]` + `html[data-side]` กำหนด `--ss-side` (ความกว้าง Dock + sidebar) ที่เนื้อหา/sheet/แถบล่างใช้ (data-peek ไม่เปลี่ยน --ss-side)
  รายการเอกสารจัดซื้อ/ขาย (`DocList.vue`): แท็บสถานะมีจำนวน, ค้นหา/ช่วงวันที่/คู่ค้า/เกินกำหนด/ขอบเขต, เรียงคอลัมน์, เลือกหลายแถวแล้วส่ง (`submit_docs` ใช้ savepoint ต่อใบ), ส่งออก CSV
  คอลัมน์ต่อชนิดเอกสารใน `DocTable.vue` (ท้ายตาราง: มอบหมาย `_assign` / แก้ไขล่าสุด / ถูกใจ `frappe.desk.like.toggle_like`)
  `get_docs` คืน rows + total + sums (ยอดรวมทั้งชุด) + counts (ของแต่ละแท็บ) มือถือ = การ์ด (`DocCard.vue`) + ตัวกรองใน sheet, แท็บเล็ต/จอใหญ่ = ตาราง (`DocTable.vue`) + แบ่งหน้า
  sidebar พับ/กางใช้โครงแนวตั้งเดียวกัน (หัว/โครงการ 52px, เมนู 48px) ห้ามให้ความสูงต่างกันตามสถานะ ไม่งั้นเมนูขยับตอนเปิด-ปิด
  หน้าหลักทุกหมวด (`Hero.vue`): มือถือ = hero เต็ม, ≥768 = แถบเตี้ยแถวเดียว
  จอ ≥1480: รายการ = ตาราง + ตัวอย่างเอกสารขวา (`DocPreview.vue`, คลิก = ดูตัวอย่าง, ↑↓ เลื่อน, ดับเบิลคลิก/Enter = เปิดเต็มหน้า)
  แผงตัวอย่างต้องพอดีจอโน้ตบุ๊ก (สูง ~760px) โดยไม่เลื่อน: รายการ 3 แถวแรก + ยอดสำคัญ (ยอดรวม/ยอดสุทธิ/ค้าง) รายละเอียดอื่นดูในหน้าเต็ม
  ฟอร์ม = แผงข้อมูลประกอบของแถวที่เลือก (`ItemInsight.vue`, `site_docs.get_item_insight`: คงเหลือ / แผนวัสดุเทียบขอ-สั่ง-รับ / ราคาล่าสุด / PO ค้างรับ)
  เทสต์แบบ rollback บน dev: คำสั่งที่ทำ DDL (เช่น frappe เพิ่มคอลัมน์ `_liked_by` ครั้งแรก) commit ทันที ข้อมูลทดสอบจะค้าง ตรวจและลบเองทุกครั้ง
  สลับแล้วไปเมนูล่าสุดของหมวดนั้น (`state.last_tab`)
  ฟอร์มบนแท็บเล็ต/จอใหญ่: เลย์เอาต์ในขั้นของฟอร์มใช้ container query (`.ss-step-body`) ตามความกว้างฟอร์ม ไม่ใช่ความกว้างจอ
  ฟอร์มทีละขั้น ≥1180 = แถบขั้นตอนซ้าย (`.ss-wizard`) พร้อมสรุปของขั้น (`step_hint`), งานที่ทำ 1 งาน = 1 แถว, Ctrl/⌘+Enter = ถัดไป/ส่ง
  จอใช้เมาส์ (`hover: hover` + `pointer: fine`) ช่องกรอกเตี้ยลงและมีเส้นขอบ จอสัมผัสคงขนาดใหญ่ แถบล่างปุ่มชิดขวา
  สีหลักตามหมวด: `data-section` ที่ `<html>` (sheet ถูก Teleport ไป body) ทับ `--ss-brand*`
  ชื่อหน้า (view) ห้ามซ้ำข้ามหมวด (`go(view)` หาหมวดจาก `ROUTES`), summary แยกหมวดใน `state.summaries`
  ควบคุมงาน: หน้าหลัก % จริง/แผน + S-Curve (`SCurve.vue`, ข้อมูล `dashboard.progress_curve`), ปฏิทินรายงาน (`get_site_calendar`)
  เขียน Daily Report / ขอ-อนุมัติ-ไม่อนุมัติ Daily Request ในแอป (`ReportForm.vue` ทีละขั้น, `ReportView.vue`, API `site_app.save_report`)
  แอปส่งเฉพาะช่องใน `FORM_FIELDS` / `ITEM_FIELDS` ค่าอื่นคำนวณใน validate ของเอกสารเหมือนกรอกในระบบเต็ม
  ฟอร์มใหม่เก็บร่างใน localStorage ระหว่างกรอก (สัญญาณหลุดไม่หาย) ขอตรวจงาน / Punch List ยังสร้างในระบบเต็ม
  ขออนุมัติได้ทุกวัน (ย้อนหลังได้) PDF/แชร์ไฟล์: `site_app.pdf_url` เลือกตัวสร้าง PDF แบบหน้าพิมพ์ของระบบเต็ม (Print Format → Print Settings)
  ดู PDF ในแอป (`PdfViewer.vue`) วาดด้วย PDF.js ที่ `public/js/lib/pdfjs/` (มือถือแสดง PDF ใน iframe ไม่ได้) โหลดเมื่อเปิดครั้งแรก
  ไม่ใช้ desk: เรียก API ด้วย fetch เอง (`api.js`), router เอง (`/site/<หมวด>/<view>/<params>`, `website_route_rules`), CSS อยู่ `site.css` (class `ss-`)
  `/store/...` เดิมเด้งไป `/site/store/...` (`website_redirects` ใน hooks.py) ไอคอนที่ติดตั้งไว้แล้วยังใช้ได้
  CSS ต้อง `@import` ใน `<style>` ของ `App.vue` (Frappe ฝัง CSS เข้า bundle เฉพาะที่มาจาก .vue ถ้า import .css ตรงๆ ไฟล์ JS ถูกลบตอน build)
  Responsive 3 ขนาด: มือถือ = แถบเมนูล่าง, ≥768 = แถบไอคอนซ้าย + sheet เป็นหน้าต่างกลางจอ, ≥1180 = sidebar + ฟอร์มแบ่งซ้าย-ขวา (`.ss-split`) ใช้เต็มจอ: จอกว้างได้คอลัมน์เพิ่ม (auto-fill) ไม่ยืดการ์ด, การ์ดในรายการสูงเท่ากัน (`grid-auto-rows: 1fr`)
  แถบล่าง/ปุ่มลอยของหน้า ต้อง `<Teleport to="#ss-layer">` (ตอนเปลี่ยนหน้า view มี transform ทำให้ position: fixed เพี้ยน)
  ห้ามส่ง reactive object ของ Vue เข้า `history.pushState/replaceState` (clone ไม่ได้ แอปค้าง) `/app/site-store` เดิมเด้งไป `/site/store`
  สโตร์ รับของ: PO ของโครงการ → Purchase Receipt (บัญชีทำ PI ต่อจาก PR), MR ผู้ว่าจ้างจัดหา → Stock Entry Material Receipt
  ตีกลับที่หน้างาน = ไม่รับเข้า ยอดค้างที่ PO/MR เก็บใน `custom_site_rejected_qty` / `custom_site_reject_reason` ของแถว
  ตีกลับทั้งหมด = ไม่มีใบรับ บันทึก Comment ที่ PO/MR, รูปอัปโหลดก่อนแล้ว server ผูกกับเอกสาร (`attach_files`)
- แผนตัดเหล็ก: `Bar Cut Plan` ใช้ `Rebar Type` และ `Bar Shape` (สูตรความยาว + รูป SVG) ตัวจัดตัดอยู่ใน `bar_cut_plan/optimizer.py`
  ด้าน A-F, R (มม.), N (รอบ), T (องศา) สูตรใช้ `sqrt` และ `sin`/`cos`/`tan` (องศา) ได้
  ข้อมูลมาตรฐานสร้างด้วย patch `seed_bar_cut_masters`, `seed_more_bar_shapes`, `seed_more_rebar_types` (ข้ามที่มีอยู่แล้ว) รหัสรูปทรงไม่ใช่รหัส BS 8666
  ไซต์ใหม่ `install-app` ข้าม patch ทั้งหมด จึงเรียก seed ซ้ำใน `consbiz/install.py` (`after_install`) seed ใหม่ต้องเพิ่มที่นั่นด้วย
  น้ำหนักต่อเมตรใช้มวลระบุจากตาราง มอก. 20/24 (`rebar_type.nominal_mass`)
- เงินประกันผลงาน (`consbiz/retention.py`, ปุ่ม/dialog ใน `public/js/retention.js`):
  ผู้ว่าจ้าง: Sales Invoice → `Retention Receivable` (RR) → `Retention Invoice` (RI) → JE รับคืน (Dr. เงินสด/ธนาคาร Cr. `Company.custom_retention_receivable`)
  ผรม.: Purchase Invoice → `Retention Payable` (RP) → `Retention Release` → JE จ่ายคืน (Dr. `Company.custom_retention_payable` Cr. เงินสด/ธนาคาร)
  RR/RP ระบบสร้างและ Submit เองตอน Submit ใบแจ้งหนี้ (ยกเลิกใบแจ้งหนี้ = ยกเลิกตาม) ไม่ลงบัญชีเอง
  (ยอดเข้าบัญชีเงินประกันตอนรับ/จ่ายชำระใบแจ้งหนี้ ผ่าน `custom_payment_entry_deduction`)
  RI/Release รวมหลาย RR/RP และเบิกบางส่วนได้ แถว `Retention Claim Item` อ้าง RR/RP ด้วย Dynamic Link (`retention_doctype` + `retention_reference`)
  ยอดเบิกรวมใบร่างด้วย กันเบิกเกินยอด RR/RP ส่วน `Retention Items` เป็นแถวที่มา (ใบแจ้งหนี้) ของ RR/RP เท่านั้น
  `billed_amount` / `paid_amount` / `outstanding_amount` / `status` ของ RR/RP คำนวณใหม่เสมอ (`update_source`) ห้ามแก้ตรง
  RI/Release เป็น Paid เมื่อ JE ในช่อง `journal_entry` Submit (doc_events ของ Journal Entry) ยกเลิกใบเบิกต้องยกเลิก JE ก่อน
  `due_date` ของ RR/RP = วันครบกำหนดคืนเงินประกัน แก้ได้หลัง Submit scheduler รายวัน `update_overdue` เปลี่ยนเป็น Overdue
- ใบนำส่งเอกสาร: `Transmittal` (เดิมชื่อ `Transmittal Ext`, patch `merge_transmittals`) ใบเดียวใช้ส่งให้ลูกค้า / ผู้ขาย / สำนักงานบัญชี
  แถว (`Transmittal List`) อ้างเอกสารในระบบด้วย `reference_doctype` + `reference_name` หรือพิมพ์เอง/นำเข้า Excel (qty = จำนวน, amount = ยอดเงิน)
  ปุ่ม "ดึงเอกสาร" ใช้ `SOURCES` ใน `transmittal.py` (ใบกำกับภาษีขาย/ซื้อ, หนังสือรับรองหัก ณ ที่จ่าย ของ thai_tax, SI, PI, Retention Invoice)
  ไม่แสดงเอกสารที่อยู่ในใบนำส่ง (ไม่ยกเลิก) ของผู้รับประเภทเดียวกัน/คู่ค้าเดียวกันแล้ว ส่งให้ผู้รับต่างกันได้
  สถานะคำนวณจากวันที่เสมอ: Draft / To Send / Sent (`sent_date`) / Received (`received_date`) / Cancelled
  ฟอร์มเอกสารต้นทางมีปุ่ม Create > ใบนำส่งเอกสาร และแถบแจ้งว่านำส่งแล้ว (`public/js/transmittal.js`, รายชื่อต้องตรงกับ `SOURCES`)
  `Transmittal Entry` / `Transmittal Note` (บันทึกส่งใบกำกับให้สำนักงานบัญชี) เลิกใช้และลบแล้ว ตารางเดิมในฐานข้อมูลยังอยู่
- ปุ่มเปลี่ยนบริษัท (`public/js/company_switcher.js`) มี 2 ที่ ใช้ avatar และเมนูชุดเดียวกัน
  - Dock: กล่อง `.dock-company` เหนือ `.dock-user` ห้ามใส่ใน `.dock-user` (Frappe ผูกคลิกทั้งกล่องกับเมนูผู้ใช้)
  - Sidebar: ใช้ class `.dropdown-navbar-user` ของ Frappe จึงซ่อนตอน Dock แบบ Pinned และแสดงตอน Floating

## การตั้งชื่อ

- DocType: ชื่ออังกฤษ Title Case คำเต็ม (เช่น `Daily Report`, `Retention Release`)
- เอกสารที่ submit ได้: `autoname = naming_series:` ใช้ `.ABBR.` ถ้าต้องการตัวย่อบริษัท/โครงการ
- prefix ที่ใช้แล้ว ห้ามใช้ซ้ำ: `BCP-` Bar Cut Plan, `CM-` Construction Management, `CU-` Concrete Usage, `DR-` Daily Report, `DRQ-` Daily Request, `EB-` Equipment Borrowing, `EOT-` Extension of Time, `IR-` Inspection Request, `OPO-` Material Request ผู้ว่าจ้างจัดหา, `PL-` Punch List, `TX-` Transmittal, `VO-` Variation Order, `WHTE-` WHT Employee
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
