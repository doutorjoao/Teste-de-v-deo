"""Reels edit: golpe da falsa recuperação de contas do Instagram.

Renders 1080x1920 @30fps frames (full-frame subject over a clean light studio
backdrop, overlays, captions) and pipes them to ffmpeg with the mixed audio.
Usage: python edit.py OUT.mp4            -> full render
       python edit.py --stills DIR t1 t2  -> preview stills at timeline seconds
"""
import sys, os, subprocess, functools
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

S = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, S)
from backgrounds import studio_light  # noqa: E402

W, H, FPS = 1080, 1920, 30
FONT = "/usr/share/fonts/opentype/inter/Inter-%s.otf"
GOLD = (212, 175, 96)        # gold on dark / over the picture
GOLD_DEEP = (168, 124, 44)   # gold on the light backdrop
WHITE = (255, 255, 255)
INK = (17, 17, 17)

# ---------------------------------------------------------------- timeline
# (clip, src_in, src_out, extra_tail)  extra_tail = seconds held after src_out
EDL = [
    ("0186", 0.65, 6.33, 0.12),   # 1 abertura (promessa suspeita, eco leve)
    ("0185", 0.92, 6.30, 0.0),    # 2 alerta direto
    ("0188", 0.66, 9.70, 0.0),    # 3 situação
    ("0182", 0.62, 5.55, 0.0),    # 4 cobranças
    ("0183", 0.45, 5.75, 0.0),    # 5 conta não volta
    ("0184", 0.70, 6.20, 0.0),    # 6 explicação
    ("0187", 0.60, 7.72, 0.0),    # 7 sinais de alerta
    ("0181", 0.45, 4.78, 0.50),   # 8 encerramento (segura último quadro)
]
START = []
_t = 0.0
for c in EDL:
    START.append(_t)
    _t += (c[2] - c[1]) + c[3]
TOTAL = _t
NFRAMES = int(round(TOTAL * FPS))


def T(scene, src):
    """Timeline time of a source timestamp inside scene index (0-based)."""
    return START[scene] + (src - EDL[scene][1])


def scene_at(t):
    for i in range(len(EDL) - 1, -1, -1):
        if t >= START[i] - 1e-6:
            return i
    return 0


# white-wall reference ratios (measured) -> gentle white balance
WALL = {
    "0181": (0.997, 1.025, 0.977), "0182": (1.006, 1.022, 0.972),
    "0183": (1.005, 1.021, 0.975), "0184": (1.008, 1.020, 0.972),
    "0185": (0.993, 1.031, 0.977), "0186": (0.993, 1.031, 0.977),
    "0187": (0.999, 1.025, 0.976), "0188": (1.007, 1.019, 0.974),
}

# ---------------------------------------------------------------- easing
def clamp01(x):
    return 0.0 if x < 0 else 1.0 if x > 1 else x


def ease_out(x):
    x = clamp01(x)
    return 1 - (1 - x) ** 3


def ease_inout(x):
    x = clamp01(x)
    return x * x * (3 - 2 * x)


def ease_back(x, s=1.4):
    x = clamp01(x)
    x -= 1
    return x * x * ((s + 1) * x + s) + 1


# ---------------------------------------------------------------- text sprites
@functools.lru_cache(maxsize=None)
def font(weight, size):
    return ImageFont.truetype(FONT % weight, size)


def runs_of(text):
    """'a [[b]] c' -> [('a ', False), ('b', True), (' c', False)]"""
    out = []
    for i, part in enumerate(text.replace("]]", "[[").split("[[")):
        if part:
            out.append((part, i % 2 == 1))
    return out


