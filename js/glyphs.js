// The manuscript file and its pages, in EVA or in the Voynich-like script (the program's own font).
// Compound signs are separate glyphs in the font, at private code points: same mapping as carattere.in_segni.
const COMPOUNDS = ['cth', 'ckh', 'cph', 'cfh', 'ch', 'sh'];
const CODE = Object.fromEntries(COMPOUNDS.map((u, i) => [u, String.fromCharCode(0xE000 + i)]));

export function toGlyphs(word) {
  let out = '';
  let i = 0;
  while (i < word.length) {
    const u = COMPOUNDS.find((c) => word.startsWith(c, i));
    if (u) { out += CODE[u]; i += u.length; } else { out += word[i]; i += 1; }
  }
  return out;
}

// [{folio, lines: [{para, words}]}] from the text of a manuscript file (<folio.line> words.separated.by.dots)
export function parseManuscript(text) {
  const pages = new Map();
  for (let line of text.split(/\r?\n/)) {
    line = line.trim();
    if (!line || line.startsWith('#')) continue;
    const m = line.match(/^(@?)<([^>]+)\.\d+>\s*(.*)$/);
    if (!m) continue;
    if (!pages.has(m[2])) pages.set(m[2], []);
    pages.get(m[2]).push({ para: m[1] === '@', words: m[3].split('.').filter(Boolean) });
  }
  return [...pages].map(([folio, lines]) => ({ folio, lines }));
}

// Writes one page into el: one line per manuscript line, a half-line gap before each paragraph, the type size chosen
// so that most lines fit the width (the few much longer lines are set smaller), as in the PDF.
export function renderPage(el, page, mode = 'script') {
  el.replaceChildren();
  el.classList.toggle('eva', mode === 'eva');
  const box = document.createElement('div');
  box.className = 'lines';
  el.append(box);
  const spans = page.lines.map((l, i) => {
    const d = document.createElement('div');
    d.className = 'line' + (l.para && i > 0 ? ' para' : '');
    const s = document.createElement('span');
    s.textContent = mode === 'eva' ? l.words.join('.') : l.words.map(toGlyphs).join(' ');
    d.append(s);
    box.append(d);
    return s;
  });
  const label = document.createElement('div');
  label.className = 'folio-label';
  label.textContent = page.folio;
  el.append(label);
  fit(el, box, spans);
}

function fit(el, box, spans) {
  const base = 20;
  box.style.fontSize = base + 'px';
  const widths = spans.map((s) => s.getBoundingClientRect().width || 1);
  const sorted = [...widths].sort((a, b) => a - b);
  const w85 = sorted[Math.floor(0.85 * (sorted.length - 1))] || 1;
  const avail = box.clientWidth;
  const gaps = spans.filter((s) => s.parentElement.classList.contains('para')).length * 0.5;
  const availH = el.clientHeight * 0.86;
  const lineH = 1.75;
  const size = Math.min(15 * 1.6, base * avail / w85, availH / ((spans.length + gaps) * lineH));
  box.style.fontSize = size.toFixed(2) + 'px';
  spans.forEach((s, i) => {
    const own = base * avail / widths[i];
    s.style.fontSize = own < size ? (own / size).toFixed(3) + 'em' : '';
  });
}
