// The illustrated book: each folio of the generated manuscript is composed on vellum, with the drawing of the real
// folio of the same name lifted from the Voynich (or one of its section, when that folio has none), and the generated
// text written around it in brown ink with small irregularities. The same layout serves the preview and the PDF.
import { toGlyphs } from './glyphs.js';

export const PAGE = { w: 432, h: 619 };                 // points: 6 x 8.6 inches
const M = { left: 42, right: 42, top: 50, bottom: 52 };
const INK = [74, 48, 28];
const LINE = 1.5;                                        // line height, in type sizes
const PDF_PX = 150 / 72;                                 // pixels per point for the images in the PDF (150 dpi)

let assets = null;
const measurer = document.createElement('canvas').getContext('2d');

// ---------------------------------------------------------------- assets
export function loadAssets() {
  if (!assets) {
    assets = (async () => {
      const [drawings, stars] = await Promise.all([
        fetch('book/drawings.json').then((r) => r.json()),
        fetch('book/stars/stars.json').then((r) => r.json()),
        document.fonts.load('20px "Voynichizer EVA"'),
      ]);
      const bySection = {};
      for (const [f, d] of Object.entries(drawings)) {
        if (d && !d.shared) (bySection[d.section] = bySection[d.section] || []).push({ src: 'book/' + d.file, w: d.w, h: d.h, of: f });
      }
      // sections whose folios have no usable drawing of their own
      bySection.A = [{ src: 'img/stars-f67r.jpg', w: 560, h: 684, of: 'f67r1' }];
      bySection.C = [{ src: 'img/margin/fRos.jpg', w: 272, h: 1092, of: 'fRos' }];
      return { drawings, stars: stars.map((s) => 'book/stars/' + s), bySection, images: new Map() };
    })().catch((e) => { assets = null; throw e; });
  }
  return assets;
}

export function image(src) {
  return assets.then((a) => {
    if (!a.images.has(src)) {
      a.images.set(src, new Promise((ok, ko) => {
        const im = new Image();
        im.onload = () => ok(im);
        im.onerror = ko;
        im.src = src;
      }));
    }
    return a.images.get(src);
  });
}

