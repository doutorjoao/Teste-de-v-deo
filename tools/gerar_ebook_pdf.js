// Pagina o e-book e imprime o PDF.
// Uso: node tools/gerar_ebook_pdf.js <url de ebook/ebook.html> <saída.pdf> [pasta para prévias PNG]
// (sirva a raiz do repositório por HTTP, para as fontes carregarem: python3 -m http.server 8770)
const { chromium } = require('playwright');
const [,, url, pdfOut, pngDir] = process.argv;
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 512, height: 800 }, deviceScaleFactor: 2 });
  const errs = []; p.on('pageerror', e => errs.push(e.message)); p.on('response', r => { if (r.status() >= 400) errs.push(r.status() + ' ' + r.url()); });
  await p.goto(url); await p.evaluate(() => document.fonts.ready);
  const report = await p.evaluate(() => {
    const mk = (mod) => {
      const s = document.createElement('section'); s.className = 'page';
      s.innerHTML = `<div class="runhead"><span>Direito Digital na Prática</span><span>Módulo ${mod}</span></div><div class="inner"></div><div class="folio"></div>`;
      return s;
    };
    const over = (inner) => inner.scrollHeight > inner.clientHeight + 1;
    const oversize = [];
    document.querySelectorAll('.flow').forEach(flow => {
      const mod = flow.dataset.mod; const blocks = [...flow.children];
      let page = mk(mod); flow.before(page); let inner = page.querySelector('.inner');
      const newPage = () => { const next = mk(mod); page.after(next); page = next; inner = page.querySelector('.inner'); };
      blocks.forEach((blk, idx) => {
        // a conclusão do módulo começa em página nova se a atual já estiver na metade
        const used = () => inner.lastElementChild ? (inner.lastElementChild.getBoundingClientRect().bottom - inner.getBoundingClientRect().top) / inner.clientHeight : 0;
        if (blk.classList.contains('concl') && inner.children.length && used() > 0.5) newPage();
        inner.appendChild(blk);
        if (!over(inner)) return;
        inner.removeChild(blk);
        const carry = [];
        while (inner.lastElementChild && inner.lastElementChild.classList.contains('keep')) carry.unshift(inner.lastElementChild), inner.removeChild(inner.lastElementChild);
        // o último bloco do módulo (citação de fecho) não vai sozinho para a página seguinte
        if (idx === blocks.length - 1 && !carry.length && inner.children.length > 2) carry.unshift(inner.lastElementChild), inner.removeChild(inner.lastElementChild);
        newPage();
        carry.forEach(c => inner.appendChild(c)); inner.appendChild(blk);
        if (over(inner)) oversize.push(blk.textContent.slice(0, 40));
      });
      flow.remove();
    });
    const pages = [...document.querySelectorAll('.page')];
    pages.forEach((pg, i) => { const f = pg.querySelector('.folio'); if (f && i > 0) f.textContent = i + 1; });
    document.querySelectorAll('.toc .pg').forEach(el => {
      const op = document.querySelector(`[data-mod-start="${el.dataset.mod}"]`); el.textContent = pages.indexOf(op) + 1;
    });
    // páginas quase vazias (sinal de quebra ruim)
    const sparse = pages.map((pg, i) => { const inn = pg.querySelector('.inner'); if (!inn || !inn.lastElementChild) return null; const used = inn.lastElementChild.getBoundingClientRect().bottom - inn.getBoundingClientRect().top; return used / inn.clientHeight < 0.45 ? `${i + 1}(${Math.round(used / inn.clientHeight * 100)}%)` : null; }).filter(Boolean);
    return { pages: pages.length, oversize, sparse };
  });
  await p.pdf({ path: pdfOut, printBackground: true, preferCSSPageSize: true });
  if (pngDir) { const ps = await p.$$('.page'); for (let i = 0; i < ps.length; i++) await ps[i].screenshot({ path: `${pngDir}/pg-${String(i + 1).padStart(2, '0')}.png` }); }
  console.log(JSON.stringify(report), 'erros:', errs.length ? errs : 'nenhum');
  await b.close();
})();
