// The Voynichizer engine: runs the unchanged Python program inside the browser (Pyodide), in a background thread.
// Messages in:  {id, cmd: 'init'|'encode'|'decode'|'pdf'|'bits', ...}
// Messages out: {id, type: 'progress'|'done'|'error', ...}
import { scrypt } from './noble-hashes/scrypt.js';

const VERSION = new URL(self.location.href).searchParams.get('v') || 'v21';
const ENGINE = new URL('../engine/' + VERSION + '/', self.location.href).href;
const DIR = '/engine/' + VERSION;
let py = null;
let manifest = null;
let pages = [];                // folio names, in order
let current = null;            // id of the request being served (for progress messages sent from Python)

const progress = (data) => postMessage({ id: current, type: 'progress', ...data });

async function init() {
  if (py) return;
  progress({ phase: 'load', step: 'manifest' });
  manifest = await (await fetch(ENGINE + 'manifest.json')).json();
  progress({ phase: 'load', step: 'python' });
  const { loadPyodide } = await import('https://cdn.jsdelivr.net/pyodide/v' + manifest.pyodide + '/full/pyodide.mjs');
  const p = await loadPyodide();
  progress({ phase: 'load', step: 'libraries' });
  await p.loadPackage(manifest.packages, { messageCallback: () => {} });
  progress({ phase: 'load', step: 'program' });
  p.FS.mkdirTree(DIR);
  await Promise.all(Object.keys(manifest.files).map(async (f) => {
    const r = await fetch(ENGINE + f);
    if (!r.ok) throw new Error('cannot load ' + f);
    p.FS.writeFile(DIR + '/' + f, new Uint8Array(await r.arrayBuffer()));
  }));
  // The browser's Python has no hashlib.scrypt (no OpenSSL): it comes from @noble/hashes, a standard implementation
  // that gives the same bytes. Progress is reported by wrapping, from outside, the two functions that the program
  // calls once per page; what they compute is not changed.
  p.registerJsModule('voynichizer_js', {
    scrypt: (pw, salt, N, r, q, dkLen) => scrypt(pw, salt, { N, r, p: q, dkLen }),
    progress: (phase, page) => progress({ phase, page }),
  });
  await p.runPythonAsync(`
import sys, hashlib
sys.path.insert(0, '${DIR}')
import voynichizer_js
from pyodide.ffi import to_js
if not hasattr(hashlib, 'scrypt'):
    def _scrypt(password, *, salt, n, r, p, maxmem=0, dklen=64):
        return voynichizer_js.scrypt(to_js(bytes(password)), to_js(bytes(salt)), n, r, p, dklen).to_bytes()
    hashlib.scrypt = _scrypt
assert hashlib.scrypt(b'password', salt=b'NaCl', n=1024, r=8, p=16, dklen=8).hex() == 'fdbabe1c9d347200'
import canale_sacco, disposizione, v0, voynichizzatore
assert voynichizzatore.VERSIONE == '${VERSION}'

_fase = ['']
_dist, _pagina = canale_sacco.distribuzione, disposizione.Disposizione.pagina
def _dist_contata(s, p, *a, **k):
    voynichizer_js.progress(_fase[0], p)
    return _dist(s, p, *a, **k)

# The program learns the capacity of the book once all word counts are drawn (about a tenth of the time), but says
# "too long" only at the end. The bit counter it uses is recorded from outside, and the same check is made when the
# arrangement starts, with the program's own message.
import v1
_bisogno = [None]
class _ContaRegistrata(canale_sacco.Conta):
    ultima = None
    def __init__(self, bit):
        super().__init__(bit)
        _ContaRegistrata.ultima = self
canale_sacco.Conta = _ContaRegistrata

def _pagina_contata(self, p, *a, **k):
    if _bisogno[0] is not None:
        capacita = _ContaRegistrata.ultima.n - v1.PREC
        bisogno, _bisogno[0] = _bisogno[0], None
        if bisogno > capacita:
            raise ValueError('text too long for this book: it needs %d bits, the book carries %d' % (bisogno, capacita))
    voynichizer_js.progress('arrange', p)
    return _pagina(self, p, *a, **k)
canale_sacco.distribuzione = _dist_contata
disposizione.Disposizione.pagina = _pagina_contata

def _pagine():
    import pezzi
    s, _ = pezzi.pezzi()
    return list(dict.fromkeys(p for p, _, _ in s.rr))

def scrivi(testo, chiave):
    _fase[0] = 'choose'
    _bisogno[0] = bit_necessari(testo, chiave) if testo is not None else None
    try:
        righe, info = canale_sacco.codifica(testo, chiave, voynichizzatore.VERSIONE, verifica=False)
    except SystemExit as e:          # the program's own "too long" (SystemExit would stop the browser's Python)
        raise ValueError(str(e)) from None
    finally:
        _bisogno[0] = None
    v0.salva(righe, '/tmp/manuscript.txt')
    if testo is not None:
        _fase[0] = 'check'
        if canale_sacco.decodifica(v0.carica('/tmp/manuscript.txt'), chiave, voynichizzatore.VERSIONE) != testo:
            raise ValueError('the check reading did not return the text')
    return open('/tmp/manuscript.txt', encoding='utf-8').read(), dict(info)

def leggi(manoscritto, chiave):
    _fase[0] = 'read'
    with open('/tmp/to_read.txt', 'w', encoding='utf-8') as f:
        f.write(manoscritto)
    righe = v0.carica('/tmp/to_read.txt')
    if not righe:
        raise ValueError('this file has no manuscript lines (<page.line> words)')
    return canale_sacco.decodifica(righe, chiave, voynichizzatore.VERSIONE)

def bit_necessari(testo, chiave):
    return len(canale_sacco.bit_cifrati(testo, chiave)[0])
`);
  // the model of the real manuscript (built once, about a tenth of the writing time) and the list of folios
  progress({ phase: 'load', step: 'model' });
  pages = p.runPython('_pagine()').toJs();
  py = p;
  progress({ phase: 'load', step: 'ready' });
}

