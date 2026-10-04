# -*- coding: utf-8 -*-
"""Il generatore a pezzi (e400-e406): del Voynich vero usa l'impaginazione e le statistiche.

1. Sacco di pagina (sacco.py): parole note dal lessico di sezione e lingua con il carattere nei segni di una pagina tipo
   (kappa) e poca ripetizione (theta); posti delle parole nuove dal modello; parole nuove dal modello dei segni delle parole
   uniche (parole_nuove.FormeUniche).
2. Disposizione (disposizione.py): le parole di ogni pagina vanno nei posti secondo l'affinita' parola-posto e i legami fra
   vicine, con i pesi regolati sul pannello.
I parametri di ogni versione stanno in pezzi_parametri_<versione>.json (v8: e406; v9: e407).
"""
import json, os, sys
from collections import OrderedDict

QUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, QUI)
sys.path.insert(0, os.path.join(QUI, '..', 'analisi'))
sys.path.insert(0, os.path.join(QUI, '..', 'esperimenti'))
import trascrizione

PARAMETRI = os.path.join(QUI, 'pezzi_parametri_%s.json')
_C = {}


def voynich():
    """Righe (pagina, inizio paragrafo, parole pulite) e, per pagina, (sezione, lingua)."""
    if 'v' not in _C:
        rr, tipo = [], OrderedDict()
        for r in trascrizione.testo_corrente(trascrizione.leggi('ZL')):
            ps = [w for w in r.parole if trascrizione.pulita(w)] if r.parole else []
            if ps:
                rr.append((r.pagina, bool(r.inizio_par), ps))
                tipo.setdefault(r.pagina, (r.sezione, r.lingua or '?'))
        _C['v'] = (rr, tipo)
    return _C['v']


def pezzi():
    if 's' not in _C:
        import disposizione, sacco
        rr, tipo = voynich()
        _C['s'], _C['d'] = sacco.Sacco(rr, tipo), disposizione.Disposizione(rr)
    return _C['s'], _C['d']


def sacco_di(seme, x):
    s, _ = pezzi()
    s.FORME = dict(x['forme'])
    s.POSIZIONALE = x.get('carattere') == 'posizionale'
    s.GAMMA = x.get('gamma', 1.0)
    return s.genera(seme, theta=x['theta'], nuove='inventate', kappa=x['kappa'], posti=x.get('posti', 'modello'))


def corpo(seme, versione='v8', parametri=None):
    """Il manoscritto senza messaggio per il seme dato: righe (pagina, inizio paragrafo, parole)."""
    x = parametri or json.load(open(PARAMETRI % versione, encoding='utf-8'))
    _, d = pezzi()
    return d.disponi(sacco_di(1000003 * seme + 17, x), 1000003 * seme + 18, 'D3', pesi=x['pesi_disposizione'])
