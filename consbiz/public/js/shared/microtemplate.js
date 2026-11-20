// Frappe microtemplate (frappe/public/js/frappe/microtemplate.js, หลัก John Resig, MIT) ตัดเหลือเท่าที่แม่แบบพิมพ์ทางการของ erpnext_thailand ใช้
// ใช้ render แม่แบบ query-report (pnd3, pnd53, sales/purchase tax report) นอก Desk ด้วย { data, filters } เหมือนที่ Desk ส่งให้
// ต้องคงตรรกะแปลง {% %} {%= %} {{ }} ให้ตรงของ Frappe เพื่อให้ผลพิมพ์เหมือน Desk

const compiled = {};
let counter = 0;

export function compile(str) {
	if (compiled[str]) return compiled[str];
	let s = str;
	// jinja style tags
	s = s.replace(/{{/g, "{%=").replace(/}}/g, "%}");
	s = s.replace(/{%\s?if\s?\s?not\s?([^\(][^%{]+)\s?%}/g, "{% if (! $1) { %}");
	s = s.replace(/{%\s?if\s?([^\(][^%{]+)\s?%}/g, "{% if ($1) { %}");
	s = s.replace(/{%\s?for\s([a-z._]+)\sin\s([a-z._]+)\s?%}/g, (_m, p1, p2) => {
		const i = `_i${counter++}`;
		const len = `_n${counter++}`;
		return `{% for (var ${i}=0, ${len}=${p2}.length; ${i}<${len}; ${i}++) { var ${p1} = ${p2}[${i}]; ${p1}._index = ${i}; %}`;
	});
	s = s.replace(/{%\s?endif\s?%}/g, "{% }; %}");
	s = s.replace(/{%\s?else\s?%}/g, "{% } else { %}");
	s = s.replace(/{%\s?endfor\s?%}/g, "{% }; %}");
	const fn_str =
		"var _p=[],print=function(){_p.push.apply(_p,arguments)};with(obj){\n_p.push('" +
		s
			.replace(/[\r\t\n]/g, " ")
			.split("{%")
			.join("\t")
			.replace(/((^|%})[^\t]*)'/g, "$1\r")
			.replace(/\t=(.*?)%}/g, "',$1,'")
			.split("\t")
			.join("');\n")
			.split("%}")
			.join("\n_p.push('")
			.split("\r")
			.join("\\'") +
		"');}return _p.join('');";
	compiled[str] = new Function("obj", fn_str);
	return compiled[str];
}

// helper ที่แม่แบบเรียกผ่านตัวแปรสากลของ Desk (ผ่านเฉพาะตอน render ไม่ทิ้งค่าในหน้าแอป)
const helpers = {
	frappe: { urllib: { get_full_url: (url) => new URL(url, location.origin).href } },
	__: (text, args) => (args ? String(text).replace(/{(\d+)}/g, (_m, i) => args[i]) : text),
};

export function render(str, ctx) {
	return compile(str)({ ...helpers, ...ctx });
}
