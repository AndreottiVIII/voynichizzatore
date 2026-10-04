# -*- coding: utf-8 -*-
"""Le misure con cui confrontiamo il Voynich con le lingue note.

Entropia, in bit. h1 dice quanto e' incerto un simbolo preso da solo; h2 quanto
resta incerto il simbolo successivo quando si conosce quello prima; h3 quando
si conoscono i due prima. La differenza h1 - h2 e' quanto aiuta sapere la
lettera precedente: e' la "prevedibilita' della lettera successiva".

Le stime sono quelle dirette (plug-in) sui conteggi. Sottostimano un po' quando
i simboli sono tanti e il campione e' corto, per questo i confronti si fanno
sempre su campioni della stessa lunghezza; accanto diamo anche la correzione
di Miller-Madow, che dice di quanto potrebbe spostarsi il numero.
"""
import math, random
from collections import Counter, defaultdict

LN2 = math.log(2)


def entropia(conteggi):
    n = sum(conteggi.values())
    return -sum(c / n * math.log2(c / n) for c in conteggi.values() if c)


def _miller_madow(conteggi):
    n = sum(conteggi.values())
    return entropia(conteggi) + (len(conteggi) - 1) / (2 * n * LN2)


def condizionate(seq, k_max=3, corretta=False):
    """h0..h_kmax di una sequenza di simboli (stringhe di qualsiasi lunghezza)."""
    stima = _miller_madow if corretta else entropia
    out = {'h0': math.log2(len(set(seq))), 'simboli': len(set(seq)), 'n': len(seq)}
    prima = 0.0
    for k in range(1, k_max + 1):
        grammi = Counter(tuple(seq[i:i + k]) for i in range(len(seq) - k + 1))
        congiunta = stima(grammi)
        out['h%d' % k] = congiunta - prima
        prima = congiunta
    return out


def sequenza(parole, dividi=None, spazio=True):
    """Le parole come flusso di simboli, con o senza lo spazio fra parola e parola."""
    seq = []
    for p in parole:
        seq.extend(dividi(p) if dividi else p)
        if spazio:
            seq.append(' ')
    return seq


def divisore(unita):
    """Taglia una parola in unita' prendendo sempre la piu' lunga che combacia."""
    unita = sorted(set(unita), key=len, reverse=True)

    def dividi(parola):
        out, i = [], 0
        while i < len(parola):
            for u in unita:
                if parola.startswith(u, i):
                    out.append(u)
                    i += len(u)
                    break
            else:
                out.append(parola[i])
                i += 1
        return out
    return dividi


# Nel manoscritto questi gruppi EVA sono un solo segno: la "panchina" c-h, da
# sola o con un gallows sopra. Tenerli separati regala prevedibilita' finta
# (dopo la c viene quasi sempre la h), quindi il confronto onesto li fonde.
GLIFI_EVA = ['cth', 'ckh', 'cph', 'cfh', 'ch', 'sh']


def taglia_a(parole, max_simboli, dividi=None):
    """Tiene le prime parole finche' il flusso (spazi compresi) non supera max_simboli."""
    out, tot = [], 0
    for p in parole:
        lung = len(dividi(p)) if dividi else len(p)
        if tot + lung + 1 > max_simboli:
            break
        out.append(p)
        tot += lung + 1
    return out


# --- misure a livello di parola -------------------------------------------

def distanza(a, b):
    """Distanza di Levenshtein fra due sequenze."""
    if len(a) < len(b):
        a, b = b, a
    prec = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        corr = [i]
        for j, cb in enumerate(b, 1):
            corr.append(min(prec[j] + 1, corr[j - 1] + 1, prec[j - 1] + (ca != cb)))
        prec = corr
    return prec[-1]


def informazione_mutua(coppie):
    """I(X;Y) stimata dai conteggi delle coppie (x, y)."""
    cxy = Counter(coppie)
    cx = Counter(x for x, _ in coppie)
    cy = Counter(y for _, y in coppie)
    return entropia(cx) + entropia(cy) - entropia(cxy)


