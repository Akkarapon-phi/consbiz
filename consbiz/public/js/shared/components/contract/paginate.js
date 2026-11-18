// แบ่งสัญญาจ้างเป็นแผ่น A4 (ตกลง 2026-11-18) ชุดเดียวใช้ 2 ที่ ห้ามใช้ import / ตัวแปรภายนอก:
// - ตัวอย่างในแอป (ContractPreview.vue เรียกกับ document ของ iframe, guides = เส้นประขอบพื้นที่พิมพ์)
// - PDF / หน้าพิมพ์ (consbiz/contract_terms.py ฝังโค้ดไฟล์นี้ในหน้า ตัด "export " ออก เรียกตอน load ก่อน Chrome พิมพ์)
// ต้นฉบับใน #ec-src (data-page / data-margins เป็น มม.): .ec-src-head หัวกระดาษ, .ec-src-foot ท้ายกระดาษทุกหน้า,
// .ec-src-foot-last ท้ายกระดาษหน้าสุดท้าย (นายจ้าง/พยาน สูงกว่าได้), .ec-main เนื้อหา
// เนื้อหาไหลเป็นคอลัมน์สูงเท่าพื้นที่เนื้อหาของ 1 หน้า (Chrome ตัดย่อหน้า/break-inside แบบเดียวกับตอนพิมพ์)
// แล้วแสดงคอลัมน์ที่ i ในแผ่นที่ i ท้ายเนื้อหามีที่ว่างเท่าส่วนที่ท้ายกระดาษหน้าสุดท้ายสูงกว่า (ไม่พอ = ขึ้นแผ่นใหม่)
export function ec_paginate(doc, options) {
	var opts = options || {};
	var MM = 96 / 25.4;
	var GAP = 40;
	var src = doc.getElementById("ec-src");
	var pages = doc.getElementById("ec-pages");
	if (!src || !pages) return 0;
	var size = (src.getAttribute("data-page") || "210 297").split(" ").map(Number);
	var m = (src.getAttribute("data-margins") || "25 20 20 30").split(" ").map(Number);
	var t = m[0], r = m[1], b = m[2], l = m[3];
	var w = (size[0] - l - r) * MM;
	var h = (size[1] - t - b) * MM;
	var html = function (sel) {
		var el = src.querySelector(sel);
		return el ? el.innerHTML : "";
	};
	var probe = doc.createElement("div");
	probe.style.cssText = "position:absolute;left:-99999px;top:0;width:" + w + "px";
	doc.body.appendChild(probe);
	var part = function (content) {
		if (!content) return null;
		var el = doc.createElement("div");
		el.className = "ec-doc";
		el.style.display = "flow-root";
		el.innerHTML = content;
		probe.appendChild(el);
		return el;
	};
	var head = part(html(".ec-src-head"));
	var foot = part(html(".ec-src-foot"));
	var foot_last = part(html(".ec-src-foot-last")) || foot;
	// ตัวอย่างในแอปย่อทั้งหน้าด้วย CSS zoom: getBoundingClientRect ได้ขนาดหลังย่อ แต่ความสูงที่ตั้งเป็น px ไม่ถูกย่อ
	// หารด้วยอัตราย่อ (กว้างจริงของ probe ÷ กว้างที่ตั้ง) ไม่งั้นหัว/ท้ายกระดาษเตี้ยลง เนื้อหาต่อหน้ามากกว่า PDF
	var scale = probe.getBoundingClientRect().width / w || 1;
	var height = function (el) {
		return el ? el.getBoundingClientRect().height / scale : 0;
	};
	var head_h = height(head);
	var foot_h = height(foot);
	var extra = Math.max(0, height(foot_last) - foot_h);
	var body_h = Math.max(80, h - head_h - foot_h);

	var flow = doc.createElement("div");
	flow.className = "ec-doc ec-flow";
	flow.style.cssText =
		"width:" + w + "px;height:" + body_h + "px;column-width:" + w + "px;column-gap:" + GAP + "px;column-fill:auto";
	flow.innerHTML = html(".ec-main") + (extra ? '<div class="ec-last-room" style="height:' + extra + 'px"></div>' : "");
	var box = doc.createElement("div");
	box.style.cssText = "width:" + w + "px;height:" + body_h + "px;overflow:hidden";
	box.appendChild(flow);
	probe.appendChild(box);
	var count = Math.max(1, Math.round((flow.scrollWidth + GAP) / (w + GAP)));
	probe.remove();

	var place = function (el, css) {
		el.style.cssText += ";position:absolute;left:0;right:0;" + css;
		return el;
	};
	var sheets = [];
	for (var i = 0; i < count; i++) {
		var is_last = i === count - 1;
		var sheet = doc.createElement("div");
		sheet.className = "ec-sheet";
		var area = doc.createElement("div");
		area.className = "ec-sheet-area";
		area.style.cssText =
			"position:absolute;overflow:hidden;top:" + t + "mm;left:" + l + "mm;width:" + w + "px;height:" + h + "px";
		if (head) area.appendChild(place(head.cloneNode(true), "top:0"));
		var view = doc.createElement("div");
		place(view, "top:" + head_h + "px;height:" + body_h + "px;overflow:hidden");
		var copy = flow.cloneNode(true);
		copy.style.position = "absolute";
		copy.style.transform = "translateX(" + -i * (w + GAP) + "px)";
		view.appendChild(copy);
		area.appendChild(view);
		var f = is_last ? foot_last : foot;
		if (f) {
			var el = place(f.cloneNode(true), "bottom:0");
			el.querySelectorAll(".page").forEach(function (x) {
				x.textContent = i + 1;
			});
			el.querySelectorAll(".topage").forEach(function (x) {
				x.textContent = count;
			});
			area.appendChild(el);
		}
		if (opts.guides) {
			var guide = doc.createElement("div");
			guide.className = "ec-sheet-guide";
			guide.style.cssText =
				"position:absolute;pointer-events:none;top:" + t + "mm;left:" + l + "mm;width:" + w + "px;height:" + h + "px";
			sheet.appendChild(guide);
		}
		sheet.appendChild(area);
		sheets.push(sheet);
	}
	pages.innerHTML = "";
	sheets.forEach(function (s) {
		pages.appendChild(s);
	});
	return count;
}
