// Gera o carrossel do Instagram (1080x1350) sobre o e-book.
// Uso: node tools/gerar_post_ebook.js <pasta com pg-XX.png do e-book> <pasta de saída>
// Requer a raiz do repositório servida em http://127.0.0.1:8770 (fontes).
const { chromium } = require('playwright');
const fs = require('fs');
const [,, pages, out] = process.argv;
const img = n => 'data:image/png;base64,' + fs.readFileSync(`${pages}/pg-${n}.png`).toString('base64');
const grain = 'data:image/png;base64,' + fs.readFileSync(__dirname + '/../site/assets/img/grain.png').toString('base64');
const css = `
@font-face{font-family:CG;font-weight:500;src:url(/site/assets/fonts/cormorant-garamond-latin-500-normal.woff2)}
@font-face{font-family:CG;font-weight:500;font-style:italic;src:url(/site/assets/fonts/cormorant-garamond-latin-500-italic.woff2)}
@font-face{font-family:CG;font-weight:600;src:url(/site/assets/fonts/cormorant-garamond-latin-600-normal.woff2)}
@font-face{font-family:CZ;font-weight:500;src:url(/site/assets/fonts/cinzel-latin-500-normal.woff2)}
@font-face{font-family:IN;font-weight:400;src:url(/site/assets/fonts/inter-latin-400-normal.woff2)}
@font-face{font-family:IN;font-weight:500;src:url(/site/assets/fonts/inter-latin-500-normal.woff2)}
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:1080px;height:1350px;background:#0a0a0b}
.s{position:relative;width:1080px;height:1350px;overflow:hidden;color:#f2ede3;font-family:IN;
 background:radial-gradient(800px 600px at 72% 58%,rgba(201,165,92,.20),transparent 65%),radial-gradient(700px 500px at 0% 0%,rgba(201,165,92,.09),transparent 70%),#0a0a0b}
.s::after{content:"";position:absolute;inset:0;background-image:url(${grain});opacity:.35;mix-blend-mode:overlay}
.light{background:radial-gradient(700px 500px at 100% 0%,rgba(201,165,92,.22),transparent 70%),#f3eee3;color:#1c1a16}
.frame{position:absolute;inset:28px;border:1px solid rgba(201,165,92,.35);pointer-events:none}
.top{position:absolute;top:64px;left:80px;right:80px;display:flex;justify-content:space-between;align-items:center;font-family:CZ;font-size:20px;letter-spacing:.24em;color:#c9a55c}
.top .pg{font-family:CG;font-size:30px;letter-spacing:0}
.eyebrow{font-family:CZ;font-size:22px;letter-spacing:.26em;color:#c9a55c;display:flex;align-items:center;gap:18px;margin-bottom:26px}
.eyebrow::before{content:"";width:46px;height:1px;background:currentColor}
.light .eyebrow{color:#8e6a2f}
h1,h2{font-family:CG;font-weight:500;line-height:1.02;letter-spacing:-1px}
.gold{font-style:italic;background:linear-gradient(100deg,#9a7536,#e9d29a 38%,#c9a55c 58%,#f1dfae 76%,#9a7536);-webkit-background-clip:text;background-clip:text;color:transparent;padding-right:6px}
.light .gold{background:linear-gradient(100deg,#6e5220,#b08a45 50%,#6e5220);-webkit-background-clip:text;background-clip:text}
.book{position:absolute;box-shadow:30px 40px 70px rgba(0,0,0,.75),0 0 0 1px rgba(201,165,92,.5)}
.book img{display:block;width:100%}
.handle{position:absolute;bottom:62px;left:80px;right:80px;display:flex;justify-content:space-between;font-family:CZ;font-size:19px;letter-spacing:.2em;color:#c9a55c}
.light .handle{color:#8e6a2f}
.swipe{display:flex;align-items:center;gap:12px}
.list{list-style:none}
.list li{display:grid;grid-template-columns:90px 1fr;gap:10px;padding:26px 0;border-top:1px solid rgba(142,106,47,.35)}
.list li:last-child{border-bottom:1px solid rgba(142,106,47,.35)}
.list .n{font-family:CG;font-style:italic;font-size:54px;line-height:.9;color:#8e6a2f}
.list b{display:block;font-family:CG;font-weight:600;font-size:36px;line-height:1.1}
.list small{display:block;margin-top:6px;font-size:22px;line-height:1.4;color:#5d574b}
.chip{display:inline-block;padding:12px 22px;border:1px solid rgba(201,165,92,.55);border-radius:99px;font-size:24px;color:#ead39b;margin:0 10px 14px 0}
.cta{display:inline-flex;align-items:center;gap:14px;padding:26px 42px;background:linear-gradient(180deg,#e2c482,#c9a55c 55%,#b48d48);color:#14110b;font-size:30px;font-weight:500;border-radius:4px;box-shadow:0 20px 50px -14px rgba(201,165,92,.6)}
`;
const logo = `<svg viewBox="0 0 100 116" style="width:48px;height:56px"><defs><linearGradient id="g1" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#8e6a2f"/><stop offset=".45" stop-color="#ead39b"/><stop offset="1" stop-color="#a67f3b"/></linearGradient></defs><path d="M50 2 97 29v58l-47 27L3 87V29z" fill="none" stroke="url(#g1)" stroke-width="3"/><path d="M50 10 90 33v50l-40 23-40-23V33z" fill="none" stroke="url(#g1)" stroke-width="1.2"/><text x="50" y="75" text-anchor="middle" font-family="CG" font-weight="600" font-size="50" fill="#d9bb78" letter-spacing="-2">JP</text></svg>`;
const top = (n, light) => `<div class="top"><span style="display:flex;align-items:center;gap:16px">${logo}E-BOOK</span><span class="pg">${n} / 5</span></div>`;
const hand = (t) => `<div class="handle"><span>@ADVOGADOOHACKER</span><span class="swipe">${t}</span></div>`;

