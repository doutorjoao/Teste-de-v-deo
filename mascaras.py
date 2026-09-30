#!/usr/bin/env python3
"""Gera as máscaras das cenas (cenas/mascaras/*.png) usadas na animação.

Pessoas vêm do recorte automático do MediaPipe (pip install mediapipe==0.10.14); portas,
mesas, céu e mar são marcados à mão em coordenadas de 1672x941.

    python3 mascaras.py
"""
from pathlib import Path

import cv2
import numpy as np

from animacao import maior_mancha, poligono

RAIZ = Path(__file__).resolve().parent
CENAS = RAIZ / "cenas"
SAIDA = CENAS / "mascaras"
FORMA = (941, 1672)


def ret(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def uniao(*mascaras):
    return np.maximum.reduce([m.astype(np.float32) for m in mascaras])


def polys(*pontos, suavizar=0):
    return uniao(*[poligono(FORMA, p, suavizar) for p in pontos])


def rampa(y_ini, y_fim):
    """1 acima de y_ini, some até y_fim (para o mar terminar suave na areia)."""
    r = np.clip((y_fim - np.arange(FORMA[0])) / (y_fim - y_ini), 0, 1).astype(np.float32)
    return np.repeat(r[:, None], FORMA[1], 1)


def pessoas(img):
    import mediapipe as mp
    with mp.solutions.selfie_segmentation.SelfieSegmentation(model_selection=0) as seg:
        m = seg.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB)).segmentation_mask
    return (m > 0.5).astype(np.float32)


def escuro(img, limite):
    return (cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) < limite).astype(np.float32)


def objeto(img, *retangulos):
    """Recorta objetos (bule, xícara, cadeira) pelo contorno, a partir de um retângulo em volta."""
    total = np.zeros(FORMA, np.float32)
    for x0, y0, x1, y1 in retangulos:
        m = np.zeros(FORMA, np.uint8)
        fundo, frente = np.zeros((1, 65), np.float64), np.zeros((1, 65), np.float64)
        cv2.grabCut(img, m, (x0, y0, x1 - x0, y1 - y0), fundo, frente, 6, cv2.GC_INIT_WITH_RECT)
        total = np.maximum(total, np.isin(m, (cv2.GC_FGD, cv2.GC_PR_FGD)).astype(np.float32))
    return total


