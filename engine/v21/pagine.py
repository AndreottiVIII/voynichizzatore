# -*- coding: utf-8 -*-
"""Dal manoscritto in EVA alle pagine: un PDF con una pagina per pagina del manoscritto, scritta con il carattere del
voynichizzatore (carattere.py). I paragrafi sono staccati da mezzo rigo; il corpo del carattere si adatta alla pagina
(le poche righe molto lunghe sono scritte piu' strette).

    python voynichizzatore/pagine.py manoscritto.txt --uscita libro.pdf [--pagine 12]
"""
import argparse, os, sys
from collections import OrderedDict

QUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, QUI)
import carattere

LARGHEZZA, ALTEZZA = 6.0, 8.6            # pollici
MARGINE_X, MARGINE_SU, MARGINE_GIU = 0.6, 0.65, 0.75
CORPO_MAX, INTERLINEA = 15.0, 1.75       # punti; interlinea in corpi
CARTA, INCHIOSTRO = '#f0e6cf', '#463220'


def leggi(percorso):
    """[(pagina, [(inizio paragrafo, parole)])] da un file del voynichizzatore (<pagina.riga> parole.separate.da.punti)."""
    pagine = OrderedDict()
    for riga in open(percorso, encoding='utf-8'):
        riga = riga.strip()
        if not riga or riga.startswith('#'):
            continue
        ini = riga.startswith('@')
        etichetta, _, testo = riga.lstrip('@').partition('>')
        pag = etichetta.strip('<').rsplit('.', 1)[0]
        pagine.setdefault(pag, []).append((ini, [w for w in testo.strip().split('.') if w]))
    return list(pagine.items())


def avanzamenti():
    from fontTools.ttLib import TTFont
    f = TTFont(carattere.FONT)
    cmap, hmtx = f.getBestCmap(), f['hmtx']
    return {chr(c): hmtx[n][0] / f['head'].unitsPerEm for c, n in cmap.items()}


def pdf(percorso, uscita, quante=None, stampa=True, immagine=None):
    import matplotlib
    matplotlib.use('Agg')
    matplotlib.rcParams['pdf.fonttype'] = 42
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages
    from matplotlib.font_manager import FontProperties
    if not os.path.exists(carattere.FONT):
        carattere.costruisci()
    adv = avanzamenti()
    pagine = leggi(percorso)[:quante]
    utile_x, utile_y = (LARGHEZZA - 2 * MARGINE_X) * 72, (ALTEZZA - MARGINE_SU - MARGINE_GIU) * 72
    with PdfPages(uscita) as out:
        for k, (pag, righe) in enumerate(pagine):
            testi = [' '.join(carattere.in_segni(w) for w in ws) for _, ws in righe]
            larghezze = [sum(adv.get(c, 0.5) for c in t) for t in testi]
            larghezza = sorted(larghezze)[int(0.85 * (len(larghezze) - 1))]      # le poche righe piu' lunghe si stringono
            stacchi = sum(1 for i, (ini, _) in enumerate(righe) if ini and i > 0) * 0.5
            corpo = min(CORPO_MAX, utile_x / larghezza, utile_y / ((len(righe) + stacchi) * INTERLINEA))
            fig = plt.figure(figsize=(LARGHEZZA, ALTEZZA))
            fig.patch.set_facecolor(CARTA)
            y = ALTEZZA * 72 - MARGINE_SU * 72 - corpo
            for i, ((ini, _), t) in enumerate(zip(righe, testi)):
                if ini and i > 0:
                    y -= 0.5 * corpo * INTERLINEA
                fp = FontProperties(fname=carattere.FONT, size=min(corpo, utile_x / larghezze[i]))
                fig.text(MARGINE_X / LARGHEZZA, y / (ALTEZZA * 72), t, fontproperties=fp, color=INCHIOSTRO, va='baseline', ha='left')
                y -= corpo * INTERLINEA
            fig.text(0.5, 0.35 / ALTEZZA, pag, fontsize=7, color='#8a7a60', ha='center', va='center')
            out.savefig(fig, facecolor=CARTA)
            if immagine and k == 0:
                fig.savefig(immagine, dpi=170, facecolor=CARTA)
            plt.close(fig)
            if stampa and (k + 1) % 50 == 0:
                print('%d pages' % (k + 1), flush=True)
    return len(pagine)


def main():
    ap = argparse.ArgumentParser(description='Dal manoscritto in EVA al PDF delle pagine')
    ap.add_argument('file')
    ap.add_argument('--uscita', '--out', dest='uscita')
    ap.add_argument('--pagine', '--pages', dest='pagine', type=int, help='solo le prime N pagine')
    ap.add_argument('--immagine', '--image', dest='immagine', help='salva anche la prima pagina come immagine')
    a = ap.parse_args()
    uscita = a.uscita or os.path.splitext(a.file)[0] + '.pdf'
    n = pdf(a.file, uscita, a.pagine, immagine=a.immagine)
    print('scritto %s: %d pagine' % (uscita, n))


if __name__ == '__main__':
    main()