const slides = [
// 1 — capa / gancho
`<div class="s"><div class="frame"></div>${top(1)}
 <div style="position:absolute;left:80px;top:210px;width:500px">
  <p class="eyebrow">Para advogados</p>
  <h1 style="font-size:104px">Direito Digital<br>não é só <span class="gold">LGPD.</span></h1>
  <p style="margin-top:34px;font-size:29px;line-height:1.5;color:#cfc6b4">É vazamento íntimo, perfil falso, golpe via Pix, conta banida e plataforma que não remove conteúdo.</p>
 </div>
 <div class="book" style="width:370px;right:74px;top:500px;transform:rotate(4deg)"><img src="${img('01')}"></div>
 ${hand('ARRASTE →')}</div>`,
// 2 — o que tem dentro
`<div class="s light"><div class="frame"></div>${top(2, 1)}
 <div style="position:absolute;left:80px;right:80px;top:180px">
  <p class="eyebrow">O que você vai encontrar</p>
  <h2 style="font-size:76px;margin-bottom:34px">5 módulos, <span class="gold">da teoria à atuação.</span></h2>
  <ul class="list">
   <li><span class="n">01</span><span><b>O que é Direito Digital na prática</b><small>E o que ele não é.</small></span></li>
   <li><span class="n">02</span><span><b>Como advogados estão atuando hoje</b><small>Áreas de alta demanda e modelos de honorários.</small></span></li>
   <li><span class="n">03</span><span><b>Petições que funcionam no digital</b><small>Fatos, fundamentos, provas e produção antecipada.</small></span></li>
   <li><span class="n">04</span><span><b>Como responsabilizar plataformas</b><small>Instagram, Google, TikTok e OnlyFans.</small></span></li>
   <li><span class="n">05</span><span><b>Publicidade e captação com ética</b><small>O que o Provimento 205/2021 permite.</small></span></li>
  </ul>
 </div>
 ${hand('ARRASTE →')}</div>`,
// 3 — por dentro (páginas reais)
`<div class="s"><div class="frame"></div>${top(3)}
 <div style="position:absolute;left:80px;right:80px;top:180px">
  <p class="eyebrow">Por dentro do e-book</p>
  <h2 style="font-size:78px">Casos reais, modelos de <span class="gold">fundamentação</span> e passo a passo.</h2>
 </div>
 <div class="book" style="width:330px;left:96px;top:600px;transform:rotate(-6deg)"><img src="${img('11')}"></div>
 <div class="book" style="width:330px;left:375px;top:560px;transform:rotate(1deg);z-index:2"><img src="${img('24')}"></div>
 <div class="book" style="width:330px;left:654px;top:600px;transform:rotate(7deg)"><img src="${img('07')}"></div>
 ${hand('ARRASTE →')}</div>`,
// 4 — para quem é
`<div class="s"><div class="frame"></div>${top(4)}
 <div style="position:absolute;left:80px;right:80px;top:300px">
  <p class="eyebrow">Para quem é</p>
  <h2 style="font-size:84px;margin-bottom:46px">Para quem quer atuar com <span class="gold">método, prova e ética.</span></h2>
  <div><span class="chip">Advogados iniciando no Direito Digital</span><span class="chip">Quem já atua e quer estruturar petições</span><span class="chip">Estudantes de Direito</span><span class="chip">Quem atende criadores de conteúdo</span></div>
  <p style="margin-top:44px;font-size:30px;line-height:1.55;color:#cfc6b4;max-width:860px">Escrito a partir da prática em casos de remoção de conteúdo, quebra de sigilo de dados, golpes digitais e responsabilização de plataformas.</p>
 </div>
 ${hand('ARRASTE →')}</div>`,
// 5 — CTA
`<div class="s"><div class="frame"></div>${top(5)}
 <div class="book" style="width:420px;left:330px;top:160px"><img src="${img('01')}"></div>
 <div style="position:absolute;left:80px;right:80px;top:880px;text-align:center">
  <h2 style="font-size:72px;margin-bottom:22px">Direito Digital <span class="gold">na Prática</span></h2>
  <p style="font-size:28px;color:#cfc6b4;margin-bottom:38px">E-book em PDF · 56 páginas · acesso imediato</p>
  <span class="cta">Link na bio →</span>
 </div>
 <div class="handle" style="justify-content:center;gap:40px"><span>JOÃO PEDRO GOMES · OAB/SE 17.295</span></div></div>`,
];
(async () => {
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1080, height: 1350 } });
  await p.goto('http://127.0.0.1:8770/site/privacidade.html');
  for (let i = 0; i < slides.length; i++) {
    await p.setContent(`<style>${css}</style>${slides[i]}`);
    await p.evaluate(() => document.fonts.ready); await p.waitForTimeout(400);
    await p.screenshot({ path: `${out}/post-ebook-${i + 1}.png` });
  }
  await b.close();
})();
