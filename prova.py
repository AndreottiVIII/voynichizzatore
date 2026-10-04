# -*- coding: utf-8 -*-
"""Read-back test on another computer. Usage: python prova.py
1. reads prova/manoscritto_di_prova.txt (written on the computer that prepared the package) and compares it with
   prova/testo_di_prova.txt;
2. writes a new manuscript here with the same text and key, and reads it back;
3. says whether the manuscript written here is identical to the bundled one (it does not have to be)."""
import os, platform, sys

QUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, QUI)
KEY = 'read-back test on another computer'


def main():
    import canale_sacco, v0, voynichizzatore
    import numpy, scipy, sklearn
    v = voynichizzatore.VERSIONE
    text = open(os.path.join(QUI, 'prova', 'testo_di_prova.txt'), encoding='utf-8').read()
    print('Python %s on %s %s; numpy %s, scipy %s, scikit-learn %s' % (platform.python_version(), platform.system(), platform.machine(),
                                                                       numpy.__version__, scipy.__version__, sklearn.__version__))
    bundled = v0.carica(os.path.join(QUI, 'prova', 'manoscritto_di_prova.txt'))
    try:
        one = canale_sacco.decodifica(bundled, KEY, v) == text
    except Exception as e:
        one = False
        print('   error while reading back: %s' % e)
    print('1. the manuscript written elsewhere reads back here: %s' % ('YES' if one else 'NO'))
    print('   (now writing a new manuscript: a couple of minutes)')
    again, _ = canale_sacco.codifica(text, KEY, v, verifica=False)
    v0.salva(again, os.path.join(QUI, 'prova', 'manoscritto_rifatto.txt'))
    two = canale_sacco.decodifica(v0.carica(os.path.join(QUI, 'prova', 'manoscritto_rifatto.txt')), KEY, v) == text
    print('2. a manuscript written here reads back here: %s' % ('YES' if two else 'NO'))
    a = open(os.path.join(QUI, 'prova', 'manoscritto_di_prova.txt'), encoding='utf-8').read()
    b = open(os.path.join(QUI, 'prova', 'manoscritto_rifatto.txt'), encoding='utf-8').read()
    print('3. the manuscript written here is identical to the bundled one: %s (it does not have to be)' % ('YES' if a == b else 'NO'))


if __name__ == '__main__':
    main()
