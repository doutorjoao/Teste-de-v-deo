// Gera as imagens de stories (1080x1920). Uso: node tools/gerar_stories.js <pasta com site-hero.png e site-quiz.png>
// Requer o site servido em http://127.0.0.1:8765 (para as fontes): cd site && python3 -m http.server 8765
const { chromium } = require('playwright');
const fs = require('fs');
const dir = process.argv[2];
const b64 = f => 'data:image/png;base64,' + fs.readFileSync(dir + '/' + f).toString('base64');
const HERO = b64('site-hero.png'), QUIZ = b64('site-quiz.png');
const grain = 'data:image/png;base64,' + fs.readFileSync('/home/user/Teste-de-v-deo/site/assets/img/grain.png').toString('base64');

const css = `
@font-face{font-family:CG;font-weight:500;src:url(/assets/fonts/cormorant-garamond-latin-500-normal.woff2)}
@font-face{font-family:CG;font-weight:500;font-style:italic;src:url(/assets/fonts/cormorant-garamond-latin-500-italic.woff2)}
@font-face{font-family:CG;font-weight:600;src:url(/assets/fonts/cormorant-garamond-latin-600-normal.woff2)}
@font-face{font-family:CZ;font-weight:500;src:url(/assets/fonts/cinzel-latin-500-normal.woff2)}
@font-face{font-family:IN;font-weight:400;src:url(/assets/fonts/inter-latin-400-normal.woff2)}
@font-face{font-family:IN;font-weight:500;src:url(/assets/fonts/inter-latin-500-normal.woff2)}
@font-face{font-family:IN;font-weight:600;src:url(/assets/fonts/inter-latin-600-normal.woff2)}
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:1080px;height:1920px;background:#0a0a0b}
.s{position:relative;width:1080px;height:1920px;overflow:hidden;color:#f2ede3;font-family:IN;
  background:radial-gradient(900px 700px at 70% 55%,rgba(201,165,92,.20),transparent 65%),radial-gradient(800px 600px at 0% 0%,rgba(201,165,92,.10),transparent 70%),radial-gradient(700px 600px at 10% 100%,rgba(60,70,90,.25),transparent 70%),#0a0a0b}
.s::before{content:"";position:absolute;inset:0;opacity:.6;background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='84' height='145' viewBox='0 0 56 97'%3E%3Cpath d='M28 1 55 16.5v31L28 63 1 47.5v-31z M28 63v34' fill='none' stroke='%23c9a55c' stroke-opacity='.07'/%3E%3C/svg%3E");-webkit-mask-image:radial-gradient(ellipse at 60% 50%,#000,transparent 75%)}
.s::after{content:"";position:absolute;inset:0;background-image:url(${grain});opacity:.35;mix-blend-mode:overlay;pointer-events:none}
.brand{position:absolute;top:215px;left:0;right:0;display:flex;justify-content:center;align-items:center;gap:22px}
.brand svg{width:64px;height:74px}
.bn{font-family:CZ;font-size:34px;letter-spacing:.1em}
.oabl{font-size:18px;letter-spacing:.16em;text-transform:uppercase;color:#aaa497;margin-top:6px}
.bs{font-size:18px;letter-spacing:.2em;text-transform:uppercase;color:#c9a55c;margin-top:4px}
.kick{position:absolute;left:0;right:0;text-align:center;font-family:CZ;font-size:26px;letter-spacing:.32em;color:#c9a55c;display:flex;justify-content:center;align-items:center;gap:22px}
.kick::before,.kick::after{content:"";width:70px;height:1px;background:#c9a55c}
h1{position:absolute;left:70px;right:70px;text-align:center;font-family:CG;font-weight:500;line-height:1;letter-spacing:-1.5px}
.gold{font-style:italic;background:linear-gradient(100deg,#9a7536,#e9d29a 38%,#c9a55c 58%,#f1dfae 76%,#9a7536);-webkit-background-clip:text;background-clip:text;color:transparent;padding-right:6px}
.phone{position:absolute;border-radius:64px;padding:16px;background:linear-gradient(160deg,#2a2a2e,#0d0d0f);box-shadow:0 0 0 2px rgba(201,165,92,.45),0 60px 120px -30px rgba(0,0,0,.95),0 0 120px rgba(201,165,92,.18)}
.phone .scr{border-radius:50px;overflow:hidden;background:#0a0a0b;position:relative}
.phone .scr img{display:block;width:100%}
.phone .scr.fade::after{content:"";position:absolute;inset:auto 0 0;height:30%;background:linear-gradient(transparent,rgba(10,10,11,.85))}
.chip{position:absolute;display:flex;align-items:center;gap:14px;padding:18px 26px;border-radius:99px;background:rgba(14,14,16,.92);border:1px solid rgba(201,165,92,.55);font-size:25px;font-weight:500;box-shadow:0 20px 40px -12px rgba(0,0,0,.9)}
.chip i{width:12px;height:12px;border:1.5px solid #c9a55c;transform:rotate(45deg);flex-shrink:0}
.cta{position:absolute;left:0;right:0;text-align:center}
.url{display:inline-block;padding:22px 40px;border-radius:4px;background:linear-gradient(180deg,#e2c482,#c9a55c 55%,#b48d48);color:#14110b;font-size:30px;font-weight:600;letter-spacing:.01em;box-shadow:0 20px 50px -14px rgba(201,165,92,.6)}
.hint{margin-top:22px;font-size:24px;letter-spacing:.18em;text-transform:uppercase;color:#aaa497}
.circ{position:absolute;overflow:visible}
.circ path{fill:none;stroke:#c9a55c;stroke-width:2;opacity:.8}
.circ circle{fill:#0a0a0b;stroke:#c9a55c;stroke-width:2}
.oab{position:absolute;left:0;right:0;bottom:250px;text-align:center;font-size:20px;letter-spacing:.2em;color:#7d786d;text-transform:uppercase}
`;
const logo = `<svg viewBox="0 0 100 116"><defs><linearGradient id="g1" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#8e6a2f"/><stop offset=".45" stop-color="#ead39b"/><stop offset="1" stop-color="#a67f3b"/></linearGradient><linearGradient id="g2" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#f1dfae"/><stop offset=".55" stop-color="#c9a55c"/><stop offset="1" stop-color="#8e6a2f"/></linearGradient></defs><path d="M50 2 97 29v58l-47 27L3 87V29z" fill="none" stroke="url(#g1)" stroke-width="3"/><path d="M50 10 90 33v50l-40 23-40-23V33z" fill="none" stroke="url(#g1)" stroke-width="1.2"/><text x="50" y="75" text-anchor="middle" font-family="CG" font-weight="600" font-size="50" fill="url(#g2)" letter-spacing="-2">JP</text></svg>`;
const brand = `<div class="brand">${logo}<div><div class="bn">João Pedro Gomes</div><div class="bs">Direito Digital · Crimes Cibernéticos</div><div class="oabl">Advogado · OAB/SE 17.295</div></div></div>`;
const circuits = (y) => `<svg class="circ" style="left:0;top:${y}px" width="1080" height="420" viewBox="0 0 1080 420">
  <path d="M290 120H200l-30-30H60"/><circle cx="54" cy="90" r="7"/><path d="M290 170H90"/><circle cx="84" cy="170" r="7"/><path d="M290 220H210l-30 30H80"/><circle cx="74" cy="250" r="7"/>
  <path d="M790 140h90l30-30h110"/><circle cx="1026" cy="110" r="7"/><path d="M790 190h200"/><circle cx="996" cy="190" r="7"/><path d="M790 240h80l30 30h100"/><circle cx="1006" cy="270" r="7"/></svg>`;