def limpar(m, suavizar=1.2):
    m = cv2.morphologyEx((m > 0.5).astype(np.uint8), cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    return cv2.GaussianBlur(m.astype(np.float32), (0, 0), suavizar)


def img1(img):
    porta = polys([(1255, 200), (1402, 163), (1406, 787), (1258, 792)])
    ceu = poligono(FORMA, [(0, 0), (1672, 0), (1672, 398), (1560, 400), (1480, 410), (1400, 440),
                           (1200, 470), (1000, 478), (860, 482), (760, 512), (0, 512)], 3)
    mar = poligono(FORMA, [(0, 516), (760, 516), (860, 490), (1672, 520), (1672, 941), (0, 941)], 3) * rampa(640, 730)
    return {"frente": limpar(uniao(pessoas(img), porta))}, ceu, mar


def img2(img):
    porta = polys(ret(1043, 0, 1672, 941))
    mao = pessoas(img)  # a mão fica inteira na frente da porta
    ceu = poligono(FORMA, [(0, 0), (1043, 0), (1043, 262), (830, 285), (0, 300)], 4)
    mar = poligono(FORMA, [(0, 305), (820, 300), (1043, 318), (1043, 941), (0, 941)], 4) * rampa(640, 760)
    return {"porta": limpar(porta), "mao": limpar(maior_mancha(mao > 0.5))}, ceu, mar


def img3(img):
    esq = escuro(img, 85)
    esq[:, 618:] = 0
    pessoa = maior_mancha(esq > 0.5) * polys([(300, 50), (560, 50), (622, 300), (625, 941), (172, 941),
                                              (128, 420), (165, 350)])
    porta = polys([(618, 0), (687, 0), (685, 941), (621, 941)], ret(618, 0, 1200, 47),
                  [(1182, 0), (1393, 0), (1391, 941), (1184, 941)], ret(1380, 562, 1416, 628))
    meio = polys([(826, 395), (1035, 395), (1035, 560), (1185, 560), (1185, 941), (685, 941),
                  (685, 560), (735, 560), (735, 548), (826, 548)], suavizar=2)
    ceu = poligono(FORMA, [(0, 0), (1672, 0), (1672, 222), (1600, 225), (1560, 235), (1530, 250),
                           (1480, 283), (1390, 300), (1185, 303), (1100, 305), (1010, 310),
                           (960, 322), (930, 336), (0, 336)], 3) * (1 - meio)
    mar = poligono(FORMA, [(0, 342), (930, 342), (960, 346), (1185, 346), (1390, 366), (1672, 368),
                           (1672, 941), (0, 941)], 3) * rampa(520, 590) * (1 - meio)
    return {"frente": limpar(uniao(pessoa, porta))}, ceu, mar


def img4(img):
    mesa = uniao(polys(ret(0, 862, 1672, 941)),
                 objeto(img, (0, 665, 380, 941), (335, 812, 606, 941), (280, 655, 360, 875)))
    ceu = poligono(FORMA, [(0, 0), (1672, 0), (1672, 228), (1560, 236), (1500, 262), (1450, 330),
                           (1300, 345), (1000, 356), (930, 378), (0, 380)], 3)
    mar = poligono(FORMA, [(0, 384), (930, 384), (1000, 362), (1450, 350), (1672, 400),
                           (1672, 941), (0, 941)], 3) * rampa(700, 800)
    return {"frente": limpar(uniao(pessoas(img), mesa))}, ceu, mar


def img5(img):
    moveis = escuro(img, 90) * polys(ret(55, 600, 185, 941), ret(283, 670, 1255, 941),
                                     ret(1235, 625, 1365, 941), ret(140, 470, 565, 941))
    loucas = objeto(img, (782, 580, 928, 700), (562, 640, 646, 692), (1010, 636, 1094, 690))
    porta_longe = polys(ret(1148, 310, 1222, 610), suavizar=3)
    ceu = poligono(FORMA, [(0, 0), (1672, 0), (1672, 212), (1560, 222), (1450, 265), (1200, 275),
                           (950, 285), (920, 300), (870, 340), (740, 390), (0, 395)], 3)
    mar = poligono(FORMA, [(0, 398), (740, 396), (870, 398), (1672, 402), (1672, 941), (0, 941)], 3)
    mar = mar * rampa(640, 720) * (1 - porta_longe)
    return {"frente": limpar(uniao(pessoas(img), moveis, loucas))}, ceu, mar


def img6(img):
    moveis = uniao(polys(ret(0, 832, 1672, 941), [(1300, 610), (1500, 598), (1500, 865), (1300, 865)]),
                   objeto(img, (355, 700, 685, 941), (312, 760, 450, 868), (780, 860, 960, 941)))
    ceu = poligono(FORMA, [(0, 0), (1672, 0), (1672, 130), (1500, 150), (1300, 178), (1100, 215),
                           (900, 240), (700, 258), (550, 285), (520, 298), (0, 298)], 3)
    mar = poligono(FORMA, [(0, 302), (520, 302), (700, 290), (1672, 300), (1672, 941), (0, 941)], 3)
    return {"frente": limpar(uniao(pessoas(img), moveis))}, ceu, mar * rampa(640, 740)


def img7(img):
    moveis = uniao(polys(ret(0, 878, 1672, 941), ret(1600, 575, 1672, 941)),
                   objeto(img, (112, 570, 240, 892), (1320, 640, 1650, 941)))
    porta_longe = polys(ret(1498, 305, 1575, 600), suavizar=3)
    ceu = poligono(FORMA, [(0, 0), (1672, 0), (1672, 225), (1600, 240), (1500, 280), (1400, 300),
                           (1300, 335), (1250, 360), (0, 362)], 3)
    mar = poligono(FORMA, [(0, 366), (1250, 364), (1672, 372), (1672, 941), (0, 941)], 3)
    return {"frente": limpar(uniao(pessoas(img), moveis))}, ceu, mar * rampa(680, 780) * (1 - porta_longe)


def salvar(nome, camadas, ceu, mar):
    for chave, m in [*camadas.items(), ("ceu", ceu), ("mar", mar)]:
        cv2.imwrite(str(SAIDA / f"{nome}_{chave}.png"), (np.clip(m, 0, 1) * 255).astype(np.uint8))


def carregar(nome):
    """{nome_da_mascara: float32 0..1} de uma cena."""
    return {p.stem.split("_", 1)[1]: cv2.imread(str(p), cv2.IMREAD_GRAYSCALE).astype(np.float32) / 255
            for p in sorted(SAIDA.glob(f"{nome}_*.png"))}


if __name__ == "__main__":
    SAIDA.mkdir(parents=True, exist_ok=True)
    for f in (img1, img2, img3, img4, img5, img6, img7):
        salvar(f.__name__, *f(cv2.imread(str(CENAS / f"{f.__name__}.jpg"))))
        print("máscaras:", f.__name__)
