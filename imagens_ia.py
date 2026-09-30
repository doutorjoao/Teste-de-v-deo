#!/usr/bin/env python3
"""Gera as imagens de partida de cada cena com a API do Gemini, usando as fotos como referência.

Precisa da variável de ambiente GEMINI_API_KEY (chave criada no Google AI Studio).

Uso:
    python3 imagens_ia.py 1              # gera a IMG 1
    python3 imagens_ia.py 3 5 -n 3       # 3 variações das IMG 3 e 5
    python3 imagens_ia.py todas
    python3 imagens_ia.py 1 --modelo gemini-2.5-flash-image

As imagens saem em imagens_ia/img<N>_<variação>.png
"""
import argparse
import base64
import io
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

from PIL import Image

RAIZ = Path(__file__).resolve().parent
SAIDA = RAIZ / "imagens_ia"
API = "https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent"

# Foto 1: terno azul no estúdio (quem chega e abre a porta).
# Foto 2: colete de frente (quem espera sentado).
TERNO = ("fotos/1_estudio.jpg", (0, 442, 1224, 2278))  # recorte tira as faixas pretas do print
COLETE = ("fotos/5_frente.jpg", None)
COLETE_PERFIL = ("fotos/3_noite_olhando_direita.jpg", None)

ESTILO = (" Photorealistic cinematic film still, 16:9. Overcast hazy daylight on an empty beach, "
          "calm grey sea, pale sand. Muted desaturated colors (beige, grey-blue), soft contrast, "
          "35mm film grain, shallow depth of field.")

CENAS = {
    1: ([TERNO],
        "Wide shot of an empty beach. A single freestanding wooden door with a grey-blue frame stands "
        "upright alone in the sand, closed. The man from the reference photo — identical face, short dark "
        "hair, thin mustache and goatee — wearing a dark navy suit, white shirt and black tie with small "
        "white dots, walks toward the door, seen from the side, small in the frame."),
    2: ([TERNO],
        "Extreme close-up of a man's right hand wearing a gold ring and the sleeve of a dark navy suit, "
        "reaching for the round metal handle of a grey-blue wooden door standing on a beach. Background "
        "softly out of focus: sand and sea."),
    3: ([TERNO, COLETE],
        "View from behind the man in the dark navy suit (reference photo 1) standing in the open doorway "
        "of a freestanding door on the beach. Through the door, in the distance, a long wooden table on "
        "the sand with a silver coffee pot and two cups. At the far end of the table, seated on a wooden "
        "chair, waits the same man (reference photo 2, identical face) wearing a black suit vest, white "
        "shirt and grey tie with gold stripes, calmly looking toward the door. Both men have exactly the "
        "same face as the reference photos."),
    4: ([COLETE, COLETE_PERFIL],
        "Close-up of the man from the reference photos (identical face, dark wavy hair swept to the side, "
        "thin mustache and goatee), wearing a black suit vest, white shirt and striped tie, seated at a "
        "wooden table on the beach, head turned in profile looking to the right of the frame."),
    5: ([TERNO, COLETE],
        "Wide side view of a long wooden table on an empty beach, sea in the background, silver coffee "
        "pot in the middle. On the left end, seated on a wooden chair, the man in the black vest and "
        "striped tie (reference photo 2). On the right end, standing next to an empty wooden chair, the "
        "same man in the dark navy suit (reference photo 1). Identical faces, looking at each other. The "
        "freestanding door stands open far behind them. Both men have exactly the same face as the "
        "reference photos."),
    6: ([TERNO],
        "Close-up, three-quarter profile, of the man from the reference photo in a dark navy suit, white "
        "shirt and dotted black tie, seated at a table on the beach, looking to the left of the frame "
        "with a serious, confident expression."),
    7: ([COLETE],
        "Medium close-up of the man in the black vest, white shirt and striped tie (reference photo), "
        "seated at a wooden table on the beach, holding a small white coffee cup near his lips, eyes "
        "fixed on someone off-screen to the right."),
}


def foto_base64(caminho, recorte, lado_max=1536):
    img = Image.open(RAIZ / caminho).convert("RGB")
    if recorte:
        img = img.crop(recorte)
    img.thumbnail((lado_max, lado_max))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=92)
    return base64.b64encode(buf.getvalue()).decode()


def gerar_imagem(chave, modelo, refs, prompt):
    partes = [{"text": prompt + ESTILO}]
    partes += [{"inline_data": {"mime_type": "image/jpeg", "data": foto_base64(*r)}} for r in refs]
    corpo = {
        "contents": [{"parts": partes}],
        "generationConfig": {"responseModalities": ["TEXT", "IMAGE"],
                             "imageConfig": {"aspectRatio": "16:9"}},
    }
    req = urllib.request.Request(API.format(modelo=modelo), data=json.dumps(corpo).encode(),
                                 headers={"Content-Type": "application/json", "x-goog-api-key": chave})
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            resposta = json.load(r)
    except urllib.error.HTTPError as e:
        raise SystemExit(f"Erro {e.code} da API: {e.read().decode()[:800]}")
    for cand in resposta.get("candidates", []):
        for parte in cand.get("content", {}).get("parts", []):
            dado = parte.get("inlineData") or parte.get("inline_data")
            if dado:
                return base64.b64decode(dado["data"])
    raise SystemExit("A API não devolveu imagem: " + json.dumps(resposta)[:800])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cenas", nargs="+", help="números das imagens (1 a 7) ou 'todas'")
    ap.add_argument("-n", "--variacoes", type=int, default=1)
    ap.add_argument("--modelo", default="gemini-2.5-flash-image")
    args = ap.parse_args()
    chave = os.environ.get("GEMINI_API_KEY")
    if not chave:
        raise SystemExit("Defina a variável de ambiente GEMINI_API_KEY.")
    numeros = sorted(CENAS) if args.cenas == ["todas"] else [int(c) for c in args.cenas]
    SAIDA.mkdir(exist_ok=True)
    for n in numeros:
        refs, prompt = CENAS[n]
        for v in range(1, args.variacoes + 1):
            destino = SAIDA / f"img{n}_{v}.png"
            destino.write_bytes(gerar_imagem(chave, args.modelo, refs, prompt))
            print("salvo:", destino.relative_to(RAIZ))
