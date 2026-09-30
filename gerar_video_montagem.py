#!/usr/bin/env python3
"""Montagem final: movimento real do vídeo do Gemini + closes das cenas do ChatGPT.

Os planos abertos (ele atravessando a porta e sentando de frente para o outro) vêm do clipe
gerado no Gemini, que tem movimento de verdade. Os closes, onde o rosto importa, vêm das cenas
do ChatGPT (animadas como "foto viva"). A cor do clipe do Gemini é puxada para o tom dourado
das cenas, para tudo parecer o mesmo filme.

Uso:
    python3 gerar_video_montagem.py                 # legenda em português
    python3 gerar_video_montagem.py --idioma en
"""
import argparse
import re
import subprocess
from pathlib import Path

import cv2
import numpy as np

import gerar_video as gv
import gerar_video_praia as gp

CLIPE = gv.RAIZ / "clipes" / "gemini_porta_mesa.mp4"


def estatisticas_lab(imagens):
    lab = np.concatenate([cv2.cvtColor(i, cv2.COLOR_RGB2LAB).reshape(-1, 3) for i in imagens])
    return lab.mean(0), lab.std(0) + 1e-6


class Clipe:
    """Trecho de vídeo usado como plano; o trecho inteiro é esticado para a duração do plano."""

    def __init__(self, caminho, inicio, fim, espelhar=False, cor_alvo=None, forca=0.75):
        info = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(caminho)], capture_output=True, text=True).stderr
        w, h = map(int, re.search(r"Video:.*?(\d{3,5})x(\d{3,5})", info).groups())
        bruto = subprocess.run(["ffmpeg", "-loglevel", "error", "-ss", str(inicio), "-i", str(caminho),
                                "-t", str(fim - inicio), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                               capture_output=True, check=True).stdout
        self.quadros = np.frombuffer(bruto, np.uint8).reshape(-1, h, w, 3)
        if espelhar:
            self.quadros = self.quadros[:, :, ::-1]
        self.cor = None
        if cor_alvo is not None:
            amostras = [self.quadros[i].astype(np.float32) / 255
                        for i in np.linspace(0, len(self.quadros) - 1, 6).astype(int)]
            self.cor = (*estatisticas_lab(amostras), *cor_alvo, forca)
        self.shape = (h, w, 3)

    def _cor(self, img):
        if self.cor is None:
            return img
        mu_o, sd_o, mu_a, sd_a, forca = self.cor
        lab = cv2.cvtColor(img, cv2.COLOR_RGB2LAB)
        alvo = (lab - mu_o) / sd_o * sd_a + mu_a
        lab = (lab + forca * (alvo - lab)).astype(np.float32)
        return np.clip(cv2.cvtColor(lab, cv2.COLOR_LAB2RGB), 0, 1)

    def primeiro(self):
        return self._cor(self.quadros[0].astype(np.float32) / 255)

    def quadro(self, t, t_plano, cam, cam0, largura, altura):
        i = int(round(t_plano * (len(self.quadros) - 1)))
        img = self._cor(self.quadros[min(i, len(self.quadros) - 1)].astype(np.float32) / 255)
        return gv.renderizar_quadro(img, *cam)


QUADRO_CLIPE = ((640, 360, 1250), (640, 360, 1210))

PLANOS = [
    gp.PLANOS[0],                                   # caminha até a porta (cena 1)
    gp.PLANOS[1],                                   # mão na maçaneta, porta abrindo (cena 2)
    (2.93, 5.43, "porta", *QUADRO_CLIPE),           # Gemini: atravessa a porta, o outro espera
    gp.PLANOS[3],                                   # o outro percebe quem chegou (cena 4)
    (6.00, 9.70, "mesa", *QUADRO_CLIPE),            # Gemini: senta de frente para o outro
    gp.PLANOS[5],                                   # o especialista encara (cena 6)
    gp.PLANOS[6],                                   # o outro toma o café (cena 7)
    (15.27, gv.DURACAO, "mesa_fim", (640, 360, 1250), (640, 360, 1240)),  # os dois se encarando
]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--idioma", choices=gv.LEGENDAS, default="pt")
    ap.add_argument("--audio", default=gv.RAIZ / "audio" / "trilha.m4a")
    ap.add_argument("--saida")
    args = ap.parse_args()

    fontes = gp.carregar_cenas()
    animadas = gp.montar_animadas({k: v for k, v in fontes.items() if k in {"img1", "img2", "img4", "img6", "img7"}})
    alvo = estatisticas_lab([fontes["img3"], fontes["img5"]])
    animadas["porta"] = Clipe(CLIPE, 0.88, 3.38, cor_alvo=alvo)
    # espelhado: o de terno fica à direita, como nas cenas do ChatGPT e nos olhares dos closes
    animadas["mesa"] = Clipe(CLIPE, 3.46, 6.92, espelhar=True, cor_alvo=alvo)
    animadas["mesa_fim"] = Clipe(CLIPE, 6.20, 6.80, espelhar=True, cor_alvo=alvo)
    for nome in ("porta", "mesa", "mesa_fim"):
        fontes[nome] = animadas[nome].primeiro()

    grade = gv.Grade(saturacao=0.9, tom=(1.0, 1.0, 0.99))
    audio = Path(args.audio) if Path(args.audio).exists() else None
    saida = args.saida or gv.RAIZ / f"video_especialista_final_{args.idioma}.mp4"
    gv.gerar(saida, args.idioma, audio, fontes, PLANOS, grade, amp_balanco=0.0035, animadas=animadas)
