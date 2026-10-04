# -*- coding: utf-8 -*-
"""Le scelte di grafia di una parola (ch/sh, k/t, -l/-r, e/ee, qo-/o-, ain/aiin, -dy/-ey)."""
import misure, trascrizione

D = misure.divisore(misure.GLIFI_EVA)
GALLOWS = {'k', 't', 'p', 'f'}
BANCHI = {'ch', 'sh', 'k', 't', 'ckh', 'cth'}


def pos_riga(i, n):
    return 'prima' if i == 0 else 'ultima' if i == n - 1 else 'seconda' if i == 1 else 'interna'


def occorrenze(righe):
    """righe: (pagina, parole). -> lista di (scelta, riga, strato, valore)."""
    out = []
    for k, (pag, ps) in enumerate(righe):
        n = len(ps)
        for i, w in enumerate(ps):
            if not trascrizione.pulita(w):
                continue
            u = D(w)
            pr = pos_riga(i, n)
            L = len(u)
            for j, g in enumerate(u):
                dopo = u[j + 1] if j + 1 < L else '$'
                prima = u[j - 1] if j > 0 else '^'
                if g in ('ch', 'sh'):
                    out.append((0, k, (pag, pr, j == 0, dopo), 1 if g == 'sh' else 0))
                if g in ('k', 't'):
                    out.append((1, k, (pag, prima, dopo, pr), 1 if g == 't' else 0))
                if g in BANCHI and dopo == 'e':
                    m = j + 1
                    while m < L and u[m] == 'e':
                        m += 1
                    out.append((3, k, (pag, g, u[m] if m < L else '$'), 1 if m - j - 1 >= 2 else 0))
            if L >= 2 and u[-1] in ('l', 'r') and u[-2] in ('o', 'a'):
                out.append((2, k, (pag, u[-2], 0 if L <= 3 else 1 if L <= 5 else 2), 1 if u[-1] == 'r' else 0))
            if L >= 3 and u[0] == 'q' and u[1] == 'o' and u[2] in GALLOWS:
                out.append((4, k, (pag, u[2], pr), 1))
            elif L >= 2 and u[0] == 'o' and u[1] in GALLOWS:
                out.append((4, k, (pag, u[1], pr), 0))
            if L >= 4 and u[-4:] == ['a', 'i', 'i', 'n']:
                out.append((5, k, (pag, u[-5] if L >= 5 else '^'), 1))
            elif L >= 3 and u[-3:] == ['a', 'i', 'n']:
                out.append((5, k, (pag, u[-4] if L >= 4 else '^'), 0))
            if L >= 2 and u[-1] == 'y' and u[-2] in ('d', 'e'):
                out.append((6, k, (pag, u[-3] if L >= 3 else '^'), 1 if u[-2] == 'd' else 0))
    return out
