"""Gera o cartão de contato (vCard) e os QR codes.

- extras/qr-site.png / .svg ........ QR para o endereço do site (cartão de visita impresso)
- extras/qr-contato.png ............ QR que salva o contato direto na agenda
- tools/_qr_contato_path.txt ....... caminho SVG do QR de contato (embutido no site)
- tools/_vcard.txt ................. texto do vCard (embutido no botão "Salvar contato")
"""
from pathlib import Path
import qrcode
from qrcode.image.svg import SvgPathImage

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://joaopedrogomesadvhacker.adv.br/"
VCARD = "\r\n".join([
    "BEGIN:VCARD", "VERSION:3.0",
    "N:Santos;João Pedro Gomes dos;;Dr.;",
    "FN:João Pedro Gomes dos Santos",
    "ORG:João Pedro Gomes — Direito Digital e Crimes Cibernéticos",
    "TITLE:Advogado — OAB/SE 17.295",
    "TEL;TYPE=CELL,VOICE:+5579999100875",
    "EMAIL;TYPE=INTERNET:joaopedrogomes2322@gmail.com",
    "URL:" + SITE,
    "X-SOCIALPROFILE;TYPE=instagram:https://instagram.com/advogadoohacker",
    "ADR;TYPE=WORK:;;;Aracaju;SE;;Brasil",
    "NOTE:Direito Digital e Crimes Cibernéticos",
    "END:VCARD", ""])

def make(data, ec=qrcode.constants.ERROR_CORRECT_M):
    q = qrcode.QRCode(error_correction=ec, border=4, box_size=20)
    q.add_data(data.encode("utf-8")); q.make(fit=True)
    return q

(ROOT / "extras").mkdir(exist_ok=True)
site_q = make(SITE, qrcode.constants.ERROR_CORRECT_H)
site_q.make_image(fill_color="black", back_color="white").save(ROOT / "extras/qr-site.png")
site_q.make_image(image_factory=SvgPathImage).save(ROOT / "extras/qr-site.svg")
VCARD_QR = "\r\n".join([  # versão curta: QR menos denso, fácil de ler na tela
    "BEGIN:VCARD", "VERSION:3.0", "N:Santos;João Pedro Gomes dos;;Dr.;", "FN:Dr. João Pedro Gomes",
    "TITLE:Advogado OAB/SE 17.295", "TEL;TYPE=CELL:+5579999100875", "URL:" + SITE, "END:VCARD"])
c = make(VCARD_QR, qrcode.constants.ERROR_CORRECT_L)
c.make_image(fill_color="black", back_color="white").save(ROOT / "extras/qr-contato.png")

# caminho SVG compacto (1 unidade = 1 módulo) para embutir no site
m = c.get_matrix()
parts = []
for y, row in enumerate(m):
    x = 0
    while x < len(row):
        if row[x]:
            start = x
            while x < len(row) and row[x]: x += 1
            parts.append(f"M{start} {y}h{x-start}v1h-{x-start}z")
        else:
            x += 1
(ROOT / "tools/_qr_contato_path.txt").write_text(f"{len(m)}|" + "".join(parts))
(ROOT / "tools/_vcard.txt").write_text(VCARD, encoding="utf-8")
print("módulos:", len(m), "| versão:", c.version, "| bytes QR:", len(VCARD_QR.encode()))
