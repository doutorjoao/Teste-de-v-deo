// Gera a capa de destaque "Site" do Instagram. Uso: node tools/gerar_capa_destaque.js <pasta de saída>
const { chromium } = require('playwright');
const out = process.argv[2];
const AMBER = '#e09a3a';
// ícone em linha: janela de navegador + globo + cursor (mesma espessura do ícone "Rede Social")
const icon = (cx, cy) => `
<g transform="translate(${cx},${cy}) scale(1.16) translate(-262,-235)" fill="none" stroke="${AMBER}" stroke-width="15" stroke-linecap="round" stroke-linejoin="round">
  <rect x="20" y="20" width="500" height="370" rx="34"/>
  <path d="M20 96H520"/>
  <circle cx="70" cy="58" r="9" fill="${AMBER}" stroke="none"/><circle cx="104" cy="58" r="9" fill="${AMBER}" stroke="none"/><circle cx="138" cy="58" r="9" fill="${AMBER}" stroke="none"/>
  <rect x="190" y="44" width="290" height="28" rx="14" stroke-width="10"/>
  <circle cx="270" cy="243" r="104"/>
  <path d="M166 243H374"/>
  <path d="M270 139c-34 30-50 66-50 104s16 74 50 104"/>
  <path d="M270 139c34 30 50 66 50 104s-16 74-50 104"/>
  <path d="M184 190h172M184 296h172" stroke-width="10"/>
  <path d="M398 300l-6 160 44-42 30 64 30-14-30-64 62-4z" fill="#0b0a07" stroke-width="13"/>
</g>`;
const svg = (w, h) => `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}">
  <rect width="${w}" height="${h}" fill="#0b0a07"/>
  <circle cx="${w / 2}" cy="${h / 2}" r="448" fill="none" stroke="${AMBER}" stroke-width="30"/>
  ${icon(w / 2, h / 2)}
</svg>`;
(async () => {
  const b = await chromium.launch(); const p = await b.newPage();
  for (const [name, w, h] of [['capa-destaque-site-1080x1080', 1080, 1080], ['capa-destaque-site-1080x1920', 1080, 1920]]) {
    await p.setViewportSize({ width: w, height: h });
    await p.setContent(`<style>html,body{margin:0;background:#0b0a07}</style>${svg(w, h)}`);
    await p.screenshot({ path: `${out}/${name}.png` });
  }
  await b.close();
})();