@functools.lru_cache(maxsize=None)
def text_sprite(text, weight="Bold", size=58, color=WHITE, hl_color=GOLD,
                hl_weight=None, shadow=True, stroke=0, tracking=0, line_gap=1.18):
    """Renders (multi-line, rich) centred text to an RGBA sprite."""
    lines = text.split("\n")
    f = font(weight, size)
    fh = font(hl_weight or weight, size)
    asc, desc = f.getmetrics()
    lh = int(size * line_gap)
    widths = []
    for ln in lines:
        widths.append(sum((fh if hl else f).getlength(p) + tracking * len(p) for p, hl in runs_of(ln)))
    pad = 30
    iw = int(max(widths)) + pad * 2
    ih = lh * (len(lines) - 1) + asc + desc + pad * 2
    img = Image.new("RGBA", (iw, ih), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for li, ln in enumerate(lines):
        x = (iw - widths[li]) / 2
        y = pad + li * lh
        for part, hl in runs_of(ln):
            ff = fh if hl else f
            col = hl_color if hl else color
            chunks = part if tracking else [part]
            for ch in chunks:
                d.text((x, y), ch, font=ff, fill=col, stroke_width=stroke, stroke_fill=(0, 0, 0, 170))
                x += ff.getlength(ch) + (tracking if tracking else 0)
    if shadow:
        a = img.split()[3]
        sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
        sh.putalpha(a.point(lambda v: int(v * 0.75)))
        sh = sh.filter(ImageFilter.GaussianBlur(7))
        base = Image.new("RGBA", img.size, (0, 0, 0, 0))
        base.alpha_composite(sh, (0, 4))
        base.alpha_composite(sh, (0, 1))
        base.alpha_composite(img)
        img = base
    return img


_blur_cache = {}


def blur_of(img, radius):
    k = (id(img), radius)
    if k not in _blur_cache:
        _blur_cache[k] = img.filter(ImageFilter.GaussianBlur(radius))
    return _blur_cache[k]


def put(layer, img, cx, cy, alpha=1.0, scale=1.0, anchor="center"):
    """Composite sprite onto layer at (cx, cy) with opacity/scale."""
    if alpha <= 0.003:
        return
    if abs(scale - 1.0) > 1e-3:
        img = img.resize((max(1, int(img.width * scale)), max(1, int(img.height * scale))), Image.BICUBIC)
    if alpha < 0.999:
        a = img.split()[3].point(lambda v, k=alpha: int(v * k))
        img = img.copy()
        img.putalpha(a)
    if anchor == "center":
        x, y = int(round(cx - img.width / 2)), int(round(cy - img.height / 2))
    elif anchor == "left":
        x, y = int(round(cx)), int(round(cy - img.height / 2))
    else:  # right
        x, y = int(round(cx - img.width)), int(round(cy - img.height / 2))
    if x < 0 or y < 0:
        img = img.crop((max(0, -x), max(0, -y), img.width, img.height))
        x, y = max(0, x), max(0, y)
    layer.alpha_composite(img, (x, y))


# ---------------------------------------------------------------- UI pieces
@functools.lru_cache(maxsize=None)
def tag_sprite(text):
    """Small letter-spaced pill label for the light backdrop."""
    f = font("SemiBold", 25)
    tr = 3.2
    tw = sum(f.getlength(c) + tr for c in text) - tr
    padx, h = 22, 50
    w = int(tw + padx * 2 + 22)
    img = Image.new("RGBA", (w + 8, h + 8), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((4, 4, 4 + w, 4 + h), radius=h // 2, fill=(255, 255, 255, 150),
                        outline=GOLD_DEEP + (255,), width=2)
    d.ellipse((4 + padx - 2, 4 + h / 2 - 5, 4 + padx + 8, 4 + h / 2 + 5), fill=GOLD_DEEP + (255,))
    x = 4 + padx + 20
    for c in text:
        d.text((x, 4 + h / 2), c, font=f, fill=(30, 30, 30, 255), anchor="lm")
        x += f.getlength(c) + tr
    return img


@functools.lru_cache(maxsize=None)
def bubble_sprite(text, accent=False):
    """Incoming chat bubble (simulation): dark glass, white text."""
    f = font("SemiBold", 34)
    tw = f.getlength(text)
    padx, pady = 28, 18
    asc, desc = f.getmetrics()
    w, h = int(tw + padx * 2 + (10 if accent else 0)), asc + desc + pady * 2 - 6
    m = 22
    img = Image.new("RGBA", (w + m * 2, h + m * 2), (0, 0, 0, 0))
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((m, m + 5, m + w, m + h + 5), radius=26, fill=(0, 0, 0, 90))
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(9)))
    d = ImageDraw.Draw(img)
    fill = (22, 22, 22, 238)
    d.rounded_rectangle((m, m, m + w, m + h), radius=26, fill=fill)
    d.polygon([(m + 2, m + h - 26), (m - 10, m + h + 2), (m + 30, m + h - 4)], fill=fill)
    if accent:
        d.rounded_rectangle((m + 12, m + 14, m + 18, m + h - 14), radius=3, fill=GOLD + (255,))
    d.text((m + padx + (10 if accent else 0), m + h / 2 + 1), text, font=f, fill=WHITE + (255,), anchor="lm")
    return img


