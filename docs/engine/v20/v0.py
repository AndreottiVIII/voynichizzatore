# -*- coding: utf-8 -*-
"""Voynichizzatore, versione 0 (bozza del 3/10/2026).

Prende un testo normale e restituisce un manoscritto intero in EVA (pagine e righe come il Voynich), con il testo nascosto
dentro; con la stessa chiave il testo torna esatto.

    python voynichizzatore/v0.py codifica testo.txt --chiave PAROLA --uscita manoscritto.txt
    python voynichizzatore/v0.py decodifica manoscritto.txt --chiave PAROLA

Come funziona (v0):
- corpo: il generatore migliore del 3/10 (e241: e233.genera + e236.dopo), con il seme ricavato dalla chiave;
- canale: le 5 scelte di grafia (ch/sh, k/t, -l/-r dopo o/a, qo-/o- davanti ai gallows, -dy/-ey) delle parole finali;
- il testo si comprime (zlib), si mette in testa la lunghezza (32 bit) e si mescola con un flusso di bit della chiave
  (XOR); i bit vanno in posizioni del libro scelte dalla chiave (permutazione delle posizioni). Le scelte non usate
  restano quelle del generatore.
Limite noto della v0: nei posti usati la scelta segue il messaggio cifrato (circa 50/50) e non le abitudini di riga;
si vede tanto piu' quanto piu' lungo e' il testo. La v1 usera' la codifica aritmetica per conservare le abitudini.
"""
import argparse, hashlib, os, random, sys, zlib
from collections import OrderedDict

QUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(QUI, '..', 'analisi'))
sys.path.insert(0, os.path.join(QUI, '..', 'esperimenti'))
import misure

D = misure.divisore(misure.GLIFI_EVA)
GALLOWS = {'k', 't', 'p', 'f'}


def numero(chiave, sale):
    return int.from_bytes(hashlib.sha256((sale + ':' + chiave).encode('utf-8')).digest()[:8], 'big')


# ------------------------------------------------------------------ il canale: posti e bit delle 5 scelte

def posti(w):
    """I posti di scelta di una parola, nell'ordine di lettura: [(tipo, indice del segno)]."""
    u = D(w)
    out = []
    for j, g in enumerate(u):
        if g in ('ch', 'sh') or g in ('k', 't'):
            out.append(('segno', j))
    if len(u) >= 2 and u[-1] in ('l', 'r') and u[-2] in ('o', 'a'):
        out.append(('lr', len(u) - 1))
    if len(u) >= 3 and u[0] == 'q' and u[1] == 'o' and u[2] in GALLOWS:
        out.append(('qo', 0))
    elif len(u) >= 2 and u[0] == 'o' and u[1] in GALLOWS:
        out.append(('qo', 0))
    if len(u) >= 2 and u[-1] == 'y' and u[-2] in ('d', 'e'):
        out.append(('dy', len(u) - 2))
    return out


def leggi_bit(w):
    u = D(w)
    bit = []
    for tipo, j in posti(w):
        if tipo == 'segno':
            bit.append(1 if u[j] in ('sh', 't') else 0)
        elif tipo == 'lr':
            bit.append(1 if u[j] == 'r' else 0)
        elif tipo == 'qo':
            bit.append(1 if u[0] == 'q' else 0)
        else:
            bit.append(1 if u[j] == 'd' else 0)
    return bit


def scrivi_bit(w, valori):
    """La parola con i bit dati nei suoi posti (None = lascia com'e'). I posti restano gli stessi."""
    u = D(w)
    pp = posti(w)
    assert len(valori) == len(pp)
    qo = None
    for (tipo, j), b in zip(pp, valori):
        if b is None:
            continue
        if tipo == 'segno':
            u[j] = ('sh' if b else 'ch') if u[j] in ('ch', 'sh') else ('t' if b else 'k')
        elif tipo == 'lr':
            u[j] = 'r' if b else 'l'
        elif tipo == 'dy':
            u[j] = 'd' if b else 'e'
        else:
            qo = b
    if qo is not None:
        if qo and u[0] != 'q':
            u = ['q'] + u
        elif not qo and u[0] == 'q':
            u = u[1:]
    nuova = ''.join(u)
    assert len(posti(nuova)) == len(pp)
    return nuova


# ------------------------------------------------------------------ il corpo: il generatore e241

def corpo(chiave):
    from collections import Counter
    import e224_generatore_completo as e224
    import e233_frequenti_esatte as e233
    import e236_due_fonti as e236
    import e251_lessico_sezione as e251
    c, c2, freq, _, _, _ = e251.contesto()
    seme = numero(chiave, 'corpo') % 1000003
    return e236.dopo(e233.genera(c2, dict(e224.BASE, eta=1.0, kappa=1.0, chi=0.2), seme), freq, 100 + seme)


