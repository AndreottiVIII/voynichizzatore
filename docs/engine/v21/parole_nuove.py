# -*- coding: utf-8 -*-
"""Parole nuove: modi di inventare parole che non sono nel Voynich, con la forma delle sue parole uniche (e403).

- variante: una modifica (operatore empirico dell'e241) di una parola di partenza;
- trigrammi: modello a trigrammi di segni imparato sulle parole uniche;
- unione: due parole scritte attaccate.
Ogni parola restituita e' ben formata per l'operatore (o campionata dal modello), non attestata e non gia' usata.
"""
import os, random, sys
from collections import Counter, defaultdict

QUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, QUI)
sys.path.insert(0, os.path.join(QUI, '..', 'analisi'))
sys.path.insert(0, os.path.join(QUI, '..', 'esperimenti'))
import misure

D = misure.divisore(misure.GLIFI_EVA)
QUOTE_MISTA = (0.72, 0.14, 0.14)      # variante, unione, trigrammi: descrizione delle parole uniche (preregistrazione e403)


class Trigrammi:
    def __init__(self, parole):
        self.t = defaultdict(Counter)
        for w in parole:
            u = ('^', '^') + tuple(D(w)) + ('$',)
            for a, b, c in zip(u, u[1:], u[2:]):
                self.t[(a, b)][c] += 1
        self.t = {k: (list(v), list(v.values())) for k, v in self.t.items()}

    def campiona(self, rnd):
        a, b, out = '^', '^', []
        while len(out) < 14:
            segni, pesi = self.t[(a, b)]
            c = rnd.choices(segni, pesi)[0]
            if c == '$':
                break
            out.append(c)
            a, b = b, c
        return ''.join(out)


class ParoleNuove:
    """conta: Counter delle parole del testo da cui si impara; mod: operatore di variante (c2['mod'] di e251._prepara)."""

    def __init__(self, conta, mod):
        self.att = set(conta)
        self.mod = mod
        self.tipi_libro = sorted(w for w, n in conta.items() if n >= 2)
        self.tri = Trigrammi(sorted(w for w, n in conta.items() if n == 1))
        self.usate = set()

    def _nuova(self, w):
        if w and len(w) >= 2 and w not in self.att and w not in self.usate:
            self.usate.add(w)
            return True
        return False

    def trigrammi(self, rnd):
        for _ in range(200):
            w = self.tri.campiona(rnd)
            if self._nuova(w):
                return w
        raise RuntimeError('trigrammi: nessuna parola nuova')

    def variante(self, basi, rnd):
        for _ in range(60):
            u = tuple(D(basi[rnd.randrange(len(basi))]))
            x = self.mod.modifica(u, rnd)
            if self.mod.valida(x) and self._nuova(''.join(x)):
                return ''.join(x)
        return self.trigrammi(rnd)

    def unione(self, basi, rnd):
        for _ in range(60):
            w = basi[rnd.randrange(len(basi))] + basi[rnd.randrange(len(basi))]
            if len(D(w)) <= 12 and self._nuova(w):
                return w
        return self.trigrammi(rnd)

    def inventa(self, modo, tipi_pagina, rnd):
        """modo: 'variante-libro', 'variante-pagina', 'trigrammi', 'mista'. tipi_pagina: tipi non unici della pagina."""
        pagina = tipi_pagina or self.tipi_libro
        if modo == 'variante-libro':
            return self.variante(self.tipi_libro, rnd)
        if modo == 'variante-pagina':
            return self.variante(pagina, rnd)
        if modo == 'trigrammi':
            return self.trigrammi(rnd)
        x = rnd.random()
        if x < QUOTE_MISTA[0]:
            return self.variante(pagina, rnd)
        if x < QUOTE_MISTA[0] + QUOTE_MISTA[1]:
            return self.unione(pagina, rnd)
        return self.trigrammi(rnd)


