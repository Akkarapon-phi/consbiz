// หน้าแรก ConsBiz: ไอคอนใหญ่ไปยังหน้าต่างๆ (กดง่ายบนมือถือ)
// แสดงใน Workspace "ConsBiz" ผ่าน Custom HTML Block "ConsBiz Home" ซึ่งมีแค่ตัวเรียก:
//   consbiz.render_home(root_element)
// Custom HTML Block อยู่ใน shadow DOM: CSS ของ consbiz (style.css) และ sprite ไอคอนของ Frappe เข้าไม่ถึง
// จึงใส่ CSS เองและคัดลอก <symbol> ของไอคอนเป็น <svg> ในตัว แสดงเฉพาะหน้าที่ผู้ใช้มีสิทธิ์ (ข้อมูลจาก frappe.boot)
// เพิ่ม/ย้ายรายการที่ HOME_GROUPS ด้านล่าง

const HOME_GROUPS = [
	{
		label: "แผนงานก่อสร้าง",
		color: "blue",
		items: [
			{ label: "แผนงาน", doctype: "Construction Management", icon: "calendar-range" },
			{ label: "ขออนุมัติปฏิบัติงาน", doctype: "Daily Request", icon: "clipboard-check" },
			{ label: "รายงานประจำวัน", doctype: "Daily Report", icon: "notebook-pen" },
			{ label: "ขอตรวจงาน", doctype: "Inspection Request", icon: "search-check" },
			{ label: "งานลด-งานเพิ่ม", doctype: "Variation Order", icon: "arrow-left-right" },
			{ label: "ขยายเวลา (EOT)", doctype: "Extension of Time", icon: "calendar-clock" },
			{ label: "Punch List", doctype: "Punch List", icon: "list-checks" },
			{ label: "BOQ", doctype: "BOQ", icon: "calculator" },
		],
	},
	{
		label: "สโตร์หน้างาน",
		color: "green",
		items: [
			{ label: "สโตร์หน้างาน", page: "site-store", icon: "package" },
			{ label: "รับของ / เบิก", doctype: "Stock Entry", icon: "boxes" },
			{ label: "ขอซื้อวัสดุ", doctype: "Material Request", icon: "shopping-cart" },
			{ label: "บันทึกคอนกรีต", doctype: "Concrete Usage", icon: "truck" },
			{ label: "ยืม-คืนอุปกรณ์", doctype: "Equipment Borrowing", icon: "wrench" },
			{ label: "แผนตัดเหล็ก", doctype: "Bar Cut Plan", icon: "scissors" },
		],
	},
	{
		label: "ซื้อ - ขาย",
		color: "orange",
		items: [
			{ label: "ใบเสนอราคา", doctype: "Quotation", icon: "file-text" },
			{ label: "คำสั่งขาย", doctype: "Sales Order", icon: "file-pen" },
			{ label: "ใบแจ้งหนี้ขาย", doctype: "Sales Invoice", icon: "receipt" },
			{ label: "คำสั่งซื้อ", doctype: "Purchase Order", icon: "shopping-bag" },
			{ label: "ใบแจ้งหนี้ซื้อ", doctype: "Purchase Invoice", icon: "receipt" },
		],
	},
	{
		label: "สัญญา / ประกันผลงาน / เอกสาร",
		color: "purple",
		items: [
			{ label: "สัญญาผู้รับเหมา", doctype: "Subcontract Agreement", icon: "signature" },
			{ label: "ประกันผลงานค้างรับ", doctype: "Retention Receivable", icon: "hand-coins" },
			{ label: "ประกันผลงานค้างจ่าย", doctype: "Retention Payable", icon: "hand-coins" },
			{ label: "ใบนำส่งเอกสาร", doctype: "Transmittal", icon: "send" },
		],
	},
	{
		label: "รายงาน",
		color: "gray",
		items: [
			{ label: "วิเคราะห์ความล่าช้า", report: "Construction Delay Analysis", icon: "timer" },
			{ label: "Earned Value", report: "Construction Earned Value", icon: "activity" },
			{ label: "คลังวัสดุโครงการ", report: "Project Stock Summary", icon: "chart-column" },
			{ label: "สรุปใบส่งของ", report: "Site Delivery Summary", icon: "clipboard-list" },
			{ label: "สรุปการใช้คอนกรีต", report: "Concrete Usage Summary", icon: "truck" },
			{ label: "อุปกรณ์ค้างคืน", report: "Borrowed Equipment Outstanding", icon: "wrench" },
		],
	},
];

