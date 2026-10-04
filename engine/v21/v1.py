# -*- coding: utf-8 -*-
"""Voynichizzatore, versione 1 (3/10/2026): come la v0, ma il messaggio non forza le scelte di grafia.

    python voynichizzatore/v1.py codifica testo.txt --chiave PAROLA --uscita manoscritto.txt
    python voynichizzatore/v1.py decodifica manoscritto.txt --chiave PAROLA [--uscita testo.txt]

Differenza dalla v0: un modello delle 5 scelte di grafia imparato dal Voynich (contesto della parola, posizione nella
riga, scelte gia' fatte nella riga e nella riga sopra) da' per ogni posto la probabilita' della forma lunga. Il messaggio
cifrato sceglie con quella probabilita' attraverso la codifica aritmetica (il "decodificatore" aritmetico nasconde, il
"codificatore" rilegge). Tutte le scelte del libro escono cosi' distribuite come nel modello del Voynich; il messaggio
occupa solo l'informazione che le scelte portano gia' (circa 0,8 bit per posto).
I contesti usano le famiglie dei segni (CH, KT, LR, DE, q iniziale tolta), quindi non dipendono dai valori scelti.
"""
import argparse, json, math, os, sys, zlib
from collections import defaultdict

QUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, QUI)
sys.path.insert(0, os.path.join(QUI, '..', 'analisi'))
sys.path.insert(0, os.path.join(QUI, '..', 'esperimenti'))
import v0

MODELLO = os.path.join(QUI, 'modello_scelte_v1.json')
TOT, PREC = 1 << 16, 32
MAXV, META, QUARTO = (1 << PREC) - 1, 1 << (PREC - 1), 1 << (PREC - 2)


# ------------------------------------------------------------------ posti con contesto indipendente dai valori

def posti_contesto(w, pr):
    """[(tipo, valore, contesto)] per i posti della parola w in posizione di riga pr (0 prima, 1 in mezzo, 2 ultima)."""
    u = v0.D(w)
    pp = v0.posti(w)
    vals = v0.leggi_bit(w)
    f = list(u)
    tipi = []
    for tipo, j in pp:
        if tipo == 'segno':
            t = 'CH' if u[j] in ('ch', 'sh') else 'KT'
            f[j] = t
        elif tipo == 'lr':
            t = f[j] = 'LR'
        elif tipo == 'dy':
            t = f[j] = 'DE'
        else:
            t = 'QO'
        tipi.append((t, j))
    q = 1 if (f and f[0] == 'q' and any(t == 'QO' for t, _ in tipi)) else 0
    g = f[q:]
    L = len(g)
    out = []
    for (t, j), v in zip(tipi, vals):
        k = j - q
        prima = g[k - 1] if k >= 1 else '^'
        dopo = g[k + 1] if k + 1 < L else '$'
        if t == 'CH':
            ctx = 'CH|%s|%d|%d' % (dopo, k == 0, pr)
        elif t == 'KT':
            ctx = 'KT|%s|%s' % (prima, dopo)
        elif t == 'LR':
            ctx = 'LR|%s|%d' % (prima, 0 if L <= 3 else 1 if L <= 5 else 2)
        elif t == 'DE':
            ctx = 'DE|%s' % (g[L - 3] if L >= 3 else '^')
        else:
            ctx = 'QO|%s|%d' % (g[1] if L >= 2 else '$', pr)
        out.append((t, v, ctx))
    return out


def scorri(righe, scelta):
    """Percorre i posti del libro nell'ordine di lettura con lo stato di riga; scelta(t, ctx, s_cur, s_prec, v) restituisce il
    valore da tenere (v e' quello attuale). Restituisce le righe con le parole aggiornate."""
    out, prec = [], defaultdict(int)
    for pag, ini, ps in righe:
        cur, nuove = defaultdict(int), []
        n = len(ps)
        for i, w in enumerate(ps):
            pr = 0 if i == 0 else (2 if i == n - 1 else 1)
            valori = []
            for t, v, ctx in posti_contesto(w, pr):
                b = scelta(t, ctx, max(-4, min(4, cur[t])), max(-6, min(6, prec[t])), v)
                valori.append(b)
                cur[t] += 1 if b else -1
            nuove.append(v0.scrivi_bit(w, valori) if valori else w)
        out.append((pag, ini, nuove))
        prec = cur
    return out


