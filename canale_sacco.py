# -*- coding: utf-8 -*-
"""Il messaggio nel sacco (e409): il testo cifrato sceglie, pagina per pagina, quante volte compare ogni parola nota.

Il sacco delle parole note di una pagina e' un campione multinomiale dal lessico di sezione pesato dal carattere della
pagina (sacco.py). Dato il numero n di posti per parole note, i conteggi si estraggono tipo per tipo, in ordine fisso, come
catena di binomiali; ogni binomiale e' codificata una decisione alla volta ("ancora una?") con la codifica aritmetica
binaria di v1 (Nasconditore sceglie dai bit del messaggio, Rilettore rilegge i bit dai conteggi).
Dalla chiave, e non dal messaggio, vengono: la pagina tipo di ogni pagina, i posti delle parole nuove, le parole nuove, la
disposizione. Ogni pagina e ogni uso ha un generatore suo, cosi' la decodifica ricalcola solo le distribuzioni.

    codifica(testo, chiave, versione) -> righe, informazioni        decodifica(righe, chiave, versione) -> testo
"""
import hashlib, hmac, json, math, os, random, sys, zlib
from collections import Counter, OrderedDict

QUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, QUI)
sys.path.insert(0, os.path.join(QUI, '..', 'analisi'))
sys.path.insert(0, os.path.join(QUI, '..', 'esperimenti'))
import pezzi, v0, v1

SCALA = 1 << 40          # i pesi dei tipi diventano interi su questa scala


# ------------------------------------------------------------------ cifratura robusta (v15): scrypt, flusso SHAKE-256, HMAC
# Con "cifra": "scrypt" nei parametri la chiave passa per scrypt (ogni tentativo di indovinarla costa caro), il messaggio
# compresso e' cifrato con un flusso SHAKE-256 e porta un'etichetta HMAC-SHA256 di 8 byte: con la chiave sbagliata la
# decodifica dice "chiave errata" in modo certo. Anche i generatori casuali di pagina derivano dalla chiave maestra.
SALE = b'voynichizzatore/canale-sacco/1'
ETICHETTA = 8
_MAESTRE = {}
_CIFRA = [None]         # la cifratura in uso nella chiamata corrente (None: quella della v10-v14)


def maestra(chiave):
    if chiave not in _MAESTRE:
        _MAESTRE[chiave] = hashlib.scrypt(chiave.encode('utf-8'), salt=SALE, n=1 << 15, r=8, p=1, maxmem=1 << 26, dklen=32)
    return _MAESTRE[chiave]


def _bit(dati):
    return [(byte >> (7 - i)) & 1 for byte in dati for i in range(8)]


def bit_cifrati(testo, chiave, riempimento=30000):
    """(bit del messaggio cifrato, bit di riempimento, byte compressi): lunghezza (4 byte), etichetta (8), testo compresso."""
    k = maestra(chiave)
    dati = zlib.compress(testo.encode('utf-8'), 9) if testo is not None else b''
    chiaro = (len(dati).to_bytes(4, 'big') + hmac.new(k, b'etichetta' + dati, hashlib.sha256).digest()[:ETICHETTA] + dati) if testo is not None else b''
    flusso = hashlib.shake_256(k + b'flusso').digest(len(chiaro) + riempimento)
    cifrato = bytes(a ^ b for a, b in zip(chiaro, flusso))
    return _bit(cifrato), _bit(flusso[len(chiaro):]), len(dati)


def testo_dai_bit(bit, chiave):
    k = maestra(chiave)
    dati = v0.da_bit(bit)
    flusso = hashlib.shake_256(k + b'flusso').digest(len(dati))
    chiaro = bytes(a ^ b for a, b in zip(dati, flusso))
    n = int.from_bytes(chiaro[:4], 'big')
    if not 0 < n <= len(chiaro) - 4 - ETICHETTA:
        raise ValueError('chiave errata, o manoscritto senza messaggio')
    etichetta, corpo = chiaro[4:4 + ETICHETTA], chiaro[4 + ETICHETTA:4 + ETICHETTA + n]
    if not hmac.compare_digest(etichetta, hmac.new(k, b'etichetta' + corpo, hashlib.sha256).digest()[:ETICHETTA]):
        raise ValueError('chiave errata, o manoscritto alterato')
    return zlib.decompress(corpo).decode('utf-8')


