#!/usr/bin/env python3
"""Vídeo "GOLPE DO FALSO ADVOGADO" (vertical 9:16) a partir dos 3 clipes gravados no celular.

Roteiro:
  1. A ISCA            - conversa no WhatsApp com o golpista e o falso link do "Drive"
  2. O LINK RASTREADOR - painel no notebook com o que o link capturou
  3. GOLPISTA EXPOSTO  - close no painel: foto, aparelho e cidade
  + cartela final com dicas de como não cair no golpe.

Privacidade: no painel, a foto da pessoa, o mapa, o GPS preciso, os IPs, o nome da
ferramenta e a barra de tarefas (ícones dos apps) são borrados. As áreas são marcadas
uma vez num quadro de referência e seguem a tela quadro a quadro por homografia
(SIFT + RANSAC). Só a localização por IP
(nível cidade) fica visível.

A narração entra como trilha, com legenda sincronizada. Por baixo vai uma música
sintetizada em musica_golpe.py (clima de investigação, que abaixa sozinha quando a voz
entra) e efeitos: whoosh nos cortes e impacto no título.

Os arquivos de entrada ficam em golpe/ (fora do git, porque têm os dados sem borrar):
    golpe/chat.mp4  golpe/painel.mp4  golpe/close.mp4  golpe/narracao.m4a

Uso:
    python3 gerar_video_golpe.py
    python3 gerar_video_golpe.py --preview prev.jpg     # só uma prancha de quadros
    python3 gerar_video_golpe.py --saida outro.mp4
    python3 gerar_video_golpe.py --so-audio          # refaz só o áudio sobre o último render
"""
import argparse
import json
import subprocess
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

import musica_golpe

RAIZ = Path(__file__).resolve().parent
ENTRADA = RAIZ / "golpe"
CACHE = ENTRADA / ".cache"

W, H, FPS = 1080, 1920, 30
SR = 48000
ESCALA = W / 576  # os clipes são 576x1024 depois da rotação

FONTE_BLACK = "/usr/share/fonts/opentype/inter/Inter-Black.otf"
FONTE_XBOLD = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"
FONTE_BOLD = "/usr/share/fonts/opentype/inter/Inter-Bold.otf"
FONTE_SEMI = "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf"

VERMELHO = (230, 30, 45)
AMARELO = (255, 214, 0)
BRANCO = (255, 255, 255)

# Quadro de referência: painel.mp4, quadro 100 (aparece a tela inteira).
REF_CLIPE, REF_QUADRO = "painel", 100

# Áreas a borrar, em pixels do quadro de referência (cantos: sup-esq, sup-dir, inf-dir, inf-esq).
BORRAR = {
    "foto": [(138, 243), (304, 245), (293, 387), (122, 381)],    # foto da câmera da pessoa
    "mapa": [(303, 238), (495, 238), (480, 397), (287, 390)],    # mapa com o pino do GPS
    "gps": [(283, 469), (460, 473), (458, 502), (278, 498)],     # "GPS preciso" (lat/lon e raio)
    "ips_locais": [(211, 477), (258, 477), (258, 499), (211, 499)],
    "ip": [(355, 529), (410, 531), (410, 549), (355, 547)],
}
# Cabeçalho com o nome da ferramenta (barra de título + logo), marcado no quadro 180 do painel.
CABECALHO_Q180 = [(-30, 175), (40, 175), (40, 209), (-30, 209)]
# Barra de tarefas inteira (ícones dos apps, inclusive o da ferramenta), marcada no quadro 1 do painel.
BARRA_TAREFAS_Q1 = [(-20, 516), (580, 585), (580, 622), (-20, 541)]
# Destaques animados (não borram nada)
LOCAL = [(281, 397), (347, 399), (347, 415), (281, 413)]          # "Aracaju, Sergipe, BR"

# Montagem: (clipe, início no vídeo final)
CLIPES = [("chat", 0.0), ("painel", 265 / FPS), ("close", (265 + 211) / FPS)]
FIM_CLIPES = (265 + 211 + 237) / FPS          # 23.77 s
DURACAO = 28.6

