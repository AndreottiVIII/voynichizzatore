# -*- coding: utf-8 -*-
"""Copies the program, unchanged, into the web site: docs/engine/<version>/, with a manifest of SHA-256 fingerprints.

    python docs/engine/build_engine.py v17

Run it from the repository at the commit of that version. Each version keeps its own folder, so that a manuscript can
always be read back with the version that wrote it. The site never changes these files: it only supplies, from
JavaScript, the one function the browser lacks (hashlib.scrypt, from @noble/hashes)."""
import hashlib, json, os, shutil, subprocess, sys

QUI = os.path.dirname(os.path.abspath(__file__))
RADICE = os.path.normpath(os.path.join(QUI, '..', '..'))
PYODIDE = '314.0.7'          # the Pyodide release the site loads for this version (numbers depend on it)


def main():
    versione = sys.argv[1] if len(sys.argv) > 1 else 'v17'
    sys.path.insert(0, RADICE)
    import voynichizzatore
    if voynichizzatore.VERSIONE != versione:
        raise SystemExit('the program in this folder is %s, not %s' % (voynichizzatore.VERSIONE, versione))
    nomi = sorted(f for f in os.listdir(RADICE) if os.path.isfile(os.path.join(RADICE, f)) and f != 'prova.py'
                  and (f.endswith('.py') or f.endswith('.json') or f.endswith('.ttf')))
    cartella = os.path.join(QUI, versione)
    os.makedirs(cartella, exist_ok=True)
    impronte = {}
    for f in nomi:
        shutil.copyfile(os.path.join(RADICE, f), os.path.join(cartella, f))
        impronte[f] = hashlib.sha256(open(os.path.join(cartella, f), 'rb').read()).hexdigest()
    try:
        commit = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=RADICE, capture_output=True, text=True).stdout.strip()
    except OSError:
        commit = ''
    manifesto = {'version': versione, 'commit': commit, 'pyodide': PYODIDE,
                 'packages': ['numpy', 'scipy', 'scikit-learn'], 'pdf_packages': ['matplotlib', 'fonttools'],
                 'files': impronte}
    with open(os.path.join(cartella, 'manifest.json'), 'w', encoding='utf-8', newline='\n') as out:
        json.dump(manifesto, out, indent=1)
    print('copied %d files into %s (commit %s)' % (len(nomi), cartella, commit[:7]))


if __name__ == '__main__':
    main()
