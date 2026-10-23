"""Reels cover (1080x1920). Key content kept inside the 3:4 profile-grid crop (y 240-1680)."""
import sys, os, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

S = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, S)
from edit import W, H, WALL, GOLD, WHITE, font, text_sprite, put  # noqa: E402
from backgrounds import studio_light  # noqa: E402

CLIP, T_SRC = "0185", "6.000"
out = sys.argv[1]


def grab(path, vf, fmt, ch):
    b = subprocess.check_output(["ffmpeg", "-v", "error", "-ss", T_SRC, "-i", path, "-frames:v", "1",
                                 "-vf", vf, "-f", "rawvideo", "-pix_fmt", fmt, "-"])
    return np.frombuffer(b, np.uint8).reshape(H, W, ch).astype(np.float32)


fill = "scale=1080:-2:flags=lanczos,crop=1080:1920:0:(ih-1920)/2"
gr, gg, gb = [(1 / v) ** 0.9 for v in WALL[CLIP]]
vf = (f"colorchannelmixer=rr={gr:.4f}:gg={gg:.4f}:bb={gb:.4f},"
      "curves=all='0/0 0.05/0.056 0.15/0.16 0.5/0.5 0.8/0.81 1/1',"
      f"eq=saturation=1.0:contrast=1.05,{fill},unsharp=5:5:0.7:5:5:0")
fg = grab(f"{S}/matte/{CLIP}-fg.mkv", vf, "rgb24", 3)
al = grab(f"{S}/matte/{CLIP}-a.mkv", fill.replace("lanczos", "bicubic"), "gray", 1) / 255.0
al = np.clip((al - 0.02) / 0.96, 0, 1)
img = studio_light() * (1 - al) + fg * al

# light fade at the bottom only (the text boxes carry their own contrast)
yy = np.arange(H, dtype=np.float32)[:, None, None]
shade = np.clip((yy - 1300) / 500, 0, 1) ** 1.5 * 0.45
img = img * (1 - shade)
canvas = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).convert("RGBA")


def box_line(text, size, fg, bg, padx=34, pady=16, tracking=0):
    """Instagram-text-tool style: one rounded box per line."""
    f = font("Black", size)
    tw = sum(f.getlength(c) + tracking for c in text) - tracking
    asc, desc = f.getmetrics()
    th = asc - 6
    w, h = int(tw + padx * 2), int(th + pady * 2)
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w - 1, h - 1), radius=min(22, h // 4), fill=bg + (255,))
    x = padx
    for c in text:
        d.text((x, h / 2 + 2), c, font=f, fill=fg + (255,), anchor="lm")
        x += f.getlength(c) + tracking
    return im


INKC = (16, 16, 16)
lines = [box_line("GOLPE DA", 104, INKC, (255, 255, 255)),
         box_line("RECUPERAÇÃO", 112, INKC, GOLD),
         box_line("DO INSTAGRAM", 72, WHITE, INKC, tracking=4)]
gw = max(l.width for l in lines)
gh = sum(l.height for l in lines) - 10 * (len(lines) - 1)
group = Image.new("RGBA", (gw + 80, gh + 80), (0, 0, 0, 0))
y = 40
for l in lines:
    group.alpha_composite(l, ((group.width - l.width) // 2, y))
    y += l.height - 10
# soft drop shadow, then a slight tilt for energy
sh = Image.new("RGBA", group.size, (0, 0, 0, 0))
sh.putalpha(group.split()[3].point(lambda v: int(v * 0.45)))
sh = sh.filter(ImageFilter.GaussianBlur(14))
g2 = Image.new("RGBA", group.size, (0, 0, 0, 0))
g2.alpha_composite(sh, (0, 10))
g2.alpha_composite(group)
group = g2.rotate(3.5, resample=Image.BICUBIC, expand=True)

# small alert tag above the block
tag = box_line("⚠ CUIDADO", 40, INKC, GOLD, padx=22, pady=12, tracking=3)
layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
cy = 1462
put(layer, group, 540, cy)
put(layer, tag.rotate(3.5, resample=Image.BICUBIC, expand=True), 540 + 255, cy - group.height / 2 - 2)

canvas.alpha_composite(layer)
canvas = canvas.convert("RGB")
canvas.save(out, quality=95)
# grid previews: 3:4 profile crop and 1:1 feed crop
canvas.crop((0, 240, 1080, 1680)).resize((540, 720)).save(out.replace(".jpg", "_grid34.jpg"), quality=90)
canvas.crop((0, 240, 1080, 1680)).save(out.replace(".jpg", "_perfil_3x4.jpg"), quality=95)
print("ok", out)
