# -*- coding: utf-8 -*-
"""Pezzi di parola (prefisso, centro, finale) e legami ai bordi fra parole vicine, imparati dal testo del Voynich."""
import math
from collections import Counter

import misure, trascrizione

LESSICO, N_MAX, PENALITA = 150, 4, 2.0
G = misure.divisore(misure.GLIFI_EVA)


def segmentatore(parole):
    conta = Counter()
    for w in parole:
        u = G(w)
        for n in range(1, N_MAX + 1):
            for i in range(len(u) - n + 1):
                conta[tuple(u[i:i + n])] += 1
    lessico = {x for x, _ in conta.most_common(LESSICO)} | {x for x in conta if len(x) == 1}
    tot = sum(conta[x] for x in lessico)
    lp = {x: math.log(conta[x] / tot) - PENALITA for x in lessico}

    def taglia(w):
        u = tuple(G(w))
        best = [(0.0, [])] + [(-1e18, None)] * len(u)
        for i in range(1, len(u) + 1):
            for n in range(1, min(N_MAX, i) + 1):
                x = u[i - n:i]
                if x in lp and best[i - n][1] is not None and best[i - n][0] + lp[x] > best[i][0]:
                    best[i] = (best[i - n][0] + lp[x], best[i - n][1] + [''.join(x)])
        return best[len(u)][1]
    return taglia


def parti_di(taglia, w):
    p = taglia(w) or [w]
    if len(p) == 1:
        return ('', p[0], '')
    if len(p) == 2:
        return (p[0], '', p[1])
    return (p[0], ''.join(p[1:-1]), p[-1])


_LEG = {}


def legami():
    """parti(w) dell'e285 e le tre tabelle dei legami fra parole vicine nella riga del Voynich: rapporto fra frequenza
    osservata e attesa con le parti indipendenti, fra 0,2 e 5 (coppie con meno di 5 attese -> 1)."""
    if not _LEG:
        voy = [[w for w in r.parole if trascrizione.pulita(w)] for r in trascrizione.testo_corrente(trascrizione.leggi('ZL')) if r.parole]
        taglia = segmentatore([w for r in voy for w in r])
        cache = {}

        def parti(w):
            if w not in cache:
                cache[w] = parti_di(taglia, w)
            return cache[w]
        tab = {}
        for nome, (i, j) in (('fin_fin', (2, 2)), ('fin_pre', (2, 0)), ('pre_pre', (0, 0))):
            coppie = [(parti(a)[i], parti(b)[j]) for r in voy for a, b in zip(r, r[1:])]
            n = len(coppie)
            cxy, cx, cy = Counter(coppie), Counter(a for a, _ in coppie), Counter(b for _, b in coppie)
            t = {}
            for a in cx:
                for b in cy:
                    e = cx[a] * cy[b] / n
                    if e >= 5:
                        t[(a, b)] = min(5.0, max(0.2, cxy[(a, b)] / e))
            tab[nome] = t
        _LEG.update(parti=parti, tab=tab)
    return _LEG['parti'], _LEG['tab']
