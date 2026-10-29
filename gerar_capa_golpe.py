#!/usr/bin/env python3
"""Capa (thumbnail 9:16) do vídeo "GOLPE DO FALSO ADVOGADO", no estilo de dossiê/prova.

Usa os quadros já borrados do vídeo (gerar_video_golpe.preparar), então a capa nunca
mostra o rosto, o mapa, o GPS preciso, os IPs, a barra de tarefas nem o nome da
ferramenta. O título e a foto ficam dentro do recorte 3:4 central, que é o que aparece
na grade do perfil.

Uso:
    python3 gerar_capa_golpe.py                     # capa_golpe_falso_advogado.jpg
    python3 gerar_capa_golpe.py --embutir           # também grava a capa dentro do mp4
"""
import argparse
import subprocess
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import gerar_video_golpe as gv
from gerar_video_golpe import AMARELO, BRANCO, VERMELHO, W, H, fonte, FONTE_BLACK, FONTE_BOLD

RAIZ = Path(__file__).resolve().parent
VERDE_WPP = (0, 92, 75)
CINZA_WPP = (32, 44, 51)

QUADRO_FUNDO = ("painel", 100)   # painel inteiro (borrado) para o fundo
QUADRO_FOTO = ("close", 205)     # close da foto (borrada) para a "prova"


def rgba(img_bgr):
    return Image.fromarray(cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)).convert("RGBA")


def fundo(quadros):
    """Painel desfocado, escuro e puxado pro vermelho, com brilho atrás da foto e scanlines."""
    q = quadros[QUADRO_FUNDO[0]][QUADRO_FUNDO[1] - 1]
    img = cv2.resize(q, (W, int(W * q.shape[0] / q.shape[1])), interpolation=cv2.INTER_CUBIC)
    img = cv2.GaussianBlur(img[:H], (0, 0), 14).astype(np.float32)
    cinza = img.mean(axis=2, keepdims=True)
    img = cinza * np.array([0.35, 0.35, 0.9]) * 0.45 + img * 0.12   # BGR: tinge de vermelho
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    brilho = np.exp(-(((xx - W / 2) / 520) ** 2 + ((yy - 1000) / 560) ** 2))
    img += brilho[..., None] * np.array([20, 20, 120])
    r = np.sqrt(((xx - W / 2) / W) ** 2 + ((yy - H / 2) / H) ** 2)
    img *= (1 - 0.7 * np.clip(r - 0.3, 0, 1))[..., None]
    img[::4] *= 0.82  # scanlines
    ruido = np.random.default_rng(3).normal(0, 6, img.shape[:2])[..., None]
    return rgba(np.clip(img + ruido, 0, 255).astype(np.uint8))


def foto_prova(quadros, trilha):
    """Recorte da foto borrada do golpista como uma foto de evidência, com mira e etiqueta."""
    nome, i = QUADRO_FOTO
    q = quadros[nome][i - 1]
    cantos = trilha[nome]["foto"][i - 1]
    x0, y0 = cantos.min(axis=0) - (18, 18)
    x1, y1 = cantos.max(axis=0) + (18, 24)
    x0, y0 = max(int(x0), 0), max(int(y0), 0)
    x1, y1 = min(int(x1), q.shape[1]), min(int(y1), q.shape[0])
    rec = q[y0:y1, x0:x1].astype(np.float32)
    rec = np.clip((rec - 128) * 1.15 + 128, 0, 255).astype(np.uint8)
    larg = 680
    foto = rgba(cv2.resize(rec, (larg, int(larg * rec.shape[0] / rec.shape[1])), interpolation=cv2.INTER_CUBIC))
    d = ImageDraw.Draw(foto)
    # mira vermelha e linha de escaneamento sobre a área da foto
    pts = (cantos - (x0, y0)) * (larg / rec.shape[1])
    gv.cantoneiras(d, pts, VERMELHO + (255,), 10, 0.22)
    y_scan = pts[0][1] + (pts[3][1] - pts[0][1]) * 0.58
    d.line([(pts[0][0], y_scan), (pts[1][0], y_scan + (pts[1][1] - pts[0][1]))], fill=(255, 60, 60, 220), width=5)
    # moldura branca de "foto de evidência" com etiqueta embaixo
    borda, rodape = 18, 70
    card = Image.new("RGBA", (foto.width + 2 * borda, foto.height + borda + rodape), (245, 245, 240, 255))
    card.alpha_composite(foto, (borda, borda))
    dc = ImageDraw.Draw(card)
    dc.text((borda + 6, card.height - 22), "EVIDÊNCIA #01", font=fonte(FONTE_BLACK, 27),
            fill=(30, 30, 30), anchor="ls")
    dc.text((card.width - borda - 6, card.height - 22), "29/10", font=fonte(FONTE_BLACK, 27),
            fill=VERMELHO, anchor="rs")
    return card