@functools.lru_cache(maxsize=None)
def chip_sprite(text):
    """'Conta sem acesso' status chip with a drawn padlock."""
    f = font("Bold", 34)
    tw = f.getlength(text)
    padx, h = 24, 76
    ic = 40
    w = int(tw + padx * 2 + ic + 18)
    m = 24
    img = Image.new("RGBA", (w + m * 2, h + m * 2), (0, 0, 0, 0))
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((m, m + 6, m + w, m + h + 6), radius=22, fill=(0, 0, 0, 110))
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(10)))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((m, m, m + w, m + h), radius=22, fill=(14, 14, 14, 240), outline=GOLD + (255,), width=2)
    lx, ly = m + padx, m + h / 2
    d.arc((lx + 8, ly - 26, lx + 32, ly + 2), 180, 360, fill=GOLD + (255,), width=5)
    d.line((lx + 8, ly - 14, lx + 8, ly - 2), fill=GOLD + (255,), width=5)
    d.line((lx + 32, ly - 14, lx + 32, ly - 2), fill=GOLD + (255,), width=5)
    d.rounded_rectangle((lx + 2, ly - 4, lx + 38, ly + 24), radius=5, fill=GOLD + (255,))
    d.ellipse((lx + 16, ly + 4, lx + 24, ly + 12), fill=(14, 14, 14, 255))
    d.text((lx + ic + 18, ly + 1), text, font=f, fill=WHITE + (255,), anchor="lm")
    return img


