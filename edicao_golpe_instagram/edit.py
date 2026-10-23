"""Reels edit: golpe da falsa recuperação de contas do Instagram.

Renders 1080x1920 @30fps video frames (background replacement, overlays,
captions) and pipes them to ffmpeg together with the mixed audio.
Usage: python edit.py OUT.mp4            -> full render
       python edit.py --stills DIR t1 t2  -> preview stills at timeline seconds
"""
import sys, os, json, math, subprocess, functools
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

S = os.path.dirname(os.path.abspath(__file__))
W, H, FPS = 1080, 1920, 30
FONT = "/usr/share/fonts/opentype/inter/Inter-%s.otf"
GOLD = (212, 175, 96)
GOLD_SOFT = (201, 165, 92)
WHITE = (255, 255, 255)
INK = (17, 17, 17)

# ---------------------------------------------------------------- timeline
# (clip, src_in, src_out, extra_tail)  extra_tail = seconds held after src_out
EDL = [
    ("0186", 0.65, 6.25, 0.25),   # 1 abertura (tela branca, eco)
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
    "0185": (0.993, 1.031, 0.977), "0187": (0.999, 1.025, 0.976),
    "0188": (1.007, 1.019, 0.974),
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
    out, hl = [], False
    for i, part in enumerate(text.replace("]]", "[[").split("[[")):
        if part:
            out.append((part, i % 2 == 1))
    return out


@functools.lru_cache(maxsize=None)
def text_sprite(text, weight="Bold", size=58, color=WHITE, hl_color=GOLD,
                hl_weight=None, shadow=True, stroke=0, tracking=0, align="center",
                line_gap=1.18):
    """Renders (multi-line, rich) text to an RGBA sprite with soft shadow.
    Returns PIL image; content is centred horizontally inside it."""
    lines = text.split("\n")
    f = font(weight, size)
    fh = font(hl_weight or weight, size)
    asc, desc = f.getmetrics()
    lh = int(size * line_gap)
    widths = []
    for ln in lines:
        w = 0
        for part, hl in runs_of(ln):
            ff = fh if hl else f
            w += ff.getlength(part) + tracking * len(part)
        widths.append(w)
    pad = 30
    iw = int(max(widths)) + pad * 2
    ih = lh * (len(lines) - 1) + asc + desc + pad * 2
    img = Image.new("RGBA", (iw, ih), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for li, ln in enumerate(lines):
        if align == "center":
            x = (iw - widths[li]) / 2
        else:
            x = pad
        y = pad + li * lh
        for part, hl in runs_of(ln):
            ff = fh if hl else f
            col = hl_color if hl else color
            if tracking:
                for ch in part:
                    d.text((x, y), ch, font=ff, fill=col, stroke_width=stroke,
                           stroke_fill=(0, 0, 0, 170))
                    x += ff.getlength(ch) + tracking
            else:
                d.text((x, y), part, font=ff, fill=col, stroke_width=stroke,
                       stroke_fill=(0, 0, 0, 170))
                x += ff.getlength(part)
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
    """Composite sprite onto layer at centre (cx, cy) with opacity/scale."""
    if alpha <= 0.003:
        return
    if abs(scale - 1.0) > 1e-3:
        nw = max(1, int(img.width * scale))
        nh = max(1, int(img.height * scale))
        img = img.resize((nw, nh), Image.BICUBIC)
    if alpha < 0.999:
        a = img.split()[3].point(lambda v, k=alpha: int(v * k))
        img = img.copy()
        img.putalpha(a)
    if anchor == "center":
        x, y = int(round(cx - img.width / 2)), int(round(cy - img.height / 2))
    elif anchor == "left":
        x, y = int(round(cx)), int(round(cy - img.height / 2))
    else:
        raise ValueError(anchor)
    layer.alpha_composite(img, (x, y)) if (x >= 0 and y >= 0) else _paste_clip(layer, img, x, y)


def _paste_clip(layer, img, x, y):
    cx0, cy0 = max(0, -x), max(0, -y)
    img = img.crop((cx0, cy0, img.width, img.height))
    layer.alpha_composite(img, (max(0, x), max(0, y)))


# ---------------------------------------------------------------- UI pieces
@functools.lru_cache(maxsize=None)
def tag_sprite(text, dark=False):
    """Small letter-spaced pill label (e.g. SIMULAÇÃO / PROMESSA SUSPEITA)."""
    f = font("SemiBold", 25)
    tr = 3.2
    tw = sum(f.getlength(c) + tr for c in text) - tr
    padx, h = 22, 50
    w = int(tw + padx * 2 + 22)
    img = Image.new("RGBA", (w + 8, h + 8), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    fill = (255, 255, 255, 0) if dark else (12, 12, 12, 150)
    d.rounded_rectangle((4, 4, 4 + w, 4 + h), radius=h // 2, fill=fill,
                        outline=GOLD + (255,), width=2)
    d.ellipse((4 + padx - 2, 4 + h / 2 - 5, 4 + padx + 8, 4 + h / 2 + 5), fill=GOLD + (255,))
    x = 4 + padx + 20
    col = (40, 40, 40, 255) if dark else (240, 240, 240, 255)
    for c in text:
        d.text((x, 4 + h / 2), c, font=f, fill=col, anchor="lm")
        x += f.getlength(c) + tr
    return img


@functools.lru_cache(maxsize=None)
def bubble_sprite(text, accent=False):
    """Incoming chat bubble (simulation)."""
    f = font("SemiBold", 36)
    tw = f.getlength(text)
    padx, pady = 30, 20
    asc, desc = f.getmetrics()
    w, h = int(tw + padx * 2), asc + desc + pady * 2 - 6
    m = 26
    img = Image.new("RGBA", (w + m * 2, h + m * 2), (0, 0, 0, 0))
    # shadow
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((m, m + 6, m + w, m + h + 6), radius=30, fill=(0, 0, 0, 150))
    sh = sh.filter(ImageFilter.GaussianBlur(10))
    img.alpha_composite(sh)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((m, m, m + w, m + h), radius=30, fill=(246, 245, 242, 255))
    # tail (bottom-left)
    d.polygon([(m + 2, m + h - 30), (m - 12, m + h + 2), (m + 34, m + h - 4)], fill=(246, 245, 242, 255))
    if accent:
        d.rounded_rectangle((m + 10, m + 16, m + 16, m + h - 16), radius=3, fill=GOLD + (255,))
    d.text((m + padx + (6 if accent else 0), m + h / 2 + 1), text, font=f, fill=(20, 20, 20, 255), anchor="lm")
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
    ImageDraw.Draw(sh).rounded_rectangle((m, m + 6, m + w, m + h + 6), radius=22, fill=(0, 0, 0, 170))
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(10)))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((m, m, m + w, m + h), radius=22, fill=(14, 14, 14, 235), outline=GOLD + (255,), width=2)
    # padlock
    lx, ly = m + padx, m + h / 2
    d.arc((lx + 8, ly - 26, lx + 32, ly + 2), 180, 360, fill=GOLD + (255,), width=5)
    d.line((lx + 8, ly - 14, lx + 8, ly - 2), fill=GOLD + (255,), width=5)
    d.line((lx + 32, ly - 14, lx + 32, ly - 2), fill=GOLD + (255,), width=5)
    d.rounded_rectangle((lx + 2, ly - 4, lx + 38, ly + 24), radius=5, fill=GOLD + (255,))
    d.ellipse((lx + 16, ly + 4, lx + 24, ly + 12), fill=(14, 14, 14, 255))
    d.text((lx + ic + 18, ly + 1), text, font=f, fill=WHITE + (255,), anchor="lm")
    return img


# ---------------------------------------------------------------- background
BL_PAD = 192  # ≈ horizontal period of the blinds (78 / sin 24°)


def make_background():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    # vertical graphite gradient
    g = np.interp(yy, [0, 700, 1920], [24, 17, 7])[..., None] * np.array([1.0, 0.985, 0.96], np.float32)
    # warm halo behind the head
    halo = np.exp(-(((xx - 540) / 470) ** 2 + ((yy - 820) / 560) ** 2))
    g = g + halo[..., None] * np.array([92, 72, 42], np.float32) * 0.62
    # second, smaller hot spot slightly above head (key light on the wall)
    hot = np.exp(-(((xx - 600) / 260) ** 2 + ((yy - 560) / 300) ** 2))
    g = g + hot[..., None] * np.array([60, 48, 30], np.float32) * 0.45
    # venetian-blind light, cast from upper right (noir office light)
    ang = math.radians(-24)
    yy, xx = np.mgrid[0:H, -BL_PAD:W].astype(np.float32)
    win = np.exp(-(((xx - 820) / 420) ** 2 + ((yy - 470) / 430) ** 2))
    blinds_period = 78.0
    # sharp-ish stripes, softened
    v = (yy * math.cos(ang) + xx * math.sin(ang))
    stripes = 0.5 + 0.5 * np.cos(2 * math.pi * v / blinds_period)
    stripes = np.clip((stripes - 0.35) / 0.4, 0, 1)
    blinds = (stripes * win)[..., None] * np.array([150, 120, 72], np.float32) * 0.22
    # vignette
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((xx - 540) / 620) ** 2 + ((yy - 900) / 1050) ** 2)
    vig = np.clip(1.15 - 0.55 * r ** 2.2, 0.28, 1.0)[..., None]
    return g.astype(np.float32), blinds.astype(np.float32), vig.astype(np.float32)


