// หน้า (view) ของ Self Service → component (ชื่อตรงกับ ROUTES ใน sections.js)
import Checkin from "./views/Checkin.vue";
import Leave from "./views/Leave.vue";
import Pay from "./views/Pay.vue";
import DayOff from "./views/DayOff.vue";
import Advances from "./views/Advances.vue";
import ApproveInbox from "./views/ApproveInbox.vue";

export default {
	checkin: Checkin,
	leave: Leave,
	pay: Pay,
	// URL เดิม /self/slips
	slips: Pay,
	dayoff: DayOff,
	advances: Advances,
	approve: ApproveInbox,
	"approve-hr": ApproveInbox,
	"approve-purchase": ApproveInbox,
};
