// Copyright (c) 2026, Siricons and contributors
// For license information, please see license.txt

// ---- ย้ายจาก Client Script "Transmittal Entry List CSS" ----

frappe.listview_settings["Transmittal Entry"] = {
	refresh: function (listview) {
		document.querySelectorAll(".list-row-col").forEach(function (col) {
			col.style.minWidth = "100px";
			col.style.maxWidth = "200px";
		});
		document.querySelectorAll(".list-subject").forEach(function (col) {
			col.style.minWidth = "200px";
			col.style.maxWidth = "200px";
		});
		document.querySelectorAll(".list-row-col.receipt").forEach(function (col) {
			col.style.width = "80px";
			col.style.minWidth = "80px";
			col.style.maxWidth = "80px";
			col.style.flex = "0 0 80px";
		});
		document.querySelectorAll(".list-row-col.custom_receipt_check").forEach(function (col) {
			col.style.width = "80px";
			col.style.minWidth = "80px";
			col.style.maxWidth = "80px";
			col.style.flex = "0 0 80px";
		});
		document.querySelectorAll(".list-row-col.tax").forEach(function (col) {
			col.style.width = "80px";
			col.style.minWidth = "80px";
			col.style.maxWidth = "80px";
			col.style.flex = "0 0 80px";
		});
		document.querySelectorAll(".list-row-col.custom_tax_check").forEach(function (col) {
			col.style.width = "80px";
			col.style.minWidth = "80px";
			col.style.maxWidth = "80px";
			col.style.flex = "0 0 80px";
		});
		document.querySelectorAll(".list-row-col.wht").forEach(function (col) {
			col.style.width = "80px";
			col.style.minWidth = "80px";
			col.style.maxWidth = "80px";
			col.style.flex = "0 0 80px";
		});
		document.querySelectorAll(".list-row-col.custom_wht_check").forEach(function (col) {
			col.style.width = "80px";
			col.style.minWidth = "80px";
			col.style.maxWidth = "80px";
			col.style.flex = "0 0 80px";
		});
		document.querySelectorAll(".list-row-col.retention").forEach(function (col) {
			col.style.width = "80px";
			col.style.minWidth = "80px";
			col.style.maxWidth = "80px";
			col.style.flex = "0 0 80px";
		});
		document.querySelectorAll(".list-row-col.custom_retention_check").forEach(function (col) {
			col.style.width = "80px";
			col.style.minWidth = "80px";
			col.style.maxWidth = "80px";
			col.style.flex = "0 0 80px";
		});
	},
};