def carimbo(txt, tam=118, angulo=-13):
    """Carimbo vermelho com textura gasta."""
    f = fonte(FONTE_BLACK, tam)
    lw = int(f.getlength(txt))
    img = Image.new("RGBA", (lw + 80, tam + 70), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([6, 6, img.width - 6, img.height - 6], 16, outline=VERMELHO + (255,), width=10)
    d.text((40, tam + 22), txt, font=f, fill=VERMELHO + (255,), anchor="ls")
    a = np.array(img)
    rng = np.random.default_rng(5)
    falhas = cv2.GaussianBlur(rng.random(a.shape[:2]).astype(np.float32), (0, 0), 1.6)
    a[..., 3] = (a[..., 3] * np.clip((falhas - 0.3) * 5, 0.45, 1)).astype(np.uint8)
    return Image.fromarray(a).rotate(angulo, expand=True, resample=Image.BICUBIC)


def balao(txt, hora, enviado):
    """Balão no estilo do WhatsApp (modo escuro)."""
    f, fh = fonte(FONTE_BOLD, 40), fonte(FONTE_BOLD, 24)
    lw = int(f.getlength(txt) + fh.getlength(hora + " ✓✓") + 70)
    img = Image.new("RGBA", (lw + 30, 100), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cor = VERDE_WPP if enviado else CINZA_WPP
    d.rounded_rectangle([12, 6, lw + 12, 90], 22, fill=cor + (255,))
    d.text((40, 62), txt, font=f, fill=BRANCO, anchor="ls")
    d.text((lw - 6, 80), hora + (" ✓✓" if enviado else ""), font=fh,
           fill=(83, 189, 235) if enviado else (170, 180, 185), anchor="rs")
    sombra = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(sombra).rounded_rectangle([18, 16, lw + 18, 98], 22, fill=(0, 0, 0, 150))
    sombra = sombra.filter(ImageFilter.GaussianBlur(8))
    sombra.alpha_composite(img)
    return sombra


def pino(d, cx, cy, r, cor):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=cor)
    d.polygon([(cx - r * 0.85, cy + r * 0.5), (cx + r * 0.85, cy + r * 0.5), (cx, cy + r * 2.1)], fill=cor)
    d.ellipse([cx - r * 0.42, cy - r * 0.42, cx + r * 0.42, cy + r * 0.42], fill=(255, 255, 255))


def texto_grande(canvas, txt, cor, tam, cy, contorno=12, sombra=True):
    f = fonte(FONTE_BLACK, tam)
    if sombra:
        s = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        ImageDraw.Draw(s).text((W / 2 + 8, cy + 10), txt, font=f, fill=(0, 0, 0, 200), anchor="mm",
                               stroke_width=contorno, stroke_fill=(0, 0, 0, 200))
        canvas.alpha_composite(s.filter(ImageFilter.GaussianBlur(10)))
    ImageDraw.Draw(canvas).text((W / 2, cy), txt, font=f, fill=cor, anchor="mm",
                                stroke_width=contorno, stroke_fill=(0, 0, 0))


def montar(quadros, trilha):
    capa = fundo(quadros)
    d = ImageDraw.Draw(capa)

    # selo de alerta
    f = fonte(FONTE_BLACK, 44)
    txt = "ALERTA DE GOLPE"
    lw = f.getlength(txt)
    x0 = W / 2 - (lw + 110) / 2
    d.rounded_rectangle([x0, 250, x0 + lw + 110, 328], 39, fill=VERMELHO)
    gv.triangulo_alerta(d, x0 + 50, 289, 21)
    d.text((x0 + 88, 305), txt, font=f, fill=BRANCO, anchor="ls")

    # título
    texto_grande(capa, "GOLPE DO", BRANCO, 140, 430)
    texto_grande(capa, "FALSO", AMARELO, 185, 582)
    texto_grande(capa, "ADVOGADO", AMARELO, 142, 734)

    # foto de evidência inclinada, com etiqueta GOLPISTA
    card = foto_prova(quadros, trilha).rotate(-4, expand=True, resample=Image.BICUBIC)
    sombra = Image.new("RGBA", (card.width + 80, card.height + 80), (0, 0, 0, 0))
    sombra.paste((0, 0, 0, 170), (40, 40), card)
    sombra = sombra.filter(ImageFilter.GaussianBlur(20))
    cx, cy = W // 2 - 10, 1135
    capa.alpha_composite(sombra, (cx - sombra.width // 2 + 14, cy - sombra.height // 2 + 22))
    capa.alpha_composite(card, (cx - card.width // 2, cy - card.height // 2))
    # fita adesiva prendendo a foto
    fita = Image.new("RGBA", (230, 64), (235, 225, 190, 190))
    fita = fita.rotate(-28, expand=True, resample=Image.BICUBIC)
    capa.alpha_composite(fita, (cx - card.width // 2 - 70, cy - card.height // 2 - 40))
    fita2 = Image.new("RGBA", (230, 64), (235, 225, 190, 190)).rotate(32, expand=True, resample=Image.BICUBIC)
    capa.alpha_composite(fita2, (cx + card.width // 2 - 160, cy - card.height // 2 - 40))
    gv.etiqueta(ImageDraw.Draw(capa), cx - card.width // 2 + 60, cy - card.height // 2 + 190, "GOLPISTA",
                VERMELHO, tam=46)

    # carimbo atravessando a foto
    st = carimbo("DESMASCARADO", tam=92, angulo=-16)
    capa.alpha_composite(st, (cx - st.width // 2 + 40, cy + 75 - st.height // 2))

    # balões da conversa e a cidade
    b1 = balao("Dr., mudou de contato?", "14:58", True).rotate(-4, expand=True, resample=Image.BICUBIC)
    capa.alpha_composite(b1, (W - b1.width - 8, 830))
    b2 = balao("Exatamente.", "15:00", False).rotate(5, expand=True, resample=Image.BICUBIC)
    capa.alpha_composite(b2, (6, 1225))

    d = ImageDraw.Draw(capa)
    f = fonte(FONTE_BLACK, 40)
    txt = "ARACAJU/SE"
    lw = f.getlength(txt)
    x0, y0 = W - lw - 140, 1395
    d.rounded_rectangle([x0, y0, x0 + lw + 110, y0 + 76], 38, fill=(0, 170, 100))
    pino(d, x0 + 46, y0 + 32, 15, (255, 255, 255))
    d.ellipse([x0 + 40, y0 + 26, x0 + 52, y0 + 38], fill=(0, 170, 100))
    d.text((x0 + 80, y0 + 53), txt, font=f, fill=BRANCO, anchor="ls")

    # chamada embaixo
    f1, f2 = fonte(FONTE_BLACK, 58), fonte(FONTE_BLACK, 58)
    linha1, linha2a, linha2b = "MANDEI UM LINK E DESCOBRI", "A CARA ", "DO GOLPISTA"
    d.text((W / 2, 1585), linha1, font=f1, fill=BRANCO, anchor="ms", stroke_width=7, stroke_fill=(0, 0, 0))
    l2 = f2.getlength(linha2a + linha2b)
    xs = W / 2 - l2 / 2
    d.text((xs, 1662), linha2a, font=f2, fill=BRANCO, anchor="ls", stroke_width=7, stroke_fill=(0, 0, 0))
    d.text((xs + f2.getlength(linha2a), 1662), linha2b, font=f2, fill=AMARELO, anchor="ls",
           stroke_width=7, stroke_fill=(0, 0, 0))
    return capa.convert("RGB")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--saida", default=str(RAIZ / "capa_golpe_falso_advogado.jpg"))
    ap.add_argument("--embutir", action="store_true", help="grava a capa como thumbnail do mp4")
    args = ap.parse_args()
    quadros, trilha = gv.preparar()
    montar(quadros, trilha).save(args.saida, quality=95)
    print("ok:", args.saida)
    if args.embutir:
        video = RAIZ / "video_golpe_falso_advogado.mp4"
        tmp = video.with_suffix(".tmp.mp4")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(video), "-i", args.saida,
                        "-map", "0", "-map", "1", "-c", "copy", "-disposition:v:1", "attached_pic",
                        "-movflags", "+faststart", str(tmp)], check=True)
        tmp.replace(video)
        print("capa embutida em", video)


if __name__ == "__main__":
    main()