def generatore(chiave, pagina, uso):
    etichetta = 'sacco|%s|%s' % (uso, pagina)
    if _CIFRA[0] == 'scrypt':
        return random.Random(int.from_bytes(hmac.new(maestra(chiave), etichetta.encode('utf-8'), hashlib.sha256).digest()[:16], 'big'))
    return random.Random(v0.numero(chiave, etichetta))


def distribuzione(s, pagina, chiave, kappa):
    """I tipi del lessico della pagina, dal piu' pesante, con i pesi interi; e la pagina tipo scelta dalla chiave."""
    tipi, conti, delta = s.carattere(pagina, generatore(chiave, pagina, 'carattere'))
    tipo_pagina = s.pagina_tipo
    cum = s.pesi_carattere(tipi, conti, delta, kappa)
    pesi = [cum[0]] + [b - a for a, b in zip(cum, cum[1:])]
    tot = cum[-1]
    interi = [max(1, int(round(x / tot * SCALA))) for x in pesi]
    ordine = sorted(range(len(tipi)), key=lambda i: (-interi[i], tipi[i]))
    return [tipi[i] for i in ordine], [interi[i] for i in ordine], tipo_pagina


def _passi(n, p):
    """Per una binomiale(n, p): le frequenze f0 (su v1.TOT) di 'mi fermo a j' dato che sono arrivato a j, j = 0, 1, ..."""
    q = 1.0 - p
    pmf = math.exp(n * math.log(q)) if q > 0 else 0.0
    resto = 1.0
    j = 0
    while j < n:
        h = pmf / resto if resto > 0 else 1.0
        yield min(v1.TOT - 1, max(1, int(round(h * v1.TOT))))
        resto -= pmf
        pmf = pmf * (n - j) / (j + 1) * (p / q) if q > 0 else 0.0
        j += 1
        if resto <= 0:
            resto = 1e-300


def conteggi_dai_bit(nasc, interi, n):
    """I conteggi dei tipi (stesso ordine dei pesi) estratti dai bit del messaggio; la somma e' n."""
    out, resta, W = [], n, sum(interi)
    for k, w in enumerate(interi):
        if resta == 0:
            out.append(0)
            continue
        if k == len(interi) - 1:
            out.append(resta)
            resta = 0
            continue
        c = 0
        for f0 in _passi(resta, w / W):
            if nasc.simbolo(f0) == 0:
                break
            c += 1
        out.append(c)
        resta -= c
        W -= w
    return out


def bit_dai_conteggi(ril, interi, conteggi):
    resta, W = sum(conteggi), sum(interi)
    for k, (w, c) in enumerate(zip(interi, conteggi)):
        if resta == 0 or k == len(interi) - 1:
            break
        j = 0
        for f0 in _passi(resta, w / W):
            if j == c:
                ril.simbolo(0, f0)
                break
            ril.simbolo(1, f0)
            j += 1
        resta -= c
        W -= w


_GABBIE = {}


def statistiche_gabbia(s):
    """Per la gabbia statistica (e415): per sezione e lingua il numero di righe per pagina, la lunghezza dei paragrafi in
    righe e la larghezza della pagina (mediana delle parole per riga); per tutto il libro, il rapporto fra le parole di una
    riga e la larghezza della sua pagina, secondo il ruolo della riga (prima, ultima, in mezzo, unica del paragrafo)."""
    if id(s) not in _GABBIE:
        import statistics
        per = OrderedDict()
        for i, (p, _, _) in enumerate(s.rr):
            per.setdefault(p, []).append(i)
        righe, paragrafi, larghezze, rapporti = {}, {}, {}, {'prima': [], 'ultima': [], 'mezzo': [], 'sola': []}
        for p, idx in per.items():
            gab = [(s.rr[i][1], len(s.rr[i][2])) for i in idx]
            larg = statistics.median(n for _, n in gab)
            par, cur = [], []
            for ini, n in gab:
                if ini and cur:
                    par.append(cur)
                    cur = []
                cur.append(n)
            par.append(cur)
            for chiave_tipo in (s.tipo[p], (s.tipo[p][0], None), None):
                righe.setdefault(chiave_tipo, []).append(len(gab))
                larghezze.setdefault(chiave_tipo, []).append(larg)
                paragrafi.setdefault(chiave_tipo, []).extend(len(x) for x in par)
            for x in par:
                for j, n in enumerate(x):
                    ruolo = 'sola' if len(x) == 1 else ('prima' if j == 0 else ('ultima' if j == len(x) - 1 else 'mezzo'))
                    rapporti[ruolo].append(n / larg)
        _GABBIE[id(s)] = (righe, paragrafi, larghezze, rapporti)
    return _GABBIE[id(s)]


