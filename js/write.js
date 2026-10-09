// The Write page: text and key in, manuscript out, with the scribe at work in between.
import { prepare, call, reset } from './engine.js';
import { Scribe } from './scribe.js';
import { parseManuscript, renderPage } from './glyphs.js';
import { loadAssets, layout, drawPage, makePdf as bookPdf, PAGE } from './book.js';
import { $, CAPACITY, CAPACITY_MAX, minutes, showKey, error, LOADING, explain } from './common.js';

const PAGES = 207;
// share of the writing time spent in each phase (measured: model 9 s, words 7 s, lines 87 s, check 2 s out of 107)
const SHARE = { choose: [0, 0.08], arrange: [0.08, 0.96], check: [0.96, 1] };

let scribe = null;
let busy = false;
let book = null;              // {manuscript, pages, txtUrl, pdfUrl}
let mode = 'script';
let shown = 0;

showKey($('show-key'), $('key'));
if (matchMedia('(pointer: coarse)').matches && Math.min(screen.width, screen.height) < 700) $('mobile-note').hidden = false;

// ---------------------------------------------------------------- the real folios (Yale photographs)
const YALE = 'https://collections.library.yale.edu/catalog/2002046?child_oid=';
let folios = null;
const folioMap = () => folios || (folios = fetch('img/folios/folios.json').then((r) => r.json()).catch(() => ({})));
let deskShown = '';
let deskTime = 0;
async function deskFolio(page) {
  // the real folio the program is working on, at most one new photograph every 2.5 s
  const now = performance.now();
  if (page === deskShown || now - deskTime < 2500) return;
  const map = await folioMap();
  if (!map[page]) return;
  deskShown = page;
  deskTime = now;
  $('desk-img').src = 'img/folios/' + page + '.jpg';
  $('desk-cap').textContent = page;
  $('desk-real').hidden = false;
}
async function realFolio(page) {
  const map = await folioMap();
  const f = map[page];
  $('real').hidden = !f;
  if (!f) return;
  $('real-img').src = 'img/folios/' + page + '.jpg';
  $('real-img').alt = 'Folio ' + page + ' of the Voynich manuscript (Beinecke MS 408)';
  $('real-link').href = YALE + f[1];
  $('real-cap').textContent = page;
}

// Start fetching Python as soon as someone begins to write: by the time they press the button, it is ready.
const warm = () => prepare().then(() => { engineReady = true; if ($('text').value) estimate(); }).catch(() => {});
$('text').addEventListener('focus', warm, { once: true });
$('key').addEventListener('focus', warm, { once: true });

// ---------------------------------------------------------------- how much of the book the text fills (estimate)
let estimateTimer = 0;
$('text').addEventListener('input', () => {
  clearTimeout(estimateTimer);
  estimateTimer = setTimeout(estimate, 300);
});
// The limit is in bits, not characters: the text becomes UTF-8 bytes, is compressed with zlib (level 9) and framed
// with 12 bytes; a book carries about 80,000-86,000 bits (81,100-85,900 over the paper's 24 keys), depending on the key
// and slightly on the message. Once the program has loaded, the size is
// computed exactly with the program's own zlib; before, it is estimated with the browser's compressor.
const HINT = 'The limit is in bits, not characters: about 10,000 bytes once compressed, i.e. roughly 20,000 ' +
  'characters of ordinary prose, more if the text is repetitive, fewer in scripts that take more bytes per character.';
let engineReady = false;
async function estimate() {
  const text = $('text').value;
  const hint = $('text-hint');
  if (!text) { hint.textContent = HINT; hint.classList.remove('bad'); return; }
  const n = (x) => Number(x).toLocaleString('en');
  const chars = [...text].length;
  let utf8 = new TextEncoder().encode(text).length;
  let compressed = null;
  let exact = false;
  if (engineReady) {
    try { ({ utf8, compressed } = await call('need', { text })); exact = true; } catch (e) { /* fall back */ }
  }
  if (compressed === null) {
    try {
      const s = new Blob([text]).stream().pipeThrough(new CompressionStream('deflate'));
      compressed = (await new Response(s).arrayBuffer()).byteLength;
    } catch (e) { compressed = utf8; }
  }
  if (text !== $('text').value) return;          // the text changed meanwhile
  const bits = 8 * (12 + compressed);
  const share = bits / CAPACITY;
  hint.textContent = n(chars) + ' characters · ' + n(utf8) + ' bytes in UTF-8 · ' + (exact ? '' : 'about ') + n(compressed) +
    ' bytes compressed → ' + (exact ? '' : 'about ') + n(bits) + ' bits, ' + Math.max(1, Math.round(100 * share)) +
    '% of the roughly 80,000–86,000 bits a book carries' +
    (bits > CAPACITY_MAX ? ': too long, please shorten it' : bits > CAPACITY ? ': it may not fit, depending on the key' : '');
  hint.classList.toggle('bad', bits > CAPACITY);
}

