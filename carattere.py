# -*- coding: utf-8 -*-
"""Il carattere del voynichizzatore: un font per scrivere l'EVA con segni che ricordano quelli del Voynich.

I segni sono disegnati qui come tratti di penna (linee e curve su un quadrato di 1000 unita'), non ricavati da immagini o
da altri font. Ogni tratto viene ingrossato, il contorno ricalcato e scritto in un font TrueType con fontTools.
I segni composti dell'EVA (ch, sh, cth, ckh, cph, cfh) sono segni a se', nei codici privati U+E000 e seguenti e come
legature (GSUB "liga") delle lettere che li compongono.

    python voynichizzatore/carattere.py            # scrive voynichizzatore/VoynichizzatoreEVA.ttf
"""
import math, os

import numpy as np

QUI = os.path.dirname(os.path.abspath(__file__))
FONT = os.path.join(QUI, 'VoynichizzatoreEVA.ttf')
PENNA = 62                      # spessore del tratto
X = 470                         # altezza delle lettere basse
COMPOSTI = ('cth', 'ckh', 'cph', 'cfh', 'ch', 'sh')
PRIVATI = {u: 0xE000 + i for i, u in enumerate(COMPOSTI)}


def arco(cx, cy, r, a0, a1, ry=None, n=28):
    """Punti di un arco di ellisse, angoli in gradi (0 a destra, antiorario)."""
    ry = r if ry is None else ry
    return [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)), cy + ry * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]


def curva(punti, n=10):
    """Curva morbida (Catmull-Rom) per i punti dati."""
    p = [punti[0]] + list(punti) + [punti[-1]]
    out = []
    for i in range(1, len(p) - 2):
        p0, p1, p2, p3 = (np.array(x, float) for x in p[i - 1:i + 3])
        for t in np.linspace(0, 1, n, endpoint=False):
            out.append(tuple(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3)))
    return out + [tuple(punti[-1])]


def sposta(tratti, dx, dy=0):
    return [[(x + dx, y + dy) for x, y in t] for t in tratti]


# --- i pezzi che tornano in piu' segni
C = arco(250, X / 2, 215, 48, 312, ry=X / 2)                                    # la curva aperta a destra (EVA e)
O = arco(250, X / 2, 205, 0, 360, ry=X / 2)                                     # il tondo
ASTA = curva([(95, X - 20), (120, 250), (165, 60), (235, 15)])                  # il trattino obliquo (EVA i)
PIUMA = curva([(0, 0), (25, 150), (140, 250), (290, 215), (335, 120)])           # il ricciolo sopra (sh, s, r)


def gamba(x, alto=1010):
    return [(x, 0), (x, alto)]


def occhio(x, verso, y=880):
    """Il cappio in cima a una gamba: verso +1 a destra, -1 a sinistra."""
    return curva([(x, y + 70), (x + verso * 150, y + 175), (x + verso * 290, y + 70), (x + verso * 215, y - 120), (x, y - 90)])


def forca(tipo, x=0):
    """Le quattro forche: k (due gambe, cappio a destra), t (due gambe, due cappi), p (una gamba, cappio a destra e
    svolazzo), f (una gamba, due cappi)."""
    if tipo == 'k':
        t = [gamba(150), gamba(440, 900), [(150, 900), (440, 900)], occhio(440, +1, 830)]
    elif tipo == 't':
        t = [gamba(300, 900), gamba(590, 900), [(300, 900), (590, 900)], occhio(590, +1, 830), occhio(300, -1, 830)]
    elif tipo == 'p':
        t = [gamba(170), curva([(170, 940), (330, 1040), (520, 990), (560, 860), (430, 770), (170, 800)]), curva([(170, 1010), (90, 1050), (10, 1000)])]
    else:
        t = [gamba(230), curva([(230, 940), (390, 1040), (580, 990), (620, 860), (490, 770), (230, 800)]),
             curva([(230, 940), (110, 1040), (-40, 980), (-60, 860), (40, 780), (230, 800)])]
    return sposta(t, x)


LARGHE = {'k': 790, 't': 940, 'p': 620, 'f': 700}       # avanzamento delle forche