# ---------------------------------------------------------------- subject reader
class ClipReader:
    """Matted foreground + alpha, colour-corrected and scaled to fill 1080x1920."""

    def __init__(self, clip, src_in):
        r = WALL[clip]
        gr, gg, gb = [(1 / v) ** 0.9 for v in r]
        fill = "scale=1080:-2:flags=lanczos,crop=1080:1920:0:(ih-1920)/2"
        vf = (f"colorchannelmixer=rr={gr:.4f}:gg={gg:.4f}:bb={gb:.4f},"
              "curves=all='0/0 0.05/0.056 0.15/0.16 0.5/0.5 0.8/0.81 1/1',"
              "eq=saturation=0.97:contrast=1.03,"
              f"{fill},unsharp=5:5:0.6:5:5:0")
        ss = f"{src_in:.3f}"
        self.fp = subprocess.Popen(
            ["ffmpeg", "-v", "error", "-ss", ss, "-i", f"{S}/matte/{clip}-fg.mkv",
             "-vf", vf, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
        self.ap = subprocess.Popen(
            ["ffmpeg", "-v", "error", "-ss", ss, "-i", f"{S}/matte/{clip}-a.mkv",
             "-vf", fill.replace("lanczos", "bicubic"), "-f", "rawvideo", "-pix_fmt", "gray", "-"],
            stdout=subprocess.PIPE)
        self.last = None

    def read(self):
        n = W * H
        b = self.fp.stdout.read(n * 3)
        a = self.ap.stdout.read(n)
        if len(b) < n * 3 or len(a) < n:
            return self.last
        self.last = (np.frombuffer(b, np.uint8).reshape(H, W, 3), np.frombuffer(a, np.uint8).reshape(H, W))
        return self.last

    def close(self):
        for p in (self.fp, self.ap):
            p.stdout.close()
            p.kill()


BG = None
GRAIN = None


def compose_subject(fg, al):
    """Light studio backdrop + matted subject -> float32 HxWx3 (0..255)."""
    a = np.clip((al.astype(np.float32) / 255.0 - 0.02) / 0.96, 0, 1)[..., None]
    return BG * (1 - a) + fg.astype(np.float32) * a


def init_globals():
    global BG, GRAIN
    BG = studio_light()
    rng = np.random.default_rng(7)
    GRAIN = [rng.normal(0, 1.4, (H // 2, W // 2, 1)).astype(np.float32).repeat(2, 0).repeat(2, 1) for _ in range(6)]


def zoom(img_u8, z, cx, cy):
    if abs(z - 1) < 1e-4:
        return img_u8
    im = Image.fromarray(img_u8)
    w, h = W / z, H / z
    x0 = min(max(cx - w / 2, 0), W - w)
    y0 = min(max(cy - h / 2, 0), H - h)
    im = im.transform((W, H), Image.EXTENT, (x0, y0, x0 + w, y0 + h), Image.BICUBIC)
    return np.asarray(im)


# ---------------------------------------------------------------- captions
# (scene, src_start, src_end, text)   [[...]] = gold highlight
CAPTIONS = [
    (1, 1.02, 1.95, "Perdeu sua conta"),
    (1, 1.95, 3.60, "e apareceu alguém\nfalando isso?"),
    (1, 3.72, 4.86, "Você pode estar prestes"),
    (1, 4.86, 6.30, "a cair em [[OUTRO GOLPE]]"),
    (2, 0.74, 2.40, "Imagina a seguinte situação:"),
    (2, 6.24, 7.68, "Aí, do nada, chega\numa pessoa falando:"),
    (3, 0.74, 2.40, "Primeiro cobra pelo serviço."),
    (3, 2.40, 4.52, "Do nada, chega uma\ntaxa de desbloqueio."),
    (3, 4.58, 5.55, "Você já viu isso\nem algum lugar?"),
    (4, 0.56, 2.30, "Você paga, e o que acontece?"),
    (4, 2.40, 4.30, "A conta continua sem voltar,"),
    (4, 4.40, 5.75, "mas o cara foi embora."),
    (5, 0.82, 1.72, "Mas veja só:"),
    (5, 1.78, 3.62, "a cobrança por um serviço,"),
    (5, 3.74, 6.20, "sozinha, não significa\nque é um golpe."),
    (6, 0.72, 2.00, "Mas o alerta é o seguinte,"),
    (6, 2.00, 3.40, "é aquela combinação:"),
    (6, 6.38, 7.72, "pra que você pague logo."),
    (7, 0.58, 1.70, "Então, fique ligado."),
    (7, 1.94, 2.86, "Perdeu a conta?"),
    (7, 2.86, 3.90, "Procura um [[advogado]]."),
    (7, 3.92, 5.30, "Ih, rimou."),
]
CAPTIONS_TL = [(T(s, a), min(T(s, b), TOTAL), txt) for s, a, b, txt in CAPTIONS]
CAP_BOTTOM = 1505
CAP_CX = 530


def draw_caption(layer, t):
    for a, b, txt in CAPTIONS_TL:
        if a <= t < b:
            spr = text_sprite(txt, "Bold", 58, WHITE, GOLD, "ExtraBold", True, 2)
            k = ease_out((t - a) / 0.14)
            y = CAP_BOTTOM - spr.height / 2 + 30 + (1 - k) * 16
            put(layer, spr, CAP_CX, y, alpha=k)


# ---------------------------------------------------------------- scenes
def ghost(layer, spr, cx, cy, t0, t, dur=0.75, amt=0.22):
    """Echo copy of a typography sprite dissipating (visual echo)."""
    p = (t - t0) / dur
    if 0 <= p <= 1:
        put(layer, blur_of(spr, 3), cx, cy - 10 * p, alpha=amt * (1 - p) ** 1.6, scale=1 + 0.10 * ease_out(p))


def word_line(layer, words, cx, cy, t, weight, size, color, shadow, echo=True, alpha=1.0):
    """Line whose words appear at given times. words=[(text, t_appear)]"""
    f = font(weight, size)
    sp = f.getlength(" ")
    sprites = [text_sprite(w, weight, size, color, color, None, shadow, 2 if shadow else 0) for w, _ in words]
    inner = [f.getlength(w) for w, _ in words]
    x = cx - (sum(inner) + sp * (len(words) - 1)) / 2
    for (w, ta), spr, iw in zip(words, sprites, inner):
        wc = x + iw / 2
        if t >= ta:
            k = ease_out((t - ta) / 0.16)
            put(layer, spr, wc, cy + (1 - k) * 18, alpha=k * alpha)
            if echo:
                ghost(layer, spr, wc, cy, ta, t, amt=0.22 * alpha)
        x += iw + sp


def scene_opening(layer, t):
    """Promessa suspeita: he speaks on camera; kinetic type echoes the pitch."""
    L = lambda src: T(0, src)
    put(layer, tag_sprite("PROMESSA SUSPEITA"), 540, 236, alpha=ease_out((t - 0.05) / 0.3))
    # top band, on the light backdrop: black type
    word_line(layer, [("Recupero", L(0.84)), ("o", L(1.38)), ("seu", L(1.46)), ("Instagram", L(1.62))],
              540, 330, t, "ExtraBold", 66, INK, False)
    # lower band, over the shirt: big white number that swaps 10 -> 15
    tn10, tn15, t_out = L(2.40), L(3.27), L(4.30)
    out_k = 1 - clamp01((t - t_out) / 0.2)
    s10 = text_sprite("10", "Black", 200, WHITE, WHITE, None, True)
    s15 = text_sprite("15", "Black", 200, WHITE, WHITE, None, True)
    ncy = 1370
    if tn10 <= t < tn15:
        k = ease_back((t - tn10) / 0.22)
        put(layer, s10, 540, ncy + (1 - k) * 40, alpha=clamp01((t - tn10) / 0.1), scale=0.9 + 0.1 * k)
        ghost(layer, s10, 540, ncy, tn10, t, 0.8, 0.2)
    elif t >= tn15 and out_k > 0:
        p = (t - tn15) / 0.13
        if p < 1:
            put(layer, s10, 540, ncy - 60 * ease_out(p), alpha=1 - p)
        k = ease_back((t - tn15) / 0.2, 1.8)
        put(layer, s15, 540, ncy + 60 * (1 - k), alpha=clamp01((t - tn15) / 0.08) * out_k)
        ghost(layer, s15, 540, ncy, tn15, t, 0.8, 0.2)
    tm = L(2.70)
    if t >= tm and out_k > 0:
        sm = text_sprite("MINUTOS", "Bold", 44, WHITE, WHITE, None, True, 0, 10)
        k = ease_out((t - tm) / 0.18) * out_k
        put(layer, sm, 540, 1505 + (1 - k) * 12, alpha=k)
        ImageDraw.Draw(layer).rectangle((540 - 46 * k, 1543, 540 + 46 * k, 1547), fill=GOLD + (int(255 * k),))
    # then the "inside contact" line replaces the number
    word_line(layer, [("Tenho", L(4.38)), ("um", L(4.58)), ("contato", L(4.66))],
              540, 1350, t, "Bold", 62, WHITE, True)
    word_line(layer, [("dentro", L(5.18)), ("da", L(5.46)), ("Meta", L(5.58))],
              540, 1432, t, "ExtraBold", 62, GOLD, True)


def scene_list(layer, t):
    """Scene 3: 'Você está…' list, one item at a time, in the caption band."""
    L = lambda src: T(2, src)
    if t < L(2.44):
        return
    fade = 1 - clamp01((t - L(6.05)) / 0.22)
    if fade <= 0:
        return
    d = ImageDraw.Draw(layer)
    lead = text_sprite("VOCÊ ESTÁ…", "Bold", 32, GOLD, GOLD, None, True, 0, 6)
    put(layer, lead, 130 - 30, 1235, alpha=ease_out((t - L(2.44)) / 0.2) * fade, anchor="left")
    items = [("Sem falar com os clientes", L(2.72), 1310), ("Sem vender", L(4.02), 1390),
             ("Desesperado", L(4.92), 1470)]
    for txt, ta, y in items:
        if t < ta:
            continue
        k = ease_out((t - ta) / 0.2)
        spr = text_sprite(txt, "Bold", 58, WHITE, WHITE, None, True, 2)
        put(layer, spr, 140 - 30 - (1 - k) * 40, y, alpha=k * fade, anchor="left")
        d.rounded_rectangle((112, y - 25, 119, y + 25), radius=3, fill=GOLD + (int(255 * k * fade),))


CHAT = None


def chat(layer, t):
    """Fictional chat (simulation) in the top band, scenes 3 → 5.
    The newest two messages are visible; older ones scroll up and fade."""
    msgs = [("Eu consigo resolver agora.", T(2, 7.74), False),
            ("Pagamento pelo serviço", T(3, 1.10), False),
            ("Taxa de desbloqueio", T(3, 3.40), True)]
    t_gone = T(4, 4.92)            # "foi embora"
    if t < msgs[0][1] or t > t_gone + 0.7:
        return
    gone_p = clamp01((t - t_gone) / 0.45)
    tg = tag_sprite("SIMULAÇÃO")
    put(layer, tg, 1040, 236, alpha=ease_out((t - msgs[0][1]) / 0.25) * (1 - gone_p), anchor="right")
    y_new, step = 392, 84
    for i, (txt, ta, acc) in enumerate(msgs):
        if t < ta:
            continue
        rank = sum(ease_inout((t - tb) / 0.28) for _, tb, _ in msgs[i + 1:] if t >= tb)
        spr = bubble_sprite(txt, acc)
        k = ease_back((t - ta) / 0.3, 1.6)
        gp = clamp01((t - t_gone - 0.08 * (len(msgs) - 1 - i)) / 0.32)
        a = clamp01((t - ta) / 0.12) * clamp01(1.6 - rank) * (1 - gp)
        put(layer, spr, 46 - 22, y_new - step * rank + (1 - k) * 24 - 12 * ease_out(gp), alpha=a,
            scale=1.0 - 0.06 * gp, anchor="left")


def scene5_chip(layer, t):
    a, b = T(4, 2.86), T(4, 4.30)
    if a <= t < b + 0.2:
        k = ease_out((t - a) / 0.18) * (1 - clamp01((t - b) / 0.2))
        put(layer, chip_sprite("Conta sem acesso"), 1062, 312 + (1 - k) * 14, alpha=k, anchor="right")


def scene6_highlight(layer, t):
    ta = T(5, 3.80)
    if t < ta:
        return
    k = ease_out((t - ta) / 0.25)
    l1 = text_sprite("Cobrança, sozinha,", "SemiBold", 50, INK, INK, None, False)
    l2 = text_sprite("não significa golpe", "ExtraBold", 64, INK, INK, None, False)
    put(layer, l1, 540, 262 + (1 - k) * 14, alpha=k)
    k2 = ease_out((t - ta - 0.32) / 0.28)
    put(layer, l2, 540, 340 + (1 - k2) * 14, alpha=k2)
    u = ease_inout((t - ta - 0.5) / 0.4)
    if u > 0:
        half = (l2.width - 60) / 2
        ImageDraw.Draw(layer).rounded_rectangle((540 - half, 382, 540 - half + 2 * half * u, 389), radius=3,
                                                fill=GOLD_DEEP + (255,))


def scene7_signals(layer, t):
    ta, tb = T(6, 3.82), T(6, 5.46)
    if t < ta:
        return
    d = ImageDraw.Draw(layer)
    lead = text_sprite("SINAIS DE ALERTA", "Bold", 28, GOLD_DEEP, GOLD_DEEP, None, False, 0, 6)
    put(layer, lead, 540, 232, alpha=ease_out((t - ta + 0.1) / 0.25))
    for txt, t0, y in (("Promessa garantida", ta, 298), ("Pressão para pagar", tb, 388)):
        if t < t0:
            continue
        k = ease_out((t - t0) / 0.2)
        spr = text_sprite(txt, "ExtraBold", 60, INK, INK, None, False)
        put(layer, spr, 540, y + (1 - k) * 14, alpha=k)
        u = ease_inout((t - t0 - 0.12) / 0.35)
        if u > 0:
            half = (spr.width - 60) / 2
            d.rounded_rectangle((540 - half, y + 38, 540 - half + 2 * half * u, y + 44), radius=3,
                                fill=GOLD_DEEP + (255,))


def zoom_for(t):
    """(z, cx, cy) camera push-ins; only two, both subtle."""
    if START[1] <= t < START[2]:
        return 1 + 0.06 * ease_inout((t - T(1, 5.40)) / 0.45), 540, 900
    if START[6] <= t < START[7]:
        return 1 + 0.035 * ease_inout((t - T(6, 5.46)) / 0.6), 540, 900
    return 1.0, 540, 960


# ---------------------------------------------------------------- render loop
def overlay_for(t):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sc = scene_at(t)
    if sc == 0:
        scene_opening(layer, t)
        return layer
    draw_caption(layer, t)
    if sc == 2:
        scene_list(layer, t)
    if sc in (2, 3, 4):
        chat(layer, t)
    if sc == 4:
        scene5_chip(layer, t)
    if sc == 5:
        scene6_highlight(layer, t)
    if sc == 6:
        scene7_signals(layer, t)
    return layer


def render(out_path=None, stills=None):
    init_globals()
    frames = range(NFRAMES) if stills is None else sorted(int(round(s * FPS)) for s in stills[1])
    enc = None
    if out_path:
        enc = subprocess.Popen(
            ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
             "-r", str(FPS), "-i", "-", "-i", f"{S}/mix.wav",
             "-c:v", "libx264", "-preset", "slow", "-crf", "19", "-pix_fmt", "yuv420p",
             "-profile:v", "high", "-level", "4.2", "-r", str(FPS),
             "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
             "-movflags", "+faststart", "-shortest", out_path], stdin=subprocess.PIPE)
    reader, rscene, held, rpos = None, -1, None, 0
    for fi in frames:
        t = fi / FPS
        sc = scene_at(t)
        clip, sin, sout, tail = EDL[sc]
        src_t = sin + (t - START[sc])
        if sc != rscene:
            if reader:
                reader.close()
            reader = ClipReader(clip, src_t)
            rscene = sc
            rpos = int(round(src_t * FPS))
        want = min(int(round(src_t * FPS)), int(round(sout * FPS)))
        while rpos <= want:
            held = reader.read()
            rpos += 1
        fg, al = held
        base = compose_subject(fg, al)
        base += GRAIN[fi % len(GRAIN)]
        img = np.clip(base, 0, 255).astype(np.uint8)
        z, zx, zy = zoom_for(t)
        img = zoom(img, z, zx, zy)
        o = np.asarray(overlay_for(t), np.float32)
        a = o[..., 3:4] / 255.0
        out = (img.astype(np.float32) * (1 - a) + o[..., :3] * a).astype(np.uint8)
        if enc:
            enc.stdin.write(out.tobytes())
        else:
            Image.fromarray(out).save(f"{stills[0]}/f{fi:05d}_{t:06.2f}.jpg", quality=90)
        if fi % 150 == 0:
            print(f"frame {fi}/{NFRAMES}", flush=True)
    if reader:
        reader.close()
    if enc:
        enc.stdin.close()
        enc.wait()


if __name__ == "__main__":
    if sys.argv[1] == "--stills":
        os.makedirs(sys.argv[2], exist_ok=True)
        render(stills=(sys.argv[2], [float(x) for x in sys.argv[3:]]))
    elif sys.argv[1] == "--info":
        print("TOTAL", TOTAL, "START", [round(s, 2) for s in START])
    else:
        render(sys.argv[1])
