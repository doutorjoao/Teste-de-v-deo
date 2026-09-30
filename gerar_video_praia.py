#!/usr/bin/env python3
"""Versão "especialista falando com especialista" com as cenas geradas no ChatGPT (pasta cenas/).

Ele caminha até a porta na praia, abre, o outro eu está esperando sentado à mesa e
os dois se encaram. Mesmo layout, trilha e pontos de corte do meme original.

Uso:
    python3 gerar_video_praia.py                    # legenda em português
    python3 gerar_video_praia.py --idioma en
    python3 gerar_video_praia.py --preview prev.png
"""
import argparse
from pathlib import Path

import cv2
import numpy as np

import gerar_video as gv

CENAS = Path(__file__).resolve().parent / "cenas"

# (início, fim, cena, (cx, cy, largura) inicial, (cx, cy, largura) final), em pixels de 1672x941
PLANOS = [
    (0.00, 1.00, "img1", (800, 470, 1560), (880, 480, 1450)),     # caminha até a porta
    (1.00, 2.93, "img2", (836, 470, 1600), (1000, 470, 1250)),    # mão na maçaneta
    (2.93, 5.43, "img3", (836, 470, 1600), (930, 520, 820)),      # atravessa a porta: o outro espera
    (5.43, 6.00, "img4", (836, 460, 1450), (840, 440, 1380)),     # ele percebe quem chegou
    (6.00, 9.70, "img5", (836, 470, 1600), (836, 450, 1420)),     # frente a frente
    (9.70, 11.60, "img6", (836, 470, 1500), (880, 400, 1250)),    # o especialista encara
    (11.60, 15.27, "img7", (836, 470, 1600), (760, 400, 1200)),   # o outro toma o café
    (15.27, gv.DURACAO, "img5", (836, 470, 1560), (836, 470, 1520)),
]


def carregar_cenas():
    fontes = {}
    for arq in sorted(CENAS.glob("img*.jpg")):
        img = cv2.imread(str(arq), cv2.IMREAD_COLOR)
        fontes[arq.stem] = cv2.cvtColor(img, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    return fontes


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--idioma", choices=gv.LEGENDAS, default="pt")
    ap.add_argument("--audio", default=gv.RAIZ / "audio" / "trilha.m4a")
    ap.add_argument("--saida")
    ap.add_argument("--preview")
    args = ap.parse_args()
    fontes = carregar_cenas()
    if args.preview:
        gv.prancha(args.preview, fontes, PLANOS)
    else:
        # as cenas já vêm com cor de cinema: tratamento mais leve que na versão com fotos
        grade = gv.Grade(saturacao=0.9, tom=(1.0, 1.0, 0.99))
        audio = Path(args.audio) if Path(args.audio).exists() else None
        saida = args.saida or gv.RAIZ / f"video_especialista_praia_{args.idioma}.mp4"
        gv.gerar(saida, args.idioma, audio, fontes, PLANOS, grade, amp_balanco=0.0035)