# ---------------------------------------------------------------- subject reader
SUB_H = 1664
SUB_Y = H - SUB_H


class ClipReader:
    def __init__(self, clip, src_in):
        sw, sh = (576, 1024) if clip in ("0185", "0186") else (464, 832)
        self.sw = int(round(sw * SUB_H / sh / 2)) * 2
        self.sh = SUB_H
        self.x0 = (W - self.sw) // 2
        r = WALL[clip]
        gr, gg, gb = [(1 / v) ** 0.9 for v in r]
        vf = (f"colorchannelmixer=rr={gr:.4f}:gg={gg:.4f}:bb={gb:.4f},"
              "curves=all='0/0 0.05/0.056 0.15/0.16 0.5/0.5 0.8/0.81 1/1',"
              "eq=saturation=0.97:contrast=1.04,"
              f"scale={self.sw}:{self.sh}:flags=lanczos,unsharp=5:5:0.7:5:5:0")
        ss = f"{src_in:.3f}"
        self.fp = subprocess.Popen(
            ["ffmpeg", "-v", "error", "-ss", ss, "-i", f"{S}/matte/{clip}-fg.mkv",
             "-vf", vf, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
        self.ap = subprocess.Popen(
            ["ffmpeg", "-v", "error", "-ss", ss, "-i", f"{S}/matte/{clip}-a.mkv",
             "-vf", f"scale={self.sw}:{self.sh}:flags=bicubic", "-f", "rawvideo", "-pix_fmt", "gray", "-"],
            stdout=subprocess.PIPE)
        ramp = np.ones(self.sw, np.float32)
        e = 28
        ramp[:e] = np.linspace(0, 1, e) ** 1.5
        ramp[-e:] = np.linspace(1, 0, e) ** 1.5
        self.ramp = ramp[None, :]
        self.last = None

    def read(self):
        n = self.sw * self.sh
        b = self.fp.stdout.read(n * 3)
        a = self.ap.stdout.read(n)
        if len(b) < n * 3 or len(a) < n:
            return self.last
        fg = np.frombuffer(b, np.uint8).reshape(self.sh, self.sw, 3)
        al = np.frombuffer(a, np.uint8).reshape(self.sh, self.sw)
        self.last = (fg, al)
        return self.last

    def close(self):
        for p in (self.fp, self.ap):
            p.stdout.close()
            p.kill()


BG, BLINDS, VIG = None, None, None
GRAIN = None


def compose_subject(t, fg, al, x0, sw):
    """Background + matted subject + warm rim -> float32 HxWx3 (0..255)."""
    drift = int((t * 9) % BL_PAD)
    frame = BG.copy()
    frame += BLINDS[:, BL_PAD - drift:BL_PAD - drift + W]
    frame *= VIG
    a0 = al.astype(np.float32) / 255.0
    # tighten soft edges and pull wall spill out of the semi-transparent fringe
    a = np.clip((a0 - 0.04) / 0.92, 0, 1) ** 1.25 * RAMP_CACHE[sw]
    # warm rim light along the silhouette (strongest near the halo)
    small = Image.fromarray(al[::4, ::4])
    blur = np.asarray(small.filter(ImageFilter.GaussianBlur(3)), np.float32) / 255.0
    rim = np.clip(al[::4, ::4].astype(np.float32) / 255.0 - blur, 0, 1)
    rim = np.asarray(Image.fromarray((rim * 255).astype(np.uint8)).resize((sw, SUB_H), Image.BILINEAR),
                     np.float32) / 255.0
    region = frame[SUB_Y:SUB_Y + SUB_H, x0:x0 + sw]
    halo = HALO_MAP[SUB_Y:SUB_Y + SUB_H, x0:x0 + sw]
    sub = fg.astype(np.float32)
    fringe = (a0 < 0.97)[..., None]
    sub = np.where(fringe, sub * (0.35 + 0.65 * a0[..., None] ** 2), sub)
    sub = sub + (rim * halo * 0.55)[..., None] * np.array([150, 118, 70], np.float32)
    region[:] = region * (1 - a[..., None]) + sub * a[..., None]
    # low-key side falloff over the whole picture hides where the shot ends
    frame *= SIDE
    return frame


RAMP_CACHE = {}
HALO_MAP = None
SIDE = None


def init_globals():
    global BG, BLINDS, VIG, GRAIN, HALO_MAP, SIDE
    BG, BLINDS, VIG = make_background()
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    HALO_MAP = np.exp(-(((xx - 560) / 430) ** 2 + ((yy - 760) / 420) ** 2)) * 0.9 + 0.1
    rng = np.random.default_rng(7)
    GRAIN = [rng.normal(0, 2.6, (H // 2, W // 2, 1)).astype(np.float32).repeat(2, 0).repeat(2, 1) for _ in range(6)]
    xs = np.arange(W, dtype=np.float32)
    dist = np.minimum(xs, W - 1 - xs)
    sd = np.clip(dist / 210.0, 0, 1)
    sd = sd * sd * (3 - 2 * sd)
    ys = np.arange(H, dtype=np.float32)
    lower = np.clip((ys - 900) / 500, 0, 1)[:, None]     # stronger towards the bottom
    SIDE = (1 - (0.30 + 0.45 * lower) * (1 - sd[None, :]))[..., None].astype(np.float32)
    for sw in (928, 936):
        e = 70
        r = np.ones(sw, np.float32)
        r[:e] = np.linspace(0, 1, e) ** 1.5
        r[-e:] = np.linspace(1, 0, e) ** 1.5
        RAMP_CACHE[sw] = r[None, :]


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
CAPTIONS_TL = [(T(s, a), T(s, b) if s != 7 else min(T(s, b), TOTAL), txt) for s, a, b, txt in CAPTIONS]
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
def ghost(layer, spr, cx, cy, t0, t, dur=0.75, amt=0.20):
    """Echo copy of a typography sprite dissipating."""
    p = (t - t0) / dur
    if 0 <= p <= 1:
        put(layer, blur_of(spr, 3), cx, cy - 10 * p, alpha=amt * (1 - p) ** 1.6, scale=1 + 0.10 * ease_out(p))


def word_line(layer, words, cx, cy, t, weight, size, color, echo=True, gap=0.28):
    """Line whose words appear at given times. words=[(text, t_appear)]"""
    f = font(weight, size)
    sp = f.getlength(" ")
    sprites = [text_sprite(w, weight, size, color, color, None, False) for w, _ in words]
    inner = [f.getlength(w) for w, _ in words]
    total = sum(inner) + sp * (len(words) - 1)
    x = cx - total / 2
    for (w, ta), spr, iw in zip(words, sprites, inner):
        wc = x + iw / 2
        if t >= ta:
            k = ease_out((t - ta) / 0.16)
            put(layer, spr, wc, cy + (1 - k) * 18, alpha=k)
            if echo:
                ghost(layer, spr, wc, cy, ta, t)
        x += iw + sp


def scene_opening(layer, t):
    s = 0
    L = lambda src: T(s, src)
    # context label
    tg = tag_sprite("PROMESSA SUSPEITA", dark=True)
    put(layer, tg, 540, 330, alpha=ease_out((t - 0.05) / 0.3))
    # line A
    word_line(layer, [("Recupero", L(0.84)), ("o", L(1.38)), ("seu", L(1.46)), ("Instagram", L(1.62))],
              540, 560, t, "Bold", 70, INK)
    # number block
    tn10, tn15 = L(2.40), L(3.27)
    s10 = text_sprite("10", "Black", 330, INK, INK, None, False)
    s15 = text_sprite("15", "Black", 330, INK, INK, None, False)
    ncy = 850
    if tn10 <= t < tn15:
        k = ease_back((t - tn10) / 0.22)
        put(layer, s10, 540, ncy + (1 - k) * 40, alpha=clamp01((t - tn10) / 0.1), scale=0.9 + 0.1 * k)
        ghost(layer, s10, 540, ncy, tn10, t, 0.8, 0.16)
    elif t >= tn15:
        p = (t - tn15) / 0.13
        if p < 1:  # old number leaves upward
            put(layer, s10, 540, ncy - 70 * ease_out(p), alpha=1 - p)
        k = ease_back((t - tn15) / 0.2, 1.8)
        put(layer, s15, 540, ncy + 70 * (1 - k), alpha=clamp01((t - tn15) / 0.08))
        ghost(layer, s15, 540, ncy, tn15, t, 0.8, 0.16)
    tm = L(2.70)
    if t >= tm:
        sm = text_sprite("MINUTOS", "SemiBold", 46, INK, INK, None, False, 0, 10)
        k = ease_out((t - tm) / 0.18)
        put(layer, sm, 540, 1045 + (1 - k) * 12, alpha=k)
        ghost(layer, sm, 540, 1045, tm, t, 0.7, 0.14)
        # thin gold rule under MINUTOS
        if k > 0:
            ImageDraw.Draw(layer).rectangle((540 - 46 * k, 1088, 540 + 46 * k, 1091), fill=GOLD + (int(255 * k),))
    # line C / D
    word_line(layer, [("Tenho", L(4.38)), ("um", L(4.58)), ("contato", L(4.66))],
              540, 1235, t, "Bold", 70, INK)
    word_line(layer, [("dentro", L(5.18)), ("da", L(5.46)), ("Meta", L(5.58))],
              540, 1330, t, "Bold", 70, INK)


def scene_list(layer, t):
    """Scene 3: 'Você está…' list in the free area above the head."""
    s = 2
    L = lambda src: T(s, src)
    t_out = L(6.05)
    fade = 1 - clamp01((t - t_out) / 0.22)
    if fade <= 0:
        return
    if t < L(2.44):
        return
    lead = text_sprite("VOCÊ ESTÁ…", "SemiBold", 30, GOLD, GOLD, None, True, 0, 6)
    k = ease_out((t - L(2.44)) / 0.2)
    put(layer, lead, 110 - 30, 268, alpha=k * fade, anchor="left")
    items = [("Sem falar com os clientes", L(2.72), 350), ("Sem vender", L(4.02), 440), ("Desesperado", L(4.92), 530)]
    d = ImageDraw.Draw(layer)
    for txt, ta, y in items:
        if t < ta:
            continue
        k = ease_out((t - ta) / 0.2)
        spr = text_sprite(txt, "Bold", 60, WHITE, WHITE, None, True)
        put(layer, spr, 120 - 30 + (1 - k) * -40, y, alpha=k * fade, anchor="left")
        # gold marker bar
        d.rounded_rectangle((90, y - 26, 97, y + 26), radius=3, fill=GOLD + (int(255 * k * fade),))


def chat(layer, t):
    """Fictional chat thread spanning scenes 3 → 5 (above the head)."""
    t1 = T(2, 7.74)            # Eu consigo resolver agora.
    t2 = T(3, 1.10)            # Pagamento pelo serviço
    t3 = T(3, 3.40)            # Taxa de desbloqueio
    t_gone = T(4, 4.92)        # "foi embora"
    if t < t1 or t > t_gone + 0.6:
        return
    msgs = [("Eu consigo resolver agora.", t1, False), ("Pagamento pelo serviço", t2, False),
            ("Taxa de desbloqueio", t3, True)]
    shown = [m for m in msgs if t >= m[1]]
    # stack anchored at the top; newest at the bottom
    tag = tag_sprite("SIMULAÇÃO")
    gone_p = clamp01((t - t_gone) / 0.45)
    put(layer, tag, 62 + tag.width / 2 - 8, 250, alpha=ease_out((t - t1) / 0.25) * (1 - gone_p))
    y = 330
    for i, (txt, ta, acc) in enumerate(shown):
        spr = bubble_sprite(txt, acc)
        k = ease_back((t - ta) / 0.28, 1.6)
        older = sum(1 for m in shown if m[1] > ta)
        op = 1.0 - 0.28 * min(older, 2)
        # staggered vanish when the "prestador" disappears
        gp = clamp01((t - t_gone - 0.07 * (len(shown) - 1 - i)) / 0.32)
        a = clamp01((t - ta) / 0.12) * op * (1 - gp)
        put(layer, spr, 64 - 26, y + (1 - k) * 26 - 10 * ease_out(gp), alpha=a,
            scale=1.0 - 0.06 * gp, anchor="left")
        y += spr.height - 30


def scene5_chip(layer, t):
    a, b = T(4, 2.86), T(4, 4.30)
    if a <= t < b + 0.2:
        k = ease_out((t - a) / 0.18) * (1 - clamp01((t - b) / 0.2))
        spr = chip_sprite("Conta sem acesso")
        put(layer, spr, 1040 - spr.width / 2 + 24, 430 + (1 - k) * 14, alpha=k)


def scene6_highlight(layer, t):
    s = 5
    ta = T(s, 3.80)
    if t < ta:
        return
    k = ease_out((t - ta) / 0.25)
    l1 = text_sprite("Cobrança, sozinha,", "SemiBold", 54, WHITE, WHITE, None, True)
    l2 = text_sprite("não significa golpe", "ExtraBold", 66, GOLD, GOLD, None, True)
    put(layer, l1, 540, 360 + (1 - k) * 14, alpha=k)
    k2 = ease_out((t - ta - 0.32) / 0.28)
    put(layer, l2, 540, 445 + (1 - k2) * 14, alpha=k2)


def scene7_signals(layer, t):
    s = 6
    ta, tb = T(s, 3.82), T(s, 5.46)
    if t < ta:
        return
    d = ImageDraw.Draw(layer)
    lead = text_sprite("SINAIS DE ALERTA", "SemiBold", 30, GOLD, GOLD, None, True, 0, 6)
    put(layer, lead, 540, 272, alpha=ease_out((t - ta + 0.1) / 0.25))
    for txt, t0, y in (("Promessa garantida", ta, 365), ("Pressão para pagar", tb, 485)):
        if t < t0:
            continue
        k = ease_out((t - t0) / 0.2)
        spr = text_sprite(txt, "ExtraBold", 68, WHITE, WHITE, None, True)
        put(layer, spr, 540, y + (1 - k) * 16, alpha=k)
        u = ease_inout((t - t0 - 0.12) / 0.35)
        if u > 0:
            half = (spr.width - 60) / 2
            d.rounded_rectangle((540 - half, y + 44, 540 - half + 2 * half * u, y + 50), radius=3, fill=GOLD + (255,))


def zoom_for(t):
    """(z, cx, cy) camera push-ins; only two, both subtle."""
    a = T(1, 5.40)
    if START[1] <= t < START[2]:
        return 1 + 0.06 * ease_inout((t - a) / 0.45), 540, 1000
    b = T(6, 5.46)
    if START[6] <= t < START[7]:
        return 1 + 0.035 * ease_inout((t - b) / 0.6), 540, 980
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


def opening_bg():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((xx - 540) / 900) ** 2 + ((yy - 900) / 1300) ** 2)
    v = 255 - 10 * np.clip(r, 0, 1) ** 2
    return np.repeat(v[..., None], 3, 2).astype(np.float32)


def render(out_path=None, stills=None):
    init_globals()
    white = opening_bg()
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
    reader, rscene, held = None, -1, None
    for fi in frames:
        t = fi / FPS
        sc = scene_at(t)
        clip, sin, sout, tail = EDL[sc]
        if sc == 0:
            base = white.copy()
        else:
            if sc != rscene:
                if reader:
                    reader.close()
                src_t = sin + (t - START[sc])
                reader = ClipReader(clip, src_t)
                rscene = sc
                rpos = int(round(src_t * FPS))
            want = int(round((sin + (t - START[sc])) * FPS))
            src_limit = int(round(sout * FPS))
            want = min(want, src_limit)
            while rpos <= want:
                held = reader.read()
                rpos += 1
            fg, al = held
            base = compose_subject(t, fg, al, reader.x0, reader.sw)
        base += GRAIN[fi % len(GRAIN)] * (0.6 if sc == 0 else 1.0)
        img = np.clip(base, 0, 255).astype(np.uint8)
        z, zx, zy = zoom_for(t)
        img = zoom(img, z, zx, zy)
        ov = overlay_for(t)
        o = np.asarray(ov, np.float32)
        a = o[..., 3:4] / 255.0
        out = (img.astype(np.float32) * (1 - a) + o[..., :3] * a).astype(np.uint8)
        if enc:
            enc.stdin.write(out.tobytes())
        else:
            Image.fromarray(out).save(f"{stills[0]}/f{fi:05d}_{t:06.2f}.jpg", quality=90)
        if fi % 150 == 0:
            print(f"frame {fi}/{NFRAMES}", flush=True)
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
