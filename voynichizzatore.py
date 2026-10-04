# -*- coding: utf-8 -*-
"""Voynichizer (voynichizzatore): turns any text into a "Voynich-like" manuscript (in EVA), with the text hidden in the
choice of the words on each page; with the key, the text comes back exactly.

    python voynichizzatore.py encode text.txt --key "a long passphrase" --out manuscript.txt
    python voynichizzatore.py decode manuscript.txt --key "a long passphrase" --out text.txt
    python voynichizzatore.py empty --key "a long passphrase" --out manuscript.txt      (a manuscript with no message)
    python voynichizzatore.py pdf manuscript.txt --out book.pdf                         (the pages, in Voynich-like script)
"""
import argparse, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
VERSIONE = 'v17'
ALIAS = {'codifica': 'encode', 'decodifica': 'decode', 'vuoto': 'empty'}


def main():
    ap = argparse.ArgumentParser(description='Voynichizer: hide a text in a Voynich-like manuscript and read it back with the key')
    ap.add_argument('action', choices=('encode', 'decode', 'empty', 'pdf', 'codifica', 'decodifica', 'vuoto'))
    ap.add_argument('file', nargs='?', help='text to hide (encode) or manuscript to read (decode, pdf)')
    ap.add_argument('--key', '--chiave', dest='key', help='the key (use a long passphrase)')
    ap.add_argument('--out', '--uscita', dest='out', help='output file')
    a = ap.parse_args()
    action = ALIAS.get(a.action, a.action)
    if action != 'empty' and not a.file:
        raise SystemExit('a file is required')
    if action == 'pdf':
        import pagine
        out = a.out or os.path.splitext(a.file)[0] + '.pdf'
        print('written %s: %d pages' % (out, pagine.pdf(a.file, out)))
        return
    if not a.key:
        raise SystemExit('--key is required')
    import canale_sacco, v0
    if action == 'decode':
        try:
            text = canale_sacco.decodifica(v0.carica(a.file), a.key, VERSIONE)
        except Exception as e:
            raise SystemExit('nothing to read: %s' % e)
        if a.out:
            open(a.out, 'w', encoding='utf-8', newline='\n').write(text)
            print('text written to %s (%d characters)' % (a.out, len(text)))
        else:
            sys.stdout.reconfigure(encoding='utf-8', newline='\n')
            sys.stdout.write(text + '\n')
        return
    text = None
    if action == 'encode':
        text = open(a.file, encoding='utf-8').read().replace('\r\n', '\n')
    rows, info = canale_sacco.codifica(text, a.key, VERSIONE)
    v0.salva(rows, a.out or 'manuscript.txt')
    print('written %s: %d lines; message %d bits out of %d available' % (a.out or 'manuscript.txt', len(rows), info['bit_messaggio'], info['capacita_bit']))


if __name__ == '__main__':
    main()
