"""Reels cover (1080x1920). Key content kept inside the 3:4 profile-grid crop (y 240-1680)."""
import sys, os, subprocess
import numpy as np
from PIL import Image, ImageDraw

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

# dark fade from the chest down so the headline reads cleanly
yy = np.arange(H, dtype=np.float32)[:, None, None]
shade = np.clip((yy - 1120) / 420, 0, 1) ** 1.3 * 0.72
img = img * (1 - shade)
canvas = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).convert("RGBA")

layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
d = ImageDraw.Draw(layer)

# alert pill
f = font("Bold", 30)
label = "CUIDADO"
tr = 4
tw = sum(f.getlength(c) + tr for c in label) - tr
pw, ph = int(tw + 40 + 46), 62
px, py = (W - pw) // 2, 1236
d.rounded_rectangle((px, py, px + pw, py + ph), radius=ph // 2, fill=GOLD + (255,))
# warning triangle icon
ix, iy = px + 26, py + ph / 2
d.polygon([(ix, iy + 13), (ix + 15, iy - 14), (ix + 30, iy + 13)], fill=(18, 18, 18, 255))
d.rectangle((ix + 13.5, iy - 5, ix + 16.5, iy + 4), fill=GOLD + (255,))
d.rectangle((ix + 13.5, iy + 7, ix + 16.5, iy + 10), fill=GOLD + (255,))
x = ix + 46
for c in label:
    d.text((x, iy + 1), c, font=f, fill=(18, 18, 18, 255), anchor="lm")
    x += f.getlength(c) + tr

put(layer, text_sprite("GOLPE DA", "Black", 112, WHITE, WHITE, None, True), 540, 1376)
put(layer, text_sprite("RECUPERAÇÃO", "Black", 124, GOLD, GOLD, None, True), 540, 1492)
put(layer, text_sprite("DO INSTAGRAM", "ExtraBold", 66, WHITE, WHITE, None, True, 0, 6), 540, 1598)

canvas.alpha_composite(layer)
canvas = canvas.convert("RGB")
canvas.save(out, quality=95)
# grid previews: 3:4 profile crop and 1:1 feed crop
canvas.crop((0, 240, 1080, 1680)).resize((540, 720)).save(out.replace(".jpg", "_grid34.jpg"), quality=90)
canvas.crop((0, 420, 1080, 1500)).resize((540, 540)).save(out.replace(".jpg", "_1x1.jpg"), quality=90)
print("ok", out)
