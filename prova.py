# -*- coding: utf-8 -*-
"""Prova di rilettura su un altro computer. Usa: python prova.py
1. rilegge prova/manoscritto_di_prova.txt (scritto sul computer che ha preparato il pacchetto) e lo confronta con
   prova/testo_di_prova.txt;
2. scrive qui un manoscritto nuovo con lo stesso testo e la stessa chiave e lo rilegge;
3. dice se il manoscritto scritto qui coincide con quello incluso (non serve che coincida)."""
import os, platform, sys

QUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, QUI)
CHIAVE = 'prova di rilettura su un altro computer'


def main():
    import canale_sacco, v0, voynichizzatore
    import numpy, scipy, sklearn
    v = voynichizzatore.VERSIONE
    testo = open(os.path.join(QUI, 'prova', 'testo_di_prova.txt'), encoding='utf-8').read()
    print('Python %s su %s %s; numpy %s, scipy %s, scikit-learn %s' % (platform.python_version(), platform.system(), platform.machine(),
                                                                       numpy.__version__, scipy.__version__, sklearn.__version__))
    incluso = v0.carica(os.path.join(QUI, 'prova', 'manoscritto_di_prova.txt'))
    try:
        uno = canale_sacco.decodifica(incluso, CHIAVE, v) == testo
    except Exception as e:
        uno = False
        print('   errore nella rilettura: %s' % e)
    print('1. il manoscritto scritto altrove si rilegge qui: %s' % ('SI' if uno else 'NO'))
    print('   (ora scrivo un manoscritto nuovo: un paio di minuti)')
    rifatto, _ = canale_sacco.codifica(testo, CHIAVE, v, verifica=False)
    v0.salva(rifatto, os.path.join(QUI, 'prova', 'manoscritto_rifatto.txt'))
    due = canale_sacco.decodifica(v0.carica(os.path.join(QUI, 'prova', 'manoscritto_rifatto.txt')), CHIAVE, v) == testo
    print('2. un manoscritto scritto qui si rilegge qui: %s' % ('SI' if due else 'NO'))
    a = open(os.path.join(QUI, 'prova', 'manoscritto_di_prova.txt'), encoding='utf-8').read()
    b = open(os.path.join(QUI, 'prova', 'manoscritto_rifatto.txt'), encoding='utf-8').read()
    print('3. il manoscritto scritto qui coincide con quello incluso: %s (non serve che coincida)' % ('SI' if a == b else 'NO'))


if __name__ == '__main__':
    main()