class FormeUniche:
    """Forma delle parole nuove imparata sulle parole uniche (e403b): trigrammi di segni con la lunghezza controllata,
    per tipo di posto (riga prima di paragrafo o no x prima, seconda, in mezzo, ultima), con scelta secondo il profilo
    dei segni della pagina. rr: righe (pagina, inizio paragrafo, parole) del testo da cui si impara."""
    DECIMO, CANDIDATE, ALFA = 0.1, 6, 50.0
    COMUNE, MINIMO_CONTESTO = 0.01, 3      # e405: segni comuni (quota nel libro); contesto di tre segni visto almeno 3 volte

    def __init__(self, rr, comuni=False, quattro=False, forza=1.0, unioni=0.0, unioni_valide=False, giuntura=0.0):
        """comuni: il profilo pesa solo i segni comuni (e405, N1); quattro: modello a quattro segni con ripiego sui
        trigrammi (N2); forza: esponente del peso di profilo nella scelta fra candidate (N3)."""
        self.comuni, self.quattro, self.forza = comuni, quattro, forza
        self.unioni = unioni        # e407: probabilita' che una parola nuova di almeno 6 segni sia l'unione di due parole note della pagina
        self.unioni_valide = unioni_valide      # e413: l'unione si accetta solo se ogni terna di segni e' vista nelle parole uniche
        self.giuntura = giuntura                # e414: probabilita' minima delle due terne di segni a cavallo della giuntura
        self.campioni = self.scartate = 0
        import math
        from disposizione import posizione
        self.log = math.log
        self.posizione = posizione
        conta = Counter(w for _, _, ps in rr for w in ps)
        self.att = set(conta)
        self.usate = set()
        tri, lung = defaultdict(lambda: defaultdict(Counter)), defaultdict(list)
        qua = defaultdict(lambda: defaultdict(Counter))
        for _, ini, ps in rr:
            for j, w in enumerate(ps):
                if conta[w] == 1:
                    u = tuple(D(w))
                    for cl in ('tutte', 4 * bool(ini) + posizione(j, len(ps))):
                        lung[cl].append(len(u))
                        v = ('^', '^') + u + ('$',)
                        for a, b, c in zip(v, v[1:], v[2:]):
                            tri[cl][(a, b)][c] += 1
                        v4 = ('^',) + v
                        for a, b, c, d in zip(v4, v4[1:], v4[2:], v4[3:]):
                            qua[cl][(a, b, c)][d] += 1
        self.lung = dict(lung)
        self.tri = {}
        for cl, t in tri.items():
            tab = {}
            for k, v in tri['tutte'].items():
                x = Counter({c: self.DECIMO * n for c, n in v.items()}) if cl != 'tutte' else Counter(v)
                if cl != 'tutte':
                    x.update(t.get(k, {}))
                tab[k] = (sorted(x), [x[c] for c in sorted(x)])
            self.tri[cl] = tab
        self.qua = {}
        for cl, t in qua.items():
            tab = {}
            for k, v in qua['tutte'].items():
                x = Counter({c: self.DECIMO * n for c, n in v.items()}) if cl != 'tutte' else Counter(v)
                if cl != 'tutte':
                    x.update(t.get(k, {}))
                if sum(v.values()) >= self.MINIMO_CONTESTO:
                    tab[k] = (sorted(x), [x[c] for c in sorted(x)])
            self.qua[cl] = tab
        libro = Counter(g for w, n in conta.items() if n >= 2 for g in D(w) for _ in range(n))
        self.q_libro = {g: n / sum(libro.values()) for g, n in libro.items()}
        self.conta = conta

    def profilo(self, parole_pagina):
        """Logaritmo del rapporto pagina / libro per ogni segno, dalle parole non uniche della pagina."""
        c = Counter(g for w in parole_pagina if self.conta.get(w, 0) >= 2 for g in D(w))
        n = sum(c.values())
        return {g: self.log((c[g] + self.ALFA * q) / (n + self.ALFA) / q) for g, q in self.q_libro.items()
                if not self.comuni or q >= self.COMUNE}

    def _una(self, cl, L, rnd):
        tab = self.tri[cl]
        tab4 = self.qua[cl] if self.quattro else {}
        vicina = None
        for _ in range(400):
            z, a, b, out = '^', '^', '^', []
            while len(out) <= L + 1:
                segni, pesi = tab4.get((z, a, b)) or tab[(a, b)]
                c = rnd.choices(segni, pesi)[0]
                if c == '$':
                    break
                out.append(c)
                z, a, b = a, b, c
            w = ''.join(out)
            self.campioni += 1
            self.scartate += w in self.att
            if len(w) >= 2 and w not in self.att and w not in self.usate:
                if len(out) == L:
                    return w
                if vicina is None or abs(len(out) - L) < abs(len(tuple(D(vicina))) - L):
                    vicina = w
        return vicina

    def ben_formata(self, w):
        """Ogni terna di segni consecutivi (inizio e fine compresi) e' stata vista nelle parole uniche."""
        u = ('^', '^') + tuple(D(w)) + ('$',)
        tab = self.tri['tutte']
        return all((a, b) in tab and c in tab[(a, b)][0] for a, b, c in zip(u, u[1:], u[2:]))

    def giuntura_probabile(self, a, b):
        """Le due terne di segni a cavallo della giuntura hanno probabilita' condizionata almeno self.giuntura nel modello
        dei segni delle parole uniche."""
        ua, ub = ('^', '^') + tuple(D(a)), tuple(D(b)) + ('$',)
        tab = self.tri['tutte']
        for ctx, c in (((ua[-2], ua[-1]), ub[0]), ((ua[-1], ub[0]), ub[1])):
            if ctx not in tab:
                return False
            segni, pesi = tab[ctx]
            if c not in segni or pesi[segni.index(c)] / sum(pesi) < self.giuntura:
                return False
        return True

    def _unione(self, per_lung, L, rnd):
        for _ in range(20):
            la = rnd.randrange(2, L - 1)
            if per_lung.get(la) and per_lung.get(L - la):
                a, b = rnd.choice(per_lung[la]), rnd.choice(per_lung[L - la])
                w = a + b
                if (w not in self.att and w not in self.usate and (not self.unioni_valide or self.ben_formata(w))
                        and (not self.giuntura or self.giuntura_probabile(a, b))):
                    return w
        return None

    def inventa(self, modo, classe, profilo, rnd, per_lung=None):
        """modo: 'T-L' (lunghezza), 'T-LP' (anche tipo di posto), 'T-LPS' (anche profilo della pagina)."""
        cl = 'tutte' if modo == 'T-L' else classe
        if cl not in self.tri:
            cl = 'tutte'
        cand = []
        for _ in range(self.CANDIDATE if modo == 'T-LPS' else 1):
            w = None
            while w is None:
                L = rnd.choice(self.lung[cl])
                if self.unioni and per_lung and L >= 6 and rnd.random() < self.unioni:
                    w = self._unione(per_lung, L, rnd)
                if w is None:
                    w = self._una(cl, L, rnd)
            cand.append(w)
        if len(cand) > 1:
            import math
            pesi = [math.exp(self.forza * sum(profilo.get(g, 0.0) for g in D(w))) for w in cand]
            w = rnd.choices(cand, pesi)[0]
        else:
            w = cand[0]
        self.usate.add(w)
        return w
