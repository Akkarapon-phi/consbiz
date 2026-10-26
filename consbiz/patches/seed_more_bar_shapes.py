# เพิ่มรูปทรงการดัดเหล็กที่ใช้บ่อยต่อจาก seed_bar_cut_masters (ข้ามรหัสที่มีอยู่แล้ว ผู้ใช้แก้ต่อได้)
# - รหัสเป็นของ ConsBiz ไม่ใช่รหัส BS 8666 (รหัสเดิม 01, 12, 41, 51, 61 ความหมายไม่ตรงกับ BS)
# - ขอของปลอก/เหล็กรัดนับจุดดัดที่ขอด้วย (แบบปลอก 51) ขอปลายเหล็กแกนไม่นับ (แบบ 01)
# - ขอ 90° ของเหล็กแกนยื่น 12d ตาม ACI จึงเขียนในสูตรตรงๆ ส่วน hooks_90 ใช้กับขอปลอก

import frappe

LINE = 'fill="none" stroke="currentColor" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"'
DASH = 'fill="none" stroke="currentColor" stroke-width="1.5" stroke-dasharray="4 3"'


def svg(paths, labels, dashed=()):
	body = "".join(f'<path d="{d}" {LINE}/>' for d in paths)
	body += "".join(f'<path d="{d}" {DASH}/>' for d in dashed)
	body += "".join(
		f'<text data-dim="{dim}" x="{x}" y="{y}" text-anchor="middle" font-size="13" font-weight="600" '
		f'fill="currentColor">{dim}</text>'
		for dim, x, y in labels
	)
	return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 160 100">{body}</svg>'