try:   # la stessa distanza, calcolata in C: cento volte piu' veloce
    from rapidfuzz.distance import Levenshtein as _Lev
    _levenshtein = _Lev.distance
except ImportError:
    _levenshtein = distanza

_DIST = {}


def _dist_norm(a, b):
    """Distanza di Levenshtein divisa per la parola piu' lunga, con memoria:
    le parole frequenti tornano di continuo e ricalcolarle costa."""
    chiave = (a, b) if a <= b else (b, a)
    d = _DIST.get(chiave)
    if d is None:
        d = _DIST[chiave] = _levenshtein(a, b) / max(len(a), len(b))
    return d


def vicinato(blocchi, dividi=None, campioni=6, semi=0):
    """Le parole vicine si somigliano piu' di due parole prese a caso nello
    STESSO blocco (riga, pagina, o tratto di testo lungo uguale)?

    Il confronto con il resto del testo non basta: se il vocabolario cambia da
    una pagina all'altra, due parole vicine si somigliano anche solo perche'
    stanno nella stessa pagina. Qui il termine di paragone e' il blocco stesso,
    quindi resta solo l'effetto dell'essere una accanto all'altra.

    Restituisce, per le coppie di parole adiacenti rispetto alle coppie a caso
    nel blocco: quante volte piu' spesso sono identiche, e il rapporto fra le
    distanze quando non lo sono (sotto 1 = le vicine si somigliano di piu')."""
    rnd = random.Random(semi)
    uguali_adj = coppie_adj = 0
    uguali_caso = coppie_caso = 0.0
    dist_adj, dist_caso = [], []
    for blocco in blocchi:
        b = [tuple(dividi(p)) if dividi else tuple(p) for p in blocco]
        n = len(b)
        if n < 3:
            continue
        for i in range(1, n):
            coppie_adj += 1
            if b[i] == b[i - 1]:
                uguali_adj += 1
            else:
                dist_adj.append(_dist_norm(b[i - 1], b[i]))
        # probabilita' esatta che due posizioni diverse del blocco abbiano la stessa parola
        conti = Counter(b)
        uguali_caso += sum(c * (c - 1) for c in conti.values()) / (n * (n - 1)) * (n - 1)
        coppie_caso += n - 1
        for _ in range(campioni * (n - 1)):
            x, y = rnd.sample(range(n), 2)
            if b[x] != b[y]:
                dist_caso.append(_dist_norm(b[x], b[y]))
    p_adj = uguali_adj / coppie_adj
    p_caso = uguali_caso / coppie_caso
    # Paragone ancora piu' largo: due parole prese a caso in tutto il testo.
    # Dice quanto il blocco e' omogeneo rispetto al resto ("grappoli").
    tutte = [tuple(dividi(p)) if dividi else tuple(p) for blocco in blocchi for p in blocco]
    conti = Counter(tutte)
    n = len(tutte)
    p_testo = sum(c * (c - 1) for c in conti.values()) / (n * (n - 1))
    dist_testo = []
    while len(dist_testo) < len(dist_caso):
        x, y = rnd.randrange(n), rnd.randrange(n)
        if tutte[x] != tutte[y]:
            dist_testo.append(_dist_norm(tutte[x], tutte[y]))
    media = lambda xs: sum(xs) / len(xs)
    return {
        'coppie': coppie_adj,
        'identiche_vicine': p_adj,
        'identiche_caso': p_caso,
        'identiche_testo': p_testo,
        'identiche_rapporto': p_adj / p_caso if p_caso else float('nan'),
        'distanza_rapporto': media(dist_adj) / media(dist_caso),
        'grappolo_identiche': p_caso / p_testo,
        'grappolo_distanza': media(dist_caso) / media(dist_testo),
    }


