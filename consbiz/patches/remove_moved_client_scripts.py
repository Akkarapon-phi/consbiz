# Client Script ที่ย้ายเข้าไฟล์ JS ของแอปแล้ว (DocType .js และ public/js ผ่าน doctype_js)
# ลบออกเพื่อไม่ให้โค้ดรันซ้ำสองชุด ถ้าโค้ดบนไซต์ไม่ตรงกับตอนที่ย้าย (มีคนแก้ทีหลัง)
# จะปิดไว้แทนการลบ เพื่อให้เทียบกับไฟล์แล้วย้ายส่วนที่แก้ตามมาได้

import hashlib

import frappe

# ชื่อ Client Script: md5 ของโค้ดตอนที่ย้าย
MOVED = {
	"BOQ Calulation": "1ff62b20b543a027d0b20c9ed4abe166",
	"Get Price History": "4d6f2fc9852eada959ac5fe0434ade90",
	"Employee Year of Joining": "8f21e14bd519a0475f92dd78c8f364d8",
	"Envelope Receiver Filter": "b4e50bc7f1488c1b4d00c2106fafd52f",
	"Letter In - Approval": "bb954ec89cfb54a08632d5d2ce53eb66",
	"Material Request Print": "5c7bf27294ad1fb45aa956a15487c830",
	"Material Request - Calulation": "8f80e54c0525e439ec286fbba9d756ef",
	"Material Request - Stepper": "14f0d5163d5bb0988241dcbda86e2dca",
	"Print Purchase Invoice": "99cc68a6de678d8c6293048939c2d027",
	"Purchase Invoice Is Cash": "3cef24e8f563d4493764a5d83e96e5db",
	"Print Purchase Order": "da5436e860ce05fa05f32a6b3044bb23",
	"FIx Retention Receivable Grand Total": "ee43d1894b141133b78545457c32af0d",
	"Print Sales Invoice": "75901d7f1cffbe2b27f365764a9d1fb6",
	"Sales Invoice Edit WHT-Rentention": "5831160e71e3ff1608f019fb2974e31b",
	"Transmittal Entry List CSS": "a0896c7d4ede3ea9fce02618fb969038",
	"Transmittal Ext Update Sent Date": "ece84fe0f9c73e7e4e5822a0e2698fc3",
	"Transmittal Ext Arrange": "87f614397457d5385e881d6682eb8168",
	"Transmittal Ext Import": "9d08b912d7ba0f793fb74274bee8fb7b",
}


def execute():
	for name, checksum in MOVED.items():
		script = frappe.db.get_value("Client Script", name, "script")
		if script is None:
			continue
		if hashlib.md5(script.encode()).hexdigest() == checksum:
			frappe.delete_doc("Client Script", name, ignore_permissions=True)
		else:
			frappe.db.set_value("Client Script", name, "enabled", 0)
			print(f"Client Script {name!r} differs from the moved code, disabled instead of deleted")
	frappe.clear_cache()
