#!/usr/bin/env python3
"""Gera o vídeo no formato do meme "Me whenever I need an expert's advice".

Layout igual ao vídeo de referência (vertical 9:16): fundo preto, faixa branca
com a legenda e, logo abaixo, um quadro 16:9 com as fotos em movimento
(zoom/pan lento, tratamento de cor "cinema" e granulação de filme). Os cortes
caem nos mesmos instantes do vídeo original, sobre a mesma trilha.

Uso:
    python3 gerar_video.py                      # legenda em português
    python3 gerar_video.py --idioma en          # legenda original em inglês
    python3 gerar_video.py --preview prev.png   # só gera uma prancha dos planos
"""
import argparse
import subprocess
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

RAIZ = Path(__file__).resolve().parent
FOTOS = RAIZ / "fotos"

W, H, FPS = 1080, 1920, 30
DURACAO = 15.87
BARRA_Y0, BARRA_Y1 = 333, 599      # faixa branca da legenda
VID_Y0, VW, VH = 599, 1080, 608    # quadro 16:9 do vídeo
ASPECTO = VH / VW

LEGENDAS = {
    "pt": ["Eu sempre que preciso do", "conselho de um especialista"],
    "en": ["Me whenever", "I need an expert's advice"],
}
FONTE = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"


def carregar(nome):
    img = cv2.imread(str(FOTOS / nome), cv2.IMREAD_COLOR)
    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0


def estender_para_16x9(img, suavizar=160, borda=60):
    """Coloca uma foto vertical num quadro 16:9 estendendo o fundo liso pelas laterais."""
    h, w = img.shape[:2]
    cw = int(round(h / ASPECTO))
    x0 = (cw - w) // 2
    # cor de cada linha nas bordas esquerda/direita, interpolada pelo quadro todo
    esq = cv2.GaussianBlur(img[:, :borda].mean(axis=1, keepdims=True), (0, 0), 25)
    dir_ = cv2.GaussianBlur(img[:, -borda:].mean(axis=1, keepdims=True), (0, 0), 25)
    t = np.clip((np.arange(cw, dtype=np.float32) - x0) / w, 0, 1)[None, :, None]
    fundo = esq * (1 - t) + dir_ * t
    # leve queda de luz para as pontas, como num fundo de estúdio
    queda = 1 - 0.12 * np.clip(np.abs(np.arange(cw) - cw / 2) - w / 2, 0, None) / (x0 or 1)
    fundo = (fundo * queda[None, :, None].astype(np.float32)).astype(np.float32)
    mascara = np.ones(w, np.float32)
    rampa = np.linspace(0, 1, suavizar, dtype=np.float32)
    mascara[:suavizar] = rampa
    mascara[-suavizar:] = rampa[::-1]
    mascara = mascara[None, :, None]
    fundo[:, x0:x0 + w] = img * mascara + fundo[:, x0:x0 + w] * (1 - mascara)
    return np.ascontiguousarray(fundo)


def colar(canvas, img, escala, ancora_img, ancora_canvas):
    """Renderiza `img` escalada no canvas, com ancora_img caindo em ancora_canvas."""
    ch, cw = canvas.shape[:2]
    tx = ancora_canvas[0] - ancora_img[0] * escala
    ty = ancora_canvas[1] - ancora_img[1] * escala
    m = np.float32([[escala, 0, tx], [0, escala, ty]])
    interp = cv2.INTER_AREA if escala < 1 else cv2.INTER_CUBIC
    return cv2.warpAffine(img, m, (cw, ch), flags=interp, borderMode=cv2.BORDER_REFLECT)


def montar_dupla(olha_dir, olha_esq):
    """As duas versões dele frente a frente: a cena de "consultar o especialista"."""
    cw, ch = 1800, 1013
    base = np.zeros((ch, cw, 3), np.float32)
    # rosto (centro) de cada foto -> posição no quadro
    esq = colar(base, olha_dir, 1.25, (580, 730), (0.24 * cw, 0.52 * ch))
    dir_ = colar(base, olha_esq, 1.05, (585, 665), (0.76 * cw, 0.52 * ch))
    x = np.arange(cw, dtype=np.float32)
    t = np.clip((x - 780) / (1040 - 780), 0, 1)
    t = (t * t * (3 - 2 * t))[None, :, None]
    return esq * (1 - t) + dir_ * t


