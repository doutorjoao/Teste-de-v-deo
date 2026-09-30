"""Efeitos de "foto viva" para as cenas: camadas com profundidade, mar e nuvens em movimento.

Cada cena é separada em fundo (céu, mar, areia) e camadas na frente (pessoas, porta, mesa).
O fundo ganha movimento de água e nuvens; as camadas se deslocam mais que o fundo quando a
câmera anda (paralaxe), o que dá a sensação de profundidade, e podem ter movimento próprio
(ex.: a mão girando a maçaneta e a porta abrindo).
"""
import cv2
import numpy as np


def poligono(forma, pontos, suavizar=3):
    m = np.zeros(forma[:2], np.float32)
    cv2.fillPoly(m, [np.int32(pontos)], 1.0)
    return cv2.GaussianBlur(m, (0, 0), suavizar) if suavizar else m


def maior_mancha(binaria):
    n, rot, stats, _ = cv2.connectedComponentsWithStats(binaria.astype(np.uint8), 8)
    if n <= 1:
        return np.zeros(binaria.shape, np.float32)
    i = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    return (rot == i).astype(np.float32)


def preencher(img, mascara, folga=5, vertical=False):
    """Tira o que está na máscara e preenche cada linha ligando as cores dos dois lados.

    Mar, céu e areia são faixas horizontais, então continuar as linhas na horizontal
    fica bem mais natural do que borrar em volta. vertical=True liga as cores de cima e de
    baixo (para texturas verticais, como as tábuas da porta).
    """
    if vertical:
        return preencher(img.transpose(1, 0, 2), mascara.T, folga).transpose(1, 0, 2).copy()
    h, w = img.shape[:2]
    buraco = cv2.dilate((mascara > 0.02).astype(np.uint8), np.ones((2 * folga + 1,) * 2, np.uint8)) > 0
    if not buraco.any():
        return img
    amostra = cv2.GaussianBlur(img, (0, 0), sigmaX=2, sigmaY=0.7)
    col = np.arange(w)[None, :].repeat(h, 0)
    esq = np.maximum.accumulate(np.where(buraco, -1, col), axis=1)
    dir_ = np.minimum.accumulate(np.where(buraco, w, col)[:, ::-1], axis=1)[:, ::-1]
    tem_esq, tem_dir = esq >= 0, dir_ < w
    linhas = np.arange(h)[:, None].repeat(w, 1)
    cor_esq = amostra[linhas, np.clip(esq, 0, w - 1)]
    cor_dir = amostra[linhas, np.clip(dir_, 0, w - 1)]
    peso = np.where(tem_esq & tem_dir, (col - esq) / np.maximum(dir_ - esq, 1), np.where(tem_esq, 0.0, 1.0))
    cheio = cor_esq * (1 - peso[..., None]) + cor_dir * peso[..., None]
    k = cv2.GaussianBlur(buraco.astype(np.float32), (0, 0), 1.5)[..., None]
    return (img * (1 - k) + cheio.astype(np.float32) * k).astype(np.float32)


def suave(t):
    t = np.clip(t, 0.0, 1.0)
    return 0.5 - 0.5 * np.cos(np.pi * t)


class Camada:
    """Parte da imagem que fica na frente do fundo.

    paralaxe: quanto mais perto da câmera, maior (1 = anda junto com o fundo).
    movimento(t) -> dict opcional com
        "torcao": (cx, cy, raio, angulo) giro que diminui do centro até o raio (dedos na maçaneta)
        "afim": matriz 2x3 aplicada depois da torção (ex.: porta abrindo em direção à câmera)
    t vai de 0 a 1 ao longo do plano.
    """

    def __init__(self, mascara, paralaxe=1.1, movimento=None, preencher_vertical=False):
        self.mascara, self.paralaxe, self.movimento = mascara, paralaxe, movimento
        self.preencher_vertical = preencher_vertical
        self.fonte = None


