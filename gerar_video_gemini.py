#!/usr/bin/env python3
"""O vídeo do Gemini inteiro no formato do meme, em câmera lenta e com cara de cinema.

As três cenas do clipe (atravessa a porta, senta de frente para o outro, os dois se encaram)
são desaceleradas para ocupar a trilha inteira. Assim os cortes caem nas mesmas batidas do
meme original (5,43s e 11,6s). A câmera lenta usa interpolação de movimento (quadros novos
entre os originais) para não ficar travada; o resultado da interpolação fica em cache em
clipes/.cache porque é a parte demorada.

Uso:
    python3 gerar_video_gemini.py                 # legenda em português
    python3 gerar_video_gemini.py --idioma en
"""
import argparse
import subprocess
from pathlib import Path

import cv2
import numpy as np

import gerar_video as gv
import gerar_video_praia as gp
from gerar_video_montagem import CLIPE, Clipe, estatisticas_lab

CACHE = gv.RAIZ / "clipes" / ".cache"
INTERPOLAR = "minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1"

# trechos do clipe original (sem pegar os quadros dos cortes, em 3,42s e 6,96s)
TRECHOS = {"andar": (0.0, 3.40), "sentar": (3.44, 6.94), "encarar": (6.98, 10.0)}

# (início, fim, trecho, (cx, cy, largura) inicial, (cx, cy, largura) final), em pixels de 1280x720
PLANOS = [
    (0.00, 5.43, "andar", (640, 360, 1250), (660, 340, 1060)),
    (5.43, 11.60, "sentar", (640, 370, 1250), (640, 385, 1100)),
    (11.60, gv.DURACAO, "encarar", (640, 360, 1250), (640, 375, 1080)),
]


def interpolado(nome, inicio, fim):
    """Trecho em 60 quadros/s com interpolação de movimento (gerado uma vez e guardado)."""
    CACHE.mkdir(parents=True, exist_ok=True)
    arq = CACHE / f"{nome}_60fps.mp4"
    if not arq.exists():
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", str(inicio), "-i", str(CLIPE),
                        "-t", str(fim - inicio), "-vf", INTERPOLAR, "-an", "-c:v", "libx264",
                        "-crf", "12", "-preset", "fast", str(arq)], check=True)
    return arq


class GradeEstilo(gv.Grade):
    """Tratamento de cinema com um leve brilho (bloom) nas luzes altas."""

    def __call__(self, img, i):
        luz = np.clip((img - 0.72) / 0.28, 0, 1) * img
        img = img + 0.3 * cv2.GaussianBlur(luz, (0, 0), 14)
        return super().__call__(np.clip(img, 0, 1), i)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--idioma", choices=gv.LEGENDAS, default="pt")
    ap.add_argument("--audio", default=gv.RAIZ / "audio" / "trilha.m4a")
    ap.add_argument("--saida")
    args = ap.parse_args()

    cenas = gp.carregar_cenas()
    alvo = estatisticas_lab([cenas["img3"], cenas["img5"]])  # tom dourado das cenas do ChatGPT
    clipes, fontes = {}, {}
    for nome, (ini, fim) in TRECHOS.items():
        arq = interpolado(nome, ini, fim)
        clipes[nome] = Clipe(arq, 0, fim - ini + 1, cor_alvo=alvo, forca=0.7)
        fontes[nome] = clipes[nome].primeiro()

    grade = GradeEstilo(saturacao=0.92, tom=(1.0, 1.0, 0.99))
    audio = Path(args.audio) if Path(args.audio).exists() else None
    saida = args.saida or gv.RAIZ / f"video_especialista_gemini_{args.idioma}.mp4"
    gv.gerar(saida, args.idioma, audio, fontes, PLANOS, grade, amp_balanco=0.0025, animadas=clipes)
