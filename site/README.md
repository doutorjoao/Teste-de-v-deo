# Site — João Pedro Gomes · Direito Digital e Crimes Cibernéticos

Site estático (HTML + CSS + JavaScript puro, sem bibliotecas nem serviços de terceiros).

## Estrutura

```
index.html          Página principal
treinamento.html    Página do treinamento (separada dos serviços — Código de Ética da OAB, art. 40, IV)
privacidade.html    Política de privacidade (LGPD)
favicon.ico
assets/
  css/style.css     Estilos de todas as páginas
  js/main.js        Interações (menu, triagem, linha do tempo, animações)
  fonts/            Fontes hospedadas no próprio site (licença SIL OFL)
  img/              Fotos, ícones e imagem de prévia (og-image.jpg)
```

## Como publicar

> **Mais simples:** use a pasta `site-arquivo-unico/` (gerada por `python3 tools/gerar_arquivo_unico.py`).
> Cada página traz CSS, JS, fontes e fotos embutidos, então funciona mesmo se as subpastas não forem enviadas.

Versão em várias pastas (esta):

Envie **todo o conteúdo desta pasta** para a raiz do domínio (`joaopedrogomesadvhacker.adv.br`),
mantendo a estrutura de pastas. Os arquivos antigos `fundo.png`, `musica-fundo.mp3`, `beep.mp3`,
`alerta.mp3`, `foto-topo.jpeg`, `foto-joao-pedro.jpeg` e `foto-camila.jpeg` não são mais usados.
A música fica em `musica-fundo.mp3`, na raiz (se o arquivo não existir, o botão de som não aparece).

Depois de publicar, teste a prévia do link em https://developers.facebook.com/tools/debug/
(clique em "Coletar novamente" para o WhatsApp atualizar a imagem).

## Pendências (preencher)

- **Formação** em `index.html`, seção "Sobre" — há um comentário `PREENCHER` com o local exato.
- **E-mail profissional**: trocar `joaopedrogomes2322@gmail.com` por um endereço do domínio
  (ex.: `contato@joaopedrogomesadvhacker.adv.br`) em `index.html` (rodapé e JSON-LD) e `privacidade.html`.
- **Fotos**: `assets/img/joao-estudio.webp` foi recortada de uma captura de tela; o arquivo original
  do fotógrafo terá mais qualidade. `joao-noite.webp` veio de uma captura de tela (540 px) — o original deixa a foto mais nítida.

## Testar localmente

```
python3 -m http.server 8000
```
e abra http://localhost:8000 (abrir o arquivo direto pelo navegador bloqueia as fontes).