# ------------------------------------------------------------------ il modello (logistica per tipo, imparata dal Voynich)

def addestra():
    import trascrizione
    from sklearn.linear_model import LogisticRegression
    righe = [('', bool(r.inizio_par), [w for w in r.parole if trascrizione.pulita(w)]) for r in trascrizione.testo_corrente(trascrizione.leggi('ZL')) if r.parole]
    dati = defaultdict(list)

    def registra(t, ctx, sc, sp, v):
        dati[t].append((ctx, sc, sp, v))
        return v
    scorri(righe, registra)
    modello = {}
    for t, xs in dati.items():
        contesti = sorted({c for c, _, _, _ in xs})
        idx = {c: i for i, c in enumerate(contesti)}
        X = [[0.0] * (len(contesti) + 2) for _ in xs]
        for row, (c, sc, sp, _) in zip(X, xs):
            row[idx[c]] = 1.0
            row[-2], row[-1] = sc / 4, sp / 6
        y = [v for _, _, _, v in xs]
        m = LogisticRegression(C=1.0, max_iter=2000).fit(X, y)
        modello[t] = {'contesti': {c: float(m.coef_[0][i]) for c, i in idx.items()}, 'stato_riga': float(m.coef_[0][-2]),
                      'stato_riga_sopra': float(m.coef_[0][-1]), 'intercetta': float(m.intercept_[0]), 'posti': len(xs), 'quota_lunghe': sum(y) / len(y)}
    json.dump(modello, open(MODELLO, 'w', encoding='utf-8'), ensure_ascii=False, indent=1, sort_keys=True)
    return modello


def carica_modello():
    return json.load(open(MODELLO, encoding='utf-8')) if os.path.exists(MODELLO) else addestra()


def f0_di(modello, t, ctx, sc, sp):
    m = modello[t]
    z = m['intercetta'] + m['contesti'].get(ctx, 0.0) + m['stato_riga'] * sc / 4 + m['stato_riga_sopra'] * sp / 6
    p1 = 1.0 / (1.0 + math.exp(-z))
    return min(TOT - 1, max(1, TOT - int(round(p1 * TOT))))


# ------------------------------------------------------------------ codifica aritmetica binaria (Witten, Neal, Cleary)

def taglio(basso, alto, f0):
    return basso + (alto - basso + 1) * f0 // TOT - 1


class Nasconditore:
    """Il decodificatore aritmetico alimentato dai bit del messaggio: sceglie i simboli."""
    def __init__(self, bit):
        self.bit, self.basso, self.alto, self.valore = bit, 0, MAXV, 0
        for _ in range(PREC):
            self.valore = (self.valore << 1) | next(self.bit)

    def simbolo(self, f0):
        s = taglio(self.basso, self.alto, f0)
        b = 0 if self.valore <= s else 1
        if b == 0:
            self.alto = s
        else:
            self.basso = s + 1
        while True:
            if self.alto < META:
                pass
            elif self.basso >= META:
                self.valore -= META; self.basso -= META; self.alto -= META
            elif self.basso >= QUARTO and self.alto < 3 * QUARTO:
                self.valore -= QUARTO; self.basso -= QUARTO; self.alto -= QUARTO
            else:
                break
            self.basso, self.alto = 2 * self.basso, 2 * self.alto + 1
            self.valore = 2 * self.valore + next(self.bit)
        return b


