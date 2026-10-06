#!/usr/bin/env python3
"""Edita o retrato noturno com o livro "Vade Mecum de Direito Digital".

O livro sai da foto (fotos/livro_direito_digital.jpg), é desentortado e flutua como um
holograma na direção do olhar, com brilho ciano/verde-limão e luz batendo no rosto. A
rede de pontos da capa se espalha pelo céu da cidade, atrás da pessoa (recorte do
MediaPipe: pip install mediapipe==0.10.14).

    python3 editar_foto_livro.py            # gera foto_direito_digital.jpg
"""
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

RAIZ = Path(__file__).resolve().parent
FOTOS = RAIZ / "fotos"
SAIDA = RAIZ / "foto_direito_digital.jpg"
FONTE = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

# cantos da capa na foto do livro (2976x3968), no sentido horário a partir do canto superior esquerdo
CAPA_ORIGEM = [(525, 741), (2262, 704), (2359, 3265), (563, 3296)]
CAPA_W, CAPA_H = 1000, 1420
# onde a capa fica no retrato (1224x2176): virada para o rosto, borda direita mais longe
CAPA_DESTINO = [(818, 1180), (1140, 1232), (1160, 1705), (846, 1765)]
ESPESSURA = (19, -12)              # deslocamento das folhas que aparecem na lateral direita

CIANO = np.array([255, 215, 40], np.float32)    # BGR
LIMAO = np.array([40, 225, 190], np.float32)


def capa():
    img = cv2.imread(str(FOTOS / "livro_direito_digital.jpg"))
    M = cv2.getPerspectiveTransform(np.float32(CAPA_ORIGEM),
                                    np.float32([(0, 0), (CAPA_W, 0), (CAPA_W, CAPA_H), (0, CAPA_H)]))
    c = cv2.warpPerspective(img, M, (CAPA_W, CAPA_H), flags=cv2.INTER_CUBIC)
    return c[6:-6, 8:-6]  # tira a lombada e as bordas que pegaram o fundo


def pessoa(img):
    import mediapipe as mp
    with mp.solutions.selfie_segmentation.SelfieSegmentation(model_selection=0) as seg:
        m = seg.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB)).segmentation_mask
    return cv2.GaussianBlur(np.clip((m - 0.3) / 0.4, 0, 1).astype(np.float32), (0, 0), 2)


def tela(base, luz):
    """Mistura "screen": clareia sem estourar."""
    return 1 - (1 - base) * (1 - np.clip(luz, 0, 1))


def gradacao(img):
    """Sombras puxadas para o azul da capa, contraste leve e vinheta."""
    lum = img.mean(2, keepdims=True)
    sombra = np.clip(1 - lum * 2.2, 0, 1)
    img = img + sombra * np.float32([0.035, 0.012, -0.012])
    img = np.clip((img - 0.5) * 1.06 + 0.5, 0, 1)
    h, w = img.shape[:2]
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.sqrt(((x - w * 0.5) / (w * 0.75)) ** 2 + ((y - h * 0.48) / (h * 0.7)) ** 2)
    return img * (1 - 0.35 * np.clip(d - 0.45, 0, 1))[..., None]


def rede(forma, rng, ancora):
    """Pontos e linhas como os da capa, mais densos no céu e ligados ao livro."""
    h, w = forma
    pts = np.column_stack([rng.uniform(-40, w + 40, 70), rng.uniform(-40, 1380, 70) ** 1.0])
    pts = np.vstack([pts, rng.uniform([30, 40], [w - 30, 420], (18, 2))])
    linhas = np.zeros((h, w), np.float32)
    nos = np.zeros((h, w), np.float32)
    for i, p in enumerate(pts):
        d = np.linalg.norm(pts - p, axis=1)
        for j in np.argsort(d)[1:4]:
            if j > i and d[j] < 260:
                cv2.line(linhas, tuple(map(int, p)), tuple(map(int, pts[j])), rng.uniform(0.35, 0.8), 1, cv2.LINE_AA)
        cv2.circle(nos, tuple(map(int, p)), int(rng.integers(2, 4)), 1.0, -1, cv2.LINE_AA)
    # fios saindo do livro até os pontos mais próximos
    perto = np.argsort(np.linalg.norm(pts - ancora, axis=1))[:7]
    for j in perto:
        cv2.line(linhas, tuple(map(int, ancora + rng.normal(0, 40, 2))), tuple(map(int, pts[j])), 0.7, 1, cv2.LINE_AA)
    return linhas, nos


def particulas(forma, rng, centro):
    """Faíscas e dígitos binários soltos em volta do livro, na frente da pessoa."""
    h, w = forma
    camada = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(camada)
    fontes = [ImageFont.truetype(FONTE, s) for s in (14, 18, 24)]
    for _ in range(60):
        ang, r = rng.uniform(0, 2 * np.pi), abs(rng.normal(0, 260))
        x, y = centro + np.array([np.cos(ang) * r * 0.9, np.sin(ang) * r * 1.1 - 60])
        if 0 < x < w and 0 < y < h:
            if rng.random() < 0.45:
                d.text((x, y), str(rng.integers(0, 2)), fill=int(rng.uniform(90, 230)),
                       font=fontes[rng.integers(0, 3)], anchor="mm")
            else:
                s = rng.uniform(1, 3.2)
                d.ellipse((x - s, y - s, x + s, y + s), fill=int(rng.uniform(140, 255)))
    return np.asarray(camada, np.float32) / 255