def segni():
    """nome -> (tratti, avanzamento)."""
    s = {}
    s['o'] = ([O], 540)
    s['e'] = ([C], 470)
    s['c'] = ([C], 470)
    s['h'] = ([C, [(120, X - 15), (330, X - 15)]], 470)
    s['a'] = ([O, curva([(450, X - 10), (455, 230), (480, 60), (545, 15)])], 600)
    s['i'] = ([ASTA], 250)
    s['n'] = ([curva([(95, X - 20), (120, 250), (165, 60), (260, 10), (390, 70), (455, 240), (420, 430), (290, 540), (120, 560), (-10, 500)])], 520)
    s['r'] = ([ASTA, sposta([PIUMA], 100, X - 40)[0]], 450)
    s['s'] = ([C, sposta([PIUMA], 250, X - 10)[0]], 560)
    s['d'] = ([curva([(330, 330), (200, 420), (70, 300), (110, 110), (260, 10), (400, 110), (390, 290), (250, 420), (190, 560), (290, 680), (410, 620), (400, 500), (330, 410)])], 540)
    s['y'] = ([arco(250, 290, 185, 0, 360, ry=185), curva([(435, 300), (430, 60), (350, -150), (200, -250), (70, -230)])], 540)
    s['q'] = ([[(330, X + 10), (330, -250)], curva([(330, X + 10), (200, 330), (70, 180)]), [(70, 180), (440, 180)]], 520)
    s['l'] = ([curva([(110, X - 10), (190, 330), (330, 130), (450, 10)]),
               curva([(430, X - 20), (300, 330), (170, 190), (90, 80), (130, 0), (230, 20), (290, 130), (250, 230)])], 520)
    s['m'] = ([curva([(95, X - 20), (120, 250), (165, 60), (260, 10), (380, 90), (430, 280), (360, 440), (270, 380), (290, 150), (330, -80), (300, -260)])], 500)
    s['g'] = ([s['d'][0][0], curva([(400, 110), (420, -80), (340, -230), (200, -260)])], 540)
    for t in 'ktpf':
        s[t] = (forca(t), LARGHE[t])
    # i segni composti: due curve unite da una barra in cima; con una forca in mezzo nei quattro "banchi con forca"
    barra = lambda x0, x1: [(x0, X - 12), (x1, X - 12)]
    s['ch'] = ([C, sposta([C], 380)[0], barra(330, 560)], 850)
    s['sh'] = (s['ch'][0] + [sposta([PIUMA], 420, X - 10)[0]], 850)
    for t in 'ktpf':
        larg = LARGHE[t]
        dx = 330
        s['c%sh' % t] = ([C] + forca(t, dx) + [sposta([C], dx + larg - 120)[0], barra(330, dx + larg + 60)], dx + larg + 350)
    # segni rari dell'EVA: forme semplici, per non lasciare buchi
    s['x'] = ([[(80, X - 10), (420, 10)], [(420, X - 10), (80, 10)]], 500)
    s['b'] = ([O, [(45, 240), (45, 900)]], 540)
    s['j'] = ([curva([(160, X - 20), (180, 100), (140, -160), (40, -250)])], 300)
    s['u'] = ([ASTA, sposta([ASTA], 200)[0]], 480)
    s['v'] = ([curva([(80, X - 20), (160, 20), (250, 20), (360, X - 20)])], 440)
    s['z'] = ([[(90, X - 20), (400, X - 20), (90, 15), (410, 15)]], 500)
    return s