def spazi(righe, dividi=None, contesto=1):
    """Quanto e' prevedibile lo spazio dal segno (o dai segni) che lo precedono.

    Per ogni posizione dentro una riga, tranne l'ultima: dato il segno appena
    scritto (o gli ultimi `contesto` segni della parola in corso), viene uno
    spazio o no? Restituisce l'entropia di questa scelta prima e dopo aver
    visto il contesto, e la quota di incertezza che il contesto toglie. Se lo
    spazio dipende quasi solo dal segno precedente, e' una regola di scrittura
    (una forma di fine parola), non una scelta di chi scrive."""
    scelte = []
    for r in righe:
        u = [tuple(dividi(p)) if dividi else tuple(p) for p in r]
        for i, parola in enumerate(u):
            for j in range(len(parola)):
                fine = j == len(parola) - 1
                if fine and i == len(u) - 1:
                    continue                      # fine riga: non e' una scelta
                ctx = parola[max(0, j - contesto + 1):j + 1]
                scelte.append((ctx, fine))
    tot = Counter(f for _, f in scelte)
    h_prima = entropia(tot)
    per_ctx = defaultdict(Counter)
    for ctx, f in scelte:
        per_ctx[ctx][f] += 1
    n = len(scelte)
    h_dopo = sum(sum(c.values()) / n * entropia(c) for c in per_ctx.values())
    return {'h_spazio': h_prima, 'h_spazio_dato_contesto': h_dopo,
            'spiegata': 1 - h_dopo / h_prima if h_prima else 0.0,
            'quota_spazi': tot[True] / n}


def a_blocchi(parole, lunghezza):
    """Taglia una sequenza di parole in blocchi consecutivi di lunghezza fissa."""
    return [parole[i:i + lunghezza] for i in range(0, len(parole) - lunghezza + 1, lunghezza)]


def parole_misure(parole, dividi=None, semi=5, max_coppie=8000):
    """Impronta a livello di parola. Le misure sulle coppie di parole vicine
    sono confrontate con le stesse parole rimescolate: quello che resta dopo il
    rimescolamento e' struttura vera, non un effetto della frequenza.

    Tutte queste misure, tranne la lunghezza, non cambiano se ogni parola viene
    cifrata sempre allo stesso modo: sostituzione semplice, cifrario verboso,
    codice parola per parola. Sono il banco di prova di quelle ipotesi."""
    unita = [tuple(dividi(p)) if dividi else tuple(p) for p in parole]
    n = len(unita)
    lunghezze = Counter(len(u) for u in unita)
    freq = Counter(unita)
    media = sum(len(u) for u in unita) / n
    var = sum((len(u) - media) ** 2 for u in unita) / n
    terzo = sum((len(u) - media) ** 3 for u in unita) / n
    ripetute = sum(1 for i in range(1, n) if unita[i] == unita[i - 1]) / (n - 1)
    attese = sum((c / n) ** 2 for c in freq.values())   # due parole a caso uguali

    coppie = list(zip(unita, unita[1:]))
    im_vera = informazione_mutua(coppie)
    rnd = random.Random(0)
    im_mescolate = []
    for s in range(semi):
        m = unita[:]
        rnd.shuffle(m)
        im_mescolate.append(informazione_mutua(list(zip(m, m[1:]))))
    vicine, caso, vicine_div, caso_div = [], [], [], []
    for i in rnd.sample(range(1, n), min(max_coppie, n - 1)):
        a, b = unita[i - 1], unita[i]
        d = _dist_norm(a, b)
        vicine.append(d)
        if a != b:
            vicine_div.append(d)
        c, e = unita[rnd.randrange(n)], unita[rnd.randrange(n)]
        d = _dist_norm(c, e)
        caso.append(d)
        if c != e:
            caso_div.append(d)
    im_mescolata = sum(im_mescolate) / semi
    media_ = lambda xs: sum(xs) / len(xs)
    return {
        'parole': n,
        'tipi': len(freq),
        'tipi_su_parole': len(freq) / n,
        'hapax': sum(1 for c in freq.values() if c == 1) / len(freq),
        'lung_media': media,
        'lung_dev': math.sqrt(var),
        'lung_asimmetria': terzo / var ** 1.5 if var else 0.0,
        'lunghezze': {str(k): v for k, v in sorted(lunghezze.items())},
        'h_parola': entropia(freq),
        'im_vicine': im_vera,
        'im_vicine_mescolate': im_mescolata,
        'im_vicine_eccesso': im_vera - im_mescolata,
        'ripetute': ripetute,
        'ripetute_attese': attese,
        'ripetute_rapporto': ripetute / attese,
        'dist_vicine': media_(vicine),
        'dist_caso': media_(caso),
        'dist_rapporto': media_(vicine) / media_(caso),
        'dist_rapporto_diverse': media_(vicine_div) / media_(caso_div),
    }


