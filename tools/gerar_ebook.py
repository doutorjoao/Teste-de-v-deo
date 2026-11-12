"""Gera o e-book "Direito Digital na Prática" a partir de ebook/conteudo.txt.

Uso:  python3 tools/gerar_ebook.py          → ebook/ebook.html
Depois o PDF é impresso pelo navegador (tools/gerar_ebook_pdf.js), que pagina o
texto automaticamente.

Marcação de ebook/conteudo.txt (blocos separados por linha em branco):
  # N | título | parte em dourado | linha de apoio   → abertura de módulo
  ## Título                                          → título de seção
  ### Título                                         → subtítulo
  !lead texto                                        → frase de destaque
  - **Rótulo:** texto                                → item de lista
  > texto                                            → citação
  !box Título | texto                                → quadro escuro
  !ex Título | texto                                 → quadro de exemplo
  !case ETIQUETA | Título | texto                    → cartão de caso
  !concl Título                                      → conclusão do módulo
  !tripod                                            → os três pilares
  **negrito**  *itálico*
"""
import html
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "ebook"


def inline(t: str) -> str:
    t = html.escape(t, quote=False)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"\*(.+?)\*", r"<em>\1</em>", t)
    return t


def block(raw: str) -> str:
    lines = raw.strip().split("\n")
    first = lines[0]
    if first.startswith("- "):
        return "\n".join(f'<ul class="list"><li>{inline(l[2:].strip())}</li></ul>' for l in lines)
    text = " ".join(l.strip() for l in lines)
    if text.startswith("### "):
        return f'<h3 class="keep">{inline(text[4:])}</h3>'
    if text.startswith("## "):
        return f'<h2 class="sec keep">{inline(text[3:])}</h2>'
    if text.startswith("!lead "):
        return f'<p class="lead">{inline(text[6:])}</p>'
    if text.startswith("> "):
        return f"<blockquote>{inline(text[2:])}</blockquote>"
    if text.startswith("!box "):
        t, b = [x.strip() for x in text[5:].split("|", 1)]
        return f'<div class="callout"><span class="k">{inline(t.upper())}</span><p>{inline(b)}</p></div>'
    if text.startswith("!ex "):
        t, b = [x.strip() for x in text[4:].split("|", 1)]
        return f'<div class="example"><span class="k">{inline(t)}</span><p>{inline(b)}</p></div>'
    if text.startswith("!case "):
        tag, t, b = [x.strip() for x in text[6:].split("|", 2)]
        return f'<div class="case"><p class="tag">{inline(tag)}</p><b>{inline(t)}</b><p>{inline(b)}</p></div>'
    if text.startswith("!concl "):
        return f'<div class="concl keep"><p class="eyebrow">Conclusão do módulo</p><h2>{inline(text[7:])}</h2></div>'
    if text == "!tripod":
        return ('<div class="tripod"><div><i>i.</i><span>TECNOLOGIA</span></div>'
                '<div><i>ii.</i><span>COMPORTAMENTO HUMANO</span></div>'
                '<div><i>iii.</i><span>RESPONSABILIZAÇÃO</span></div></div>')
    cls = ' class="keep"' if text.endswith(":") else ""
    return f"<p{cls}>{inline(text)}</p>"


def opener(n, title, gold, tagline):
    return f'''<section class="page dark opener" data-mod-start="{n}">
  <div class="runhead"><span>Direito Digital na Prática</span><span>Módulo {n}</span></div>
  <span class="num">{n}</span>
  <div class="txt">
    <p class="eyebrow">Módulo {n}</p>
    <h2>{inline(title)} <span class="gold">{inline(gold)}</span></h2>
    <p class="tagline">{inline(tagline)}</p>
  </div>
  <div class="folio"></div>
</section>'''


src = (ROOT / "conteudo.txt").read_text(encoding="utf-8")
parts = re.split(r"^# ", src, flags=re.M)
out = []
for part in parts:
    if not part.strip():
        continue
    head, _, body = part.partition("\n")
    n, title, gold, tagline = [x.strip() for x in head.split("|")]
    out.append(opener(n, title, gold, tagline))
    blocks = [b for b in re.split(r"\n\s*\n", body) if b.strip()]
    out.append(f'<div class="flow" data-mod="{n}">\n' + "\n".join(block(b) for b in blocks) + "\n</div>")

final = '''<section class="page dark final">
  <svg class="rings" viewBox="0 0 400 400" aria-hidden="true"><g fill="none" stroke="#c9a55c" stroke-opacity=".22"><circle cx="200" cy="200" r="60"/><circle cx="200" cy="200" r="110"/><circle cx="200" cy="200" r="160"/><circle cx="200" cy="200" r="210"/></g></svg>
  <div class="final-txt">
    <svg class="hex" style="width:40pt;height:46pt"><use href="#logo"/></svg>
    <h2>Quer aprender <span class="gold">mais?</span></h2>
    <p>Conteúdo sobre Direito Digital, provas, plataformas e advocacia ética toda semana.</p>
    <div class="links">
      <span><small>INSTAGRAM</small>@advogadoohacker</span>
      <span><small>SITE</small>joaopedrogomesadvhacker.adv.br</span>
    </div>
  </div>
  <div class="final-foot">João Pedro Gomes dos Santos · Advogado · OAB/SE 17.295<br>
  Conteúdo informativo e educativo. Não substitui a análise individual de cada caso.<br>
  © Todos os direitos reservados. Proibida a reprodução sem autorização.</div>
</section>'''
out.append(final)

page = (ROOT / "modelo.html").read_text(encoding="utf-8")
page = page.replace("<!--CONTEUDO-->", "\n\n".join(out))
(ROOT / "ebook.html").write_text(page, encoding="utf-8")
print("ebook.html gerado:", len(out) - 1, "blocos de módulo")
