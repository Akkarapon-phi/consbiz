# สร้างรูปทรงการดัดเหล็กมาตรฐานและประเภทเหล็กที่ใช้บ่อย (ข้ามรายการที่มีอยู่แล้ว ผู้ใช้แก้ต่อได้)
# รูป SVG: เส้นใช้ currentColor ให้ตามสีตัวอักษรของหน้า ป้ายด้านใช้ data-dim ให้หน้าจอแทนค่าจริงได้

import frappe

LINE = 'fill="none" stroke="currentColor" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"'


def svg(paths, labels):
	body = "".join(f'<path d="{d}" {LINE}/>' for d in paths)
	body += "".join(
		f'<text data-dim="{dim}" x="{x}" y="{y}" text-anchor="middle" font-size="13" font-weight="600" '
		f'fill="currentColor">{dim}</text>'
		for dim, x, y in labels
	)
	return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 160 100">{body}</svg>'


SHAPES = [
	{
		"shape_code": "00",
		"shape_name": "เหล็กตรง",
		"dimensions": "A",
		"sides_formula": "A",
		"svg": svg(["M15,55 L145,55"], [("A", 80, 45)]),
	},
	{
		"shape_code": "01",
		"shape_name": "เหล็กตรงงอขอ 180° สองปลาย",
		"dimensions": "A",
		"sides_formula": "A",
		"hooks_180": 2,
		"svg": svg(
			["M30,60 L130,60", "M130,60 A9,9 0 0 0 130,42 L122,42", "M30,60 A9,9 0 0 1 30,42 L38,42"],
			[("A", 80, 82)],
		),
	},
	{
		"shape_code": "11",
		"shape_name": "งอฉาก (ตัว L)",
		"dimensions": "A,B",
		"sides_formula": "A+B",
		"bends_90": 1,
		"svg": svg(["M35,15 L35,75 L145,75"], [("A", 20, 49), ("B", 90, 94)]),
	},
	{
		"shape_code": "12",
		"shape_name": "งอฉาก ปลายงอขอ 180°",
		"dimensions": "A,B",
		"sides_formula": "A+B",
		"bends_90": 1,
		"hooks_180": 1,
		"svg": svg(
			["M35,30 L35,75 L145,75", "M35,30 A9,9 0 0 1 53,30 L53,38"], [("A", 20, 56), ("B", 90, 94)]
		),
	},
	{
		"shape_code": "21",
		"shape_name": "ตัว U",
		"dimensions": "A,B,C",
		"sides_formula": "A+B+C",
		"bends_90": 2,
		"svg": svg(["M35,15 L35,75 L125,75 L125,15"], [("A", 20, 49), ("B", 80, 94), ("C", 140, 49)]),
	},
	{
		"shape_code": "31",
		"shape_name": "ตัว C (4 ด้าน)",
		"dimensions": "A,B,C,D",
		"sides_formula": "A+B+C+D",
		"bends_90": 3,
		"svg": svg(
			["M80,18 L35,18 L35,78 L125,78 L125,50"],
			[("A", 58, 12), ("B", 20, 52), ("C", 80, 96), ("D", 140, 68)],
		),
	},
	{
		"shape_code": "41",
		"shape_name": "คอม้า (Crank)",
		"dimensions": "A,B,C",
		"sides_formula": "A+B+C",
		"bends_45": 2,
		"svg": svg(["M12,72 L60,72 L95,32 L148,32"], [("A", 36, 90), ("B", 66, 46), ("C", 122, 24)]),
	},
	{
		"shape_code": "51",
		"shape_name": "ปลอกสี่เหลี่ยม",
		"dimensions": "A,B",
		"sides_formula": "2*(A+B)",
		"bends_90": 3,
		"bends_135": 2,
		"hooks_135": 2,
		"svg": svg(
			["M56,42 L42,28 L118,28 L118,80 L42,80 L42,28", "M42,28 L56,14"],
			[("A", 80, 20), ("B", 136, 58)],
		),
	},
	{
		"shape_code": "61",
		"shape_name": "ปลอกวงกลม",
		"dimensions": "A",
		"sides_formula": "pi*A",
		"hooks_135": 2,
		"svg": (
			'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 160 100">'
			f'<circle cx="80" cy="52" r="36" {LINE}/>'
			f'<path d="M80,16 L92,30 M80,16 L68,30" {LINE}/>'
			'<path d="M44,52 L116,52" fill="none" stroke="currentColor" stroke-width="1.5" stroke-dasharray="4 3"/>'
			'<text data-dim="A" x="80" y="68" text-anchor="middle" font-size="13" font-weight="600" '
			'fill="currentColor">A</text></svg>'
		),
	},
]

# (ชื่อ, ผิว, ขนาด มม., ชั้นคุณภาพ, ความยาวมาตรฐาน ม.)
REBAR_TYPES = [
	("RB6", "RB", 6, "SR24", "10"),
	("RB9", "RB", 9, "SR24", "10"),
	("DB10", "DB", 10, "SD40", "10, 12"),
	("DB12", "DB", 12, "SD40", "10, 12"),
	("DB16", "DB", 16, "SD40", "10, 12"),
	("DB20", "DB", 20, "SD40", "10, 12"),
	("DB25", "DB", 25, "SD40", "10, 12"),
	("DB28", "DB", 28, "SD40", "10, 12"),
	("DB32", "DB", 32, "SD40", "10, 12"),
]


def execute():
	frappe.reload_doc("consbiz", "doctype", "bar_shape")
	frappe.reload_doc("consbiz", "doctype", "rebar_type")

	for shape in SHAPES:
		if not frappe.db.exists("Bar Shape", shape["shape_code"]):
			frappe.get_doc({"doctype": "Bar Shape", "is_standard": 1, **shape}).insert(
				ignore_permissions=True
			)

	for name, surface, diameter, grade, lengths in REBAR_TYPES:
		if not frappe.db.exists("Rebar Type", name):
			frappe.get_doc(
				{
					"doctype": "Rebar Type",
					"rebar_name": name,
					"surface": surface,
					"diameter": diameter,
					"grade": grade,
					"standard_lengths": lengths,
				}
			).insert(ignore_permissions=True)