class Cena:
    def __init__(self, img, camadas=(), ceu=None, mar=None, horizonte=340,
                 vel_nuvem=6.0, vel_mar=0.035):
        self.img, self.camadas = img, list(camadas)
        h, w = img.shape[:2]
        vazio = np.zeros((h, w), np.float32)
        # cada camada é limpa do que está na frente dela; o fundo, de todas
        for i, c in enumerate(self.camadas):
            na_frente = np.maximum.reduce([vazio] + [d.mascara for d in self.camadas[i + 1:]])
            c.fonte = preencher(img, na_frente, vertical=c.preencher_vertical)
        self.fundo = preencher(img, np.maximum.reduce([vazio] + [c.mascara for c in self.camadas]))
        self.ceu, self.mar = ceu, mar
        self.horizonte, self.vel_nuvem, self.vel_mar = horizonte, vel_nuvem, vel_mar
        self.yy, self.xx = np.mgrid[0:h, 0:w].astype(np.float32)
        prof = np.clip(self.yy - horizonte, 0, None)
        self.prof, self.prof_rel = prof, prof / (prof.max() + 1)

    def _fundo_em(self, t):
        fundo = self.fundo
        if self.ceu is not None:  # nuvens andando para a esquerda
            nuvens = cv2.remap(self.fundo, self.xx + self.vel_nuvem * t, self.yy, cv2.INTER_LINEAR,
                               borderMode=cv2.BORDER_REFLECT)
            fundo = fundo * (1 - self.ceu[..., None]) + nuvens * self.ceu[..., None]
        if self.mar is not None:  # ondas vindo em direção à areia + leve tremular
            my = self.yy - self.prof * self.vel_mar * t
            mx = self.xx + 1.2 * np.sin(self.yy * 0.35 + t * 5.0) * self.prof_rel
            agua = cv2.remap(self.fundo, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
            fundo = fundo * (1 - self.mar[..., None]) + agua * self.mar[..., None]
        return fundo

    def quadro(self, t, t_plano, cam, cam0, largura, altura):
        """t: segundos desde o início do plano; t_plano: 0..1; cam/cam0: (cx, cy, largura) atual/inicial."""
        cx, cy, lw = cam
        cx0, cy0, lw0 = cam0
        s = largura / lw

        def matriz(escala, centro):
            return np.float32([[escala, 0, largura / 2 - centro[0] * escala],
                               [0, escala, altura / 2 - centro[1] * escala]])

        interp = cv2.INTER_AREA if s < 1 else cv2.INTER_LINEAR
        quadro = cv2.warpAffine(self._fundo_em(t), matriz(s, (cx, cy)), (largura, altura),
                                flags=interp, borderMode=cv2.BORDER_REFLECT)
        uy, ux = np.mgrid[0:altura, 0:largura].astype(np.float32)
        for c in self.camadas:
            p = c.paralaxe
            escala = s * (lw0 / lw) ** (p - 1)
            centro = (cx0 + (cx - cx0) * p, cy0 + (cy - cy0) * p)
            # coordenadas na imagem original de cada pixel da saída (transformações invertidas)
            px = (ux - largura / 2) / escala + centro[0]
            py = (uy - altura / 2) / escala + centro[1]
            mov = c.movimento(t_plano) if c.movimento else {}
            if "afim" in mov:
                inv = cv2.invertAffineTransform(np.float32(mov["afim"]))
                px, py = (inv[0, 0] * px + inv[0, 1] * py + inv[0, 2],
                          inv[1, 0] * px + inv[1, 1] * py + inv[1, 2])
            if "torcao" in mov:
                tx, ty, raio, ang = mov["torcao"]
                dx, dy = px - tx, py - ty
                a = -ang * np.clip(1 - np.hypot(dx, dy) / raio, 0, 1)
                ca, sa = np.cos(a), np.sin(a)
                px, py = tx + dx * ca - dy * sa, ty + dx * sa + dy * ca
            px, py = px.astype(np.float32), py.astype(np.float32)
            cor = cv2.remap(c.fonte, px, py, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
            alfa = cv2.remap(c.mascara, px, py, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)[..., None]
            quadro = quadro * (1 - alfa) + cor * alfa
        return quadro