def confine(righe, dividi=None, mescolamenti=5, semi=0, solo_interne=False):
    """Dipendenza attraverso lo spazio: quanto l'ultimo segno di una parola
    dice sul primo segno della parola dopo, nella stessa riga, oltre quello che
    si avrebbe rimescolando le parole dentro ogni riga.

    Se ogni parola cifra una o due lettere di un testo continuo, fine di una
    parola e inizio della successiva cifrano lettere consecutive, e dipendono
    l'una dall'altra come le lettere di una lingua. Se le parole sono parole,
    la dipendenza viene solo dalla sintassi ed e' piu' debole."""
    unita = lambda p: tuple(dividi(p)) if dividi else tuple(p)
    righe = [[unita(p) for p in r] for r in righe if len(r) > 1]
    if solo_interne:
        # la prima e l'ultima parola di una riga hanno forme proprie: fuori
        righe = [r[1:-1] for r in righe if len(r) > 3]

    def coppie(rr):
        return [(a[-1], b[0]) for r in rr for a, b in zip(r, r[1:])]

    vera = informazione_mutua(coppie(righe))
    rnd = random.Random(semi)
    mescolate = []
    for _ in range(mescolamenti):
        mescolate.append(informazione_mutua(coppie([rnd.sample(r, len(r)) for r in righe])))
    base = sum(mescolate) / len(mescolate)
    return {'im_confine': vera, 'im_confine_mescolata': base, 'im_confine_eccesso': vera - base}


# --- righe e pagine --------------------------------------------------------

DISTANZE = range(0, 7)
PAROLE_RIGA, RIGHE_PAGINA = 8, 20


def pagine_finte(parole):
    righe = [parole[i:i + PAROLE_RIGA] for i in range(0, len(parole) - PAROLE_RIGA + 1, PAROLE_RIGA)]
    return [righe[i:i + RIGHE_PAGINA] for i in range(0, len(righe), RIGHE_PAGINA)]


def decadimento(pagine, dividi=None, semi=0, coppie_caso=200000, distanze=DISTANZE):
    """Per ogni distanza fra righe: distanza media fra parole diverse e quota
    di parole identiche, divise per gli stessi valori su coppie a caso."""
    unita = lambda p: tuple(dividi(p)) if dividi else tuple(p)
    pagine = [[[unita(p) for p in riga] for riga in pag] for pag in pagine]
    tutte = [p for pag in pagine for riga in pag for p in riga]
    rnd = random.Random(semi)
    dist_caso, ident_caso = [], 0
    for _ in range(coppie_caso):
        a, b = tutte[rnd.randrange(len(tutte))], tutte[rnd.randrange(len(tutte))]
        if a == b:
            ident_caso += 1
        else:
            dist_caso.append(_dist_norm(a, b))
    base_dist = sum(dist_caso) / len(dist_caso)
    base_ident = ident_caso / coppie_caso
    out = {}
    for d in distanze:
        somma = n = ident = tot = 0
        for pag in pagine:
            for i in range(len(pag) - d):
                sopra, sotto = pag[i], pag[i + d]
                if d == 0:
                    coppie = [(sopra[x], sopra[y]) for x in range(len(sopra)) for y in range(x + 1, len(sopra))]
                else:
                    coppie = [(a, b) for a in sopra for b in sotto]
                for a, b in coppie:
                    tot += 1
                    if a == b:
                        ident += 1
                    else:
                        somma += _dist_norm(a, b)
                        n += 1
        out[d] = {'coppie': tot, 'distanza': (somma / n) / base_dist,
                  'identiche': (ident / tot) / base_ident if base_ident else None}
    return out