const HOME_STYLE = `
	.ch {
		display: flex;
		flex-direction: column;
		gap: 24px;
		padding: 4px 0 16px;
		color: var(--text-color);
	}
	.ch-group-label {
		margin: 0 0 10px;
		color: var(--heading-color);
		font-size: var(--text-base);
		font-weight: 600;
	}
	.ch-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(104px, 1fr));
		gap: 10px;
	}
	.ch-tile {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 8px;
		padding: 14px 6px 12px;
		border: 1px solid var(--border-color);
		border-radius: var(--radius-lg, 12px);
		background: var(--card-bg);
		color: var(--text-color);
		text-align: center;
		text-decoration: none;
		transition: background 0.15s, box-shadow 0.15s;
	}
	.ch-tile:hover,
	.ch-tile:focus-visible {
		background: var(--fg-hover-color);
		box-shadow: var(--shadow-sm);
		text-decoration: none;
	}
	.ch-icon {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 48px;
		height: 48px;
		border-radius: 14px;
	}
	.ch-icon svg {
		width: 24px;
		height: 24px;
		fill: none;
		stroke: currentColor;
		stroke-width: 1.75;
		stroke-linecap: round;
		stroke-linejoin: round;
	}
	.ch-label {
		font-size: var(--text-sm);
		line-height: 1.3;
	}
	.ch-blue .ch-icon { background: var(--bg-blue); color: var(--text-on-blue); }
	.ch-green .ch-icon { background: var(--bg-green); color: var(--text-on-green); }
	.ch-orange .ch-icon { background: var(--bg-orange); color: var(--text-on-orange); }
	.ch-purple .ch-icon { background: var(--bg-purple); color: var(--text-on-purple); }
	.ch-gray .ch-icon { background: var(--bg-gray); color: var(--text-on-gray); }
	@media (max-width: 576px) {
		.ch-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; }
		.ch-icon { width: 44px; height: 44px; }
	}
`;

frappe.provide("consbiz");

consbiz.render_home = function (root) {
	const style = document.createElement("style");
	style.textContent = HOME_STYLE;
	const body = document.createElement("div");
	body.className = "ch";
	for (const group of HOME_GROUPS) {
		const items = group.items.filter(home_allowed);
		if (!items.length) continue;
		const section = document.createElement("section");
		section.className = `ch-${group.color}`;
		section.innerHTML = `<h4 class="ch-group-label">${frappe.utils.escape_html(__(group.label))}</h4><div class="ch-grid"></div>`;
		const grid = section.querySelector(".ch-grid");
		for (const item of items) grid.appendChild(home_tile(item));
		body.appendChild(section);
	}
	root.appendChild(style);
	root.appendChild(body);
};

function home_allowed(item) {
	if (item.doctype) return frappe.model.can_read(item.doctype);
	if (item.report) return Boolean(frappe.boot.allowed_reports?.[item.report]);
	if (item.page) return Boolean(frappe.boot.page_info?.[item.page]);
	return true;
}

function home_route(item) {
	if (item.doctype) return ["List", item.doctype];
	if (item.report) return ["query-report", item.report];
	return [item.page];
}

function home_tile(item) {
	const route = home_route(item);
	const tile = document.createElement("a");
	tile.className = "ch-tile";
	tile.href = `/app/${route[0] === "List" ? frappe.router.slug(route[1]) : route.map(encodeURIComponent).join("/")}`;
	tile.innerHTML = `<span class="ch-icon">${home_icon(item.icon)}</span><span class="ch-label">${frappe.utils.escape_html(
		__(item.label)
	)}</span>`;
	// ไปหน้าภายใน desk โดยไม่โหลดหน้าใหม่ (Ctrl/Cmd + คลิก = เปิดแท็บใหม่ตามปกติ)
	tile.addEventListener("click", (event) => {
		if (event.ctrlKey || event.metaKey || event.shiftKey) return;
		event.preventDefault();
		frappe.set_route(...route);
	});
	return tile;
}

// <svg> ในตัวจาก <symbol id="icon-..."> ของ sprite ที่ Frappe ใส่ไว้ในหน้า (<use href> ข้าม shadow DOM ไม่ได้)
function home_icon(name) {
	const symbol = document.getElementById(`icon-${name}`);
	if (!symbol) return "";
	return `<svg viewBox="${symbol.getAttribute("viewBox") || "0 0 24 24"}" aria-hidden="true">${symbol.innerHTML}</svg>`;
}