// ---------------------------------------------------------------- writing
$('form').addEventListener('submit', async (e) => {
  e.preventDefault();
  if (busy) return;
  const empty = $('empty').checked;
  const text = $('text').value;
  const key = $('key').value;
  if (!empty && !text.trim()) return error($('error'), 'Write a text first, or choose a book with no message.');
  if (key.length < 8) return error($('error'), 'The key is too short: use at least 8 characters; a long random passphrase (six random words or twelve random characters) is much better.');
  error($('error'), '');
  await write(empty ? null : text, key, $('want-pdf').checked);
});

async function write(text, key, wantPdf) {
  busy = true;
  window.addEventListener('beforeunload', hold);
  $('form').hidden = true;
  $('result').hidden = true;
  $('scriptorium').hidden = false;
  $('scriptorium').scrollIntoView({ behavior: 'smooth', block: 'center' });
  if (!scribe) scribe = new Scribe($('desk'));
  scribe.setFolio('f1r');
  $('desk-real').hidden = true;
  deskShown = '';
  await document.fonts.load('16px "Voynichizer EVA"');
  scribe.start();
  setBar(0);
  const t0 = performance.now();
  try {
    const info = await prepare((m) => { if (m.phase === 'load') caption(LOADING[m.step] || ''); });
    if (text !== null) {
      caption('The scribe reads your text…');
      const { bits } = await call('bits', { text, key });
      if (bits > CAPACITY_MAX) {
        throw new Error('too long for this book: it needs ' + bits.toLocaleString('en') + ' bits, a book carries about 80,000 to ' +
          '86,000 depending on the key (shorten it by about ' + Math.ceil(100 * (1 - CAPACITY / bits)) + '%)');
      }
      if (bits > CAPACITY) caption('A long text: whether it fits depends on the key. The scribe will know in a minute…');
    }
    const count = { choose: 0, arrange: 0, check: 0 };
    const started = {};
    let arrangeStart = 0;
    const t1 = performance.now();
    const out = await call('encode', { text, key }, (m) => {
      if (!(m.phase in count)) return;
      const i = ++count[m.phase];
      if (i === 1) started[m.phase] = performance.now();
      if (m.phase === 'arrange' && i === 1) arrangeStart = performance.now();
      scribe.setFolio(m.page);
      if (m.phase !== 'check') deskFolio(m.page);
      caption(m.phase === 'choose' ? 'Choosing the words of folio ' + m.page
        : m.phase === 'arrange' ? 'Writing folio ' + m.page
          : 'Proofreading: reading your text back');
      const [a, b] = SHARE[m.phase];
      setBar(a + (b - a) * Math.min(1, i / PAGES));
      let left = '';
      if (m.phase === 'arrange' && i >= 8) {
        const rate = (performance.now() - arrangeStart) / i;
        left = ' · about ' + minutes(rate * (PAGES - i) + 0.06 * rate * PAGES) + ' left';
      }
      $('meta').textContent = 'Folio ' + Math.min(i, PAGES) + ' of ' + PAGES + ' · ' + minutes(performance.now() - t0) + left;
    });
    setBar(1);
    started.end = performance.now();
    started.start = t1;
    finish(out, info, wantPdf, performance.now() - t1, started);
  } catch (err) {
    stopWriting();
    $('scriptorium').hidden = true;
    $('form').hidden = false;
    error($('error'), explain(err.message));
  }
}

function hold(e) { e.preventDefault(); e.returnValue = ''; }

function stopWriting() {
  busy = false;
  window.removeEventListener('beforeunload', hold);
  if (scribe) scribe.stop();
}

