# -*- coding: utf-8 -*-
"""Voynichizzatore: un testo normale diventa un manoscritto "alla Voynich" (in EVA) con il testo nascosto nella scelta delle
parole di ogni pagina; con la parola chiave il testo torna esatto.

    python voynichizzatore.py codifica testo.txt --chiave PAROLA --uscita manoscritto.txt
    python voynichizzatore.py decodifica manoscritto.txt --chiave PAROLA --uscita testo.txt
    python voynichizzatore.py vuoto --chiave PAROLA --uscita manoscritto.txt      (manoscritto senza messaggio)
"""
import argparse, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
VERSIONE = 'v17'


def main():
    ap = argparse.ArgumentParser(description='Voynichizzatore')
    ap.add_argument('azione', choices=('codifica', 'decodifica', 'vuoto'))
    ap.add_argument('file', nargs='?')
    ap.add_argument('--chiave', required=True)
    ap.add_argument('--uscita')
    a = ap.parse_args()
    import canale_sacco, v0
    if a.azione == 'decodifica':
        try:
            testo = canale_sacco.decodifica(v0.carica(a.file), a.chiave, VERSIONE)
        except Exception as e:
            raise SystemExit('niente da leggere: %s' % e)
        if a.uscita:
            open(a.uscita, 'w', encoding='utf-8', newline='\n').write(testo)
            print('testo scritto in %s (%d caratteri)' % (a.uscita, len(testo)))
        else:
            sys.stdout.reconfigure(encoding='utf-8', newline='\n')
            sys.stdout.write(testo + '\n')
        return
    testo = None
    if a.azione == 'codifica':
        testo = open(a.file, encoding='utf-8').read().replace('\r\n', '\n')
    righe, info = canale_sacco.codifica(testo, a.chiave, VERSIONE)
    v0.salva(righe, a.uscita or 'manoscritto.txt')
    print('scritto %s: %d righe; messaggio %d bit su %d disponibili' % (a.uscita or 'manoscritto.txt', len(righe), info['bit_messaggio'], info['capacita_bit']))


if __name__ == '__main__':
    main()