def livro(forma):
    """Capa em perspectiva + lateral com as folhas; devolve cor e alfa."""
    h, w = forma
    c = capa()
    ch, cw = c.shape[:2]
    dst = np.float32(CAPA_DESTINO)
    M = cv2.getPerspectiveTransform(np.float32([(0, 0), (cw, 0), (cw, ch), (0, ch)]), dst)
    cor = cv2.warpPerspective(c, M, (w, h), flags=cv2.INTER_CUBIC).astype(np.float32) / 255
    alfa = cv2.warpPerspective(np.ones((ch, cw), np.float32), M, (w, h), flags=cv2.INTER_LINEAR)

    # folhas: faixa creme com riscos finos, mais escura no fundo
    tr, br = dst[1], dst[2]
    lateral = np.float32([tr, tr + ESPESSURA, br + ESPESSURA, br])
    folhas = np.zeros((h, w), np.float32)
    cv2.fillPoly(folhas, [np.int32(lateral)], 1.0, cv2.LINE_AA)
    t = np.linspace(0, 1, 60)
    riscos = np.zeros((h, w), np.float32)
    for k in np.linspace(0.1, 0.9, 9):
        a, b = tr + np.float32(ESPESSURA) * k, br + np.float32(ESPESSURA) * k
        cv2.line(riscos, tuple(map(int, a)), tuple(map(int, b)), 1.0, 1, cv2.LINE_AA)
    papel = np.float32([0.72, 0.84, 0.88]) * (1 - 0.18 * riscos[..., None])
    cor = cor * (1 - folhas[..., None]) + papel * folhas[..., None] * (1 - alfa[..., None])
    alfa = np.maximum(alfa, folhas)

    # reflexo em diagonal, como luz passando na capa plastificada
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    faixa = np.exp(-((x * 0.8 + y * 0.6 - 1680) / 55) ** 2) * 0.22
    cor = tela(cor, faixa[..., None] * alfa[..., None])
    return cor, alfa


def legenda(img):
    h, w = img.shape[:2]
    camada = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(camada)
    f1, f2 = ImageFont.truetype(FONTE, 34), ImageFont.truetype(FONTE, 74)
    d.text((w // 2, 150), "O FUTURO DO DIREITO É", font=f1, fill=(255, 255, 255, 235), anchor="mm")
    d.text((w // 2, 222), "DIGITAL", font=f2, fill=(190, 225, 40, 255), anchor="mm")
    d.line((w // 2 - 150, 280, w // 2 + 150, 280), fill=(40, 170, 255, 230), width=5)
    d.line((w // 2 - 110, 294, w // 2 + 110, 294), fill=(120, 200, 60, 230), width=5)
    arr = np.asarray(camada, np.float32) / 255
    texto, a = arr[..., 2::-1], arr[..., 3:]
    brilho = cv2.GaussianBlur(a, (0, 0), 14)[..., None] * 0.6
    img = img * (1 - brilho * 0.5)  # sombra suave atrás das letras
    return img * (1 - a) + texto * a


def main():
    img = cv2.imread(str(FOTOS / "retrato_noite.webp"))
    h, w = img.shape[:2]
    rng = np.random.default_rng(7)
    mascara = pessoa(img)[..., None]
    base = gradacao(img.astype(np.float32) / 255)

    centro = np.float32(CAPA_DESTINO).mean(0)
    linhas, nos = rede((h, w), rng, centro)
    cor_rede = (linhas * 0.45)[..., None] * CIANO / 255
    cor_rede += cv2.GaussianBlur(linhas, (0, 0), 3)[..., None] * 0.35 * CIANO / 255
    cor_rede += (nos * 0.85 + cv2.GaussianBlur(nos, (0, 0), 5) * 1.8)[..., None] * np.float32([1, 0.95, 0.85])
    base = tela(base, cor_rede * (1 - mascara))

    cor, alfa = livro((h, w))
    # aura do livro e luz que ele joga no rosto e na roupa
    aura = cv2.GaussianBlur(alfa, (0, 0), 28)
    aura = aura[..., None] * CIANO / 255 * 0.9 + cv2.GaussianBlur(alfa, (0, 0), 90)[..., None] * LIMAO / 255 * 0.35
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    raio = np.exp(-(((x - centro[0]) / 430) ** 2 + ((y - centro[1] + 120) / 520) ** 2))
    base = tela(base, aura * 0.85 + (raio * 0.32 * mascara[..., 0])[..., None] * CIANO / 255)

    base = base * (1 - alfa[..., None]) + cor * alfa[..., None]
    faiscas = particulas((h, w), rng, centro) * (1 - alfa)  # nada por cima da capa
    base = tela(base, faiscas[..., None] * (CIANO / 255 * 0.6 + 0.4))
    base = legenda(base)

    # granulação leve para tudo parecer uma foto só
    base = np.clip(base + rng.normal(0, 0.012, (h, w, 1)).astype(np.float32), 0, 1)
    cv2.imwrite(str(SAIDA), (base * 255).astype(np.uint8), [cv2.IMWRITE_JPEG_QUALITY, 94])
    print(SAIDA)


if __name__ == "__main__":
    main()
