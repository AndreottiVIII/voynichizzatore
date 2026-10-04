// Small helpers shared by the pages.
export const $ = (id) => document.getElementById(id);
export const CAPACITY = 80000;      // bits a book carries at the least: 80,000-85,000 depending on the key (tests: 80,344-84,678)
export const CAPACITY_MAX = 86000;  // above this a text never fits

export function minutes(ms) {
  const s = Math.max(0, Math.round(ms / 1000));
  return s < 60 ? s + ' s' : Math.floor(s / 60) + ' min ' + String(s % 60).padStart(2, '0') + ' s';
}

export function showKey(button, input) {
  button.addEventListener('click', () => {
    const show = input.type === 'password';
    input.type = show ? 'text' : 'password';
    button.textContent = show ? 'Hide' : 'Show';
    button.setAttribute('aria-pressed', String(show));
  });
}

export function error(el, text) {
  el.textContent = text;
  el.hidden = !text;
}

// Captions while Python and the program are loading
export const LOADING = {
  manifest: 'Sharpening the quill…',
  python: 'Fetching ink and vellum (the first time, about 27 MB)…',
  libraries: 'Fetching ink and vellum (the first time, about 27 MB)…',
  program: 'Laying out the pens…',
  model: 'The scribe studies the real manuscript…',
  ready: 'The scribe is ready.',
};

// A friendlier wording of the program's own messages
export function explain(message) {
  if (/wrong key/.test(message)) return 'Nothing to read: wrong key, or a manuscript without a message.';
  if (/too long/.test(message)) return 'The text is too long for one book: ' + message.replace(/^.*too long for this book:\s*/, '') + '.';
  if (/stopped/.test(message)) return '';
  if (/fetch|network|import/i.test(message)) return 'The page could not fetch Python and its libraries. Check the connection and try again.';
  return 'Something went wrong: ' + message;
}