function message(e) {
  // Python errors arrive as long tracebacks: keep the last line, which is the program's own message
  const s = String(e && e.message || e).trim().split('\n').filter((l) => l.trim());
  let last = s[s.length - 1] || 'unknown error';
  last = last.replace(/^(\w+\.)*(SystemExit|ValueError|Exception|RuntimeError|zlib\.error|error):\s*/, '');
  return last;
}

async function serve(m) {
  await init();
  if (m.cmd === 'init') return { version: VERSION, pyodide: manifest.pyodide, commit: manifest.commit, pages };
  if (m.cmd === 'need') {
    // exact size of the message: UTF-8 bytes, zlib level 9 (the program's own compression), plus the 12-byte frame
    py.globals.set('_t', m.text);
    const r = py.runPython('import zlib as _z\n_b = _t.encode("utf-8")\n[len(_b), len(_z.compress(_b, 9))]').toJs();
    return { utf8: r[0], compressed: r[1], bits: 8 * (12 + r[1]) };
  }
  if (m.cmd === 'bits') {
    py.globals.set('_t', m.text); py.globals.set('_k', m.key);
    return { bits: py.runPython('bit_necessari(_t, _k)') };
  }
  if (m.cmd === 'encode') {
    // a JavaScript null reaches Python as JsNull, not None: a book with no message is said with a separate flag
    py.globals.set('_vuoto', m.text === null); py.globals.set('_t', m.text === null ? '' : m.text); py.globals.set('_k', m.key);
    const r = py.runPython('scrivi(None if _vuoto else _t, _k)');
    const [manuscript, info] = r.toJs({ dict_converter: Object.fromEntries });
    r.destroy();
    return { manuscript, info };
  }
  if (m.cmd === 'decode') {
    py.globals.set('_m', m.manuscript); py.globals.set('_k', m.key);
    return { text: py.runPython('leggi(_m, _k)') };
  }
  throw new Error('unknown command ' + m.cmd);
}

let queue = Promise.resolve();
self.onmessage = (e) => {
  const m = e.data;
  queue = queue.then(async () => {
    current = m.id;
    try {
      const out = await serve(m);
      postMessage({ id: m.id, type: 'done', ...out });
    } catch (err) {
      postMessage({ id: m.id, type: 'error', message: message(err) });
    }
  });
};