def gabbia_statistica(s, p, rnd):
    """Una gabbia estratta dalle statistiche della sezione e lingua della pagina p: non e' la gabbia di nessuna pagina vera."""
    righe, paragrafi, larghezze, rapporti = statistiche_gabbia(s)
    t = next(k for k in (s.tipo[p], (s.tipo[p][0], None), None) if len(righe.get(k, ())) >= 5)
    n_righe, larg = rnd.choice(righe[t]), rnd.choice(larghezze[t])
    out = []
    while len(out) < n_righe:
        lung = min(rnd.choice(paragrafi[t]), n_righe - len(out))
        if lung == 1:
            # nel Voynich non ci sono paragrafi di una riga sola: la riga che avanza chiude il paragrafo precedente
            out.append((not out, max(1, int(round(larg * rnd.choice(rapporti['ultima']))))))
            continue
        for j in range(lung):
            ruolo = 'prima' if j == 0 else ('ultima' if j == lung - 1 else 'mezzo')
            out.append((j == 0, max(1, int(round(larg * rnd.choice(rapporti[ruolo]))))))
    return out


class Conta:
    """Conta i bit consumati dal Nasconditore."""
    def __init__(self, bit):
        self.bit, self.n = iter(bit), 0

    def __iter__(self):
        return self

    def __next__(self):
        self.n += 1
        return next(self.bit)


