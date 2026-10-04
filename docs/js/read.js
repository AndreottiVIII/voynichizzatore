// The Read page: manuscript file and key in, text out.
import { prepare, call } from './engine.js';
import { $, showKey, error, LOADING, explain } from './common.js';

const PAGES = 207;
const MAX_BYTES = 2 * 1024 * 1024;       // a manuscript weighs about 260 KB
let loaded = null;                       // text of the chosen file
let textUrl = null;

showKey($('show-key'), $('key'));
const warm = () => prepare().catch(() => {});
$('key').addEventListener('focus', warm, { once: true });

async function take(file) {
  if (!file) return;
  if (file.size > MAX_BYTES) { loaded = null; $('file-name').textContent = 'This file is too big to be a manuscript.'; return; }
  if (/\.pdf$/i.test(file.name)) { loaded = null; $('file-name').textContent = 'This is the PDF: it cannot be read back. Choose the .txt file.'; return; }
  loaded = await file.text();
  $('file-name').textContent = file.name + ' · ' + Math.round(file.size / 1024) + ' KB';
  warm();
}
$('file').addEventListener('change', () => take($('file').files[0]));
const drop = $('drop');
drop.addEventListener('dragover', (e) => { e.preventDefault(); drop.classList.add('over'); });
drop.addEventListener('dragleave', () => drop.classList.remove('over'));
drop.addEventListener('drop', (e) => { e.preventDefault(); drop.classList.remove('over'); take(e.dataTransfer.files[0]); });

$('form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const manuscript = $('pasted').value.trim() ? $('pasted').value : loaded;
  const key = $('key').value;
  if (!manuscript) return error($('error'), 'Choose the manuscript file (.txt), or paste it.');
  if (!key) return error($('error'), 'Give the key the manuscript was written with.');
  error($('error'), '');
  $('form').hidden = true;
  $('working').hidden = false;
  setBar(0);
  try {
    const info = await prepare((m) => { if (m.phase === 'load') $('caption').textContent = LOADING[m.step] || ''; });
    let n = 0;
    const t1 = performance.now();
    $('caption').textContent = 'Reading the manuscript…';
    const out = await call('decode', { manuscript, key }, (m) => {
      if (m.phase !== 'read') return;
      n += 1;
      setBar(n / PAGES);
      $('caption').textContent = 'Reading folio ' + m.page;
      $('meta').textContent = 'Folio ' + Math.min(n, PAGES) + ' of ' + PAGES;
    });
    $('output').value = out.text;
    technical(out.text, manuscript, info, performance.now() - t1);
    if (textUrl) URL.revokeObjectURL(textUrl);
    textUrl = URL.createObjectURL(new Blob([out.text], { type: 'text/plain' }));
    $('dl').href = textUrl;
    $('working').hidden = true;
    $('result').hidden = false;
  } catch (err) {
    $('working').hidden = true;
    $('form').hidden = false;
    error($('error'), explain(err.message));
  }
});

function setBar(f) {
  $('bar').style.width = (100 * f).toFixed(1) + '%';
  $('progress').setAttribute('aria-valuenow', String(Math.round(100 * f)));
}

$('copy').addEventListener('click', async () => {
  try { await navigator.clipboard.writeText($('output').value); $('copy').textContent = 'Copied'; }
  catch (e) { $('output').select(); }
  setTimeout(() => { $('copy').textContent = 'Copy'; }, 1500);
});
$('again').addEventListener('click', () => {
  $('result').hidden = true;
  $('form').hidden = false;
});

async function technical(text, manuscript, info, ms) {
  const n = (x) => Number(x).toLocaleString('en');
  const lines = manuscript.split(/\r?\n/).filter((l) => /^@?</.test(l));
  const folios = new Set(lines.map((l) => l.replace(/^@?<([^>]+)\.\d+>.*$/, '$1')));
  let sha = '–';
  try {
    const h = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(manuscript));
    sha = [...new Uint8Array(h)].map((b) => b.toString(16).padStart(2, '0')).join('');
  } catch (e) { /* not available */ }
  const rows = [
    ['text', n([...text].length) + ' characters, ' + n(new TextEncoder().encode(text).length) + ' bytes in UTF-8'],
    ['manuscript', n(folios.size) + ' folios, ' + n(lines.length) + ' lines'],
    ['checks passed', 'length of the frame, 64-bit HMAC tag, zlib decompression'],
    ['time to read', (ms / 1000).toFixed(1) + ' s'],
    ['program', info.version + ' (commit ' + String(info.commit || '').slice(0, 7) + '), Pyodide ' + info.pyodide],
    ['SHA-256 of the manuscript', '<code>' + sha + '</code>'],
  ];
  $('tech-table').innerHTML = rows.map(([a, b]) => '<tr><td>' + a + '</td><td>' + b + '</td></tr>').join('');
}
