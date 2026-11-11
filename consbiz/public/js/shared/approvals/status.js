// ป้ายสถานะของใบเบิก (Employee Advance) และใบเคลียร์/เบิกคืน (Expense Claim) ใช้ทั้งหน้าเบิกเงินและหน้าอนุมัติ
export const TYPE = { "Salary Advance": "เบิกเงินเดือนล่วงหน้า", "Expense Advance": "เงินสำรองจ่าย" };

export function advance_status(row) {
	if (row.docstatus === 0) {
		if (row.approval === "Rejected") return { label: "ไม่อนุมัติ", tone: "rose" };
		if (row.approval === "Pending Executive") return { label: "รอผู้บริหาร", tone: "violet" };
		return { label: "รออนุมัติ", tone: "amber" };
	}
	if (row.docstatus === 2) return { label: "ยกเลิก", tone: "gray" };
	if (["Unpaid", "Partially Paid"].includes(row.status)) return { label: "อนุมัติ รอจ่ายเงิน", tone: "blue" };
	if (row.advance_type === "Salary Advance") return { label: "จ่ายแล้ว · หักคืนจากเงินเดือน", tone: "green" };
	if (row.overdue) return { label: "เลยกำหนดเคลียร์", tone: "rose" };
	if (row.unclaimed > 0) return { label: "รอเคลียร์", tone: "amber" };
	if (row.status === "Returned") return { label: "คืนเงินแล้ว", tone: "green" };
	return { label: "เคลียร์แล้ว", tone: "green" };
}

export function claim_status(row) {
	if (row.docstatus === 0) return row.reject_reason ? { label: "ไม่อนุมัติ", tone: "rose" } : { label: "รออนุมัติ", tone: "amber" };
	if (row.docstatus === 2) return { label: "ยกเลิก", tone: "gray" };
	if (row.status === "Paid") return { label: "เสร็จสิ้น", tone: "green" };
	return { label: "อนุมัติ รอจ่ายเงิน", tone: "blue" };
}