def codifica(testo, chiave, versione='v9', parametri=None, verifica=True):
    """Il manoscritto con il testo nascosto nei conteggi delle parole note. testo=None: soli bit di riempimento."""
    from disposizione import posizione
    x = parametri or json.load(open(pezzi.PARAMETRI % versione, encoding='utf-8'))
    s, d = pezzi.pezzi()
    s.FORME = dict(x['forme'])
    s.POSIZIONALE = x.get('carattere') == 'posizionale'
    s.GAMMA = x.get('gamma', 1.0)
    fu = s.forme()
    _CIFRA[0] = x.get('cifra')
    if _CIFRA[0] == 'scrypt':
        cifrati, riempitivo, nbyte = bit_cifrati(testo, chiave)
    elif testo is None:
        cifrati, riempitivo, nbyte = [], v0.flusso_chiave(600000, chiave), 0
    else:
        cifrati, riempitivo, nbyte = v1.bit_del_messaggio(testo, chiave)
    flusso = Conta(cifrati + riempitivo)
    nasc = v1.Nasconditore(flusso)
    per = OrderedDict()
    for i, (p, _, _) in enumerate(s.rr):
        per.setdefault(p, []).append(i)
    out, consumati = [], []
    for p, idx in per.items():
        tipi, interi, tipo_pagina = distribuzione(s, p, chiave, x['kappa'])
        # la gabbia della pagina: (inizio di paragrafo, numero di parole) per ogni riga. Di norma e' quella della pagina vera;
        # con "impaginazione": "altra pagina" (e415) e' quella di un'altra pagina della stessa sezione e lingua, scelta dalla
        # chiave: nessuna pagina del manoscritto ha la gabbia della pagina corrispondente del Voynich
        gabbia = [(s.rr[i][1], len(s.rr[i][2])) for i in idx]
        if x.get('impaginazione') == 'altra pagina':
            altre = [q for q in per if q != p and s.tipo[q] == s.tipo[p]] or [q for q in per if q != p and s.tipo[q][0] == s.tipo[p][0]]
            if altre:
                q = altre[generatore(chiave, p, 'impaginazione').randrange(len(altre))]
                gabbia = [(s.rr[i][1], len(s.rr[i][2])) for i in per[q]]
        elif x.get('impaginazione') == 'statistica':
            gabbia = gabbia_statistica(s, p, generatore(chiave, p, 'impaginazione'))
        rm = generatore(chiave, p, 'posti')
        m = s.molt_pagina[tipo_pagina]
        nuovo = [[rm.random() < min(0.95, s.quota_posto[4 * bool(ini) + posizione(j, nw)] * m) for j in range(nw)] for ini, nw in gabbia]
        n = sum(not b for r in nuovo for b in r)
        conteggi = conteggi_dai_bit(nasc, interi, n)
        note = [w for w, c in zip(tipi, conteggi) for _ in range(c)]
        generatore(chiave, p, 'ordine').shuffle(note)
        rn = generatore(chiave, p, 'nuove')
        profilo = fu.profilo(note)
        per_lung = None
        if fu.unioni:
            s._segni(set(note))
            per_lung = {}
            for w in sorted(set(note)):
                per_lung.setdefault(sum(s._cache_segni[w].values()), []).append(w)
        k = 0
        for (ini, nw), nuove_riga in zip(gabbia, nuovo):
            riga = []
            for j in range(nw):
                if nuove_riga[j]:
                    riga.append(fu.inventa('T-LPS', 4 * bool(ini) + posizione(j, nw), profilo, rn, per_lung))
                else:
                    riga.append(note[k])
                    k += 1
            out.append((p, ini, riga))
        consumati.append(flusso.n)
    righe = d.disponi(out, generatore(chiave, '', 'disposizione').getrandbits(31) if _CIFRA[0] == 'scrypt'
                      else v0.numero(chiave, 'sacco|disposizione') % (1 << 31), 'D3', pesi=x['pesi_disposizione'])
    capacita = flusso.n - v1.PREC
    info = OrderedDict([('bit_messaggio', len(cifrati)), ('capacita_bit', capacita), ('byte_compressi', nbyte),
                        ('byte_testo', len(testo.encode('utf-8')) if testo is not None else 0),
                        ('pagine_usate', sum(c - v1.PREC < len(cifrati) for c in [0] + consumati[:-1]) if cifrati else 0), ('pagine', len(per))])
    if testo is not None:
        if len(cifrati) > capacita:
            raise SystemExit('testo troppo lungo per questo libro: servono %d bit, il libro ne porta %d' % (len(cifrati), capacita))
        if verifica and decodifica(righe, chiave, versione, parametri) != testo:
            raise SystemExit('errore: la decodifica di controllo non restituisce il testo')
    return righe, info


def decodifica(righe, chiave, versione='v9', parametri=None):
    x = parametri or json.load(open(pezzi.PARAMETRI % versione, encoding='utf-8'))
    s, _ = pezzi.pezzi()
    s.POSIZIONALE = x.get('carattere') == 'posizionale'
    s.GAMMA = x.get('gamma', 1.0)
    _CIFRA[0] = x.get('cifra')
    per = OrderedDict()
    for p, _, ps in righe:
        per.setdefault(p, []).extend(ps)
    ril = v1.Rilettore()
    for p in OrderedDict((q, 1) for q, _, _ in s.rr):
        tipi, interi, _ = distribuzione(s, p, chiave, x['kappa'])
        noti = set(tipi)
        c = Counter(w for w in per.get(p, []) if w in noti)
        bit_dai_conteggi(ril, interi, [c[w] for w in tipi])
    bit = ril.bit
    if _CIFRA[0] == 'scrypt':
        return testo_dai_bit(bit, chiave)
    ks = v0.flusso_chiave(len(bit), chiave)
    testa = [b ^ k for b, k in zip(bit[:32], ks[:32])]
    n = int.from_bytes(v0.da_bit(testa), 'big')
    if not 0 < n <= (len(bit) - 32) // 8:
        raise ValueError('chiave sbagliata o manoscritto senza messaggio')
    corpo = [b ^ k for b, k in zip(bit[32:32 + 8 * n], ks[32:32 + 8 * n])]
    return zlib.decompress(v0.da_bit(corpo)).decode('utf-8')