def preparar_fontes():
    estudio = carregar("1_estudio.jpg")[442:2278]  # tira as faixas pretas do print
    return {
        "estudio": estudio,
        "estudio_aberto": estender_para_16x9(estudio),
        "selfie": carregar("2_selfie.jpg"),
        "noite_dir": carregar("3_noite_olhando_direita.jpg"),
        "noite_esq": carregar("4_noite_olhando_esquerda.jpg"),
        "frente": carregar("5_frente.jpg"),
    }


# (início, fim, fonte, (cx, cy, largura) inicial, (cx, cy, largura) final)
# Os instantes de corte são os mesmos do vídeo de referência.
PLANOS = [
    (0.00, 0.40, "frente", (480, 615, 960), (478, 612, 900)),
    (0.40, 1.00, "estudio_aberto", None, 0.93),
    (1.00, 2.93, "estudio", (483, 1300, 540), (483, 1290, 450)),
    (2.93, 5.43, "estudio", (600, 1090, 900), (598, 640, 820)),
    (5.43, 6.00, "noite_esq", (560, 660, 760), (565, 660, 720)),
    (6.00, 9.70, "dupla", None, 0.90),
    (9.70, 11.60, "noite_dir", (600, 740, 700), (590, 735, 630)),
    (11.60, 13.45, "selfie", (1075, 1700, 2160), (1075, 1660, 1880)),
    (13.45, 15.27, "frente", (475, 610, 900), (470, 600, 700)),
    (15.27, DURACAO, "dupla", None, 0.97),
]


def suave(t):
    return 0.5 - 0.5 * np.cos(np.pi * t)


def recorte(fonte, ini, fim, t):
    h, w = fonte.shape[:2]
    if ini is None:  # zoom centralizado: `fim` é a fração final da largura
        ini = (w / 2, h / 2, min(w, h / ASPECTO))
        fim = (w / 2, h / 2, ini[2] * fim)
    k = suave(t)
    cx, cy, lw = (a + (b - a) * k for a, b in zip(ini, fim))
    return cx, cy, lw


def renderizar_quadro(fonte, cx, cy, lw):
    lh = lw * ASPECTO
    s = VW / lw
    m = np.float32([[s, 0, -(cx - lw / 2) * s], [0, s, -(cy - lh / 2) * s]])
    interp = cv2.INTER_AREA if s < 1 else cv2.INTER_LINEAR
    return cv2.warpAffine(fonte, m, (VW, VH), flags=interp, borderMode=cv2.BORDER_REFLECT)


class Grade:
    """Tratamento de cor tipo cinema: menos saturação, pretos levantados, vinheta, grão."""

    def __init__(self, seed=7, saturacao=0.82, tom=(1.025, 1.0, 0.965)):
        self.saturacao, self.tom = saturacao, np.float32(tom)
        yy, xx = np.mgrid[0:VH, 0:VW].astype(np.float32)
        r2 = ((xx - VW / 2) / (VW / 2)) ** 2 + ((yy - VH / 2) / (VH / 2)) ** 2
        self.vinheta = (1 - 0.22 * r2 / 2)[..., None]
        rng = np.random.default_rng(seed)
        self.graos = [cv2.GaussianBlur(rng.normal(0, 0.016, (VH, VW)).astype(np.float32), (0, 0), 0.8)[..., None]
                      for _ in range(12)]

    def __call__(self, img, i):
        lum = img @ np.float32([0.299, 0.587, 0.114])
        img = lum[..., None] + (img - lum[..., None]) * self.saturacao
        img = img * 0.9 + 0.035
        img = img * self.tom
        img = img * self.vinheta + self.graos[i % len(self.graos)]
        return np.clip(img, 0, 1)


