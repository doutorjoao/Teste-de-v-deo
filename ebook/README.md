# E-book "Direito Digital na Prática"

- `conteudo.txt` — todo o texto do e-book (edite aqui; a marcação está descrita em `tools/gerar_ebook.py`).
- `modelo.html` — capa, sumário, páginas do autor e o estilo visual.
- `img/` — foto do autor.
- `saida/` — PDF final e capas (vertical e quadrada para a Hotmart).

Para gerar de novo:

```
python3 tools/gerar_ebook.py
python3 -m http.server 8770 &          # na raiz do repositório (para carregar as fontes)
node tools/gerar_ebook_pdf.js http://127.0.0.1:8770/ebook/ebook.html ebook/saida/Direito-Digital-na-Pratica-Joao-Pedro-Gomes.pdf
```