SHAPES = [
	{
		"shape_code": "02",
		"shape_name": "เหล็กตรงงอขอ 180° ปลายเดียว",
		"dimensions": "A",
		"sides_formula": "A",
		"hooks_180": 1,
		"svg": svg(["M30,60 L130,60", "M30,60 A9,9 0 0 1 30,42 L38,42"], [("A", 80, 82)]),
	},
	{
		"shape_code": "14",
		"shape_name": "งอทำมุม (ไม่ใช่ 90°)",
		"dimensions": "A,B",
		"sides_formula": "A+B",
		"bends_45": 1,
		"svg": svg(["M15,75 L90,75 L140,25"], [("A", 52, 92), ("B", 126, 58)]),
	},
	{
		"shape_code": "15",
		"shape_name": "เหล็กตรงงอขอ 90° ปลายเดียว (12d)",
		"dimensions": "A",
		"sides_formula": "A+12*d",
		"bends_90": 1,
		"svg": svg(["M20,70 L140,70 L140,40"], [("A", 80, 88)]),
	},
	{
		"shape_code": "16",
		"shape_name": "เหล็กตรงงอขอ 90° สองปลาย (12d)",
		"dimensions": "A",
		"sides_formula": "A+24*d",
		"bends_90": 2,
		"svg": svg(["M20,40 L20,70 L140,70 L140,40"], [("A", 80, 88)]),
	},
	{
		"shape_code": "22",
		"shape_name": "ตัว U ปลายงอขอ 180° สองปลาย",
		"dimensions": "A,B,C",
		"sides_formula": "A+B+C",
		"bends_90": 2,
		"hooks_180": 2,
		"svg": svg(
			[
				"M35,30 L35,75 L125,75 L125,30",
				"M35,30 A9,9 0 0 1 53,30 L53,38",
				"M125,30 A9,9 0 0 0 107,30 L107,38",
			],
			[("A", 20, 56), ("B", 80, 94), ("C", 140, 56)],
		),
	},
	{
		"shape_code": "23",
		"shape_name": "ตัว Z (งอฉากสลับทิศ)",
		"dimensions": "A,B,C",
		"sides_formula": "A+B+C",
		"bends_90": 2,
		"svg": svg(["M15,25 L70,25 L70,75 L145,75"], [("A", 42, 17), ("B", 84, 54), ("C", 108, 92)]),
	},
	{
		"shape_code": "24",
		"shape_name": "ตัว Z ทำมุม (เหล็กบันได)",
		"dimensions": "A,B,C",
		"sides_formula": "A+B+C",
		"bends_45": 2,
		"svg": svg(["M15,80 L55,80 L105,25 L145,25"], [("A", 35, 95), ("B", 92, 62), ("C", 125, 17)]),
	},
	{
		"shape_code": "25",
		"shape_name": "ลูกผม (Hairpin) ขาเท่ากัน",
		"dimensions": "A,B",
		"sides_formula": "2*A+B",
		"bends_90": 2,
		"svg": svg(["M140,25 L35,25 L35,75 L140,75"], [("A", 88, 17), ("B", 20, 54)]),
	},
	{
		"shape_code": "32",
		"shape_name": "ขาเก้าอี้ / ตัวหมวก (Chair)",
		"dimensions": "A,B,C",
		"sides_formula": "A+2*B+2*C",
		"bends_90": 4,
		"svg": svg(
			["M10,80 L42,80 L42,25 L118,25 L118,80 L150,80"],
			[("A", 80, 17), ("B", 28, 56), ("C", 26, 96)],
		),
	},
	{
		"shape_code": "42",
		"shape_name": "คอม้าสองข้าง (Bent-up bar)",
		"dimensions": "A,B,C",
		"sides_formula": "2*A+2*B+C",
		"bends_45": 4,
		"svg": svg(
			["M8,25 L40,25 L65,75 L95,75 L120,25 L152,25"], [("A", 24, 17), ("B", 42, 58), ("C", 80, 92)]
		),
	},
	{
		"shape_code": "43",
		"shape_name": "คอม้าทาบเสา 1:6 (กรอกระยะเยื้อง)",
		"dimensions": "A,B,C",
		"sides_formula": "A+B*sqrt(37)+C",
		"svg": svg(
			["M12,72 L60,72 L100,40 L148,40"],
			[("A", 36, 90), ("B", 110, 62), ("C", 124, 32)],
			dashed=["M100,40 L100,72"],
		),
	},
	{
		"shape_code": "44",
		"shape_name": "คอม้า (กรอกระยะเยื้องและมุม)",
		"dimensions": "A,B,C,T",
		"sides_formula": "A+B/sin(T)+C",
		"bends_45": 2,
		"svg": svg(
			["M12,75 L60,75 L95,30 L148,30"],
			[("A", 36, 92), ("B", 106, 58), ("T", 82, 70), ("C", 122, 22)],
			dashed=["M95,30 L95,75", "M60,75 L95,75"],
		),
	},
	{
		"shape_code": "45",
		"shape_name": "คอม้าสองข้าง ไม่สมมาตร",
		"dimensions": "A,B,C,D,E",
		"sides_formula": "A+B+C+D+E",
		"bends_45": 4,
		"svg": svg(
			["M8,25 L40,25 L65,75 L95,75 L120,25 L152,25"],
			[("A", 24, 17), ("B", 42, 58), ("C", 80, 92), ("D", 118, 58), ("E", 136, 17)],
		),
	},
	{
		"shape_code": "46",
		"shape_name": "รูปทรง 6 ด้าน (งอฉาก 5 จุด)",
		"dimensions": "A,B,C,D,E,F",
		"sides_formula": "A+B+C+D+E+F",
		"bends_90": 5,
		"svg": svg(
			["M35,15 L35,85 L80,85 L80,55 L115,55 L115,25 L150,25"],
			[("A", 22, 52), ("B", 58, 97), ("C", 68, 74), ("D", 98, 70), ("E", 104, 44), ("F", 134, 17)],
		),
	},
	{
		"shape_code": "52",
		"shape_name": "ปลอกตัว U แบบเปิด ขอ 135°",
		"dimensions": "A,B",
		"sides_formula": "A+2*B",
		"bends_90": 2,
		"bends_135": 2,
		"hooks_135": 2,
		"svg": svg(
			["M40,20 L40,80 L120,80 L120,20", "M40,20 L54,34", "M120,20 L106,34"], [("B", 25, 52), ("A", 80, 94)]
		),
	},
	{
		"shape_code": "53",
		"shape_name": "เหล็กรัดขวาง (Cross tie) ขอ 135° สองปลาย",
		"dimensions": "A",
		"sides_formula": "A",
		"bends_135": 2,
		"hooks_135": 2,
		"svg": svg(["M30,55 L130,55", "M30,55 L44,41", "M130,55 L116,41"], [("A", 80, 75)]),
	},
	{
		"shape_code": "54",
		"shape_name": "ปลอกเพชร (Diamond tie)",
		"dimensions": "A",
		"sides_formula": "4*A",
		"bends_90": 3,
		"bends_135": 2,
		"hooks_135": 2,
		"svg": svg(
			["M80,10 L122,50 L80,90 L38,50 Z", "M80,10 L80,30", "M80,10 L96,22"], [("A", 112, 82)]
		),
	},
	{
		"shape_code": "55",
		"shape_name": "ปลอกสี่เหลี่ยม ขอ 90°",
		"dimensions": "A,B",
		"sides_formula": "2*(A+B)",
		"bends_90": 5,
		"hooks_90": 2,
		"svg": svg(
			["M42,28 L118,28 L118,80 L42,80 L42,28", "M48,34 L48,52", "M48,34 L66,34"],
			[("A", 80, 20), ("B", 136, 58)],
		),
	},
	{
		"shape_code": "56",
		"shape_name": "เหล็กรัดขวาง ขอ 135° + 90°",
		"dimensions": "A",
		"sides_formula": "A",
		"bends_90": 1,
		"bends_135": 1,
		"hooks_90": 1,
		"hooks_135": 1,
		"svg": svg(["M30,55 L130,55", "M30,55 L44,41", "M130,55 L130,37"], [("A", 80, 75)]),
	},
	{
		"shape_code": "63",
		"shape_name": "ปลอกวงกลมแบบทาบ",
		"dimensions": "A,B",
		"sides_formula": "pi*(A-d)+B",
		"svg": svg(
			["M80,16 A36,36 1 1 0 116,52", "M80,9 A43,43 0 0 1 123,52"],
			[("A", 80, 68), ("B", 128, 22)],
			dashed=["M44,52 L116,52"],
		),
	},
	{
		"shape_code": "64",
		"shape_name": "ปลอกเกลียว (Spiral)",
		"dimensions": "A,B,N",
		"sides_formula": "N*sqrt((pi*(A-d))**2+B**2)",
		"svg": svg(
			["M40,12 L120,22 L40,32 L120,42 L40,52 L120,62 L40,72"],
			[("A", 80, 96), ("B", 140, 37), ("N", 22, 46)],
			dashed=["M40,82 L120,82", "M126,22 L136,22 M126,42 L136,42"],
		),
	},
	{
		"shape_code": "67",
		"shape_name": "เหล็กโค้ง (กรอกความยาวโค้ง)",
		"dimensions": "A",
		"sides_formula": "A",
		"svg": svg(["M20,80 Q80,10 140,80"], [("A", 80, 38)]),
	},
	{
		"shape_code": "68",
		"shape_name": "เหล็กโค้ง (กรอกรัศมีและมุม)",
		"dimensions": "R,T",
		"sides_formula": "pi*R*T/180",
		"svg": svg(
			["M31,41 A70,70 0 0 1 129,41"],
			[("R", 46, 72), ("T", 80, 80)],
			dashed=["M80,92 L31,41", "M80,92 L129,41"],
		),
	},
]


def execute():
	frappe.reload_doc("consbiz", "doctype", "bar_shape")

	for shape in SHAPES:
		if not frappe.db.exists("Bar Shape", shape["shape_code"]):
			frappe.get_doc({"doctype": "Bar Shape", "is_standard": 1, **shape}).insert(
				ignore_permissions=True
			)