def base_com_legenda(linhas):
    base = Image.new("RGB", (W, H), (0, 0, 0))
    d = ImageDraw.Draw(base)
    d.rectangle([0, BARRA_Y0, W, BARRA_Y1], fill=(255, 255, 255))
    tamanho = 62
    while True:
        fonte = ImageFont.truetype(FONTE, tamanho)
        if max(d.textlength(l, font=fonte) for l in linhas) <= 900:
            break
        tamanho -= 2
    entrelinha = int(tamanho * 1.22)
    topo = (BARRA_Y0 + BARRA_Y1) / 2 - entrelinha * len(linhas) / 2
    for n, linha in enumerate(linhas):
        d.text((W / 2, topo + entrelinha * (n + 0.5)), linha, font=fonte,
               fill=(0, 0, 0), anchor="mm")
    return np.asarray(base).copy()


def fontes_padrao():
    fontes = preparar_fontes()
    fontes["dupla"] = montar_dupla(fontes["noite_dir"], fontes["noite_esq"])
    return fontes


def balanco(tempo, lw, amp):
    """Deslocamento lento e irregular, como câmera na mão."""
    if not amp:
        return 0.0, 0.0
    dx = np.sin(2 * np.pi * 0.23 * tempo) + 0.5 * np.sin(2 * np.pi * 0.61 * tempo + 1.7)
    dy = np.sin(2 * np.pi * 0.19 * tempo + 0.6) + 0.5 * np.sin(2 * np.pi * 0.53 * tempo + 2.9)
    return amp * lw * dx, amp * lw * ASPECTO * dy


def gerar(saida, idioma, audio, fontes=None, planos=PLANOS, grade=None, amp_balanco=0.0):
    fontes = fontes or fontes_padrao()
    base = base_com_legenda(LEGENDAS[idioma])
    grade = grade or Grade()
    total = int(round(DURACAO * FPS))
    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-"]
    if audio:
        # apad completa o áudio com silêncio; -shortest então corta no fim do vídeo
        cmd += ["-i", str(audio), "-map", "0:v", "-map", "1:a", "-af", "apad",
                "-c:a", "aac", "-b:a", "160k", "-shortest"]
    cmd += ["-c:v", "libx264", "-preset", "slow", "-crf", "21", "-maxrate", "8M", "-bufsize", "16M",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart", str(saida)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(total):
        tempo = i / FPS
        ini_p, fim_p, nome, a, b = next(p for p in planos if p[0] <= tempo < p[1] or p is planos[-1])
        t = (tempo - ini_p) / (fim_p - ini_p)
        cx, cy, lw = recorte(fontes[nome], a, b, t)
        dx, dy = balanco(tempo, lw, amp_balanco)
        quadro = renderizar_quadro(fontes[nome], cx + dx, cy + dy, lw)
        quadro = grade(quadro, i)
        base[VID_Y0:VID_Y0 + VH] = (quadro * 255 + 0.5).astype(np.uint8)
        proc.stdin.write(base.tobytes())
    proc.stdin.close()
    if proc.wait() != 0:
        raise SystemExit("ffmpeg falhou")


def prancha(saida, fontes=None, planos=PLANOS):
    """Primeiro e último quadro de cada plano, lado a lado, para conferir enquadramentos."""
    fontes = fontes or fontes_padrao()
    linhas = []
    for _, _, nome, a, b in planos:
        par = [renderizar_quadro(fontes[nome], *recorte(fontes[nome], a, b, t)) for t in (0, 1)]
        linhas.append(np.hstack(par))
    img = (np.vstack(linhas) * 255).astype(np.uint8)
    Image.fromarray(img).resize((img.shape[1] // 2, img.shape[0] // 2)).save(saida)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--idioma", choices=LEGENDAS, default="pt")
    ap.add_argument("--audio", default=RAIZ / "audio" / "trilha.m4a")
    ap.add_argument("--saida")
    ap.add_argument("--preview")
    args = ap.parse_args()
    if args.preview:
        prancha(args.preview)
    else:
        audio = Path(args.audio) if args.audio and Path(args.audio).exists() else None
        gerar(args.saida or RAIZ / f"video_especialista_{args.idioma}.mp4", args.idioma, audio)
