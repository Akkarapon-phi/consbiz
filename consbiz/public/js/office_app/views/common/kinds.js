// ชนิดเอกสารของหน้ารายการกลาง (KindList.vue): key = ชื่อหน้ารายการ (view) ห้ามซ้ำข้ามหมวด
import { SARABAN_KINDS } from "../saraban/kinds.js";
import { SUBCONTRACT_KINDS } from "../subcontract/kinds.js";
import { RETENTION_KINDS } from "../retention/kinds.js";
import { HR_DOC_KINDS } from "../hr/kinds.js";
import { ACCOUNTING_KINDS } from "../accounting/kinds.js";
import { MASTER_KINDS } from "../master/kinds.js";

export const LIST_KINDS = { ...SARABAN_KINDS, ...SUBCONTRACT_KINDS, ...RETENTION_KINDS, ...HR_DOC_KINDS, ...ACCOUNTING_KINDS, ...MASTER_KINDS };