CAPITULOS = [
    (2.7, 8.5, "1 · A ISCA", "Um falso link do “Drive” com documentos do INSS"),
    (9.1, 14.3, "2 · O LINK RASTREADOR", "O golpista abriu o link… e entregou tudo"),
    (16.1, 19.3, "3 · GOLPISTA EXPOSTO", "Foto, aparelho e cidade: Aracaju/SE"),
]

# Narração (transcrita do áudio), com início/fim de cada frase em segundos.
FALAS = [
    (0.99, 3.35, "Veja só, nem sempre a justiça funciona."),
    (3.54, 6.12, "Então temos que usar das malícias que escolhemos na vida"),
    (6.54, 10.29, "pra saber quem é o golpista que se passa pelo seu próprio advogado."),
    (10.96, 14.45, "Usando só uma engenharia social e um linkzinho que eu mesmo criei,"),
    (14.65, 16.34, "podemos descobrir aqui o nome,"),
    (16.74, 17.41, "o endereço"),
    (17.95, 18.30, "e…"),
    (18.83, 21.37, "simplesmente a foto do safado. Veja só aí!"),
    (21.71, 23.40, "Nem sempre a justiça é tão rápida"),
    (23.71, 25.35, "quanto a própria malícia da vida."),
]
DESTAQUES = {"justiça", "malícias", "malícia", "golpista", "advogado", "engenharia", "social",
             "linkzinho", "nome", "endereço", "foto", "safado", "rápida"}

DICAS_INICIO = FIM_CLIPES + 0.15
DICAS = [
    "Desconfie de “mudei de número”",
    "Ligue no telefone oficial do escritório",
    "Nunca pague taxa pra liberar processo",
    "Na dúvida, consulte o processo no site do tribunal",
]


# ----------------------------------------------------------------------------- entrada

def ler_quadros(nome):
    """Lê todos os quadros do clipe já girados (o ffmpeg aplica a rotação do celular)."""
    cmd = ["ffmpeg", "-v", "error", "-i", str(ENTRADA / f"{nome}.mp4"), "-f", "rawvideo",
           "-pix_fmt", "bgr24", "-"]
    dados = subprocess.run(cmd, capture_output=True, check=True).stdout
    return list(np.frombuffer(dados, np.uint8).reshape(-1, 1024, 576, 3))


def rastrear(quadros_por_clipe):
    """Homografia referência -> quadro, para cada quadro do painel e do close (com cache)."""
    arq = CACHE / "homografias.json"
    if arq.exists():
        return {k: [np.array(h) for h in v] for k, v in json.loads(arq.read_text()).items()}
    sift = cv2.SIFT_create(nfeatures=6000, contrastThreshold=0.02)
    ref = cv2.cvtColor(quadros_por_clipe[REF_CLIPE][REF_QUADRO - 1], cv2.COLOR_BGR2GRAY)
    mascara = np.zeros_like(ref)
    mascara[160:620] = 255  # só a tela do notebook
    k_ref, d_ref = sift.detectAndCompute(ref, mascara)
    bf = cv2.BFMatcher(cv2.NORM_L2)

    def casar(img, previsto):
        k, d = sift.detectAndCompute(img, None)
        pares = [p for p in bf.knnMatch(d_ref, d, k=2) if len(p) == 2]
        bons = [m for m, n in pares if m.distance < 0.8 * n.distance]
        src = np.float32([k_ref[m.queryIdx].pt for m in bons])
        dst = np.float32([k[m.trainIdx].pt for m in bons])
        if previsto is not None and len(src):
            perto = np.linalg.norm(cv2.perspectiveTransform(src[None], previsto)[0] - dst, axis=1) < 40
            src, dst = src[perto], dst[perto]
        if len(src) < 12:
            return None, 0
        hom, inl = cv2.findHomography(src, dst, cv2.RANSAC, 3.0)
        return hom, (0 if inl is None else int(inl.sum()))

    res = {}
    for nome in ("painel", "close"):
        anterior, lista = None, []
        for q in quadros_por_clipe[nome]:
            img = cv2.cvtColor(q, cv2.COLOR_BGR2GRAY)
            hom, n = casar(img, anterior)
            if hom is None or n < 25:  # perdeu o rastro: tenta sem previsão
                hom2, n2 = casar(img, None)
                if hom2 is not None and n2 > n:
                    hom, n = hom2, n2
            hom = anterior if hom is None else hom
            lista.append(hom)
            anterior = hom
        res[nome] = lista
    CACHE.mkdir(parents=True, exist_ok=True)
    arq.write_text(json.dumps({k: [h.tolist() for h in v] for k, v in res.items()}))
    return res


