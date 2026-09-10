// Renders the subset of Markdown the copied README.md blocks use: h3, paragraph, fenced code,
// table, ordered list, unordered list, inline code, bold, link. The input is repository text, not
// anything a visitor supplies, and it is still escaped before any tag is added.

const ESCAPES = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' };

function escape(text) {
	return text.replace(/[&<>"]/g, (c) => ESCAPES[c]);
}

function inline(text) {
	return escape(text)
		.replace(/`([^`]+)`/g, '<code>$1</code>')
		.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
		.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2">$1</a>');
}

function tableRow(line) {
	return line
		.replace(/^\||\|$/g, '')
		.split('|')
		.map((cell) => cell.trim());
}

/**
 * @param {string} source Markdown.
 * @returns {string} HTML.
 */
export function render(source) {
	const lines = source.replace(/\r\n/g, '\n').split('\n');
	const out = [];
	let i = 0;

	while (i < lines.length) {
		const line = lines[i];

		if (line.trim() === '') {
			i += 1;
			continue;
		}

		if (line.startsWith('```')) {
			const lang = line.slice(3).trim();
			const body = [];
			i += 1;
			while (i < lines.length && !lines[i].startsWith('```')) {
				body.push(lines[i]);
				i += 1;
			}
			i += 1;
			const label = lang ? ` data-lang="${escape(lang)}"` : '';
			out.push(`<pre${label}><code>${escape(body.join('\n'))}</code></pre>`);
			continue;
		}

		if (line.startsWith('### ')) {
			out.push(`<h3>${inline(line.slice(4))}</h3>`);
			i += 1;
			continue;
		}

		if (line.startsWith('|') && lines[i + 1] && /^\|[\s:|-]+\|$/.test(lines[i + 1])) {
			const head = tableRow(line);
			i += 2;
			const body = [];
			while (i < lines.length && lines[i].startsWith('|')) {
				body.push(tableRow(lines[i]));
				i += 1;
			}
			const th = head.map((cell) => `<th scope="col">${inline(cell)}</th>`).join('');
			const tr = body
				.map((row) => `<tr>${row.map((cell) => `<td>${inline(cell)}</td>`).join('')}</tr>`)
				.join('');
			out.push(`<table><thead><tr>${th}</tr></thead><tbody>${tr}</tbody></table>`);
			continue;
		}

		const listMatch = /^(\d+)\.\s+|^-\s+/.exec(line);
		if (listMatch) {
			const ordered = /^\d/.test(line);
			const marker = ordered ? /^\d+\.\s+/ : /^-\s+/;
			const items = [];
			while (i < lines.length && marker.test(lines[i])) {
				const item = [lines[i].replace(marker, '')];
				i += 1;
				// A wrapped list item continues on an indented line.
				while (i < lines.length && /^\s{2,}\S/.test(lines[i])) {
					item.push(lines[i].trim());
					i += 1;
				}
				items.push(`<li>${inline(item.join(' '))}</li>`);
			}
			out.push(ordered ? `<ol>${items.join('')}</ol>` : `<ul>${items.join('')}</ul>`);
			continue;
		}

		// A paragraph runs to the blank line, or to the first line that opens another block. It always
		// takes its own first line, so the loop cannot stall on a line that starts with a marker
		// character without being a block of its own.
		const opensBlock = /^(\|\|?|```|### |\d+\.\s|-\s)/;
		const paragraph = [line.trim()];
		i += 1;
		while (i < lines.length && lines[i].trim() !== '' && !opensBlock.test(lines[i])) {
			paragraph.push(lines[i].trim());
			i += 1;
		}
		out.push(`<p>${inline(paragraph.join(' '))}</p>`);
	}

	return out.join('\n');
}
