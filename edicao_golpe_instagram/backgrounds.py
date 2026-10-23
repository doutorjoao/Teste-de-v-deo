"""Procedural backgrounds (1080x1920 float32 RGB, 0..255)."""
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

W, H = 1080, 1920


def _grid():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    return yy, xx


def library(seed=11):
    """Defocused law library: wooden shelves with book spines + warm lamp."""
    rng = np.random.default_rng(seed)
    img = Image.new("RGB", (W, H), (46, 32, 24))
    d = ImageDraw.Draw(img)
    pal = [(98, 28, 26), (72, 22, 24), (30, 52, 42), (26, 36, 58), (122, 92, 52), (64, 46, 34),
           (150, 118, 66), (176, 162, 136), (40, 30, 26), (110, 60, 36), (52, 62, 48)]
    shelf_h = 300
    for row in range(-1, H // shelf_h + 2):
        y_board = row * shelf_h + 120
        x = -20
        while x < W + 20:
            bw = int(rng.integers(20, 52))
            bh = int(rng.integers(190, 262))
            c = np.array(pal[rng.integers(len(pal))], float) * rng.uniform(0.75, 1.15)
            if rng.random() < 0.08:          # small gap / leaning book
                x += bw
                continue
            d.rectangle((x, y_board - bh, x + bw - 2, y_board), fill=tuple(int(v) for v in np.clip(c, 0, 255)))
            # gilt bands on some spines
            if rng.random() < 0.45:
                gy = y_board - bh + int(rng.integers(18, 40))
                d.rectangle((x + 3, gy, x + bw - 5, gy + 5), fill=(190, 156, 90))
                d.rectangle((x + 3, gy + 14, x + bw - 5, gy + 17), fill=(170, 138, 80))
            x += bw
        d.rectangle((0, y_board, W, y_board + 26), fill=(118, 84, 54))
        d.rectangle((0, y_board + 26, W, y_board + 44), fill=(58, 40, 28))
    img = img.filter(ImageFilter.GaussianBlur(16))
    a = np.asarray(img, np.float32)
    yy, xx = _grid()
    # warm practical lamp glow, top-right, and soft key spill behind the head
    lamp = np.exp(-(((xx - 900) / 260) ** 2 + ((yy - 380) / 300) ** 2))
    spill = np.exp(-(((xx - 540) / 520) ** 2 + ((yy - 760) / 600) ** 2))
    a = a * (0.55 + 0.35 * spill[..., None]) + lamp[..., None] * np.array([120, 86, 40]) * 0.55
    vig = np.clip(1.08 - 0.42 * (((xx - 540) / 640) ** 2 + ((yy - 860) / 1100) ** 2), 0.45, 1)
    return (a * vig[..., None]).astype(np.float32)


def studio_light():
    """Clean warm-grey seamless studio backdrop with a soft spot behind the head."""
    yy, xx = _grid()
    spot = np.exp(-(((xx - 540) / 560) ** 2 + ((yy - 720) / 700) ** 2))
    base = np.array([168, 162, 154], np.float32)
    top = np.array([232, 228, 221], np.float32)
    a = base + (top - base) * spot[..., None]
    a *= np.clip(1.04 - 0.10 * ((yy - 900) / 1000) ** 2, 0.85, 1)[..., None]
    return a.astype(np.float32)


def city_night(seed=5):
    """Office window at night: deep blue-black with defocused warm city lights."""
    rng = np.random.default_rng(seed)
    yy, xx = _grid()
    a = np.zeros((H, W, 3), np.float32)
    a += (np.interp(yy, [0, 1920], [26, 8])[..., None] * np.array([0.55, 0.7, 1.0]))
    layer = Image.new("RGB", (W, H), (0, 0, 0))
    d = ImageDraw.Draw(layer)
    for _ in range(70):
        x, y = rng.uniform(-60, W + 60), rng.uniform(150, 1500)
        r = rng.uniform(18, 60)
        warm = rng.random() < 0.75
        c = (np.array([255, 182, 92]) if warm else np.array([170, 200, 255])) * rng.uniform(0.25, 0.7)
        d.ellipse((x - r, y - r, x + r, y + r), fill=tuple(int(v) for v in c))
    layer = layer.filter(ImageFilter.GaussianBlur(14))
    a += np.asarray(layer, np.float32) * 0.8
    spill = np.exp(-(((xx - 540) / 520) ** 2 + ((yy - 760) / 600) ** 2))
    a += spill[..., None] * np.array([40, 34, 30]) * 0.6
    vig = np.clip(1.1 - 0.45 * (((xx - 540) / 640) ** 2 + ((yy - 860) / 1100) ** 2), 0.4, 1)
    return np.clip(a * vig[..., None], 0, 255).astype(np.float32)


STYLES = {"biblioteca": library, "estudio_claro": studio_light, "noite": city_night}