$('cancel').addEventListener('click', () => {
  reset();
  stopWriting();
  $('scriptorium').hidden = true;
  $('form').hidden = false;
});

function caption(t) { if (t) $('caption').textContent = t; }
function setBar(f) {
  $('bar').style.width = (100 * f).toFixed(1) + '%';
  $('progress').setAttribute('aria-valuenow', String(Math.round(100 * f)));
}

// ---------------------------------------------------------------- the finished book
function finish(out, info, wantPdf, ms, started) {
  stopWriting();
  if (book) { URL.revokeObjectURL(book.txtUrl); if (book.pdfUrl) URL.revokeObjectURL(book.pdfUrl); }
  const pages = parseManuscript(out.manuscript);
  const lines = pages.reduce((n, p) => n + p.lines.length, 0);
  book = { manuscript: out.manuscript, pages, txtUrl: URL.createObjectURL(new Blob([out.manuscript], { type: 'text/plain' })), pdfUrl: null };
  const i = out.info;
  const used = i.bit_messaggio
    ? 'Your text takes ' + i.bit_messaggio.toLocaleString('en') + ' of the ' + i.capacita_bit.toLocaleString('en') +
      ' bits the book carries (' + Math.max(1, Math.round(100 * i.bit_messaggio / i.capacita_bit)) + '%); the rest is ' +
      'filler, so nobody can see where the message ends.'
    : 'A book with no message: every word is filler.';
  $('summary').textContent = pages.length + ' pages, ' + lines.toLocaleString('en') + ' lines, written in ' + minutes(ms) +
    ' with version ' + info.version + '. ' + used;
  $('dl-txt').href = book.txtUrl;
  technical(out, info, pages, started);
  fileNames(out.manuscript).then((stem) => {
    $('dl-txt').download = stem + '.txt';
    $('dl-pdf').download = stem + '.pdf';
    $('txt-name').textContent = 'Its name: ' + stem + '.txt; the PDF has the same name, so that the two stay paired.';
  });
  $('folio').replaceChildren(...pages.map((p, k) => new Option(p.folio, String(k))));
  $('scriptorium').hidden = true;
  $('result').hidden = false;
  show(0);
  $('result').scrollIntoView({ behavior: 'smooth', block: 'start' });
  $('pdf-row').hidden = !wantPdf;
  $('dl-pdf').hidden = true;
  if (wantPdf) makePdf(book);
}

// sections of the folios (H herbal, S recipes, B biological, P pharmaceutical, C cosmological, A astronomical, T text)
let sections = null;
const sectionMap = () => sections || (sections = fetch('book/sections.json').then((r) => r.json()));

async function makePdf(b) {
  $('pdf-note').textContent = 'Binding the book…';
  try {
    const blob = await bookPdf(b.pages, await sectionMap(), (n, tot) => {
      if (b === book) $('pdf-note').textContent = 'Binding the book: page ' + n + ' of ' + tot + '…';
    });
    if (b !== book) return;
    b.pdfUrl = URL.createObjectURL(blob);
    $('dl-pdf').href = b.pdfUrl;
    $('dl-pdf').hidden = false;
    $('pdf-note').textContent = b.pages.length + ' pages, ' + (blob.size / 1048576).toFixed(1) +
      ' MB, with real drawings of the Voynich (not generated). For looking at, not for reading back.';
  } catch (err) {
    $('pdf-note').textContent = 'The PDF could not be made: ' + err.message;
  }
}

function show(k) {
  if (!book) return;
  shown = Math.max(0, Math.min(book.pages.length - 1, k));
  $('folio').value = String(shown);
  const page = book.pages[shown];
  if (mode === 'eva') {
    $('page').classList.remove('illustrated');
    renderPage($('page'), page, 'eva');
  } else {
    drawIllustrated(page);
  }
  realFolio(page.folio);
}
$('prev').addEventListener('click', () => show(shown - 1));
$('next').addEventListener('click', () => show(shown + 1));
$('folio').addEventListener('change', () => show(Number($('folio').value)));
for (const [id, m] of [['mode-script', 'script'], ['mode-eva', 'eva']]) {
  $(id).addEventListener('click', () => {
    mode = m;
    $('mode-script').setAttribute('aria-pressed', String(m === 'script'));
    $('mode-eva').setAttribute('aria-pressed', String(m === 'eva'));
    show(shown);
  });
}
let resizeTimer = 0;
addEventListener('resize', () => { clearTimeout(resizeTimer); resizeTimer = setTimeout(() => show(shown), 200); });
$('again').addEventListener('click', () => {
  $('result').hidden = true;
  $('form').hidden = false;
  $('form').scrollIntoView({ behavior: 'smooth' });
});

