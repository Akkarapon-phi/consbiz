// ชนิดเอกสารของหน้ารายการกลาง (KindList.vue): key = ชื่อหน้ารายการ (view) ห้ามซ้ำข้ามหมวด
import { SARABAN_KINDS } from "../saraban/kinds.js";
import { SUBCONTRACT_KINDS } from "../subcontract/kinds.js";

export const LIST_KINDS = { ...SARABAN_KINDS, ...SUBCONTRACT_KINDS };
