# -*- coding: utf-8 -*-
"""Il sacco di pagina: quali parole stanno in ogni pagina (e404).

Parole note (viste almeno due volte nel libro): pescate dal lessico della sezione e lingua della pagina (occorrenze delle
altre pagine), con ripetizione dentro la pagina: a ogni parola, con probabilita' n/(n+theta) si ripete una parola nota gia'
messa nella pagina (n = quante ce ne sono), altrimenti si pesca dal lessico. theta = None: nessuna ripetizione (K1).
Parole nuove: vere, oppure inventate da parole_nuove.FormeUniche (T-LPS) nei posti delle parole uniche vere.
"""
import bisect, itertools, math, os, random, sys
from collections import Counter, OrderedDict

QUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, QUI)
sys.path.insert(0, os.path.join(QUI, '..', 'analisi'))
sys.path.insert(0, os.path.join(QUI, '..', 'esperimenti'))


class Sacco:
    """rr: righe (pagina, inizio paragrafo, parole) del Voynich; tipo: pagina -> (sezione, lingua)."""

    def __init__(self, rr, tipo):
        self.rr, self.tipo = rr, tipo
        self.conta = Counter(w for _, _, ps in rr for w in ps)
        note = OrderedDict()
        for p, _, ps in rr:
            note.setdefault(p, []).extend(w for w in ps if self.conta[w] >= 2)
        self.pagine = list(note)
        self.lessico = {}
        for p in self.pagine:
            serb = [w for q in self.pagine if q != p and tipo[q] == tipo[p] for w in note[q]]
            if len(serb) < 500:
                serb = [w for q in self.pagine if q != p and tipo[q][0] == tipo[p][0] for w in note[q]]
            if len(serb) < 500:
                serb = [w for q in self.pagine if q != p for w in note[q]]
            self.lessico[p] = serb
        self._fu = None
        self.note = note
        self._car = {}
        # posti delle parole nuove (e406): quota di parole uniche per tipo di posto, e per pagina
        from disposizione import posizione
        tot, uni, ptot, puni = Counter(), Counter(), Counter(), Counter()
        for p, ini, ps in rr:
            for j, w in enumerate(ps):
                c = 4 * bool(ini) + posizione(j, len(ps))
                tot[c] += 1
                ptot[p] += 1
                if self.conta[w] == 1:
                    uni[c] += 1
                    puni[p] += 1
        self.quota_posto = {c: uni[c] / tot[c] for c in tot}
        media = sum(uni.values()) / sum(tot.values())
        self.molt_pagina = {p: (puni[p] / ptot[p]) / media for p in ptot}

    # --- carattere della pagina (e404b) ---
    ALFA = 50.0

    POSIZIONALE = False     # e411: il carattere distingue il primo segno, l'ultimo e quelli in mezzo
    GAMMA = 1.0             # e413: esponente sulla frequenza delle parole del lessico (1 = frequenza cosi' com'e')

    def _segni(self, parole):
        import misure
        if not hasattr(self, '_D'):
            self._D = misure.divisore(misure.GLIFI_EVA)
            self._cache_segni = {}
            self._cache_pos = {}
        c = Counter()
        for w in parole:
            u = self._cache_segni.get(w)
            if u is None:
                d = self._D(w)
                u = self._cache_segni[w] = Counter(d)
                n = len(d)
                self._cache_pos[w] = Counter((g, 'i' if j == 0 else ('f' if j == n - 1 else 'm')) for j, g in enumerate(d))
            c.update(self._cache_pos[w] if self.POSIZIONALE else u)
        return c

    def carattere(self, p, rnd):
        """Scostamenti dei segni (logaritmo del rapporto con la sezione) di un'altra pagina vera, a caso, della stessa
        sezione e lingua; e il lessico di sezione della pagina p come (tipi, conteggi, segni per tipo)."""
        chiave = (p, self.POSIZIONALE)
        if chiave not in self._car:
            cs = Counter(self.lessico[p])
            tipi = sorted(cs)
            self._segni(tipi)
            fs = self._segni(self.lessico[p])
            n = sum(fs.values())
            self._car[chiave] = (tipi, [cs[w] for w in tipi], {g: x / n for g, x in fs.items()})
        tipi, conti, fsez = self._car[chiave]
        altre = [q for q in self.pagine if q != p and self.tipo[q] == self.tipo[p] and len(self.note[q]) >= 40]
        altre = altre or [q for q in self.pagine if q != p and len(self.note[q]) >= 40]
        q = altre[rnd.randrange(len(altre))]
        cq = self._segni(self.note[q])
        nq = sum(cq.values())
        delta = {g: math.log((cq[g] + self.ALFA * f) / (nq + self.ALFA) / f) for g, f in fsez.items()}
        self.pagina_tipo = q
        return tipi, conti, delta

    def pesi_carattere(self, tipi, conti, delta, kappa):
        cache = self._cache_pos if self.POSIZIONALE else self._cache_segni
        pesi = [c ** self.GAMMA * math.exp(kappa * sum(delta.get(g, 0.0) * k for g, k in cache[w].items())) for w, c in zip(tipi, conti)]
        return list(itertools.accumulate(pesi))

    FORME = {}      # argomenti di parole_nuove.FormeUniche (e405: comuni, quattro, forza)

    def forme(self):
        chiave = tuple(sorted(self.FORME.items()))
        if self._fu is None or self._fu[0] != chiave:
            import parole_nuove
            self._fu = (chiave, parole_nuove.FormeUniche(self.rr, **self.FORME))
        self._fu[1].usate = set()
        return self._fu[1]

    def genera(self, seme, theta=None, nuove='vere', kappa=None, posti='veri'):
        """Il testo con le parole note pescate (e, con nuove='inventate', le uniche sostituite); stessa impaginazione.
        kappa: forza del carattere della pagina (None: nessun carattere, e le parole nuove seguono il profilo della pagina
        vera, come nell'e404; con kappa le parole nuove seguono il profilo delle parole note generate).
        posti: 'veri' (le parole nuove stanno dove stanno le parole uniche vere) o 'modello' (e406: ogni posto e' nuovo con
        probabilita' quota del tipo di posto x moltiplicatore della pagina tipo; richiede kappa)."""
        from disposizione import posizione
        rnd = random.Random(seme)
        fu = self.forme() if nuove == 'inventate' else None
        per = OrderedDict()
        for i, (p, _, _) in enumerate(self.rr):
            per.setdefault(p, []).append(i)
        out = {}
        for p, idx in per.items():
            gia = []
            serb = self.lessico[p]
            if kappa is not None:
                tipi, conti, delta = self.carattere(p, rnd)
                cum = self.pesi_carattere(tipi, conti, delta, kappa)
            nuovo = {}
            for i in idx:
                _, ini, ps = self.rr[i]
                if posti == 'modello':
                    m = self.molt_pagina[self.pagina_tipo]
                    nuovo[i] = [rnd.random() < min(0.95, self.quota_posto[4 * bool(ini) + posizione(j, len(ps))] * m) for j in range(len(ps))]
                else:
                    nuovo[i] = [self.conta[w] == 1 for w in ps]
            righe = {}
            for i in idx:
                riga = []
                for j, w in enumerate(self.rr[i][2]):
                    if not nuovo[i][j]:
                        if theta is not None and gia and rnd.random() < len(gia) / (len(gia) + theta):
                            w = gia[rnd.randrange(len(gia))]
                        elif kappa is not None:
                            w = tipi[bisect.bisect(cum, rnd.random() * cum[-1])]
                        else:
                            w = serb[rnd.randrange(len(serb))]
                        gia.append(w)
                    riga.append(w)
                righe[i] = riga
            if fu:
                profilo = fu.profilo(gia if kappa is not None else [w for i in idx for w in self.rr[i][2]])
                per_lung = None
                if fu.unioni:
                    self._segni(set(gia))
                    per_lung = {}
                    for w in sorted(set(gia)):
                        per_lung.setdefault(sum(self._cache_segni[w].values()), []).append(w)
                for i in idx:
                    _, ini, ps = self.rr[i]
                    for j, w in enumerate(ps):
                        if nuovo[i][j]:
                            righe[i][j] = fu.inventa('T-LPS', 4 * bool(ini) + posizione(j, len(ps)), profilo, rnd, per_lung)
            for i in idx:
                out[i] = (p, self.rr[i][1], righe[i])
        return [out[i] for i in range(len(self.rr))]