def contorni(tratti, penna=PENNA):
    """I contorni (in unita' del font) dei tratti ingrossati: [(punti, esterno?)]."""
    from PIL import Image, ImageDraw
    from skimage import measure
    S, OX, OY, W, H = 2, 250, 420, 2200, 1900          # 2 pixel per unita'; margini per discendenti e svolazzi a sinistra
    im = Image.new('L', (W * S // 2 + 2 * OX, H), 0)
    d = ImageDraw.Draw(im)
    conv = lambda x, y: ((x + OX) * S / 2 * 1.0 + 0, H - (y + OY) * S / 2)
    r = penna * S / 4
    for t in tratti:
        p = [conv(x, y) for x, y in t]
        d.line(p, fill=255, width=int(round(2 * r)), joint='curve')
        for x, y in p:
            d.ellipse([x - r, y - r, x + r, y + r], fill=255)
    a = np.asarray(im, float) / 255
    out = []
    for c in measure.find_contours(a, 0.5):
        c = measure.approximate_polygon(c, 1.2)
        if len(c) < 4:
            continue
        pts = [(col * 2 / S - OX, (H - riga) * 2 / S - OY) for riga, col in c[:-1]]
        # esterno o buco: il punto appena dentro il contorno e' inchiostro?
        area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1])) / 2
        out.append((pts, area))
    # il contorno piu' grande e ogni contorno non contenuto in un altro sono esterni; i buchi stanno dentro
    from matplotlib.path import Path
    paths = [Path(p) for p, _ in out]
    ris = []
    for i, (p, area) in enumerate(out):
        dentro = sum(paths[j].contains_point(p[0]) for j in range(len(out)) if j != i)
        ris.append((p, dentro % 2 == 0, area))
    return ris


def costruisci(percorso=FONT):
    from fontTools.fontBuilder import FontBuilder
    from fontTools.pens.ttGlyphPen import TTGlyphPen
    from fontTools.feaLib.builder import addOpenTypeFeaturesFromString
    s = segni()
    nomi = ['.notdef', 'space', 'period'] + sorted(s)
    glifi, metriche = {}, {}
    for n in nomi:
        pen = TTGlyphPen(None)
        if n in s:
            tratti, avanzamento = s[n]
            for pts, esterno, area in contorni(tratti):
                # TrueType: contorni esterni in senso orario (area negativa con y in su), buchi al contrario
                if (area > 0) == esterno:
                    pts = pts[::-1]
                pen.moveTo((int(round(pts[0][0])), int(round(pts[0][1]))))
                for x, y in pts[1:]:
                    pen.lineTo((int(round(x)), int(round(y))))
                pen.closePath()
        elif n == 'period':
            avanzamento = 260
            for pts, esterno, area in contorni([[(110, 30), (112, 32)]], penna=90):
                pts = pts[::-1] if (area > 0) == esterno else pts
                pen.moveTo((int(round(pts[0][0])), int(round(pts[0][1]))))
                for x, y in pts[1:]:
                    pen.lineTo((int(round(x)), int(round(y))))
                pen.closePath()
        else:
            avanzamento = 330 if n == 'space' else 500
        glifi[n] = pen.glyph()
        metriche[n] = (avanzamento, 0)
    mappa = {ord(' '): 'space', ord('.'): 'period'}
    for n in s:
        if len(n) == 1:
            mappa[ord(n)] = n
        else:
            mappa[PRIVATI[n]] = n
    fb = FontBuilder(1000, isTTF=True)
    fb.setupGlyphOrder(nomi)
    fb.setupCharacterMap(mappa)
    fb.setupGlyf(glifi)
    fb.setupHorizontalMetrics(metriche)
    fb.setupHorizontalHeader(ascent=1150, descent=-320)
    fb.setupNameTable({'familyName': 'Voynichizzatore EVA', 'styleName': 'Regular', 'uniqueFontIdentifier': 'VoynichizzatoreEVA-Regular',
                       'fullName': 'Voynichizzatore EVA', 'psName': 'VoynichizzatoreEVA-Regular', 'version': 'Version 1.0',
                       'licenseDescription': 'MIT License', 'copyright': 'Copyright (c) 2026 Davide Caniatti'})
    fb.setupOS2(sTypoAscender=1150, sTypoDescender=-320, usWinAscent=1150, usWinDescent=320, sxHeight=X, sCapHeight=1010)
    fb.setupPost()
    addOpenTypeFeaturesFromString(fb.font, 'feature liga {\n' + ''.join('  sub %s by %s;\n' % (' '.join(u), u) for u in COMPOSTI) + '} liga;\n')
    fb.save(percorso)
    return percorso


def in_segni(parola):
    """La parola EVA come stringa per il font: i segni composti diventano i loro codici privati."""
    out, i = [], 0
    while i < len(parola):
        for u in COMPOSTI:
            if parola.startswith(u, i):
                out.append(chr(PRIVATI[u]))
                i += len(u)
                break
        else:
            out.append(parola[i])
            i += 1
    return ''.join(out)


if __name__ == '__main__':
    print('scritto', costruisci())