// ---------------------------------------------------------------- technical details of the book just written
async function technical(out, info, pages, t) {
  const i = out.info;
  const n = (x) => Number(x).toLocaleString('en');
  const s = (a, b) => (a && b ? ((b - a) / 1000).toFixed(1) + ' s' : '–');
  const words = pages.reduce((k, p) => k + p.lines.reduce((m, l) => m + l.words.length, 0), 0);
  const paras = pages.reduce((k, p) => k + p.lines.filter((l) => l.para).length, 0);
  let sha = '–';
  try {
    const h = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(out.manuscript));
    sha = [...new Uint8Array(h)].map((b) => b.toString(16).padStart(2, '0')).join('');
  } catch (e) { /* not available on plain http other than localhost */ }
  const rows = [
    ['text', i.byte_testo ? n(i.byte_testo) + ' bytes in UTF-8' : 'none (a book with no message)'],
    ['compressed (zlib, level 9)', i.byte_compressi ? n(i.byte_compressi) + ' bytes' : '–'],
    ['encrypted frame (length 4 bytes, tag 8 bytes, data)', i.bit_messaggio ? n(i.bit_messaggio) + ' bits' : '0 bits'],
    ['capacity of this book (depends on the key, and slightly on the message)', n(i.capacita_bit) + ' bits'],
    ['share used by the message', (100 * i.bit_messaggio / i.capacita_bit).toFixed(1) + '%'],
    ['pages carrying the message (the rest: filler)', n(i.pagine_usate) + ' of ' + n(i.pagine)],
    ['pages; lines; paragraphs; words', pages.length + '; ' + n(pages.reduce((k, p) => k + p.lines.length, 0)) + '; ' + n(paras) + '; ' + n(words)],
    ['time: word counts; arrangement; check', s(t.choose, t.arrange) + '; ' + s(t.arrange, t.check || t.end) + '; ' + s(t.check, t.end)],
    ['program', info.version + ' (commit ' + String(info.commit || '').slice(0, 7) + '), Pyodide ' + info.pyodide],
    ['SHA-256 of the manuscript file', '<code>' + sha + '</code>'],
  ];
  $('tech-table').innerHTML = rows.map(([a, b]) => '<tr><td>' + a + '</td><td>' + b + '</td></tr>').join('');
}

// File names: the date and the first 8 hex digits of the SHA-256 of the manuscript, the same for the .txt and the PDF
async function fileNames(manuscript) {
  const d = new Date();
  const day = d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
  let id = Date.now().toString(16).slice(-8);
  try {
    const h = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(manuscript));
    id = [...new Uint8Array(h)].slice(0, 4).map((b) => b.toString(16).padStart(2, '0')).join('');
  } catch (e) { /* digest unavailable: time-based id */ }
  return 'voynich-II_' + day + '_' + id;
}

// The folio as it will be in the PDF: vellum, the drawing, the text in ink (same layout as the PDF)
async function drawIllustrated(page) {
  const box = $('page');
  box.classList.add('illustrated');
  let c = box.querySelector('canvas');
  if (!c) {
    box.replaceChildren();
    c = document.createElement('canvas');
    c.setAttribute('role', 'img');
    box.append(c);
  }
  c.setAttribute('aria-label', 'Folio ' + page.folio + ' of the generated book, with a drawing from the real manuscript');
  const w = Math.max(200, box.clientWidth);
  c.width = Math.round(w * (window.devicePixelRatio || 1));
  c.height = Math.round(c.width * PAGE.h / PAGE.w);
  try {
    const a = await loadAssets();
    const lay = layout(a, page, (await sectionMap())[page.folio] || 'H');
    if (book && book.pages[shown] === page) await drawPage(c, lay);
  } catch (e) {
    box.classList.remove('illustrated');
    renderPage(box, page, 'script');
  }
}