// ---------------------------------------------------------------- small deterministic random numbers, per folio
function rng(seedText) {
  let h = 1779033703;
  for (let i = 0; i < seedText.length; i++) h = Math.imul(h ^ seedText.charCodeAt(i), 3432918353) >>> 0;
  return () => {
    h = (h + 0x6D2B79F5) >>> 0;
    let t = h;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function width(text, size) {
  measurer.font = '100px "Voynichizer EVA"';
  return measurer.measureText(text).width * size / 100;
}

// ---------------------------------------------------------------- which drawing
export function drawingFor(a, folio, section) {
  const own = a.drawings[folio];
  if (own) return { src: 'book/' + own.file, w: own.w, h: own.h, of: own.shared || folio };
  const pool = a.bySection[section];
  if (!pool || section === 'S' || section === 'T') return null;
  return pool[Math.floor(rng(folio)() * pool.length)];
}

// ---------------------------------------------------------------- layout
// lines: [{para, words}] of the folio; returns everything needed to draw it, in points.
export function layout(a, page, section) {
  const r = rng(page.folio);
  const lines = page.lines.map((l) => ({ para: l.para, glyphs: l.words.map(toGlyphs) }));
  const natural = lines.map((l) => l.glyphs.reduce((s, g) => s + width(g, 1), 0) + width(' ', 1) * 1.15 * Math.max(0, l.glyphs.length - 1));
  const draw = drawingFor(a, page.folio, section);
  const W = PAGE.w, H = PAGE.h, x0 = M.left, x1 = W - M.right, y0 = M.top, y1 = H - M.bottom, tw = x1 - x0;
  const recto = /r\d*$/.test(page.folio) || page.folio === 'fRos';
  const stars = section === 'S';
  const starCol = stars ? 30 : 0;

  // the areas for a given layout kind and drawing scale k
  function areas(kind, k, size) {
    const L = size * LINE;
    if (!draw) return { pic: null, areas: [{ x0: x0 + starCol, x1, y0, y1 }] };
    const ratio = draw.h / draw.w;
    if (kind === 'side') {                            // on one side: left on versos, right on rectos
      let dw = tw * 0.34 * k, dh = dw * ratio;
      if (dh > (y1 - y0)) { dh = y1 - y0; dw = dh / ratio; }
      const left = !recto;
      const pic = { x: left ? x0 : x1 - dw, y: y0 + 4, w: dw, h: dh };
      const beside = left ? { x0: x0 + dw + 14, x1 } : { x0, x1: x1 - dw - 14 };
      const out = [{ ...beside, y0, y1: Math.min(y1, pic.y + dh) }];
      if (pic.y + dh + 2 * L < y1) out.push({ x0, x1, y0: pic.y + dh + 10, y1 });
      return { pic, areas: out };
    }
    if (kind === 'top') {                             // across the top, text below
      let dw = tw * 0.96 * k, dh = dw * ratio;
      if (dh > (y1 - y0) * 0.5 * k) { dh = (y1 - y0) * 0.5 * k; dw = dh / ratio; }
      const pic = { x: x0 + (tw - dw) / 2, y: y0 + 2, w: dw, h: dh };
      return { pic, areas: [{ x0, x1, y0: pic.y + dh + 12, y1 }] };
    }
    // in the middle, text above and below
    let dw = tw * 0.7 * k, dh = dw * ratio;
    if (dh > (y1 - y0) * 0.55 * k) { dh = (y1 - y0) * 0.55 * k; dw = dh / ratio; }
    const above = Math.min(Math.round(lines.length * 0.32), Math.max(0, lines.length - 3));
    const yd = Math.min(y1 - dh - 2 * L, y0 + (above > 0 ? above * L + L * 0.6 : 0) + 4);
    const pic = { x: x0 + (tw - dw) / 2, y: yd, w: dw, h: dh };
    const out = [];
    if (yd - y0 > L) out.push({ x0, x1, y0, y1: yd - 6 });
    out.push({ x0, x1, y0: yd + dh + 12, y1 });
    return { pic, areas: out };
  }

  // do the lines fit the areas at this size? where does each go?
  function place(size, ar) {
    const L = size * LINE;
    const out = [];
    let k = 0;
    for (const A of ar) {
      let y = A.y0 + size;
      let first = true;
      while (k < lines.length) {
        const gap = lines[k].para && !first && k > 0 ? L * 0.45 : 0;
        if (y + gap > A.y1) break;
        y += gap;
        out.push({ k, y, x0: A.x0, x1: A.x1 });
        y += L;
        first = false;
        k++;
      }
    }
    return k === lines.length ? out : null;
  }

  // the largest type size that fits, for a kind and a scale of the drawing
  function fit(kind, k) {
    let lo = 5.5, hi = 13.5, found = null;
    for (let it = 0; it < 14; it++) {
      const s = (lo + hi) / 2;
      const ar = areas(kind, k, s);
      const p = place(s, ar.areas);
      if (p) { found = { size: s, ar, p, k, kind }; lo = s; } else hi = s;
    }
    return found;
  }

  // every kind is tried; the drawing shrinks (down to 0.64) only while the text would be smaller than 7.5 pt; the
  // choice weighs the size the lines really get (long lines are set smaller) against the area of the drawing
  let best = null;
  const candidates = [];
  for (const kind of draw ? ['side', 'top', 'middle'] : ['plain']) {
    let f = null;
    for (const k of [1, 0.86, 0.74, 0.64]) {
      f = fit(kind, k) || f;
      if (f && f.size >= 7.5 && f.k === k) break;
    }
    if (!f) continue;
    // the size the lines really get: their mean, but no more than 1.15 times the smallest (one squeezed line spoils a page)
    const reali = f.p.map((q) => Math.min(f.size, (q.x1 - q.x0) / natural[q.k]));
    const eff = Math.min(reali.reduce((s, x) => s + x, 0) / Math.max(1, reali.length), 1.15 * Math.min(...reali, f.size));
    const area = f.ar.pic ? f.ar.pic.w * f.ar.pic.h : 0;
    f.score = Math.min(eff, 10.5) + 0.5 * Math.sqrt(area) / 20;
    candidates.push({ kind, k: f.k, size: +f.size.toFixed(2), eff: +eff.toFixed(2), min: +Math.min(...reali).toFixed(2), area: Math.round(area), score: +f.score.toFixed(2) });
    if (!best || f.score > best.score) best = f;
  }
  if (!best) {                                        // a very long page: smallest size, no drawing
    const s = 5.5;
    best = { size: s, ar: { pic: null, areas: [{ x0, x1, y0, y1: H - 20 }] }, p: place(s, [{ x0, x1, y0, y1: H - 20 }]) || [] };
  }

  const size = best.size;
  const placed = best.p.map(({ k, y, x0: ax0, x1: ax1 }) => {
    const l = lines[k];
    const room = ax1 - ax0;
    const s = natural[k] * size > room ? room / natural[k] : size;       // a few long lines are set smaller
    const slope = (r() - 0.5) * 0.012;
    let x = ax0 + r() * 3;
    const words = l.glyphs.map((g) => {
      const w = width(g, s);
      const item = { t: g, x, y: y + slope * (x - ax0) + (r() - 0.5) * 0.5, s, op: 0.8 + r() * 0.17 };
      x += w + width(' ', s) * 1.15 * (0.8 + r() * 0.45);
      return item;
    });
    return { para: l.para, slope, words, star: stars && l.para ? { x: x0 + 2, y: y - size * 1.1, s: size * 2.1 } : null };
  });
  const starList = placed.filter((l) => l.star).map((l, i) => ({ ...l.star, src: a.stars[(i + Math.floor(r() * 8)) % a.stars.length] }));
  return { candidates, folio: page.folio, size, pic: best.ar.pic ? { ...best.ar.pic, src: draw.src, of: draw.of } : null, lines: placed, stars: starList };
}

// ---------------------------------------------------------------- the page background (vellum, darker edges)
let background = null;
export function pageBackground(pxPerPt) {
  if (background && background.k === pxPerPt) return Promise.resolve(background.canvas);
  return image('img/vellum-tile.jpg').then((tile) => {
    const c = document.createElement('canvas');
    c.width = Math.round(PAGE.w * pxPerPt);
    c.height = Math.round(PAGE.h * pxPerPt);
    const g = c.getContext('2d');
    g.fillStyle = g.createPattern(tile, 'repeat');
    g.fillRect(0, 0, c.width, c.height);
    const e = Math.min(c.width, c.height);
    for (const [x, y, w, h, gx0, gy0, gx1, gy1] of [
      [0, 0, c.width, e * 0.1, 0, 0, 0, e * 0.1], [0, c.height - e * 0.1, c.width, e * 0.1, 0, c.height, 0, c.height - e * 0.1],
      [0, 0, e * 0.1, c.height, 0, 0, e * 0.1, 0], [c.width - e * 0.1, 0, e * 0.1, c.height, c.width, 0, c.width - e * 0.1, 0]]) {
      const gr = g.createLinearGradient(gx0, gy0, gx1, gy1);
      gr.addColorStop(0, 'rgba(95,62,30,0.30)');
      gr.addColorStop(1, 'rgba(95,62,30,0)');
      g.fillStyle = gr;
      g.fillRect(x, y, w, h);
    }
    background = { k: pxPerPt, canvas: c };
    return c;
  });
}

// ---------------------------------------------------------------- drawing on a canvas (the preview)
export async function drawPage(canvas, lay) {
  const a = await loadAssets();
  const k = canvas.width / PAGE.w;
  const g = canvas.getContext('2d');
  g.setTransform(1, 0, 0, 1, 0, 0);
  g.drawImage(await pageBackground(k), 0, 0, canvas.width, canvas.height);
  g.globalCompositeOperation = 'multiply';
  if (lay.pic) g.drawImage(await image(lay.pic.src), lay.pic.x * k, lay.pic.y * k, lay.pic.w * k, lay.pic.h * k);
  for (const s of lay.stars) g.drawImage(await image(s.src), s.x * k, s.y * k, s.s * k, s.s * k);
  g.globalCompositeOperation = 'source-over';
  for (const l of lay.lines) {
    for (const w of l.words) {
      g.setTransform(1, 0, 0, 1, w.x * k, w.y * k);
      g.rotate(Math.atan(l.slope));
      g.font = (w.s * k).toFixed(2) + 'px "Voynichizer EVA"';
      g.fillStyle = 'rgba(' + INK.join(',') + ',' + w.op.toFixed(2) + ')';
      g.fillText(w.t, 0, 0);
    }
  }
  g.setTransform(1, 0, 0, 1, 0, 0);
  g.font = 'italic ' + (13 * k).toFixed(1) + 'px "EB Garamond", Georgia, serif';
  g.fillStyle = 'rgb(96,70,48)';
  g.textAlign = 'right';
  g.fillText(lay.folio.slice(1), (PAGE.w - M.right + 6) * k, (M.top - 22) * k);
  g.textAlign = 'left';
  return a;
}

// ---------------------------------------------------------------- the PDF
function loadScript(src) {
  return new Promise((ok, ko) => {
    if (window.jspdf) return ok();
    const s = document.createElement('script');
    s.src = src;
    s.onload = ok;
    s.onerror = () => ko(new Error('cannot load ' + src));
    document.head.append(s);
  });
}

function base64(buffer) {
  let s = '';
  const b = new Uint8Array(buffer);
  for (let i = 0; i < b.length; i += 0x8000) s += String.fromCharCode.apply(null, b.subarray(i, i + 0x8000));
  return btoa(s);
}

// pages: [{folio, lines}] ; sections: folio -> section letter
export async function makePdf(pages, sections, onProgress) {
  const a = await loadAssets();
  await loadScript('js/vendor/jspdf.umd.min.js');
  const { jsPDF } = window.jspdf;
  const doc = new jsPDF({ unit: 'pt', format: [PAGE.w, PAGE.h], compress: true });
  const ttf = await fetch('engine/v20/VoynichizzatoreEVA.ttf').then((r) => r.arrayBuffer());
  doc.addFileToVFS('VoynichizzatoreEVA.ttf', base64(ttf));
  doc.addFont('VoynichizzatoreEVA.ttf', 'Voynich', 'normal');
  doc.setProperties({ title: 'Voynich II', subject: 'A manuscript written by the Voynichizer', creator: 'Voynichizer v20' });
  const bg = await pageBackground(PDF_PX);
  const bgData = bg.toDataURL('image/jpeg', 0.82);
  const states = [0.8, 0.84, 0.88, 0.92, 0.96].map((op) => new doc.GState({ opacity: op }));
  const scratch = document.createElement('canvas');
  for (let n = 0; n < pages.length; n++) {
    const p = pages[n];
    const lay = layout(a, p, sections[p.folio] || 'H');
    if (n > 0) doc.addPage([PAGE.w, PAGE.h]);
    doc.addImage(bgData, 'JPEG', 0, 0, PAGE.w, PAGE.h, 'vellum', 'FAST');
    // drawings are multiplied onto the vellum here, at their place, so the PDF needs no blend modes
    const pictures = (lay.pic ? [lay.pic] : []).concat(lay.stars.map((s) => ({ x: s.x, y: s.y, w: s.s, h: s.s, src: s.src })));
    for (const pic of pictures) {
      const im = await image(pic.src);
      scratch.width = Math.max(1, Math.round(pic.w * PDF_PX));
      scratch.height = Math.max(1, Math.round(pic.h * PDF_PX));
      const g = scratch.getContext('2d');
      g.globalCompositeOperation = 'source-over';
      g.drawImage(bg, pic.x * PDF_PX, pic.y * PDF_PX, scratch.width, scratch.height, 0, 0, scratch.width, scratch.height);
      g.globalCompositeOperation = 'multiply';
      g.drawImage(im, 0, 0, scratch.width, scratch.height);
      doc.addImage(scratch.toDataURL('image/jpeg', 0.8), 'JPEG', pic.x, pic.y, pic.w, pic.h, undefined, 'FAST');
    }
    doc.setFont('Voynich', 'normal');
    doc.setTextColor(INK[0], INK[1], INK[2]);
    for (const l of lay.lines) {
      const angle = -Math.atan(l.slope) * 180 / Math.PI;
      for (const w of l.words) {
        doc.setGState(states[Math.min(4, Math.floor((w.op - 0.8) / 0.035))]);
        doc.setFontSize(w.s);
        doc.text(w.t, w.x, w.y, { angle });
      }
    }
    doc.setGState(states[4]);
    doc.setFont('times', 'italic');
    doc.setFontSize(13);
    doc.setTextColor(96, 70, 48);
    doc.text(lay.folio.slice(1), PAGE.w - M.right + 6, M.top - 22, { align: 'right' });
    if (onProgress) onProgress(n + 1, pages.length);
    if (n % 4 === 3) await new Promise((ok) => setTimeout(ok, 0));     // let the page breathe
  }
  return doc.output('blob');
}
