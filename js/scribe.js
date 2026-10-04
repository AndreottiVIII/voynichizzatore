// The scribe at work: a quill writing Voynich-like lines on a sheet while the program computes. The words written here
// are for show (common Voynich words); the folio number in the corner is the one the program is working on.
import { toGlyphs } from './glyphs.js';

const WORDS = ('daiin ol chedy aiin shedy chol or ar chey dar qokeey qokedy qokeedy qokain qokaiin shey dy okaiin ' +
  'cheey okeey chor dal otedy qol ytaiin chdy cthy shol kchdy otaiin sain okal cheol sheey lkeedy cphy oteey ' +
  'qokal okedy chckhy saiin dain al s y qotedy otar kaiin shckhy chody okar otal lchedy qokar ykeedy cheody ' +
  'opchedy otol sheol choty chos dol oky').split(' ');
const OPENERS = 'pchedy tshol kchor pchol tchey fachys podaiin pshedy kshol tolshedy pchdar ksheody'.split(' ');
const QUILL = `<svg viewBox="0 0 100 130" width="78" height="101" aria-hidden="true">
  <path class="vane" d="M31 94 C 20 62, 44 22, 94 3 C 86 31, 71 66, 39 97 Z"/>
  <path class="barbs" d="M40 82 L57 55 M46 72 L66 43 M53 61 L75 31 M60 49 L83 19 M37 88 L48 66"/>
  <path class="shaft" d="M4 127 C 21 105, 51 60, 94 3"/>
  <path class="nib" d="M3 128 L9 113 L14 117 Z"/>
</svg>`;
const TIP = [3 * 0.78, 128 * 0.78];   // where the nib touches the sheet, in pixels from the top left of the drawing

const pick = (a, r) => a[Math.floor(r() * a.length)];

export class Scribe {
  constructor(desk) {
    this.desk = desk;
    this.sheet = desk.querySelector('.sheet');
    this.lines = this.sheet.querySelector('.lines');
    this.label = this.sheet.querySelector('.folio-label');
    this.quill = document.createElement('div');
    this.quill.className = 'quill';
    this.quill.innerHTML = QUILL;
    desk.append(this.quill);
    this.folio = '';
    this.running = false;
    this.calm = matchMedia('(prefers-reduced-motion: reduce)').matches;
    this.seed = 1;
    this.measure = document.createElement('canvas').getContext('2d');
  }

  rand() {               // a small deterministic generator: the show does not need real randomness
    this.seed = (this.seed * 1103515245 + 12345) % 2147483648;
    return this.seed / 2147483648;
  }

  setFolio(name) {
    this.folio = name;
    if (!this.label.textContent) this.label.textContent = name;
  }

  start() {
    if (this.running) return;
    this.running = true;
    this.newPage();
    this.loop();
  }

  stop() {
    this.running = false;
    clearTimeout(this.timer);
    this.quill.classList.remove('writing');
  }

  newPage() {
    this.lines.replaceChildren();
    this.label.textContent = this.folio;
    const size = parseFloat(getComputedStyle(this.lines).fontSize);
    const family = getComputedStyle(this.lines).fontFamily;
    this.measure.font = size + 'px ' + family;
    this.width = this.lines.clientWidth;
    this.room = Math.floor(this.lines.clientHeight / (size * 1.75)) - 1;
    this.written = 0;
    this.paraLeft = 0;
  }

  nextLine() {
    const para = this.paraLeft <= 0;
    this.paraLeft = para ? 3 + Math.floor(this.rand() * 4) : this.paraLeft - 1;
    const short = this.paraLeft === 0 ? 0.35 + this.rand() * 0.4 : 0.97;
    const words = [para ? pick(OPENERS, () => this.rand()) : pick(WORDS, () => this.rand())];
    for (;;) {
      const w = pick(WORDS, () => this.rand());
      const t = [...words, w].map(toGlyphs).join(' ');
      if (this.measure.measureText(t).width > this.width * short) break;
      words.push(w);
    }
    const div = document.createElement('div');
    div.className = 'line' + (para && this.written > 0 ? ' para' : '');
    const ink = document.createElement('span');
    const caret = document.createElement('span');
    caret.className = 'caret';
    div.append(ink, caret);
    this.lines.append(div);
    this.written += para && this.written > 0 ? 1.5 : 1;
    return { ink, caret, text: [...words.map(toGlyphs).join(' ')], i: 0 };
  }

  place(caret) {
    const d = this.desk.getBoundingClientRect();
    const c = caret.getBoundingClientRect();
    const size = parseFloat(getComputedStyle(this.lines).fontSize);
    this.quill.style.transform = `translate(${c.left - d.left - TIP[0]}px, ${c.top - d.top + size * 0.95 - TIP[1]}px)`;
  }

  loop() {
    if (!this.running) return;
    if (!this.line || this.line.i >= this.line.text.length) {
      if (this.written >= this.room) {
        this.quill.classList.remove('writing');
        this.sheet.classList.add('turning');
        this.timer = setTimeout(() => {
          this.sheet.classList.remove('turning');
          this.newPage();
          this.line = null;
          this.loop();
        }, 700);
        return;
      }
      this.line = this.nextLine();
      if (this.calm) {
        this.line.ink.textContent = this.line.text.join('');
        this.line.i = this.line.text.length;
        this.timer = setTimeout(() => this.loop(), 900);
        return;
      }
      this.place(this.line.caret);
      this.timer = setTimeout(() => this.loop(), 260);
      return;
    }
    const l = this.line;
    const ch = l.text[l.i++];
    l.ink.textContent += ch;
    this.quill.classList.add('writing');
    this.place(l.caret);
    const pause = ch === ' ' ? 140 : 55 + this.rand() * 45;
    this.timer = setTimeout(() => this.loop(), pause);
  }
}
