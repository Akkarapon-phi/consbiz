// Print the displayed values (already formatted and escaped by Vue) in an isolated A4 document.
export function tax_print(table, title, period, scope) {
	const doc = document.implementation.createHTMLDocument(title);
	doc.documentElement.lang = "th";
	const style = doc.createElement("style");
	style.textContent = `
		@font-face { font-family: "ConsBiz Print"; font-weight: 100 900;
			src: url("/assets/consbiz/fonts/noto-sans-thai/NotoSansThai-Variable-latin.woff2"); }
		@font-face { font-family: "ConsBiz Print"; font-weight: 100 900; unicode-range: U+0E00-0E7F;
			src: url("/assets/consbiz/fonts/noto-sans-thai/NotoSansThai-Variable-thai.woff2"); }
		@page { size: A4 landscape; margin: 12mm; }
		* { box-sizing: border-box; }
		body { margin: 0; background: white; color: #17233f; font: 10pt/1.5 "ConsBiz Print", sans-serif; }
		h1 { font-size: 18pt; margin: 0; }
		p { margin: 1mm 0 6mm; }
		table { width: 100%; border-collapse: collapse; }
		th, td { padding: 2mm; border-bottom: 1px solid #ccd2da; text-align: left; overflow-wrap: anywhere; }
		th { border-block: 1px solid #778294; }
		.is-num { text-align: right; white-space: nowrap; font-variant-numeric: tabular-nums; }
		tr { break-inside: avoid; }
		@media screen { body { padding: 12mm; min-height: 210mm; } }
	`;
	doc.head.append(style);
	const heading = doc.createElement("h1");
	heading.textContent = title;
	const subtitle = doc.createElement("p");
	subtitle.textContent = [period, scope].join(" · ");
	const copy = table.cloneNode(true);
	copy.querySelectorAll(".col-modified").forEach((cell) => cell.remove());
	doc.body.append(heading, subtitle, copy);
	return "<!doctype html>" + doc.documentElement.outerHTML;
}
