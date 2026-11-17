# ไซต์ที่ติดตั้ง consbiz ใหม่ Frappe จะข้าม patch ทั้งหมด (บันทึกว่ารันแล้ว)
# จึงเรียก patch ที่สร้างข้อมูลมาตรฐานเองหลังติดตั้ง

from consbiz.patches import (
	create_concrete_item_group,
	seed_cost_categories,
	seed_bar_cut_masters,
	seed_more_bar_shapes,
	seed_more_rebar_types,
	seed_social_security_rates,
)


def after_install():
	seed_bar_cut_masters.execute()
	seed_more_bar_shapes.execute()
	seed_more_rebar_types.execute()
	seed_cost_categories.execute()
	seed_social_security_rates.execute()
	# ไซต์ที่ยังไม่ผ่าน setup wizard ไม่มีกลุ่มราก ข้ามไปได้ (สร้างกลุ่มเองทีหลัง)
	create_concrete_item_group.execute()