def projetar(pts, hom):
    return cv2.perspectiveTransform(np.float32(pts)[None], hom)[0]


def trilhas(homs, poligono, janela=2):
    """Cantos do polígono em cada quadro, suavizados no tempo para não tremer."""
    cantos = np.stack([projetar(poligono, h) for h in homs])
    suav = np.empty_like(cantos)
    for i in range(len(cantos)):
        suav[i] = cantos[max(0, i - janela):i + janela + 1].mean(axis=0)
    return suav


def expandir(cantos, fator=1.06, px=3):
    c = cantos.mean(axis=0)
    v = cantos - c
    n = np.linalg.norm(v, axis=1, keepdims=True) + 1e-6
    return c + v * fator + v / n * px


# ----------------------------------------------------------------------------- borrões

def borrar(img, cantos, tipo):
    """Borra um quadrilátero: mosaico grosso para foto/mapa, desfoque forte para texto."""
    fator = {"foto": 1.08, "mapa": 1.08, "barra": 1.02}.get(tipo, 1.12)
    cantos = expandir(cantos, fator, 2 if tipo == "barra" else 3)
    x0, y0 = np.floor(cantos.min(axis=0)).astype(int) - 12
    x1, y1 = np.ceil(cantos.max(axis=0)).astype(int) + 12
    x0, y0 = max(x0, 0), max(y0, 0)
    x1, y1 = min(x1, img.shape[1]), min(y1, img.shape[0])
    if x1 - x0 < 4 or y1 - y0 < 4:
        return
    rec = img[y0:y1, x0:x1].astype(np.float32)
    lado = np.linalg.norm(cantos[1] - cantos[0])
    alto = np.linalg.norm(cantos[3] - cantos[0])
    if tipo in ("foto", "mapa"):
        bloco = max(6, int(lado / 11))
    else:
        bloco = max(4, int(alto / 2.2))
    pequeno = cv2.resize(rec, (max(1, (x1 - x0) // bloco), max(1, (y1 - y0) // bloco)),
                         interpolation=cv2.INTER_AREA)
    mosaico = cv2.resize(pequeno, (x1 - x0, y1 - y0), interpolation=cv2.INTER_NEAREST)
    mosaico = cv2.GaussianBlur(mosaico, (0, 0), bloco * 0.35)
    if tipo not in ("foto", "mapa"):
        mosaico = cv2.GaussianBlur(mosaico, (0, 0), alto * 0.5)
    m = np.zeros((y1 - y0, x1 - x0), np.float32)
    cv2.fillPoly(m, [np.round(cantos - (x0, y0)).astype(np.int32)], 1.0, cv2.LINE_AA)
    m = cv2.GaussianBlur(m, (0, 0), 1.5)[..., None]
    img[y0:y1, x0:x1] = np.clip(rec * (1 - m) + mosaico * m, 0, 255).astype(np.uint8)


# ----------------------------------------------------------------------------- texto

_fontes = {}


def fonte(arq, tam):
    if (arq, tam) not in _fontes:
        _fontes[(arq, tam)] = ImageFont.truetype(arq, tam)
    return _fontes[(arq, tam)]


def suave(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def sai_mola(x):
    """Entrada com leve passada do ponto (efeito "pop")."""
    x = min(max(x, 0.0), 1.0)
    return 1 + 2.2 * (x - 1) ** 3 + 1.2 * (x - 1) ** 2


def texto_com_contorno(draw, xy, txt, f, cor, contorno=7, anchor="la"):
    draw.text(xy, txt, font=f, fill=cor, stroke_width=contorno, stroke_fill=(0, 0, 0), anchor=anchor)


def blocos_legenda():
    """Quebra cada fala em blocos de até 3 palavras, com tempo de cada palavra."""
    blocos = []
    for ini, fim, frase in FALAS:
        palavras = frase.split()
        pesos = np.array([len(p) + 2 for p in palavras], float)
        bordas = ini + np.concatenate([[0], np.cumsum(pesos)]) / pesos.sum() * (fim - ini)
        atual = []
        for i, p in enumerate(palavras):
            atual.append((p, bordas[i], bordas[i + 1]))
            chars = sum(len(a[0]) for a in atual)
            if len(atual) == 3 or chars > 13 or p[-1] in ",.!?…" or i == len(palavras) - 1:
                blocos.append(atual)
                atual = []
    # cada bloco fica na tela até o próximo começar (ou um pouco depois do fim da fala)
    saida = []
    for i, b in enumerate(blocos):
        fim = b[-1][2] + 0.35
        if i + 1 < len(blocos):
            fim = min(fim, blocos[i + 1][0][1]) if blocos[i + 1][0][1] - b[-1][2] < 0.6 else fim
        saida.append((b[0][1], fim, b))
    return saida


BLOCOS = blocos_legenda()


def desenhar_legenda(canvas, t):
    for ini, fim, palavras in BLOCOS:
        if not ini <= t < fim:
            continue
        f = fonte(FONTE_BLACK, 78)
        tokens = [p[0].upper() for p in palavras]
        esp = 22
        larg = [f.getlength(tk) for tk in tokens]
        total = sum(larg) + esp * (len(tokens) - 1)
        camada = Image.new("RGBA", (int(total) + 60, 140), (0, 0, 0, 0))
        d = ImageDraw.Draw(camada)
        x = 30
        for (p, pi, pf), tk, lw in zip(palavras, tokens, larg):
            limpa = p.strip(",.!?…:“”").lower()
            falando = pi <= t < pf + 0.05
            cor = AMARELO if (limpa in DESTAQUES or falando) else BRANCO
            if limpa in DESTAQUES and not falando and t < pi:
                cor = BRANCO
            d.text((x + 4, 76), tk, font=f, fill=(0, 0, 0, 150), anchor="ls")  # sombra
            d.text((x, 70), tk, font=f, fill=cor, stroke_width=8, stroke_fill=(0, 0, 0), anchor="ls")
            x += lw + esp
        s = 0.82 + 0.18 * sai_mola((t - ini) / 0.16)
        camada = camada.resize((max(1, int(camada.width * s)), max(1, int(camada.height * s))),
                               Image.LANCZOS)
        canvas.alpha_composite(camada, (int(W / 2 - camada.width / 2), int(1450 - camada.height / 2)))


def triangulo_alerta(d, cx, cy, r, cor=AMARELO):
    d.polygon([(cx, cy - r), (cx + r * 1.1, cy + r * 0.85), (cx - r * 1.1, cy + r * 0.85)], fill=cor)
    f = fonte(FONTE_BLACK, int(r * 1.3))
    d.text((cx, cy + r * 0.55), "!", font=f, fill=(0, 0, 0), anchor="ms")


def desenhar_titulo(canvas, t):
    """Abertura: alerta piscando + título em duas linhas."""
    if t > 2.9:
        return
    sai = 1 - suave((t - 2.5) / 0.4)
    camada = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(camada)
    # faixa escura atrás do título
    for y in range(240, 860):
        a = int(170 * sai * (1 - abs(y - 550) / 310) ** 0.6)
        d.line([(0, y), (W, y)], fill=(0, 0, 0, a))
    # selo "ALERTA" piscando
    if (int(t * 4) % 2 == 0 or t > 1.2) and t > 0.05:
        f = fonte(FONTE_BLACK, 46)
        txt = "ALERTA DE GOLPE"
        lw = f.getlength(txt)
        x0 = W / 2 - (lw + 110) / 2
        d.rounded_rectangle([x0, 330, x0 + lw + 110, 410], 18, fill=VERMELHO + (int(255 * sai),))
        triangulo_alerta(d, x0 + 48, 372, 22)
        d.text((x0 + 88, 388), txt, font=f, fill=(255, 255, 255, int(255 * sai)), anchor="ls")
    canvas.alpha_composite(camada)
    for i, (txt, cor, tam, y) in enumerate([("GOLPE DO", BRANCO, 120, 560),
                                            ("FALSO ADVOGADO", AMARELO, 108, 690)]):
        p = sai_mola((t - 0.12 - i * 0.18) / 0.3)
        if p <= 0:
            continue
        f = fonte(FONTE_BLACK, tam)
        lw = int(f.getlength(txt)) + 40
        img = Image.new("RGBA", (lw, tam + 60), (0, 0, 0, 0))
        di = ImageDraw.Draw(img)
        di.text((20, tam + 20), txt, font=f, fill=cor + (255,), stroke_width=10, stroke_fill=(0, 0, 0),
                anchor="ls")
        s = 1.6 - 0.6 * p
        img = img.resize((int(img.width * s), int(img.height * s)), Image.LANCZOS)
        if sai < 1:
            a = np.array(img)
            a[..., 3] = (a[..., 3] * sai).astype(np.uint8)
            img = Image.fromarray(a)
        canvas.alpha_composite(img, (int(W / 2 - img.width / 2), int(y - img.height / 2 - 20)))


def desenhar_selo(canvas, t):
    """Selo fixo no topo depois da abertura."""
    if t < 2.6 or t > DICAS_INICIO + 0.3:
        return
    a = suave((t - 2.6) / 0.3) * (1 - suave((t - DICAS_INICIO) / 0.3))
    d = ImageDraw.Draw(canvas)
    f = fonte(FONTE_BLACK, 36)
    txt = "GOLPE DO FALSO ADVOGADO"
    lw = f.getlength(txt)
    x0, y0 = W / 2 - (lw + 96) / 2, 96 - (1 - a) * 40
    d.rounded_rectangle([x0, y0, x0 + lw + 96, y0 + 66], 33, fill=VERMELHO + (int(235 * a),))
    triangulo_alerta(d, x0 + 42, y0 + 33, 16)
    d.text((x0 + 72, y0 + 46), txt, font=f, fill=(255, 255, 255, int(255 * a)), anchor="ls")


def desenhar_capitulo(canvas, t):
    for ini, fim, titulo, sub in CAPITULOS:
        if not ini <= t < fim:
            continue
        e = suave((t - ini) / 0.35)
        s = 1 - suave((t - fim + 0.35) / 0.35)
        a = e * s
        dx = (1 - e) * -120
        camada = Image.new("RGBA", (W, 260), (0, 0, 0, 0))
        d = ImageDraw.Draw(camada)
        ft, fs = fonte(FONTE_BLACK, 50), fonte(FONTE_SEMI, 34)
        lw = max(ft.getlength(titulo), fs.getlength(sub)) + 70
        d.rounded_rectangle([40, 10, 40 + lw, 150], 22, fill=(10, 10, 14, 200))
        d.rectangle([40, 10, 52, 150], fill=AMARELO)
        d.text((76, 70), titulo, font=ft, fill=AMARELO, anchor="ls")
        d.text((76, 124), sub, font=fs, fill=BRANCO, anchor="ls")
        arr = np.array(camada)
        arr[..., 3] = (arr[..., 3] * a).astype(np.uint8)
        canvas.alpha_composite(Image.fromarray(arr), (int(dx), 190))


def desenhar_dicas(canvas, t):
    if t < DICAS_INICIO:
        return
    d = ImageDraw.Draw(canvas)
    u = t - DICAS_INICIO
    ft = fonte(FONTE_BLACK, 66)
    a = suave(u / 0.35)
    y = 300 + (1 - a) * 40
    triangulo_alerta(d, 140, y - 22, 34)
    d.text((200, y), "COMO NÃO CAIR", font=ft, fill=(255, 255, 255, int(255 * a)), anchor="ls")
    d.text((200, y + 80), "NESSE GOLPE", font=ft, fill=AMARELO + (int(255 * a),), anchor="ls")
    fd = fonte(FONTE_BOLD, 42)
    for i, dica in enumerate(DICAS):
        e = suave((u - 0.45 - i * 0.45) / 0.35)
        if e <= 0:
            continue
        yy = 560 + i * 150
        x = 80 + (1 - e) * 80
        d.rounded_rectangle([x, yy, x + 920, yy + 118], 24, fill=(255, 255, 255, int(235 * e)))
        d.ellipse([x + 28, yy + 30, x + 86, yy + 88], fill=VERMELHO + (int(255 * e),))
        d.text((x + 57, yy + 74), str(i + 1), font=fonte(FONTE_BLACK, 40), fill=(255, 255, 255),
               anchor="ms")
        linhas = quebrar(dica, fd, 780)
        for j, ln in enumerate(linhas):
            d.text((x + 112, yy + 72 - (len(linhas) - 1) * 24 + j * 48), ln, font=fd,
                   fill=(15, 15, 20, int(255 * e)), anchor="ls")
    e = suave((u - 2.6) / 0.4)
    if e > 0:
        f = fonte(FONTE_XBOLD, 44)
        d.text((W / 2, 1210), "Compartilhe e proteja quem você ama.", font=f,
               fill=(255, 255, 255, int(255 * e)), anchor="ms", stroke_width=4, stroke_fill=(0, 0, 0))


def quebrar(txt, f, largura):
    linhas, atual = [], ""
    for p in txt.split():
        tent = (atual + " " + p).strip()
        if f.getlength(tent) > largura and atual:
            linhas.append(atual)
            atual = p
        else:
            atual = tent
    return linhas + [atual]


def cantoneiras(d, pts, cor, larg=7, frac=0.22):
    """Cantoneiras (estilo mira) num quadrilátero."""
    for i in range(4):
        p, ant, prox = pts[i], pts[i - 1], pts[(i + 1) % 4]
        for q in (ant, prox):
            fim = p + (q - p) * frac
            d.line([tuple(p), tuple(fim)], fill=cor, width=larg)


def etiqueta(d, x, y, txt, cor_fundo, cor_txt=(255, 255, 255), tam=34):
    f = fonte(FONTE_BLACK, tam)
    lw = f.getlength(txt)
    d.rounded_rectangle([x, y - tam - 14, x + lw + 32, y + 6], 10, fill=cor_fundo)
    d.text((x + 16, y - 6), txt, font=f, fill=cor_txt, anchor="ls")


# ----------------------------------------------------------------------------- áudio

def gerar_ambiencia(arq):
    """Música de fundo + whoosh antes de cada corte + impacto no título."""
    n = int(DURACAO * SR)
    rng = np.random.default_rng(7)
    musica = musica_golpe.compor(DURACAO, entrada_batida=CLIPES[1][1], revelacao=18.83,
                                 inicio_dicas=DICAS_INICIO)
    sinal = np.zeros(n)

    def ruido_filtrado(dur, f0, f1):
        m = int(dur * SR)
        r = rng.standard_normal(m)
        espec = np.fft.rfft(r)
        fr = np.fft.rfftfreq(m, 1 / SR)
        out = np.zeros(m)
        # varre um passa-banda de f0 até f1 em pedaços
        pedacos = 24
        for k in range(pedacos):
            fc = f0 * (f1 / f0) ** (k / (pedacos - 1))
            filtro = np.exp(-((np.log(fr + 1) - np.log(fc)) ** 2) / 0.25)
            parte = np.fft.irfft(espec * filtro, m)
            env = np.zeros(m)
            a, b = int(k * m / pedacos), int((k + 1) * m / pedacos)
            env[a:b] = 1
            out += parte * np.convolve(env, np.hanning(m // 8 + 1), "same") / (m // 16 + 1)
        return out / (np.abs(out).max() + 1e-9)

    def somar(clip, inicio, ganho):
        i = int(inicio * SR)
        j = min(n, i + len(clip))
        if i < n:
            sinal[i:j] += clip[:j - i] * ganho

    whoosh = ruido_filtrado(0.5, 300, 5000) * np.hanning(int(0.5 * SR))
    for _, ini in CLIPES[1:]:
        somar(whoosh, ini - 0.42, 0.18)
    somar(whoosh, DICAS_INICIO - 0.42, 0.18)
    tb = np.arange(int(1.2 * SR)) / SR
    boom = np.sin(2 * np.pi * (45 + 60 * np.exp(-tb * 18)) * tb) * np.exp(-tb * 3.2)
    somar(boom, 0.12, 0.35)
    for _, ini in CLIPES[1:]:
        somar(boom, ini, 0.2)
    estereo = musica[:n] * 0.4 + np.stack([sinal, sinal], axis=1)
    pcm = (np.clip(estereo, -1, 1) * 32767).astype("<i2")
    import wave
    with wave.open(str(arq), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


# ----------------------------------------------------------------------------- montagem

def preparar():
    quadros = {nome: ler_quadros(nome) for nome, _ in CLIPES}
    homs = rastrear(quadros)
    cab_ref = projetar(CABECALHO_Q180, np.linalg.inv(homs["painel"][179]))
    barra_ref = projetar(BARRA_TAREFAS_Q1, np.linalg.inv(homs["painel"][0]))
    regioes = dict(BORRAR, cabecalho=cab_ref, barra=barra_ref)
    trilha = {}
    for nome in ("painel", "close"):
        trilha[nome] = {k: trilhas(homs[nome], p) for k, p in regioes.items()}
        trilha[nome]["_local"] = trilhas(homs[nome], LOCAL)
    # privacidade primeiro: borra os quadros na resolução original
    for nome in ("painel", "close"):
        for i, q in enumerate(quadros[nome]):
            q = q.copy()
            for k in regioes:
                borrar(q, trilha[nome][k][i], k if k in ("foto", "mapa", "barra") else "texto")
            quadros[nome][i] = q
    return quadros, trilha


def vinheta():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H / 2) / (H * 0.62)) ** 2)
    return (1 - 0.38 * np.clip(r - 0.55, 0, 1) ** 1.5)[..., None].astype(np.float32)


VINHETA = None


def quadro_base(quadros, t):
    """Escolhe o quadro do clipe certo e aplica zoom lento + "soco" de zoom nos cortes."""
    if t >= FIM_CLIPES:
        nome, i, ini = "close", len(quadros["close"]) - 1, CLIPES[2][1]
    else:
        nome, ini = [c for c in CLIPES if c[1] <= t + 1e-6][-1]
        i = min(int(round((t - ini) * FPS)), len(quadros[nome]) - 1)
    q = quadros[nome][i]
    u = t - ini
    s = ESCALA * (1.0 + 0.012 * u)
    if t < FIM_CLIPES:
        s *= 1 + 0.10 * (1 - suave(u / 0.25))  # entra com zoom e assenta
    else:
        s *= 1 + 0.012 * (t - FIM_CLIPES)
    cx, cy = 288, 512
    m = np.float32([[s, 0, W / 2 - cx * s], [0, s, H / 2 - cy * s]])
    img = cv2.warpAffine(q, m, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
    return img, nome, i, m


def para_saida(pts, m):
    return np.asarray(pts) @ m[:, :2].T + m[:, 2]


def renderizar_quadro(quadros, trilha, t):
    global VINHETA
    if VINHETA is None:
        VINHETA = vinheta()
    img, nome, i, m = quadro_base(quadros, t)
    img = img.astype(np.float32)
    # tratamento: um pouco mais de contraste e vinheta
    img = np.clip((img - 128) * 1.08 + 124, 0, 255) * VINHETA
    # glitch RGB nos cortes
    for _, ini in CLIPES[1:] + [("", DICAS_INICIO)]:
        if 0 <= t - ini < 0.12:
            k = int(18 * (1 - (t - ini) / 0.12))
            img[..., 2] = np.roll(img[..., 2], k, axis=1)
            img[..., 0] = np.roll(img[..., 0], -k, axis=1)
    if t >= FIM_CLIPES:  # congela, desfoca e escurece para as dicas
        e = suave((t - FIM_CLIPES) / 0.5)
        borrado = cv2.GaussianBlur(img, (0, 0), 1 + 24 * e)
        img = borrado * (1 - 0.55 * e)
    elif t < 2.7:  # abertura um pouco mais escura
        img *= 0.85 + 0.15 * suave((t - 2.2) / 0.5)
    # flash branco nos cortes
    for _, ini in CLIPES[1:]:
        if 0 <= t - ini < 0.2:
            a = 0.75 * (1 - (t - ini) / 0.2) ** 2
            img = img * (1 - a) + 255 * a
    rgb = cv2.cvtColor(np.clip(img, 0, 255).astype(np.uint8), cv2.COLOR_BGR2RGB)
    canvas = Image.fromarray(rgb).convert("RGBA")

    # destaques rastreados na tela do notebook
    if t < FIM_CLIPES and nome in trilha:
        cam = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(cam)
        if (nome == "painel" and i >= 110) or (nome == "close" and i < 90):
            ini_loc = 110 if nome == "painel" else 0
            a = suave((i - ini_loc) / 8) if nome == "painel" else 1 - suave((i - 80) / 8)
            pts = para_saida(expandir(trilha[nome]["_local"][i], 1.15, 6), m)
            cor = (0, 230, 140, int(255 * a))
            cantoneiras(d, pts, cor, 6, 0.3)
            x, y = pts[:, 0].min(), pts[:, 1].min() - 10
            if a > 0.05:
                etiqueta(d, x, y, "CIDADE (POR IP)", (0, 170, 100, int(235 * a)), tam=30)
        if nome == "close" and i >= 92:
            a = suave((i - 92) / 6)
            pts = para_saida(expandir(trilha[nome]["foto"][i], 1.1, 8), m)
            pulso = 0.75 + 0.25 * np.sin(t * 9)
            cor = VERMELHO + (int(255 * a * pulso),)
            cantoneiras(d, pts, cor, 9, 0.24)
            # linha de "escaneamento" descendo pela foto
            fase = ((i - 92) / 40) % 1
            esq = pts[0] + (pts[3] - pts[0]) * fase
            dir_ = pts[1] + (pts[2] - pts[1]) * fase
            d.line([tuple(esq), tuple(dir_)], fill=(255, 60, 60, int(200 * a)), width=5)
            # etiqueta embaixo da foto, para não brigar com o selo e o capítulo no topo
            x, y = pts[:, 0].min(), pts[:, 1].max() + 62
            etiqueta(d, max(x, 24), min(y, 1300), "GOLPISTA", VERMELHO + (int(240 * a),), tam=40)
        canvas.alpha_composite(cam)

    desenhar_titulo(canvas, t)
    desenhar_selo(canvas, t)
    desenhar_capitulo(canvas, t)
    desenhar_dicas(canvas, t)
    desenhar_legenda(canvas, t)
    return np.array(canvas.convert("RGB"))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--saida", default=str(RAIZ / "video_golpe_falso_advogado.mp4"))
    ap.add_argument("--preview", help="gera só uma prancha de quadros neste arquivo")
    ap.add_argument("--so-audio", action="store_true", help="reaproveita o vídeo já renderizado")
    args = ap.parse_args()
    video_mudo = CACHE / "video_mudo.mp4"
    if args.so_audio:
        mixar(video_mudo, args.saida)
        return

    quadros, trilha = preparar()

    if args.preview:
        tempos = [0.5, 1.5, 4.5, 9.5, 12.0, 14.5, 17.0, 19.8, 22.5, 24.5, 26.5, 28.3]
        fotos = [cv2.resize(renderizar_quadro(quadros, trilha, t), (360, 640)) for t in tempos]
        linhas = [np.hstack(fotos[k:k + 4]) for k in range(0, len(fotos), 4)]
        cv2.imwrite(args.preview, cv2.cvtColor(np.vstack(linhas), cv2.COLOR_RGB2BGR))
        return

    CACHE.mkdir(parents=True, exist_ok=True)
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "18",
           "-pix_fmt", "yuv420p", str(video_mudo)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    total = int(round(DURACAO * FPS))
    for k in range(total):
        proc.stdin.write(renderizar_quadro(quadros, trilha, k / FPS).tobytes())
        if k % 60 == 0:
            print(f"quadro {k}/{total}", flush=True)
    proc.stdin.close()
    proc.wait()
    mixar(video_mudo, args.saida)


def mixar(video_mudo, saida):
    """Narração normalizada por cima da música, que abaixa (sidechain) quando a voz entra."""
    amb = CACHE / "ambiencia.wav"
    gerar_ambiencia(amb)
    filtro = ("[1:a]aresample=48000,highpass=f=70,acompressor=threshold=-20dB:ratio=3:attack=5:release=120,"
              "loudnorm=I=-15:TP=-1.5:LRA=9,apad,asplit[voz][chave];"
              "[2:a][chave]sidechaincompress=threshold=0.04:ratio=5:attack=15:release=400:makeup=1[amb];"
              "[voz][amb]amix=inputs=2:duration=shortest:normalize=0,alimiter=limit=0.95[a]")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(video_mudo),
                    "-i", str(ENTRADA / "narracao.m4a"), "-i", str(amb),
                    "-filter_complex", filtro, "-map", "0:v", "-map", "[a]",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-t", f"{DURACAO}",
                    "-movflags", "+faststart", saida], check=True)
    print("ok:", saida)


if __name__ == "__main__":
    main()