def indice_posti(righe):
    """Tutti i posti del libro: [(riga, parola, posto)]."""
    return [(i, j, k) for i, (_, _, ps) in enumerate(righe) for j, w in enumerate(ps) for k in range(len(posti(w)))]


def ordine(n, chiave):
    idx = list(range(n))
    random.Random(numero(chiave, 'posti')).shuffle(idx)
    return idx


def flusso_chiave(n, chiave):
    r = random.Random(numero(chiave, 'flusso'))
    return [r.getrandbits(1) for _ in range(n)]


def in_bit(dati):
    return [(byte >> (7 - i)) & 1 for byte in dati for i in range(8)]


def da_bit(bit):
    return bytes(sum(b << (7 - i) for i, b in enumerate(bit[k:k + 8])) for k in range(0, len(bit) - 7, 8))


def codifica(testo, chiave):
    righe = corpo(chiave)
    dati = zlib.compress(testo.encode('utf-8'), 9)
    bit = in_bit(len(dati).to_bytes(4, 'big') + dati)
    tutti = indice_posti(righe)
    if len(bit) > len(tutti):
        raise SystemExit('testo troppo lungo: servono %d bit, il libro ne porta %d (circa %d caratteri compressi)' % (len(bit), len(tutti), len(tutti) // 8 - 4))
    ks = flusso_chiave(len(bit), chiave)
    scelti = ordine(len(tutti), chiave)[:len(bit)]
    da_mettere = {}
    for pos, b, k in zip(scelti, bit, ks):
        i, j, p = tutti[pos]
        da_mettere.setdefault((i, j), {})[p] = b ^ k
    out = []
    for i, (pag, ini, ps) in enumerate(righe):
        nuove = []
        for j, w in enumerate(ps):
            if (i, j) in da_mettere:
                v = [da_mettere[(i, j)].get(p) for p in range(len(posti(w)))]
                w = scrivi_bit(w, v)
            nuove.append(w)
        out.append((pag, ini, nuove))
    return out, OrderedDict([('bit_usati', len(bit)), ('posti_nel_libro', len(tutti)), ('quota_usata', len(bit) / len(tutti)),
                             ('byte_testo', len(testo.encode('utf-8'))), ('byte_compressi', len(dati))])


def decodifica(righe, chiave):
    tutti = indice_posti(righe)
    letti = {}
    for i, (_, _, ps) in enumerate(righe):
        for j, w in enumerate(ps):
            for p, b in enumerate(leggi_bit(w)):
                letti[(i, j, p)] = b
    ordine_ = ordine(len(tutti), chiave)
    ks = flusso_chiave(len(tutti), chiave)
    testa = [letti[tutti[ordine_[k]]] ^ ks[k] for k in range(32)]
    n = int.from_bytes(da_bit(testa), 'big')
    bit = [letti[tutti[ordine_[k]]] ^ ks[k] for k in range(32, 32 + 8 * n)]
    return zlib.decompress(da_bit(bit)).decode('utf-8')


# ------------------------------------------------------------------ file

def salva(righe, percorso):
    with open(percorso, 'w', encoding='utf-8', newline='\n') as f:
        f.write('# Manoscritto prodotto dal voynichizzatore v0 (EVA). Una riga per riga del manoscritto: <pagina.riga> parole separate da punti.\n')
        f.write('# Le righe che iniziano un paragrafo hanno il segno @ prima della pagina.\n')
        cont = {}
        for pag, ini, ps in righe:
            cont[pag] = cont.get(pag, 0) + 1
            f.write('%s<%s.%d> %s\n' % ('@' if ini else '', pag, cont[pag], '.'.join(ps)))


def carica(percorso):
    righe = []
    for riga in open(percorso, encoding='utf-8'):
        if riga.startswith('#') or not riga.strip():
            continue
        ini = riga.startswith('@')
        etich, testo = riga.lstrip('@').rstrip('\n').split(' ', 1)
        pag = etich.strip('<>').rsplit('.', 1)[0]
        righe.append((pag, ini, testo.split('.')))
    return righe


def main():
    ap = argparse.ArgumentParser(description='Voynichizzatore v0')
    ap.add_argument('azione', choices=('codifica', 'decodifica'))
    ap.add_argument('file')
    ap.add_argument('--chiave', required=True)
    ap.add_argument('--uscita')
    a = ap.parse_args()
    if a.azione == 'codifica':
        righe, info = codifica(open(a.file, encoding='utf-8').read(), a.chiave)
        salva(righe, a.uscita or 'manoscritto.txt')
        print('scritto %s: %d righe; %s' % (a.uscita or 'manoscritto.txt', len(righe), dict(info)))
    else:
        try:
            testo = decodifica(carica(a.file), a.chiave)
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
