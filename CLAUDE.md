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
  ผู้ใช้เห็นคำว่า "แผนสัญญา" แทน Baseline ทุกที่ (ข้อความในโค้ด + `th.csv`) ชื่อ DocType/field/ค่า `plan_basis` ยังเป็น Baseline
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
  แอป ConsERP มีหน้าแก้แผนของตัวเอง (`PlanEdit.vue` ในหัวข้อแอปหน้างาน) ใช้ `schedule.js` และ API ชุดเดียวกัน แก้ logic ที่ `schedule.js` มีผลทั้งสองหน้า
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
  ERPNext นับของที่รับเข้าของ MR ผู้ว่าจ้างจัดหาใน `per_ordered` / `ordered_qty` (ไม่ใช่ `per_received`) แอปแสดงเป็นรับของด้วย `site_docs.received_as_received`
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
- แผนหน้าแอป (ตกลง 2026-11-06): แยกตามกลุ่มคนใช้/อุปกรณ์ บนแอป Frappe `consbiz` ตัวเดียว เป็นหน้าจอครอบ DocType ของ ERPNext/HRMS ไม่เขียนระบบใหม่
  | URL | คนใช้ | เนื้อหา |
  |---|---|---|
  | `/conserp` | หน้างาน (มือถือ) | ควบคุมงาน, สโตร์, แผนงาน, ทรัพยากร, การเงิน, ขอซื้อ/ขอเบิก + ติดตามสถานะ |
  | `/conserp/purchase`, `/conserp/sales`, ... | ออฟฟิศ (จอใหญ่) | ซื้อ, ขาย, บัญชี, ประกันผลงาน, แอดมิน (หนังสือเข้า-ออก, สัญญา ผรม., ใบนำส่ง, ใบปะหน้า, ค่าแรงรายวัน) |
  | `/conserp/self` | พนักงานทุกคน | Self Service: ลงเวลา, ลา, สลิป, วันหยุดประจำสัปดาห์ + ตารางทีม, เบิกเงินเดือนล่วงหน้า/เงินสำรองจ่าย/เบิกคืน + อนุมัติ หน้าจอครอบ HRMS (แทนแผน `/hr-app` เดิม) |
  | `/contractor` | ผู้รับเหมาช่วง (คนนอก) | อัปเดตผลงาน, ดูสัญญา/งวดของตัวเอง API แยกและตรวจสิทธิ์ทุกคำขอ |
  ห้ามใช้ `/me` (หน้า My Account ของ Frappe), `/hr/...` (Roster ของ HRMS), `/hrms` (ESS ของ HRMS)
  โค้ดหน้าจอกลางอยู่ `public/js/shared/`: `AppShell.vue` (Dock/แถบล่าง/เลือกโครงการ/toast), `api.js` (เรียก API, router, state, รูปแบบ),
  `app.js` (`configure()` ค่าของแต่ละแอป: base, storage, sections, routes, views, summary_api), `components/`, `docs/` (เอกสารซื้อ-ขาย + `kinds.js` = DOC_KINDS),
  `style.css` (CSS ทุกแอป class `ss-`) แต่ละแอป = `<แอป>.bundle.js` ที่ `configure()` แล้ว mount `AppShell` ห้ามอ่าน `app` ตอนโหลดโมดูล (import มาก่อน configure)
  แก้ไฟล์ใน `shared/` มีผลทุกแอป ตรวจทุกแอปทุกครั้ง
  ผู้ใช้เห็นเป็นแอปเดียว "ConsERP" (ตกลง 2026-11-08): PWA ตัวเดียว `site_app/manifest.webmanifest` (scope `/conserp`, start_url `/conserp/desktop`,
  id `/site` คงไว้จากแอปเดิม ห้ามเปลี่ยน) แก้ manifest แล้วเพิ่มเลข `?v=` ที่ลิงก์ใน www/*.html (`/assets` cache 12 ชม.)
  ทุกหมวดของทุกแอปอยู่ระดับเดียวกัน `/conserp/<หมวด>` (ทุก bundle `base: "/conserp"`) server เลือก bundle ตามชื่อหมวด (`website_route_rules`:
  `_OFFICE_SECTIONS` ใน hooks.py = bundle ออฟฟิศ ตรงกับ `site_app.office_sections` ที่เหลือ = bundle หน้างาน) ชื่อหมวดจึงห้ามซ้ำข้ามแอป
  หมวดใหม่ของออฟฟิศต้องเพิ่มใน `_OFFICE_SECTIONS` ด้วย URL เดิม `/site`, `/office`, `/conserp/office`, `/store` เด้งมาที่ใหม่ (`website_redirects` ข้อแรกที่ตรงชนะ)
  หมวดออฟฟิศ `purchase`/`sales` ใช้ชุดเอกสาร `buy`/`sell` (`sections[].docs`, `DOC_KINDS[].section`, ชื่อหน้า `buy-doc` ฯลฯ) ภาพรวมออฟฟิศเลิกใช้แล้ว
  Dock พับ/กางจำค่าเดียวทุก bundle (`consbiz.conserp.sidebar`) หน้าแรก/ตารางหมวด = ไอคอน + ชื่อ (`ModuleGrid.vue`, คำอธิบายอยู่ใน tooltip)
  ทุกหน้า www ของแอปลิงก์ manifest นี้ ไอคอน = `public/images/logo.png` (สร้าง `conserp-round-*.png` (ขอบมน) + `conserp-maskable.png` (เต็มกรอบ ให้ Android ตัดเอง), `logo-96.png` เปลี่ยนรูปต้องเปลี่ยนชื่อไฟล์ เพราะ Chrome จำไอคอนตาม URL ใน `public/site_app/`) ข้างในยังแยก bundle ต่อแอป
  หน้าแรก (Desktop) = หมวดพิเศษ `desktop` ที่ `configure()` ใส่ให้ทุกแอป (`shared/components/Desktop.vue`, ไม่ต้องเลือกโครงการ)
  ชื่อ/ไอคอน/สีของหมวดทุกแอปอยู่ `shared/modules.js` (`MODULE_META`) ที่เดียว sections.js ดึงไปใช้
  หมวดที่มีสิทธิ์ของทุกแอป = `site_app.app_modules` → `boot.modules` (แสดงทั้งขอซื้อ `buy` ของหน้างานและจัดซื้อ `purchase` ของออฟฟิศ) หมวดของแอปอื่น = ลิงก์ (โหลด bundle นั้น)
  สิทธิ์ของหน้าจอ: เมนู = `tab.when(boot)` (สิทธิ์อ่าน `boot.can.view_*` / `boot.docs.<kind>.read`, เปิดจาก URL ตรงก็กลับหน้าหลักหมวด), ปุ่มสร้าง/ส่ง/ส่งออก = `boot.can.*` / `can_doc(kind, ptype)` (`site_docs.doc_permissions`), ปุ่มรายใบ = `can_*` จาก server ไม่มีสิทธิ์ = ไม่แสดง (ไม่ใช่ disabled) API ตรวจซ้ำเสมอ เมนู/ปุ่มใหม่ต้องผูกสิทธิ์ด้วย
  หน้าตั้งค่า (เมนู avatar เฉพาะ System Manager, `boot.can.settings`): `shared/components/SettingsDialog.vue` เพิ่มหัวข้อที่ `PAGES` สิทธิ์ (เลือกหมวดแล้วเพิ่ม Role) = `settings/PermissionSettings.vue` + `consbiz/app_settings.py` (ครอบ Custom DocPerm ของ Frappe เอกสารของหมวดอยู่ใน `MODULES` เพิ่มหมวด/เอกสารใหม่ต้องเพิ่มที่นั่น)
  ลบเอกสารในแอป: `shared/components/DeleteSheet.vue` + `store_app.can_delete` / `delete_document` (ร่างหรือยกเลิกแล้ว + สิทธิ์ลบ) เอกสารใหม่ที่มีหน้าดูต้องส่ง `can_delete`
  build ของ Frappe ไม่แบ่งโหลด (code splitting) จึงแยกเป็น bundle ต่อกลุ่มแอป ไม่ใช่ต่อหมวด และไม่รวมเป็น bundle เดียว (ตกลง 2026-11-08:
  แอปจะเพิ่มอีกมาก bundle เดียวโตเรื่อยๆ มือถือเปิดช้า) สลับหมวดในกลุ่มลื่น ข้ามกลุ่มโหลดหน้าใหม่ (ผ่านหน้าแรกเท่านั้น)
- แอปหน้างาน `/conserp` (มือถือ, ติดตั้งลงหน้าจอได้) = หน้า www (`consbiz/www/site.html`) + Vue (`public/js/site_app/`) แอปเดียวแบ่งหมวดงาน
  หมวดขอซื้อของหน้างาน = ใบขอซื้ออย่างเดียว (`doc_kinds: ["mr"]`) สั่งซื้อ/แจ้งหนี้/ขาย อยู่แอปออฟฟิศ
- BOQ (หมวด `boq` ของแอปออฟฟิศ `/conserp/boq`, `office_app/views/boq/`, API `consbiz/boq_app.py`): สร้าง/แก้ร่าง นำเข้า-ส่งออก Excel Submit สร้างแผนงาน ใช้แทนฟอร์มระบบเต็ม เฉพาะ Projects Manager / System Manager
  สร้างแผนงานได้ตั้งแต่ BOQ เป็นร่าง แก้ร่างแล้วกด "อัปเดตแผนงาน" (`construction_management/boq_sync.py`, แสดงสรุปก่อน): แถวเดิมคงวันที่/งานก่อนหน้า ชื่อ/ปริมาณ/ราคา/ลำดับ/WBS ตาม BOQ จับคู่ด้วย `boq_detail` แล้วชื่องาน + หน่วย งานเหมาคงมูลค่าในแผน แถวที่ถูกใช้ห้ามลบ/เปลี่ยนเลข/เป็นหัวกลุ่ม ใช้ได้เมื่อยังไม่มี Baseline/VO `boq_app.fill` ต้องคงรหัสแถว BOQ (แผนอ้างด้วยรหัสนี้)
  Baseline ต้องการ BOQ ที่ Submit แล้ว Submit BOQ ต้องให้แผนตรงกันก่อน (`BOQ.before_submit`) หลัง Submit งานเพิ่ม-ลดเป็นหน้าที่ของ VO BOQ ที่มีแผนแล้วยกเลิกไม่ได้ (`BOQ.before_cancel`) ยอด/เลข WBS ใน `BoqForm.vue` ต้องตรงกับ `calculate_row` / `assign_wbs` ใน `boq.py`
- มูลค่าในแผนงาน: ช่องเงินของ CM และ Task เป็น permlevel 1 ผู้ไม่มีสิทธิ์ `get_schedule_data` ส่งมูลค่าเป็นสัดส่วนของสัญญา (`hide_values`, รวม = 100 ให้ % และ S-Curve คำนวณได้) `get_dashboard` ตัดจำนวนเงิน (`hide_money`) หน้าจอซ่อนด้วย `can_view_value` / `show_values`
- แอปออฟฟิศ (`/conserp/purchase`, `/conserp/sales`, จอใหญ่) = `consbiz/www/office.html` + `public/js/office_app/` (sections/views/bundle) หมวดจัดซื้อ/ขายเต็ม (`doc_kinds` ทั้ง 6 ชนิด)
  boot = `site_app.office_boot_data` หมวดตามสิทธิ์ `site_app.office_sections` / ของหน้างาน `site_app.site_sections`
  `site_app.APPS` + `available_apps` → `boot.apps` (ใช้หาแอปที่ดูแลเอกสาร `doc_url`)
  เอกสารชนิดที่แอปไม่ได้ดูแล: `open_doc` / `doc_url` (`shared/docs/kinds.js`) เปิดในแอปออฟฟิศ (ไม่มีสิทธิ์ = ระบบเต็ม) ปุ่มสร้างเอกสารถัดไปซ่อน (`in_app`)
  URL เดิม `/site/sell/...`, `/site/buy/(po|pi)...`, `/site/buy/(buy-doc|buy-form)/(po|pi)/...` เด้งไป `/conserp/purchase`, `/conserp/sales` (`website_redirects`)
  `get_summary` คืน `drafts_by_kind` หน้าหลักนับร่างเฉพาะชนิดของแอปนั้น
  ออฟฟิศไม่บังคับเลือกโครงการ (`app.project_filter`): โครงการเป็นตัวกรอง (`ProjectFilter.vue`, ว่าง = ทุกโครงการ) + ตัวเลือกบริษัทที่หัว sidebar (`state.company`, `boot.companies`)
  รายการ/ตัวเลขใช้ `scope_args()` (api.js) → `get_docs`/`get_summary` รับ `company` ฟอร์มเลือกบริษัท (เอกสารใหม่) และโครงการเองได้ (`site_docs.set_project` ต้องเป็นบริษัทเดียวกัน ย้ายคลังของรายการตาม)
  คีย์ลัด (`shared/shortcuts.js`, `app.shortcuts`): รายการ `/` ค้นหา `n` สร้าง `j`/`k` เลื่อนแถว, หน้าดู `e` แก้ไข `p` PDF `i` แผงข้อมูล
  หมวด (`site_app/sections.js`, หน้า → component ใน `site_app/views.js`): สโตร์ (`views/store/`, API `consbiz/store_app.py`) / ควบคุมงาน (`views/work/`, รวมคอนกรีต) / แผนงาน (`views/pm/`) / ทรัพยากร (`views/resources/`) API 2 หมวดนี้ + เมนูการเงินของแผนงาน (`views/finance/`)อยู่ `consbiz/site_app.py`
  จัดซื้อ (MR ประเภท Purchase → PO → PI) / ขาย (Quotation → SO → SI): `shared/docs/` ชุดเดียวกันทั้ง 6 ชนิด (`DOC_KINDS` ใน `shared/docs/kinds.js` ตรงกับ `DOCS` ใน `consbiz/site_docs.py`)
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
  แก้หลังส่ง: ดินสอข้างช่อง (`shared/components/InlineEdit.vue`, จอใช้เมาส์แก้ตรงที่เดิม จอสัมผัสเป็น sheet) → `site_docs.save_after_submit`
  ช่องที่แก้ได้ = `AFTER_SUBMIT` ใน site_docs.py ∩ ช่องที่ระบบตั้ง Allow on Submit (ไม่เปิดช่องบัญชี/ศูนย์ต้นทุน) วันที่ต้องการ/กำหนดส่งห้ามว่างและห้ามก่อนวันที่เอกสาร
  sidebar ขวาของหน้าดู แยกจากเนื้อหา เปิด-ปิดที่ปุ่มบน TopBar: จอ ≥1480 กางค้าง (`html[data-rside]` → `--ss-rside` ดันเนื้อหา/แถบล่าง จำในเครื่อง), เล็กกว่า = เลื่อนทับ (z-index ต่ำกว่า sheet)
  เนื้อหา sidebar (`DocActivity.vue`, `site_docs.get_activity`): ถูกใจ, มอบหมาย (`frappe.desk.form.assign_to`), ไฟล์แนบ (`upload(file, {doctype, docname})` / `remove_attachment`),
  เอกสารที่เกี่ยวข้อง, ความคิดเห็น (`add_comment` ผ่าน `clean_html`, ลบได้เฉพาะของตัวเอง) + ความเคลื่อนไหวจาก Version/Comment แบบ timeline ของระบบเต็ม
  ช่องเลือก/วันที่ของแอปใช้ `shared/components/SelectBox.vue` / `DateInput.vue` (ปฏิทิน พ.ศ.) ห้ามใช้ `<select>` / `<input type="date">` ของเบราว์เซอร์
  ช่องเงินใช้ `MoneyInput.vue` (แสดง 1,234.50 / โฟกัสแล้วเป็นตัวเลขดิบ) รายละเอียดรายการ (HTML ของ Quill) แสดงด้วย `RichText.vue` แก้ด้วย `RichEditor.vue`
  HTML จากระบบเต็มต้องผ่าน `sanitize_html` (api.js) ก่อน `v-html` ทุกครั้ง (ตัด `span.ql-ui`, Quill 2 ใช้ `li[data-list]` แยกลำดับเลข/หัวข้อย่อย)
  ดูเอกสาร (`DocView.vue`): หัวเอกสาร = คู่ค้า/สถานะ + ช่องข้อมูลเป็นตาราง, ≥768 = ตารางรายการ + สรุปยอดท้ายตาราง, ≥1180 = แผงข้าง (เอกสารที่เกี่ยวข้อง/หมายเหตุ)
  เอกสารถัดไป (`MAPPERS`: MR→PO, PO→PI, QTN→SO, SO→SI) ใช้ mapper ของ ERPNext ตอนบันทึกเรียก mapper ใหม่แล้วจับคู่แถวด้วย `key` (แถวบันทึกแล้ว = name, แถวจาก mapper = ลำดับ)
  ยอด/ภาษีคำนวณที่ server (`preview_doc`) แล้ว rollback เสมอ (ERPNext สร้าง Item Price อัตโนมัติระหว่างเติมค่า) PI มีเลขที่ใบกำกับภาษี (erpnext_thailand บังคับเมื่อมีภาษีซื้อ)
  ทางเข้าจากระบบเต็ม: Desktop Icon "ConsERP" (`consbiz/desktop_icon/conserp.json`, External → /conserp/desktop) และ "ConsOffice" (`consoffice.json` → /conserp/purchase, patch `add_consoffice_to_desktop_layouts`) ผู้ใช้ที่มี Desktop Layout ของตัวเองเห็นไอคอนใหม่เฉพาะที่อยู่ใน layout (patch `add_conserp_to_desktop_layouts`)
  แผนงาน (หมวด `pm`, สิทธิ์อ่าน CM): ภาพรวม (`dashboard.get_dashboard`), แผนงาน (`Plan.vue` = `PlanEdit.vue` แบบ `readonly` ใช้ตาราง Gantt ชุดเดียวกับหน้าแก้แผน), Look-ahead (`lookahead.get_lookahead` สถานะวันตรงกับ `LookAhead.vue`), เอกสาร (`PmDocs.vue` 1 ชนิดเอกสาร = 1 tab: VO / EOT / ขอตรวจงาน / Punch List / รายงานประจำวัน / ขออนุมัติ / Baseline / แผนและรายงาน, จำนวน `get_documents` รายการ `site_app.get_pm_document_rows` เพิ่มชนิดใหม่ที่ `DOCUMENT_LISTS` และ `TABS`, ขอตรวจงาน/Punch List มีที่หมวดควบคุมงานด้วย ใช้ข้อมูลชุดเดียวกัน) สร้าง/แก้/ดู VO, EOT, ขอตรวจงาน, Punch List ในแอป: `views/project_docs/` (`PROJECT_KINDS` ใน `kinds.js` ตรงกับ `KINDS` ใน `consbiz/project_docs.py`) VO/EOT อยู่หมวด `pm` (`pm-doc`, `pm-doc-form`) ขอตรวจงาน/Punch List อยู่หมวด `work` (`site-doc`, `site-form`) ยกเลิก/amend ใช้ระบบเต็ม VO แก้ในแอปเฉพาะผู้ที่เห็นงบต้นทุน
  ทรัพยากร (หมวด `resources`, `views/resources/Resources.vue` ทุกคนที่เข้าหมวดหน้างานได้): ต้องสั่ง / ยอดวัสดุ / คน-เครื่อง / Gantt / รายเดือน แต่ละเมนูเป็น view ของหน้าเดียว ใช้ planner ร่วมกัน (`resource_board.js`)
  ส่วนแสดงผล `pm/planner/ResourcePane.vue`, `MaterialOrders.vue`, `MaterialSupply.vue`, `ResourcePeople.vue`, `ResourceBoard.vue`, `ResourceMonthly.vue`, `resource_rows.js` (มุมมองของหน้าแผนงานใช้ชุดเดียวกัน แกนเวลา `planner/time_axis.js`) API `site_app.get_resource_board` ไม่ส่งมูลค่า/น้ำหนัก ติ๊กขอซื้อ = สิทธิ์สร้าง Material Request เปิดฟอร์มใบขอซื้อใหม่ (`buy-form` source `plan`, `site_docs.plan_request`) ยังไม่บันทึกจนกว่าผู้ใช้จะกดเอง ซื้อเอง/ผู้ว่าจ้างจัดหาปนกัน = ทำทีละใบ
  การเงิน (เมนูในหมวด `pm` เห็นตาม `boot.can.finance` ผ่าน `when` ของเมนูใน sections.js, `views/finance/Finance.vue`): tab Cash Flow / ต้นทุน / Earned Value (`/conserp/pm/finance/<tab>`, URL เดิม `/conserp/finance` เด้งมา) ข้อมูล `finance.get_finance` ผ่าน `site_app.get_project_finance` เห็นเฉพาะผู้ที่เห็นงบต้นทุน (`site_app.can_view_finance` = permlevel 1 ของ CM)
  แก้แผนงาน (สิทธิ์เขียน CM): หน้าเต็มจอ `plan-edit` (`views/pm/PlanEdit.vue`, ไม่ใช้ desk) แถบเครื่องมือ 2 แถว (แท็บ "แผนงาน"/"มุมมอง" / ไอคอน: จอเมาส์ไอคอนล้วน + tooltip, จอสัมผัสมีชื่อ) เมนูคอลัมน์ = ซ้ายสุดของแท็บ "มุมมอง" ช่องติ๊กเปิด-ปิด + ลากย้ายลำดับ (`settings.column_order`, wbs/ชื่องานอยู่ต้นตารางเสมอ) + ตาราง + Gantt + แผงงาน + แถบสถานะ
  state/การแก้/Undo/บันทึกอัตโนมัติ = `views/pm/planner/planner.js` (คำนวณด้วย `construction_management/schedule.js`, API `get_schedule_data` / `save_tasks` เหมือนหน้า Gantt ระบบเต็ม)
  ตาราง + Gantt = `planner/PlanSheet.vue` (กล่องเลื่อนเดียว ตารางติดซ้าย, ลากแถบด้วยเมาส์ จอสัมผัสแตะ = แก้ในแผง, สัปดาห์แบ่งในเดือน/รายเดือนช่องกว้างเท่ากัน: คิดตำแหน่งผ่าน `x()` / `axis.day_at()` ห้ามคูณ `ppd` ตรง, tooltip = `planner/PlanTooltip.vue` เขียน `title` ตามปกติ) รายละเอียดงาน = `planner/PlanInspector.vue`
  แก้ได้: วันเริ่ม/จบ/จำนวนวัน, งานก่อนหน้า, % แผนรายช่วง (แท็บ "% แผน" `planner/PlanDistribution.vue` ตรงกับ `plan_dialog.js` ของระบบเต็ม), คน/เครื่องจักร + วัสดุ (แท็บ "ทรัพยากร" `planner/PlanResources.vue` ตรงกับ `TaskPanel.vue`, บันทึกพร้อม `save_tasks`), % จริง ณ วัน Cut-off, คลิกขวาที่แถว = เมนู (`planner/PlanMenu.vue` รายการอยู่ใน `open_menu` ของ PlanEdit) พิมพ์ = แท็บ "พิมพ์" (`planner/PlanPrint.vue`: Preview ซ้าย + Properties ขวา, สั่งพิมพ์จาก iframe ของ Preview จึงตรงกัน, ป้ายท้ายแถบจัดตำแหน่งเอง (`placed_end_texts` ใน print.js) ขวา/ซ้าย/ตัดชื่อ และเผื่อท้าย Timeline เท่าป้ายสถานะ, ปุ่มดู PDF = `print_pdf.get_plan_pdf` (Chromium ฝั่ง server ตรวจ HTML แบบ allowlist: ถ้า print.js ใช้แท็ก/แอตทริบิวต์ใหม่ต้องเพิ่มใน `ALLOWED_*`), แบบเอกสาร = `THEMES` ใน print.js (ตามหน้าจอ/ทางการ/แถบข้าง desk ใช้แบบเดิม), ตัวเทียบหลักของหัวกระดาษ/ตารางสรุป/S-Curve = Baseline, ย่อ-หุบ WBS ของงานพิมพ์แยกจากตาราง ค่าจำในเครื่องแยกตามแผน `consbiz.planner.print.<CM>`, ข้อมูล `planner/print_model.js` ตัวสร้าง `build_print` ใน `construction_management/print.js` ชุดเดียวกับระบบเต็ม, `print_env.js` แทนฟังก์ชันของ desk) ส่วน Excel/บันทึก Baseline/แผนทรัพยากร ยังเปิดหน้า Gantt ของระบบเต็ม (แท็บใหม่)
  แก้โครงสร้างงาน (แท็บ "แผนงาน" เพิ่มงาน/งานย่อย/Indent/Outdent/ลบ, Shift เลือกหลายงาน) = `construction_management/structure.py` บันทึกทันที Undo ไม่ได้ งานเพิ่มในแผน (`boq_detail` ว่าง) มูลค่า 0 งาน BOQ เป็นหัวกลุ่มหรือถูกลบไม่ได้ บันทึก Baseline ชุดแรก = ยืนยันแผน: ปิดคำสั่งโครงสร้างทั้งหมด (WBS มาจาก BOQ/VO เท่านั้น) ยกเลิกการยืนยัน (`unconfirm_plan` ลบ Baseline ทุกชุด) ได้เฉพาะแผนที่ยังไม่มีความคืบหน้า/เอกสารอ้าง WBS/งาน VO ก่อนยืนยัน: ไม่มีเอกสารอ้าง = รันเลข WBS ใหม่ทั้งแผน มีเอกสารอ้าง = งานที่ถูกใช้ล็อก งานใหม่ได้เลขถัดไปท้ายกลุ่ม งานที่เพิ่มเองไม่ขึ้นใน Daily Report / Daily Request (`is_planning_task`) ผู้วางแผนอัปเดต % ในหน้าแก้แผน คอลัมน์ "เลข BOQ" (`boq_wbs`) = เลขเดิมใน BOQ เอกสารที่อ้าง WBS เพิ่มใหม่ต้องเพิ่มใน `CHILD_REFERENCES` / `HEADER_REFERENCES`
  ออกจากหน้าผ่าน `set_leave_guard` (api.js) บันทึกงานค้างก่อน (`planner.flush`) แก้ logic ฝั่ง App.vue ของระบบเต็มต้องแก้ planner.js ด้วย
  Look-ahead: มือถือ = การ์ดทีละสัปดาห์, แท็บเล็ต = ตาราง 2 สัปดาห์, จอใหญ่ = ตารางทั้งช่วง (matchMedia ใน `Lookahead.vue`)
  summary ของหมวดที่ `lazy` (แผนงาน) โหลดเมื่อเปิดหมวดนั้นเท่านั้น
  หมวดที่เห็นตามสิทธิ์ (`site_app.boot_data` → `sections`) สลับหมวด: มือถือ = ตารางหมวดทุกแอป (`SectionLauncher.vue` → `ModuleGrid.vue`) เปิดจากปุ่มซ้ายสุดของ `TopBar.vue`
  แท็บเล็ต/จอใหญ่ = Dock แถบเดียว `.ss-rail` ใน AppShell กว้าง 56px เท่า Dock ของ Frappe (ไม่มี sidebar แยก) โลโก้ = หน้าแรก, หมวดของกลุ่มแอปนี้เท่านั้น
  (หน้าแรกแสดงทุกกลุ่ม ตารางหมวดของมือถือ = กลุ่มนี้ + ปุ่มหน้าแรก `ModuleGrid local_only`),
  เมนูของหมวด = แท็บบนแถบบน (`SectionTabs.vue`, ข้อมูลจาก AppShell `provide("section_nav")`): อยู่ใน `TopBar` แทนชื่อหน้า
  (เฉพาะหน้าที่ไม่มีปุ่มย้อนกลับ) จอ < 1100 แท็บที่ไม่ได้เลือกเหลือไอคอน Dock ค่าเริ่มต้นพับ (ไอคอน)
  ชี้เมาส์แล้วไม่กางเอง (ชื่อเมนูดูจาก tooltip) จอสัมผัส = ปุ่มพับ/กางกางชั่วคราวทับเนื้อหา (`html[data-peek]`) เลือกเมนู/แตะนอกแถบแล้วพับ
  Dock ไม่มีปุ่มเลือกโครงการ: เลือกที่ปุ่มโครงการบน `TopBar.vue` (มือถือ = แถบเต็มแถวใต้แถบบน `.ss-project-bar`, เฉพาะหน้าเมนูหลักที่ไม่มีปุ่มย้อนกลับ
  หน้าดู/ฟอร์มไม่ให้เปลี่ยนโครงการกลางคัน, `no_project` = ซ่อน) Dock มีแค่ตัวเลือกบริษัทของออฟฟิศ
  หน้ารายการจอ ≥768: หัวรายการ `.ss-list-head` = แท็บสถานะ (`StatusTabs.vue` หน้าตาเดียวกับ `.pl-tabs`) + ตัวกรอง → ปุ่มส่งออก/สร้าง แถวเดียวเสมอ ต่อเป็นการ์ดเดียวกับตาราง (ไม่มีปุ่มลอย) ตัวกรองที่ไม่พอซ่อนแล้วกำหนดที่ปุ่มตัวกรอง (`use_overflow_row` ใน `table.js`, ปุ่มแสดงจำนวนตัวกรองที่ใช้ ไม่แสดงชิปบนจอ ≥768) ช่องค้นหาอยู่แถบบน (`HeaderSearch.vue` ผ่าน slot `search`, จอ < 1180 = ปุ่มแว่นขยาย กดแล้วกางทับแถบบน) ปุ่มสร้างอยู่ขวาสุดของหัวรายการ ถัดจากปุ่มโหลดใหม่ แถบบนด้านขวาเรียง โครงการ → ค้นหา → แจ้งเตือน ปุ่มโครงการตัดชื่อด้วย … แถบแคบ (≤660px) = `Project.custom_abbr` ไม่ตั้ง = ตัวย่อจากชื่อ
  มือถือ = แท็บสถานะ + ค้นหาในแถบเครื่องมือ + ตัวกรองใน sheet สโตร์และตรวจงาน/คอนกรีตใช้หัวรายการเดียวกัน หน้ารับของ/เบิก/ยืม-คืน/คลัง + ตาราง `DataTable.vue` (เรียง/แบ่งหน้าในเครื่อง)
  ปุ่มพับ/กาง = แถวบนสุดของโซนท้าย Dock เหนือบริษัท/avatar (`.ss-rail-toggle`) จอเมาส์ = ปักหมุด
  (`html[data-side="expanded"]`) กางค้างและดันเนื้อหา จำในเครื่อง ท้าย Dock = บริษัท (ออฟฟิศ) + avatar ผู้ใช้วงกลม (เมนู: ชื่อเต็ม+User → `ProfileSheet.vue` ข้อมูลส่วนตัว / ระบบเต็ม / ออกจากระบบ)
  tooltip ทุกหมวด = `shared/components/AppTooltip.vue` (วางครั้งเดียวใน AppShell) หน้าจอเขียน `title` ตามปกติ
  `html[data-side]` กำหนด `--ss-side` (56px / กาง 232px) ที่เนื้อหา/sheet/แถบล่างใช้ (data-peek ไม่เปลี่ยน --ss-side)
  รายการเอกสารจัดซื้อ/ขาย (`DocList.vue`): สถานะมีจำนวน, ค้นหา (เลขที่/คู่ค้า/เลขที่บิล/ชื่อหรือรหัสสินค้า `search_filters`)/ช่วงวันที่/คู่ค้า/เกินกำหนด/ขอบเขต, เรียงคอลัมน์, เลือกหลายแถวแล้วส่ง (`submit_docs` ใช้ savepoint ต่อใบ), ส่งออก CSV
  คอลัมน์ต่อชนิดเอกสารใน `DocTable.vue` (ท้ายตาราง: มอบหมาย `_assign` / แก้ไขล่าสุด / ถูกใจ `frappe.desk.like.toggle_like`)
  `get_docs` คืน rows + total + sums (ยอดรวมทั้งชุด) + counts (ของแต่ละแท็บ) มือถือ = การ์ด (`DocCard.vue`) + ตัวกรองใน sheet, แท็บเล็ต/จอใหญ่ = ตาราง (`DocTable.vue`) + แบ่งหน้า
  Dock พับ/กางใช้แถวสูงเท่ากัน (ชื่อแค่จางหาย) ห้ามให้ความสูงต่างกันตามสถานะ ไม่งั้นเมนูขยับตอนเปิด-ปิด
  ขนาดกระชับของแท็บเล็ต/จอใหญ่อยู่ท้าย `style.css`: จอสัมผัส ≥768 ปุ่ม 40px, จอใช้เมาส์ปุ่ม/ช่องกรอก/เครื่องมือ 32px (ใกล้ปุ่มของ Frappe) ช่องกรอกจอสัมผัส 40px, `Segmented` ขนาดเดียวกับ `.ss-status-pills`
  แถบบนทุกหน้า (`TopBar.vue`, หน้าหลักหมวดผ่าน `Hero.vue`) แถวเดียว สีพื้นตามหมวด สูงคงที่ 52px / จอ ≥768 48px ซ้ายสุด = ชื่อหมวด (มือถือ = ไอคอน กดเปลี่ยนหมวด) ขวาสุด = แจ้งเตือน จอแท็บเล็ต/จอใหญ่ห้ามมีปุ่มสร้าง/บันทึกในแถบบน เว้นแต่ผู้ใช้สั่งเป็นหน้าๆ (ให้อยู่แถบ tab ของหน้า เช่น `.ss-boq-tabbar`) หน้าเดิมที่ยังใช้ slot `actions` ค่อยย้ายเมื่อสั่ง (`NotificationBell.vue`, `shared/notifications.js` = Notification Log ของ Frappe, เอกสารที่มีหน้าในแอปใหม่เพิ่มใน `APP_PAGES` ของไฟล์นี้) ไม่มีคำทักทาย
  ตัวอักษรทั้งแอปอยู่ตัวแปร `--ss-fs*` ใน `:root` ของ `shared/style.css` ที่เดียว (จอสัมผัส เนื้อหา 13px / จอใช้เมาส์ 12px, ตัวเล็ก 11px) ห้ามใส่เลข px ตรงๆ ยกเว้นตาราง Gantt ของ `plan-edit` (11px, หัวเวลา 10px)
  จอ ≥1480: รายการ = ตาราง + ตัวอย่างเอกสารขวา (`DocPreview.vue`, คลิก = ดูตัวอย่าง, ↑↓ เลื่อน, ดับเบิลคลิก/Enter = เปิดเต็มหน้า)
  แผงตัวอย่างต้องพอดีจอโน้ตบุ๊ก (สูง ~760px) โดยไม่เลื่อน: รายการ 3 แถวแรก + ยอดสำคัญ (ยอดรวม/ยอดสุทธิ/ค้าง) รายละเอียดอื่นดูในหน้าเต็ม
  ตารางคู่แผงตัวอย่าง (`is-compact`) ซ่อนคอลัมน์ `col-wide` (วันต้องการ/ครบกำหนด, %, วัตถุประสงค์, ค้าง, มอบหมาย, แก้ไขล่าสุด) แผงจึงต้องแสดงข้อมูลเหล่านี้
  ไม่ซ้ำกับคอลัมน์ที่ยังเห็น (โครงการ, เลขที่บิล) แต่คงเลขที่/สถานะ/คู่ค้า/วันที่ไว้เป็นหัวแผง (ให้รู้ว่ากำลังดูใบไหน)
  ฟอร์ม = แผงข้อมูลประกอบของแถวที่เลือก (`ItemInsight.vue`, `site_docs.get_item_insight`: คงเหลือ / แผนวัสดุเทียบขอ-สั่ง-รับ / ราคาล่าสุด / PO ค้างรับ)
  เทสต์แบบ rollback บน dev: คำสั่งที่ทำ DDL (เช่น frappe เพิ่มคอลัมน์ `_liked_by` ครั้งแรก) commit ทันที ข้อมูลทดสอบจะค้าง ตรวจและลบเองทุกครั้ง
  สลับแล้วไปเมนูล่าสุดของหมวดนั้น (`state.last_tab`)
  ฟอร์มบนแท็บเล็ต/จอใหญ่: เลย์เอาต์ในขั้นของฟอร์มใช้ container query (`.ss-step-body`) ตามความกว้างฟอร์ม ไม่ใช่ความกว้างจอ
  ฟอร์มทีละขั้น ≥1180 = แถบขั้นตอนซ้าย (`.ss-wizard`) พร้อมสรุปของขั้น (`step_hint`), งานที่ทำ 1 งาน = 1 แถว, Ctrl/⌘+Enter = ถัดไป/ส่ง
  จอใช้เมาส์ (`hover: hover` + `pointer: fine`) ช่องกรอกเตี้ยลงและมีเส้นขอบ จอสัมผัสคงขนาดใหญ่ แถบล่างปุ่มชิดขวา
  สีหลักตามหมวด: `data-section` ที่ `<html>` (sheet ถูก Teleport ไป body) ทับ `--ss-brand*`
  ชื่อหน้า (view) ห้ามซ้ำข้ามหมวด (`go(view)` หาหมวดจาก `ROUTES`), summary แยกหมวดใน `state.summaries`
  ควบคุมงาน: ภาพรวม % จริง/แผน + S-Curve (`SCurve.vue`, ข้อมูล `dashboard.progress_curve`), ปฏิทินรายงาน (`get_site_calendar`) + tab ตารางรายงาน/ขออนุมัติ เลือกหลายแถวแล้วพิมพ์รวมไฟล์เดียว (`ReportList.vue`, `site_app.get_report_list` / `reports_pdf`)
  เขียน Daily Report / ขอ-อนุมัติ-ไม่อนุมัติ Daily Request ในแอป (`ReportForm.vue` ทีละขั้น, `ReportView.vue`, API `site_app.save_report`)
  แอปส่งเฉพาะช่องใน `FORM_FIELDS` / `ITEM_FIELDS` ค่าอื่นคำนวณใน validate ของเอกสารเหมือนกรอกในระบบเต็ม
  ฟอร์มใหม่เก็บร่างใน localStorage ระหว่างกรอก (สัญญาณหลุดไม่หาย) ขอตรวจงาน / Punch List สร้างใน `views/project_docs/`
  ขออนุมัติได้ทุกวัน (ย้อนหลังได้) PDF/แชร์ไฟล์: `site_app.pdf_url` เลือกตัวสร้าง PDF แบบหน้าพิมพ์ของระบบเต็ม (Print Format → Print Settings)
  ดู PDF ในแอป (`PdfViewer.vue`) วาดด้วย PDF.js ที่ `public/js/lib/pdfjs/` (มือถือแสดง PDF ใน iframe ไม่ได้) โหลดเมื่อเปิดครั้งแรก
  ไม่ใช้ desk: เรียก API ด้วย fetch เอง (`api.js`), router เอง (`<base>/<หมวด>/<view>/<params>`, หน้าหลักของหมวดไม่มี `<view>` ใน URL params เริ่มต่อจากหมวด, `website_route_rules`), CSS อยู่ `shared/style.css` (class `ss-`)
  `/store/...` เดิมเด้งไป `/conserp/store/...` (`website_redirects` ใน hooks.py) ไอคอนที่ติดตั้งไว้แล้วยังใช้ได้
  CSS ต้อง `@import` ใน `<style>` ของ `AppShell.vue` (Frappe ฝัง CSS เข้า bundle เฉพาะที่มาจาก .vue ถ้า import .css ตรงๆ ไฟล์ JS ถูกลบตอน build)
  ห้ามวาง comment ระดับ root ใน `<template>` (ข้าง root element) ให้วางเหนือ `<template>` หรือในตัว element:
  build `--production` (เซิร์ฟเวอร์จริง) นับ comment เป็น root ด้วย class/attrs จากตัวแม่ (เช่น `ss-view`) จึงหาย dev build ไม่เป็น
  เคยทำให้หน้าแรกซื้อ/ขายกว้างเกินจอเมื่อชื่อโครงการยาว ตรวจเลย์เอาต์ก่อนขึ้นระบบด้วย `bench build --app consbiz --production`
  Responsive 3 ขนาด: มือถือ = แถบเมนูล่าง, ≥768 = แถบไอคอนซ้าย + sheet เป็นหน้าต่างกลางจอ, ≥1180 = sidebar + ฟอร์มแบ่งซ้าย-ขวา (`.ss-split`) ใช้เต็มจอ: จอกว้างได้คอลัมน์เพิ่ม (auto-fill) ไม่ยืดการ์ด, การ์ดในรายการสูงเท่ากัน (`grid-auto-rows: 1fr`)
  แถบล่าง/ปุ่มลอยของหน้า ต้อง `<Teleport to="#ss-layer">` (ตอนเปลี่ยนหน้า view มี transform ทำให้ position: fixed เพี้ยน)
  ห้ามส่ง reactive object ของ Vue เข้า `history.pushState/replaceState` (clone ไม่ได้ แอปค้าง) `/app/site-store` เดิมเด้งไป `/conserp/store`
  สโตร์ รับของ: PO ของโครงการ → Purchase Receipt (บัญชีทำ PI ต่อจาก PR), MR ผู้ว่าจ้างจัดหา → Stock Entry Material Receipt
  ตีกลับที่หน้างาน = ไม่รับเข้า ยอดค้างที่ PO/MR เก็บใน `custom_site_rejected_qty` / `custom_site_reject_reason` ของแถว
  ตีกลับทั้งหมด = ไม่มีใบรับ บันทึก Comment ที่ PO/MR, รูปอัปโหลดก่อนแล้ว server ผูกกับเอกสาร (`attach_files`)
- Self Service (`/conserp/self`, bundle `public/js/self_app/`, www `self.html`, API `consbiz/self_service.py`, หมวด `self` ใน `_SELF_SECTIONS` ของ hooks.py):
  ทุก API หาพนักงานจาก `Employee.user_id` = ผู้ใช้ที่ล็อกอิน ไม่รับรหัสพนักงานจากภายนอก (เขียนด้วย ignore_permissions หลังตรวจเจ้าของแล้ว) ไม่ผูก Employee = ไม่เห็นหมวด
  `configure({ no_project: true })` = AppShell ไม่โหลด/ไม่แสดงโครงการ (พนักงานอาจไม่มีสิทธิ์อ่าน Project)
  ลงเวลา = `Employee Checkin` ต้องมีเซลฟี่ถ่ายสด (`shared/components/LiveCamera.vue` getUserMedia ไม่มีเลือกไฟล์, 480px JPEG 0.6 ส่งเป็น data URL ในคำขอเดียว, ไฟล์ private) + อยู่ในรัศมี `Shift Location` (รัศมี 0 = ยังไม่ตั้ง ลงไม่ได้)
  ของ `Employee.custom_checkin_location` ถ้าไม่ตั้งใช้ของ `Project.custom_checkin_location` ของโครงการที่ประจำ (`Employee.custom_project`) ห้ามลงซ้ำใน 60 วินาที
  พนักงานสร้าง/แก้ Checkin เองนอกแอปไม่ได้ (doc_events `guard_checkin`, HR/Administrator ได้) ช่องของแอปบน Checkin เป็น permlevel 1 (Employee อ่านอย่างเดียว)
  รูปเซลฟี่: ดูผ่าน `self_service.selfie` (เจ้าตัว + HR) scheduler รายวัน `purge_selfies` ลบเฉพาะไฟล์ เมื่อ Salary Slip (Submit) ที่ครอบวันนั้น posting_date เกิน 90 วัน
  เว้นแต่ HR ติ๊ก `custom_keep_evidence` (ตกลง 2026-11-11) เวลา/พิกัดไม่ลบ
  ต้องยืนยัน (ตกลง 2026-11-11): นอกรัศมี หรือ GPS คลาดเกิน `ACCURACY_LIMIT` (100 ม.) ลงได้แต่ต้องมีเหตุผล / ลืมลงเวลาออก แจ้งย้อนหลังได้ `MISSING_OUT_DAYS` (7) วัน (`request_checkout`, ไม่มี GPS/รูป)
  ทั้งสองแบบ = `custom_approval_status` Pending + `skip_auto_attendance` (HRMS ไม่นับจนกว่ายืนยัน)
  ผู้อนุมัติใบลา + ลงเวลา = Role `Leave Approver` (`APPROVER_ROLE`, ไม่ใช้ Reports To / `leave_approver` ของพนักงาน, ตกลง 2026-11-11)
  ผู้อนุมัติที่ประจำโครงการ (`Employee.custom_project`) เห็นเฉพาะพนักงานโครงการเดียวกัน ไม่ประจำ = ทุกคน (`scope_employees` / `can_approve_employee`), HR เห็นทุกคน
  แจ้งเตือนส่งหาทุกคนในขอบเขต (`approvers_of`) ช่อง `custom_approver` ของ Checkin เลิกใช้
  ยืนยันในโมดูลอนุมัติ (ด้านล่าง) ไม่ยืนยันต้องมีเหตุผล ยืนยันของตัวเองไม่ได้ แจ้งเตือนผ่าน Notification Log ทั้งผู้ยืนยันและเจ้าของ
  ลืมลงเวลาออกแล้วไม่แจ้ง/ไม่ได้รับยืนยัน: ไม่สร้าง Attendance อัตโนมัติ ให้ HR ตัดสินในหน้าสรุปวันทำงาน (หมวด `hr`) กะข้ามเที่ยงคืนยังไม่รองรับ
  ลา = `Leave Application` สถานะ Open (`leave_approver` = ผู้อนุมัติคนแรกในขอบเขตไว้ก่อน อนุมัติแล้วเปลี่ยนเป็นผู้อนุมัติจริง) ถอนได้เฉพาะร่าง Open สลิป = Salary Slip ที่ Submit แล้ว PDF ผ่าน `slip_pdf` (ข้ามสิทธิ์พิมพ์หลังตรวจเจ้าของ)
  วันหยุดประจำสัปดาห์ = DocType `Weekly Day Off` (ชื่อ `WDO-<พนักงาน>-<วันจันทร์>`, 1 ใบต่อคนต่อสัปดาห์) หยุดเสาร์หรืออาทิตย์ ใครลงก่อนได้ก่อน มีผลทันที (ตกลง 2026-11-11)
  โควตาต่อโครงการ: เสาร์ = ceil(ทีม x `Project.custom_day_off_saturday_percent`% (ค่าเริ่มต้น 50)), อาทิตย์ = ceil(ส่วนที่เหลือ) ทีม = Employee Active ที่ `custom_project` เดียวกัน
  `book_day_off` ล็อกแถว Project (for_update) กันแย่งพร้อมกัน ลงได้สัปดาห์นี้ + `DAY_OFF_WEEKS` สัปดาห์ เปลี่ยน/ยกเลิกได้ถึงวันหยุดนั้น HR แก้ในระบบได้ทุกเวลา (เกินโควตาแค่เตือน) คนอื่นแก้นอกแอปไม่ได้
  ไม่ผูกกับ Holiday List: หน้าสรุปวันทำงาน (`hr_attendance.py`) อ่าน Weekly Day Off เอง
  เบิกเงิน (`consbiz/self_advance.py`, หน้า `advances`, อนุมัติในโมดูลอนุมัติ, ตกลง 2026-11-11): `Employee Advance.custom_advance_type` = Salary Advance (เบิกเงินเดือนล่วงหน้า) / Expense Advance (เงินสำรองจ่าย)
  ผู้อนุมัติ = Role `Expense Approver` (ไม่ใช้ Reports To) อนุมัติในแอป = Submit ไม่อนุมัติ = คงร่าง + เหตุผล อนุมัติของตัวเองไม่ได้ จ่ายเงิน/รับเงินคืน ฝ่ายบัญชีทำ Payment Entry ในระบบเต็ม
  เงินเดือนล่วงหน้า: วงเงิน `Company.custom_salary_advance_limit_percent` (50%) ของ base ใน Salary Structure Assignment รวมใบที่ยังหักคืนไม่ครบ เกิน = Role `Executive Approver` (fixtures `role.json`) อนุมัติอีกขั้น (`Pending Executive`)
  `guard_advance_submit` (before_submit) บังคับกติกาเดียวกันเมื่อ Submit จากระบบเต็ม หักคืน 1-6 งวด: Payment Entry on_submit สร้าง Additional Salary (`Company.custom_salary_advance_component`) งวดละเดือน งวดแรก = เดือนที่จ่าย (สลิปเดือนนั้นออกแล้ว = เดือนถัดไป)
  เงินสำรองจ่าย: จ่ายแล้ว `custom_clear_due_date` = วันจ่าย + `Company.custom_expense_clear_days` (15) เคลียร์ด้วย Expense Claim ที่ตัดยอด Advance (`get_expense_claim_advances` ของ HRMS) เลยกำหนดแจ้งเตือนพนักงานทุก 3 วัน (ไม่หักเงินเอง)
  เบิกค่าใช้จ่ายคืน = Expense Claim ไม่มี Advance ทุกแถวต้องมีรูปบิล (`Expense Claim Detail.custom_receipt`, ดูผ่าน `self_advance.receipt`) บริษัทต้องตั้ง Default Expense Claim Payable Account
  บัญชีเงินทดรองจ่ายพนักงานต้องเป็น Receivable (HRMS หายอดที่จ่ายจาก Advance Payment Ledger Entry ตามชนิดบัญชี)
- โมดูลอนุมัติ (`/conserp/approve`, หมวด `approve` ของ bundle self_app, `consbiz/approvals.py`, `self_app/views/ApproveInbox.vue`, ตกลง 2026-11-11):
  เป็นแค่ที่รวม (ตกลง 2026-11-11): แต่ละโมดูลอนุมัติในหน้าของตัวเองได้ถ้ามีสิทธิ์ ใช้ `shared/approvals/ApprovalSheet.vue` + `kinds.js` (KINDS/MODULES/`find_pending`) ชุดเดียวกัน
  เมนูย่อย = โมดูล: `approve` = ทั้งหมด, `approve-<โมดูล>` (ตอนนี้ `approve-hr`) tab = ชนิดเอกสาร ปุ่มสลับ รออนุมัติ / พิจารณาแล้ว (31 วัน) อยู่ขวาของแถบ tab (มือถือ = เหนือ tab)
  `approvals.MODULES` ตรงกับ `MODULES` ใน kinds.js, `get_inbox(module, quiet)` / `get_summary` คืนจำนวนรายโมดูล โมดูลใหม่: เพิ่ม MODULES + เมนูใน self_app/sections.js
  ในหมวดบุคคลอนุมัติได้ที่หน้าเบิกเงิน (ใบรออนุมัติ) และแผงวันของสรุปวันทำงาน (ลงเวลารอยืนยัน/ใบลา Open)
  ชนิด = `KINDS` ทั้งใน approvals.py และ ApproveInbox.vue: ใบลา (`review_leave`, Role Leave Approver ตามขอบเขตโครงการ หรือ HR) / ลงเวลา (`self_service.review_checkin`) / ใบเบิก + ใบเคลียร์ (`self_advance.review_*`)
  ผู้อนุมัติทุกชนิดกำหนดด้วย Role (ใบลา/ลงเวลา = Leave Approver, ใบเบิก/เคลียร์ = Expense Approver + Executive Approver) เห็นหมวดเมื่ออนุมัติได้อย่างน้อย 1 ชนิด (`approve_sections`, `boot.can.approve_<ชนิด>`) กลุ่มแอป self ใน Desktop ชื่อ "พนักงาน"
  หน้ารายละเอียดมีข้อมูลประกอบ (`shared/components/EmployeeContext.vue`, `approvals.get_context`): ใบลา/ลงเวลา = สิทธิ์วันลา ประวัติลา คนในโครงการที่ลาชนวัน การเข้างานเดือนนี้
  (ผู้อนุมัติที่ดูแลคนนั้น) ใบเบิก/ใบเคลียร์ = เงินเดือน วงเงิน ยอดค้างหักคืน (`repayment_of`) เฉพาะ Role การเบิก/HR หัวหน้าหน้างานไม่เห็นเงินเดือน (ตกลง 2026-11-11)
  การแจ้งเตือนของเอกสาร HR เปิดโมดูลอนุมัติถ้ามีสิทธิ์ ไม่งั้นเปิดหน้าของตัวเองใน Self Service (`APP_PAGES` รับหลายหน้า ใช้หน้าแรกที่เข้าหมวดได้)
  คนงานรายวันไม่อยู่ใน Self Service (จะอยู่โมดูลธุรการ)
- ฝ่ายบุคคล (`/conserp/hr`, หมวด `hr` ของ bundle ออฟฟิศ, `consbiz/hr_attendance.py`, `office_app/views/hr/HrAttendance.vue`, เฉพาะ HR ที่ Submit Attendance ได้, ตกลง 2026-11-11):
  Payroll คิดตาม Attendance (patch `set_payroll_based_on_attendance`, วันที่ยังไม่บันทึกนับมาทำงาน `consider_unmarked_attendance_as` = Present)
  เงินเดือน (หน้า `hr-payroll`, `consbiz/hr_payroll.py`, `HrPayroll.vue`, `boot.can.payroll`): รายเดือนอย่างเดียว 1 งวด (Payroll Entry) ต่อบริษัทต่อเดือน
  วันหยุด = Holiday List Assignment ของ HRMS v16 (ของพนักงาน > ของบริษัท, ไม่มีจึงใช้ `Employee.holiday_list`) บริษัทต้องมี ไม่งั้นออกสลิปไม่ได้
  Holiday List ของบริษัทใส่เฉพาะวันหยุดนักขัตฤกษ์ ห้ามใส่วันหยุดประจำสัปดาห์ (มาจาก Weekly Day Off ไม่งั้นได้หยุด 2 วัน)
  ขั้นตอน ตรวจการเข้างาน (วันรอตัดสิน + วันที่ผ่านมายังไม่บันทึก Attendance ต้องเป็น 0 ของพนักงานในงวด) → สร้างสลิป (Payroll Entry Submit, HRMS สร้างสลิปร่าง)
  → ตรวจ/คำนวณใหม่ → ยืนยันสลิป (`submit_slips` ตรวจการเข้างานซ้ำ + คำนวณใหม่ก่อน, HRMS ลงบัญชีค้างจ่าย) ยกเลิกงวดได้ก่อนยืนยันเท่านั้น
  สลิปเงินเดือน = Print Format standard `Salary Slip TH` (`consbiz/consbiz/print_format/salary_slip_th/`, ค่าเริ่มต้นผ่าน Property Setter) A4 หน้าเดียวไหลตามเนื้อหา
  โลโก้ฝังด้วย jinja `image_data_uri` (ไฟล์ private) เงินได้สะสม = รวม year_to_date ของแถวรายได้ (year_to_date ของสลิปเป็นยอดสุทธิ) "Salary Slip" แบบ Print Designer เดิมเลิกใช้
  บันทึกจ่ายเงิน (Bank Entry) เป็นของฝ่ายบัญชี (โมดูลบัญชีของแอปภายหลัง ตอนนี้ระบบเต็ม) ต้องตั้ง `salary_slip_based_on_timesheet` = 0 เอง (ว่าง = HRMS หาโครงสร้างไม่เจอ)
  ตั้งค่า HR (หน้า `hr-setup`, `consbiz/hr_setup.py` `CHECKS`/`FIXES`, `HrSetup.vue`): ตรวจการตั้งค่าของบริษัท (วันหยุด บัญชี รายการหัก Payroll Settings
  เงินเดือนตามวันทำงาน ประกันสังคม `SSO_FORMULA` = 5% ของ (base x payment_days/total_working_days + OT) ฐาน 1,650-17,500 ขั้นภาษีต่อเนื่อง Payroll Period
  นโยบาย/รอบ/โควตาวันลา `STATUTORY_LEAVES` ลาป่วย 30 ลากิจ 3 พักร้อน 6 (ลาป่วย/ลากิจไม่ลดตามเดือนที่เข้างาน `FULL_YEAR_LEAVES`) Role) แก้อัตโนมัติ = HR Manager/System Manager รันซ้ำได้
  ข้อที่ต้องเลือกบัญชีเอง = ลิงก์ไประบบเต็ม ใช้หลังขึ้นเซิร์ฟเวอร์จริงทุกครั้ง (ค่าตั้งเหล่านี้เป็นข้อมูล ไม่ได้มากับโค้ด)
  เพิ่ม/หัก (หน้า `hr-adjustments`, `consbiz/hr_salary.py`) = Additional Salary งวด = วันสุดท้ายของเดือน ห้ามรายการที่ระบบคำนวณ (`managed_components`: สูตรในโครงสร้าง, SAL/SSF/WHT/SAD/UNP, รายการของบริษัท)
  ค่าจ้างพนักงาน (หน้า `hr-salaries`) = Salary Structure Assignment ใบใหม่ต่อการปรับ (ประวัติคงอยู่) ขั้นภาษีจากใบล่าสุดของโครงสร้าง
  เบิกเงิน (หน้า `hr-advances`, `consbiz/hr_advances.py`) ใบเบิก/ใบเคลียร์ทั้งบริษัทแยกตามขั้น (`stage_of`) ดูอย่างเดียว
  สรุปวันทำงานรายเดือน: แถว = พนักงานของบริษัท (กรองโครงการได้) ช่อง = วัน สถานะ (`employee_days`): Attendance ที่มีอยู่ชนะเสมอ > วันหยุด (Holiday List) > หยุดประจำสัปดาห์
  (Weekly Day Off, สัปดาห์ที่ไม่ได้ลง = เสาร์/อาทิตย์ที่ไม่ได้ลงเวลา อาทิตย์ก่อน) > ชั่วโมง (`work_hours` = ช่วงเข้า-ออกที่อยู่ใน 08:00-17:00 หักพักเที่ยง 12-13)
  ≥ 4 = มาทำงาน (ไม่ตัดครึ่งวันเพราะสาย: พ.ร.บ.คุ้มครองแรงงาน ม.76), น้อยกว่า 4 = รอพิจารณา / ไม่มีลงเวลา = ขาด (ตกลง 2026-11-11)
  สาย = เข้าหลัง 08:05 นับนาทีจาก 08:00 (08:10 = 10 นาที), กลับก่อน = นาทีถึง 17:00 ไม่มีผ่อนผัน, หลัง 17:00 ไม่เป็น OT (ยังไม่มีนโยบาย) ใส่ `late_entry`/`early_exit` ของ Attendance
  จ่ายค่าจ้างเต็มเสมอ นาทีสาย/กลับก่อนไว้ใช้ทางวินัย สายเกินเหตุ/บ่อย HR กด "ไม่จ่ายเวลาที่ไม่ได้ทำงาน" รายเดือน (`set_unpaid_time`, No Work No Pay)
  = Additional Salary (Salary Component จาก `Company.custom_unpaid_time_component`) ยอด = นาทีรวม x เงินเดือน ÷ 30 ÷ 8 ÷ 60 เดือนละ 1 ใบ ยกเลิกได้จนกว่าจะออกสลิป
  ที่เหลือ = รอ HR ตัดสิน (มีรายการรอยืนยัน, ใบลารออนุมัติ, เข้า/ออกอย่างเดียว, ทั้งเดือนไม่ลงเวลาเลย แนะนำมาทำงาน) ยังไม่คิดสาย/OT
  มือถือ: การ์ดต่อคน แตะ = ปฏิทินเดือนของคนนั้น + รายการวันรอตัดสิน (จอใหญ่คลิกชื่อคนเปิดแผงเดียวกัน) เลือกเดือน/ปี = `DateInput picker="month"`
  ตัดสิน (`decide_days`, หลายวันของคนเดียวได้) = สร้าง Attendance ทันที (ครึ่งวัน = Half Day + half_day_status Absent) แก้ = ยกเลิกของเดิมสร้างใหม่ วันลาแก้ที่ใบลา งวดที่ออกสลิปแล้วแก้ไม่ได้
  ช่องติ๊ก "ไม่หักเงิน (ตักเตือน)" แยกจากสถานะ (ขาด/ครึ่งวัน, `WAIVABLE`): บันทึกเป็น Present ให้จ่ายค่าจ้าง สถานะจริงใน `Attendance.custom_waived_status`
  นับแยก (`totals.waived`) ไว้ใช้ทางวินัย ขาดบ่อยเกิน HR กด "หักเงินวันที่ยกเว้นไว้" (`charge_waived` = บันทึกเป็นสถานะจริง) ก่อนยืนยันสลิป
  "บันทึก Attendance" (`close_period`) = สร้างของวันมาทำงาน/ขาดถึงเมื่อวาน ต้องไม่มีวันรอตัดสิน ผูก `Employee Checkin.attendance` ของวันนั้น
- คนงานรายวัน (หมวดธุรการ `admin` ของกลุ่มหน้างาน `/conserp/admin`, เริ่ม 2026-11-13, แยกจาก HRMS): `Daily Worker` (ทะเบียน, ค่าแรงเป็นประวัติใน `rates` คิดตามอัตราของแต่ละวัน, จ่ายผ่าน Company หรือ Subcontractor = Supplier)
  `Labour Timesheet` 1 ใบต่อโครงการต่อรอบ (`period_of`: 1-15 / 16-สิ้นเดือน) แถว `days` = ชั่วโมงทำงานจริง 1 คนต่อวัน (เกิน 8 = OT) วันหยุดของทั้งวันในตาราง `holidays`
  ค่าแรงตามชั่วโมง (6 ชม. = 6/8 วัน) วันหยุด x 2, OT ÷ 8 x 1.5 (วันหยุด x 3) หรือ OT เหมา (`ot_flat`) ตาราง `pay` คำนวณใหม่ทุกครั้ง (กรอกได้เฉพาะหักอื่นๆ)
  Submit = อนุมัติ + ลงบัญชีตาม `Labour Settings` (1 ใบต่อบริษัท ตั้งในแอป: avatar > ตั้งค่า > หัวข้อ "บัญชี" > ค่าแรงคนงาน `settings/LabourSettings.vue`, Accounts Manager แก้ได้, ไม่มีบัญชีที่ตรง = ปุ่มสร้างบัญชี/Item ใหม่ `suggest_account` เสนอชื่อ กลุ่มแม่ เลขถัดไป):
  บริษัทจ่าย = Journal Entry ผูก Project, ผ่าน ผรม. = ร่าง Purchase Invoice ต่อ ผรม. (หัก ณ ที่จ่ายผ่าน `deductions.calculate`) Cancel = ยกเลิก JE / ลบร่าง PI
  บัญชีค้างจ่าย/เงินเบิกห้ามเป็น Payable/Receivable (JE บังคับคู่ค้า) erpnext_thailand บังคับแถวบริษัทใน Thai Tax Settings ก่อนลง JE (หน้าตั้งค่ามีรายการตรวจ)
  เบิกล่วงหน้า `Labour Advance` (เฉพาะคนงานที่บริษัทจ่าย, Submit = จ่าย JE) ใบลงเวลาตัดใบที่ค้าง (เก่าก่อน ไม่เกินค่าแรงหลังหักประกันสังคม/หักอื่นๆ) ลง `advances` ยอดค้าง/สถานะคำนวณใหม่ (`update_deduction`)
  ทะเบียนแก้ในแอป (`WorkerSheet.vue`, `get_worker` / `save_worker`: ค่าแรงใหม่ = เพิ่มแถวประวัติ, บัญชีธนาคาร + รับผ่านบัญชีผู้อื่น `account_holder*`)
  ทีม (`Daily Worker.team`, ว่าง + ผ่าน ผรม. = ชื่อ ผรม., `labour.team_of`) จัดกลุ่มหน้าลงเวลา: แถวหัวทีมพับได้ ช่องแถวทีม = ใส่ทั้งทีม แท็บกรองทีม (จุดแดง = ทีมที่ยังไม่มีชั่วโมงในวันที่เลือก, เกิน 5 ทีม = แท็บทั้งหมด/ทีมที่เลือก + ปุ่มเลือกทีมแบบค้นหา เพราะแท็บล้นแถบ) ปุ่มพับ/กางทุกทีม วางจาก Excel ได้ ย้ายทีมหลายคนที่ทะเบียน (`set_team`)
  หน้าแอป: `Labour.vue` (คลิกชื่อ = ยอดค่าแรง + หักอื่นๆ `set_deduction`, ปุ่มพิมพ์ = Print Format `Labour Timesheet` A4 แนวนอน = ใบลงเวลา + เซ็นรับเงิน), `Advances.vue`
  Daily Report ปุ่ม "ดึงจำนวนจากลงเวลาคนงาน" (`labour_on`) สูตรประกันสังคมของ HR สร้างจากตารางเดียวกัน (`hr_setup.sso_formula`, ตรวจตั้งค่าแจ้งเมื่ออัตราเปลี่ยน)
  `save_sheet` ส่งเฉพาะช่องที่แก้ ล็อก Project ก่อนหา/สร้างใบ ทะเบียน `views/admin/Workers.vue` (แก้รายละเอียดในระบบเต็ม)
  ประกันสังคม `consbiz/social_security.py` + ตาราง `Social Security Rate` (ช่วงแคบกว่าชนะ = ลดอัตราชั่วคราว, อัตราตามเดือนที่ทำงาน)
  เพดานรายเดือนคิดสะสมข้ามใบ (หักงวดนี้ = ควรหักถึงงวดนี้ - ถึงงวดก่อน) ฐานต่ำสุดเฉพาะใบที่ปิดเดือน ปัดบาทแบบ half up
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
- prefix ที่ใช้แล้ว ห้ามใช้ซ้ำ: `BCP-` Bar Cut Plan, `CM-` Construction Management, `CU-` Concrete Usage, `DR-` Daily Report, `DRQ-` Daily Request, `EB-` Equipment Borrowing, `EOT-` Extension of Time, `DW-` Daily Worker, `IR-` Inspection Request, `LA-` Labour Advance, `LT-` Labour Timesheet, `OPO-` Material Request ผู้ว่าจ้างจัดหา, `PL-` Punch List, `TX-` Transmittal, `VO-` Variation Order, `WDO-` Weekly Day Off (ตั้งชื่อด้วยโค้ด), `WHTE-` WHT Employee
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

- แก้ UI ของแอป ConsERP (`/conserp`) ต้องอ่าน `Design.md` ก่อน: ขนาด/สี/พฤติกรรมของแต่ละ component ห้ามตั้งขนาดทับเป็นรายหน้า ตกลงเรื่องหน้าตาใหม่แล้วแก้ไฟล์นั้นด้วย
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
  - PDF Generator แบบ `chrome` ใช้ `frappe-bench/chromium` ต้องติดตั้ง `libnss3 libasound2t64 libatk1.0-0t64 libatk-bridge2.0-0t64 libatspi2.0-0t64 libxdamage1` (Ubuntu ก่อน 24.04 ไม่มี `t64` ต่อท้าย) ไม่งั้นได้ "Chromium took too long to start"
    ตรวจตัวที่ขาดด้วย `ldd chromium/chrome-linux/headless_shell | grep "not found"` ติดตั้งแล้วต้อง restart bench