const story1 = `<div class="s">${brand}
  <div class="kick" style="top:400px">Novo site no ar</div>
  <h1 style="top:468px;font-size:100px">Sua vida é digital.<br>Sua defesa precisa<br>ser <span class="gold">estratégica.</span></h1>
  ${circuits(900)}
  <div class="phone" style="left:305px;top:830px;width:470px;transform:rotate(-3deg)"><div class="scr fade" style="height:650px"><img src="${HERO}"></div></div>
  <div class="chip" style="left:70px;top:930px"><i></i>Teste: isso é golpe?</div>
  <div class="chip" style="right:60px;top:1110px"><i></i>Golpes do momento</div>
  <div class="chip" style="left:90px;top:1300px"><i></i>Triagem em 3 passos</div>
  <div class="cta" style="top:1575px"><span class="url">joaopedrogomesadvhacker.adv.br</span><p class="hint">Toque no link e conheça</p></div>
</div>`;

const story2 = `<div class="s">${brand}
  <div class="kick" style="top:400px">Teste rápido</div>
  <h1 style="top:462px;font-size:112px">Você sabe<br>identificar um <span class="gold">golpe?</span></h1>
  ${circuits(880)}
  <div class="phone" style="left:305px;top:745px;width:470px;transform:rotate(3deg)"><div class="scr"><img src="${QUIZ}"></div></div>
  <div class="chip" style="left:60px;top:960px"><i></i>7 mensagens</div>
  <div class="chip" style="right:50px;top:1215px"><i></i>Golpe ou seguro?</div>
  <div class="cta" style="top:1590px"><span class="url">Faça o teste no meu site</span><p class="hint">Toque no link · leva 1 minuto</p></div>
</div>`;

(async () => {
  const br = await chromium.launch(); const p = await br.newPage({ viewport: { width: 1080, height: 1920 } });
  await p.goto('http://127.0.0.1:8765/privacidade.html');
  for (const [name, html] of [['story-1-novo-site', story1], ['story-2-teste-golpe', story2]]) {
    await p.setContent(`<style>${css}</style>${html}`);
    await p.evaluate(() => document.fonts.ready); await p.waitForTimeout(500);
    await p.screenshot({ path: `${dir}/${name}.png` });
  }
  await br.close();
})();
