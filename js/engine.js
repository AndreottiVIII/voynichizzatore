// Talks to the engine (worker.js), which runs the program in a background thread so that the page stays responsive.
export const VERSION = 'v21';

let worker = null;
let next = 0;
const pending = new Map();

function start() {
  if (worker) return worker;
  worker = new Worker(new URL('./worker.js?v=' + VERSION, import.meta.url), { type: 'module' });
  worker.onmessage = (e) => {
    const m = e.data;
    const job = pending.get(m.id);
    if (!job) return;
    if (m.type === 'progress') { job.onProgress && job.onProgress(m); return; }
    pending.delete(m.id);
    if (m.type === 'done') job.resolve(m); else job.reject(new Error(m.message));
  };
  worker.onerror = (e) => {
    for (const job of pending.values()) job.reject(new Error(e.message || 'the engine stopped'));
    pending.clear();
    worker = null;
    ready = null;
    lastStep = null;
  };
  return worker;
}

export function call(cmd, args = {}, onProgress = null) {
  const w = start();
  const id = ++next;
  return new Promise((resolve, reject) => {
    pending.set(id, { resolve, reject, onProgress });
    w.postMessage({ id, cmd, ...args });
  });
}

// Stops the engine in the middle of a job (the next call starts it again, from the browser's cache).
export function reset() {
  if (worker) worker.terminate();
  worker = null;
  ready = null;
  lastStep = null;
  for (const job of pending.values()) job.reject(new Error('stopped'));
  pending.clear();
}

let ready = null;
let lastStep = null;
const listeners = new Set();
// Loads Python, the libraries and the program once; later calls return the same promise and follow its progress.
export function prepare(onProgress) {
  if (onProgress) {
    listeners.add(onProgress);
    if (lastStep) onProgress(lastStep);
  }
  if (!ready) {
    ready = call('init', {}, (m) => { lastStep = m; for (const f of listeners) f(m); })
      .catch((e) => { ready = null; lastStep = null; throw e; });
  }
  if (onProgress) ready.finally(() => listeners.delete(onProgress)).catch(() => {});
  return ready;
}
