#!/usr/bin/env python3
"""Versão "especialista falando com especialista" com as cenas geradas no ChatGPT (pasta cenas/).

Ele caminha até a porta na praia, abre, o outro eu está esperando sentado à mesa e
os dois se encaram. Mesmo layout, trilha e pontos de corte do meme original.

As cenas são "fotos vivas": mar e nuvens se mexem, as pessoas e objetos ficam em camadas
com profundidade, e na cena da maçaneta os dedos giram e a porta vem em direção à câmera.
As máscaras ficam em cenas/mascaras (geradas por mascaras.py).

Uso:
    python3 gerar_video_praia.py                    # legenda em português
    python3 gerar_video_praia.py --idioma en
    python3 gerar_video_praia.py --estatico         # sem animação, só movimento de câmera
    python3 gerar_video_praia.py --preview prev.png
"""
import argparse
from pathlib import Path

import cv2
import numpy as np

import gerar_video as gv
from animacao import Camada, Cena, suave
from mascaras import carregar as carregar_mascaras

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

HORIZONTE = {"img1": 516, "img2": 305, "img3": 340, "img4": 382, "img5": 397, "img6": 300, "img7": 364}
PARALAXE = {"img1": 1.1, "img3": 1.12, "img4": 1.1, "img5": 1.08, "img6": 1.1, "img7": 1.1}


def gira_macaneta(t):
    """Dedos giram a maçaneta na primeira metade do plano."""
    return {"torcao": (1300, 470, 430, np.radians(9) * suave(t / 0.55))}


def puxa_porta(t):
    """Na segunda metade, porta (e a mão junto) vem em direção à câmera, presa na dobradiça à direita."""
    e = 1 + 0.07 * suave((t - 0.5) / 0.5)
    pivo = (2150, 470)
    return {"afim": [[e, 0, pivo[0] * (1 - e)], [0, e, pivo[1] * (1 - e)]]}


def mao_na_porta(t):
    return {**gira_macaneta(t), **puxa_porta(t)}


def carregar_cenas():
    fontes = {}
    for arq in sorted(CENAS.glob("img*.jpg")):
        img = cv2.imread(str(arq), cv2.IMREAD_COLOR)
        fontes[arq.stem] = cv2.cvtColor(img, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    return fontes


def montar_animadas(fontes):
    cenas = {}
    for nome, img in fontes.items():
        m = carregar_mascaras(nome)
        if nome == "img2":
            camadas = [Camada(m["porta"], 1.06, puxa_porta, preencher_vertical=True), Camada(m["mao"], 1.1, mao_na_porta)]
        else:
            camadas = [Camada(m["frente"], PARALAXE[nome])]
        cenas[nome] = Cena(img, camadas, ceu=m["ceu"], mar=m["mar"], horizonte=HORIZONTE[nome])
    return cenas


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--idioma", choices=gv.LEGENDAS, default="pt")
    ap.add_argument("--audio", default=gv.RAIZ / "audio" / "trilha.m4a")
    ap.add_argument("--saida")
    ap.add_argument("--preview")
    ap.add_argument("--estatico", action="store_true")
    args = ap.parse_args()
    fontes = carregar_cenas()
    if args.preview:
        gv.prancha(args.preview, fontes, PLANOS)
    else:
        # as cenas já vêm com cor de cinema: tratamento mais leve que na versão com fotos
        grade = gv.Grade(saturacao=0.9, tom=(1.0, 1.0, 0.99))
        audio = Path(args.audio) if Path(args.audio).exists() else None
        saida = args.saida or gv.RAIZ / f"video_especialista_praia_{args.idioma}.mp4"
        animadas = None if args.estatico else montar_animadas(fontes)
        gv.gerar(saida, args.idioma, audio, fontes, PLANOS, grade, amp_balanco=0.0035, animadas=animadas)
