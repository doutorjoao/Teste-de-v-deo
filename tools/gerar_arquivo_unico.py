"""Gera versões de página única do site (CSS, JS, fontes e fotos embutidos no HTML).

Uso: python3 tools/gerar_arquivo_unico.py
Lê site/ e grava em site-arquivo-unico/ (estrutura plana, sem subpastas).
"""
import base64, re, shutil
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "site"
OUT = SRC.parent / "site-arquivo-unico"
DOMAIN = "https://joaopedrogomesadvhacker.adv.br"
MIME = {".woff2": "font/woff2", ".png": "image/png", ".webp": "image/webp", ".jpg": "image/jpeg"}


def data_uri(path: Path) -> str:
    return f"data:{MIME[path.suffix]};base64," + base64.b64encode(path.read_bytes()).decode()


css = (SRC / "assets/css/style.css").read_text(encoding="utf-8")
css = re.sub(r'url\("\.\./(fonts|img)/([^"]+)"\)',
             lambda m: f'url("{data_uri(SRC / "assets" / m.group(1) / m.group(2))}")', css)
js = (SRC / "assets/js/main.js").read_text(encoding="utf-8")

if OUT.exists():
    shutil.rmtree(OUT)
OUT.mkdir()

for page in ("index.html", "treinamento.html", "privacidade.html"):
    html = (SRC / page).read_text(encoding="utf-8")
    html = re.sub(r'\s*<link rel="preload"[^>]*>', "", html)
    html = html.replace('<link rel="stylesheet" href="assets/css/style.css">', "<style>\n" + css + "\n</style>")
    html = html.replace('<script src="assets/js/main.js" defer></script>', "<script>\n" + js + "\n</script>")
    html = re.sub(r'src="assets/img/([^"]+)"', lambda m: f'src="{data_uri(SRC / "assets/img" / m.group(1))}"', html)
    # arquivos que precisam continuar como arquivos (prévia de link e ícones) ficam na raiz
    html = html.replace(f"{DOMAIN}/assets/img/", f"{DOMAIN}/").replace('href="/assets/img/', 'href="/')
    assert "assets/" not in html, f"{page}: ainda referencia assets/"
    (OUT / page).write_text(html, encoding="utf-8")

for f in ("og-image.jpg", "apple-touch-icon.png", "icon-512.png"):
    shutil.copy(SRC / "assets/img" / f, OUT / f)
shutil.copy(SRC / "favicon.ico", OUT / "favicon.ico")

for p in sorted(OUT.iterdir()):
    print(f"{p.name:24s} {p.stat().st_size / 1024:7.0f} KB")