class Rilettore:
    """Il codificatore aritmetico sui simboli osservati: restituisce i bit."""
    def __init__(self):
        self.basso, self.alto, self.attesa, self.bit = 0, MAXV, 0, []

    def _emetti(self, b):
        self.bit.append(b)
        self.bit.extend([1 - b] * self.attesa)
        self.attesa = 0

    def simbolo(self, b, f0):
        s = taglio(self.basso, self.alto, f0)
        if b == 0:
            self.alto = s
        else:
            self.basso = s + 1
        while True:
            if self.alto < META:
                self._emetti(0)
            elif self.basso >= META:
                self._emetti(1); self.basso -= META; self.alto -= META
            elif self.basso >= QUARTO and self.alto < 3 * QUARTO:
                self.attesa += 1; self.basso -= QUARTO; self.alto -= QUARTO
            else:
                break
            self.basso, self.alto = 2 * self.basso, 2 * self.alto + 1


# ------------------------------------------------------------------ codifica e decodifica

def bit_del_messaggio(testo, chiave):
    dati = zlib.compress(testo.encode('utf-8'), 9)
    bit = v0.in_bit(len(dati).to_bytes(4, 'big') + dati)
    ks = v0.flusso_chiave(len(bit) + 200000, chiave)
    return [b ^ k for b, k in zip(bit, ks)], ks[len(bit):], len(dati)


def rileggi(righe, chiave, modello):
    r = Rilettore()
    scorri(righe, lambda t, ctx, sc, sp, v: (r.simbolo(v, f0_di(modello, t, ctx, sc, sp)), v)[1])
    return r.bit


def decodifica(righe, chiave, modello=None):
    modello = modello or carica_modello()
    bit = rileggi(righe, chiave, modello)
    ks = v0.flusso_chiave(len(bit), chiave)
    testa = [b ^ k for b, k in zip(bit[:32], ks[:32])]
    n = int.from_bytes(v0.da_bit(testa), 'big')
    corpo = [b ^ k for b, k in zip(bit[32:32 + 8 * n], ks[32:32 + 8 * n])]
    return zlib.decompress(v0.da_bit(corpo)).decode('utf-8')


def codifica(testo, chiave, righe=None):
    modello = carica_modello()
    righe = righe if righe is not None else v0.corpo(chiave)
    cifrati, riempitivo, nbyte = bit_del_messaggio(testo, chiave)
    flusso = iter(cifrati + riempitivo)
    nasc = Nasconditore(flusso)
    out = scorri(righe, lambda t, ctx, sc, sp, v: nasc.simbolo(f0_di(modello, t, ctx, sc, sp)))
    try:
        ok = decodifica(out, chiave, modello) == testo
    except Exception:
        ok = False
    if not ok:
        raise SystemExit('testo troppo lungo per questo libro (o errore): servono %d bit' % len(cifrati))
    posti = sum(len(v0.posti(w)) for _, _, ps in out for w in ps)
    return out, {'bit_messaggio': len(cifrati), 'posti_nel_libro': posti, 'byte_compressi': nbyte, 'byte_testo': len(testo.encode('utf-8'))}


def main():
    ap = argparse.ArgumentParser(description='Voynichizzatore v1')
    ap.add_argument('azione', choices=('codifica', 'decodifica', 'addestra'))
    ap.add_argument('file', nargs='?')
    ap.add_argument('--chiave')
    ap.add_argument('--uscita')
    a = ap.parse_args()
    if a.azione == 'addestra':
        m = addestra()
        print({t: (x['posti'], round(x['quota_lunghe'], 3), round(x['stato_riga'], 2), round(x['stato_riga_sopra'], 2)) for t, x in m.items()})
    elif a.azione == 'codifica':
        righe, info = codifica(open(a.file, encoding='utf-8').read(), a.chiave)
        v0.salva(righe, a.uscita or 'manoscritto.txt')
        print('scritto %s: %d righe; %s' % (a.uscita or 'manoscritto.txt', len(righe), info))
    else:
        try:
            testo = decodifica(v0.carica(a.file), a.chiave)
        except Exception:
            raise SystemExit('niente da leggere: chiave sbagliata o manoscritto alterato')
        if a.uscita:
            open(a.uscita, 'w', encoding='utf-8', newline='\n').write(testo)
            print('testo scritto in %s (%d caratteri)' % (a.uscita, len(testo)))
        else:
            sys.stdout.reconfigure(encoding='utf-8', newline='\n')
            sys.stdout.write(testo + '\n')


if __name__ == '__main__':
    main()
