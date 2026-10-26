# ไซต์ที่ติดตั้ง consbiz ใหม่ Frappe จะข้าม patch ทั้งหมด (บันทึกว่ารันแล้ว)
# จึงเรียก patch ที่สร้างข้อมูลมาตรฐานเองหลังติดตั้ง

from consbiz.patches import (
	seed_bar_cut_masters,
	seed_more_bar_shapes,
	seed_more_rebar_types,
)


def after_install():
	seed_bar_cut_masters.execute()
	seed_more_bar_shapes.execute()
	seed_more_rebar_types.execute()
