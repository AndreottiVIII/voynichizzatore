# -*- coding: utf-8 -*-
"""Il testo del Voynich usato dal voynichizzatore: lo legge da voynich_zl3b.json (vedi il campo "fonte" del file)."""
import json, os
from collections import namedtuple

Riga = namedtuple('Riga', 'pagina inizio_par parole sezione lingua')
_QUI = os.path.dirname(os.path.abspath(__file__))


def leggi(nome='ZL'):
    d = json.load(open(os.path.join(_QUI, 'voynich_zl3b.json'), encoding='utf-8'))
    return [Riga(p, ini, ps, sez, lin) for p, ini, ps, sez, lin in d['righe']]


def testo_corrente(righe, **filtri):
    return righe


def pulita(parola):
    return '?' not in parola and '*' not in parola
