/* João Pedro Gomes — interações do site (sem bibliotecas externas) */
(function () {
  'use strict';

  var WPP = '5579999100875';
  var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var root = document.documentElement;
  var $ = function (s, c) { return (c || document).querySelector(s); };
  var $$ = function (s, c) { return Array.prototype.slice.call((c || document).querySelectorAll(s)); };
  var wppLink = function (text) { return 'https://wa.me/' + WPP + '?text=' + encodeURIComponent(text); };

  /* ---------- Entrada da página ---------- */
  // com a abertura ativa, a entrada do topo espera a logo terminar
  setTimeout(function () {
    requestAnimationFrame(function () { document.body.classList.add('is-loaded'); });
  }, root.classList.contains('has-intro') ? 1850 : 0);

  /* ---------- Ano no rodapé ---------- */
  $$('[data-year]').forEach(function (el) { el.textContent = new Date().getFullYear(); });

  /* ---------- Mensagem padrão nos links de WhatsApp ---------- */
  $$('[data-wpp="geral"]').forEach(function (a) {
    a.href = wppLink('Olá, Dr. João Pedro. Acessei seu site e gostaria de uma análise jurídica sobre um caso digital.');
  });

  /* ---------- Cabeçalho: compacta ao rolar ---------- */
  var header = $('.site-header');
  var mobileBar = $('.mobile-bar');
  var hero = $('.hero');
  function onScroll() {
    var y = window.scrollY;
    if (header) header.classList.toggle('is-scrolled', y > 30);
    document.body.classList.toggle('is-scrolled', y > 30);
    if (mobileBar) {
      var limit = hero ? hero.offsetHeight * 0.6 : 300;
      mobileBar.classList.toggle('is-visible', y > limit);
    }
  }
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();

  /* ---------- Menu do celular ---------- */
  var menuBtn = $('.menu-btn');
  var mobileNav = $('#mobileNav');
  function setMenu(open) {
    if (!menuBtn || !mobileNav) return;
    menuBtn.setAttribute('aria-expanded', String(open));
    menuBtn.setAttribute('aria-label', open ? 'Fechar menu' : 'Abrir menu');
    mobileNav.classList.toggle('is-open', open);
    document.body.style.overflow = open ? 'hidden' : '';
  }
  if (menuBtn) {
    menuBtn.addEventListener('click', function () { setMenu(menuBtn.getAttribute('aria-expanded') !== 'true'); });
    $$('a', mobileNav).forEach(function (a) { a.addEventListener('click', function () { setMenu(false); }); });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') setMenu(false); });
  }

  /* ---------- Revelação ao rolar ---------- */
  var reveals = $$('.reveal');
  if ('IntersectionObserver' in window && !reduceMotion) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) { en.target.classList.add('is-in'); io.unobserve(en.target); }
      });
    }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });
    reveals.forEach(function (el) { io.observe(el); });
  } else {
    reveals.forEach(function (el) { el.classList.add('is-in'); });
  }

  /* ---------- Menu: item ativo conforme a seção ---------- */
  var navLinks = $$('.main-nav a');
  if ('IntersectionObserver' in window && navLinks.length) {
    var navIO = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (!en.isIntersecting) return;
        navLinks.forEach(function (a) {
          if (a.getAttribute('href') === '#' + en.target.id) a.setAttribute('aria-current', 'true');
          else a.removeAttribute('aria-current');
        });
      });
    }, { rootMargin: '-45% 0px -50% 0px' });
    $$('main section[id]').forEach(function (s) { navIO.observe(s); });
  }

  /* ---------- Hero: brilho que segue o cursor ---------- */
  var heroBg = $('.hero-bg');
  if (hero && heroBg && !reduceMotion && window.matchMedia('(pointer: fine)').matches) {
    var raf = 0;
    hero.addEventListener('pointermove', function (e) {
      if (raf) return;
      raf = requestAnimationFrame(function () {
        var r = hero.getBoundingClientRect();
        heroBg.style.setProperty('--px', ((e.clientX - r.left) / r.width * 100).toFixed(1) + '%');
        heroBg.style.setProperty('--py', ((e.clientY - r.top) / r.height * 100).toFixed(1) + '%');
        raf = 0;
      });
    });
  }

  /* ---------- Hero: frases alternadas ---------- */
  var rot = $('.rotator');
  if (rot && !reduceMotion) {
    var words = $$('span', rot);
    var idx = 0;
    setInterval(function () {
      if (document.hidden) return;
      var cur = words[idx];
      idx = (idx + 1) % words.length;
      var next = words[idx];
      cur.classList.remove('is-active');
      cur.classList.add('is-leaving');
      next.classList.add('is-active');
      setTimeout(function () { cur.classList.remove('is-leaving'); }, 650);
    }, 2600);
  }

  /* ---------- Circuitos do hero: comprimento real de cada traço ---------- */
  $$('.circuit .trace').forEach(function (p) {
    try { p.style.setProperty('--len', Math.ceil(p.getTotalLength()) + 1); } catch (e) {}
  });
  if (reduceMotion) { var svg = $('.circuit'); if (svg && svg.pauseAnimations) svg.pauseAnimations(); }

  /* ---------- Holofote que segue o cursor nos cards ---------- */
  $$('.area, [data-spot]').forEach(function (card) {
    card.addEventListener('pointermove', function (e) {
      var r = card.getBoundingClientRect();
      card.style.setProperty('--mx', (e.clientX - r.left) + 'px');
      card.style.setProperty('--my', (e.clientY - r.top) + 'px');
    });
  });

  /* ---------- Linha do tempo (abas com avanço automático) ---------- */
  var tl = $('[data-timeline]');
  if (tl) {
    var tabs = $$('[role="tab"]', tl);
    var panels = $$('[role="tabpanel"]', tl);
    var progress = $('.tl-progress', tl);
    var current = 0, timer = null, userTook = false;

    function selectTab(i, focus) {
      current = i;
      tabs.forEach(function (t, k) {
        var on = k === i;
        t.setAttribute('aria-selected', String(on));
        t.tabIndex = on ? 0 : -1;
        t.classList.toggle('is-past', k < i);
        panels[k].hidden = !on;
        if (on) { panels[k].classList.remove('is-entering'); void panels[k].offsetWidth; panels[k].classList.add('is-entering'); }
      });
      if (progress) {
        var rail = progress.parentElement;
        var first = tabs[0].offsetLeft + tabs[0].offsetWidth / 2;
        var here = tabs[i].offsetLeft + tabs[i].offsetWidth / 2;
        progress.style.left = first + 'px';
        progress.style.width = (here - first) + 'px';
        if (rail.scrollWidth > rail.clientWidth) {
          rail.scrollTo({ left: here - rail.clientWidth / 2, behavior: reduceMotion ? 'auto' : 'smooth' });
        }
      }
      if (focus) tabs[i].focus();
    }
    function stopAuto() { userTook = true; clearInterval(timer); timer = null; }
    tabs.forEach(function (t, i) {
      t.addEventListener('click', function () { stopAuto(); selectTab(i); });
      t.addEventListener('keydown', function (e) {
        var n = null;
        if (e.key === 'ArrowRight') n = (i + 1) % tabs.length;
        if (e.key === 'ArrowLeft') n = (i - 1 + tabs.length) % tabs.length;
        if (e.key === 'Home') n = 0;
        if (e.key === 'End') n = tabs.length - 1;
        if (n !== null) { e.preventDefault(); stopAuto(); selectTab(n, true); }
      });
    });
    selectTab(0);
    window.addEventListener('resize', function () { selectTab(current); });
    // avança sozinha enquanto está visível e ninguém interagiu
    if (!reduceMotion && 'IntersectionObserver' in window) {
      new IntersectionObserver(function (entries) {
        entries.forEach(function (en) {
          if (en.isIntersecting && !userTook && !timer) {
            timer = setInterval(function () { selectTab((current + 1) % tabs.length); }, 5200);
          } else if (!en.isIntersecting && timer) { clearInterval(timer); timer = null; }
        });
      }, { threshold: 0.5 }).observe(tl);
    }
  }

  /* ---------- Método: dossiê acompanha a leitura ---------- */
  var steps = $$('.m-step');
  var rows = $$('.dossier-row');
  var rail = $('.method-rail i');
  var stepsBox = $('.method-steps');
  function updateMethod() {
    if (!stepsBox) return;
    var mid = window.innerHeight * 0.55;
    var active = -1;
    steps.forEach(function (s, i) { if (s.getBoundingClientRect().top < mid) active = i; });
    steps.forEach(function (s, i) { s.classList.toggle('is-current', i === active); s.classList.toggle('is-done', i < active); });
    rows.forEach(function (r, i) { r.classList.toggle('is-current', i === active); r.classList.toggle('is-done', i < active || (active === rows.length - 1 && i === active)); });
    if (rail) {
      var b = stepsBox.getBoundingClientRect();
      var pct = Math.min(1, Math.max(0, (mid - b.top) / b.height));
      rail.style.setProperty('--fill', (pct * 100).toFixed(1) + '%');
    }
  }
  if (steps.length) { window.addEventListener('scroll', updateMethod, { passive: true }); updateMethod(); }

  /* ---------- Som ambiente ----------
     Desligado por padrão (os navegadores bloqueiam som automático).
     Entrada e saída suaves, pausa ao trocar de aba e lembra a escolha entre páginas. */
  var audio = $('#ambient');
  var soundBtn = $('.sound-toggle');
  if (audio && soundBtn) {
    var KEY = 'jp-som';
    var VOLUME = 0.6; // o arquivo já foi masterizado em volume suave
    var fadeRaf = 0, resumeOnVisible = false;
    var getPref = function () { try { return localStorage.getItem(KEY); } catch (e) { return null; } };
    var setPref = function (v) { try { localStorage.setItem(KEY, v); } catch (e) {} };
    var stateEl = $('.state', soundBtn);

    var fade = function (to, ms, done) {
      cancelAnimationFrame(fadeRaf);
      var from = audio.volume, t0 = performance.now();
      var step = function (now) {
        var k = Math.min(1, (now - t0) / ms);
        try { audio.volume = from + (to - from) * k; } catch (e) {}
        if (k < 1) fadeRaf = requestAnimationFrame(step); else if (done) done();
      };
      fadeRaf = requestAnimationFrame(step);
    };
    var ui = function (on) {
      soundBtn.setAttribute('aria-pressed', String(on));
      soundBtn.setAttribute('aria-label', on ? 'Desativar som ambiente' : 'Ativar som ambiente');
      if (stateEl) stateEl.textContent = on ? 'ligado' : 'desligado';
    };
    var start = function () {
      try { audio.volume = 0; } catch (e) {}
      var pr = audio.play();
      ui(true);
      if (pr && pr.then) pr.then(function () { fade(VOLUME, 1800); }, function () { ui(false); });
      else fade(VOLUME, 1800);
    };
    var stop = function () {
      ui(false);
      fade(0, 700, function () { audio.pause(); });
    };

    soundBtn.addEventListener('click', function () {
      if (soundBtn.getAttribute('aria-pressed') === 'true') { setPref('off'); stop(); }
      else { setPref('on'); start(); }
    });

    // o botão só aparece se o arquivo de áudio existir
    var ready = function () { soundBtn.classList.add('is-ready'); };
    if (audio.readyState >= 1) ready(); else audio.addEventListener('loadedmetadata', ready, { once: true });
    audio.addEventListener('error', function () { soundBtn.remove(); });

    // pausa quando a pessoa troca de aba ou abre o WhatsApp
    document.addEventListener('visibilitychange', function () {
      if (document.hidden) {
        if (!audio.paused) { resumeOnVisible = true; audio.pause(); }
      } else if (resumeOnVisible) { resumeOnVisible = false; start(); }
    });

    // quem ligou o som numa página continua ouvindo ao navegar (a partir do primeiro toque)
    if (getPref() === 'on') {
      var resume = function (e) {
        document.removeEventListener('pointerdown', resume, true);
        document.removeEventListener('keydown', resume, true);
        if (e.target && e.target.closest && e.target.closest('.sound-toggle')) return;
        if (audio.paused) start();
      };
      document.addEventListener('pointerdown', resume, true);
      document.addEventListener('keydown', resume, true);
    }
  }

  /* ---------- Triagem ---------- */
  var triage = $('[data-triage]');
  var DATA = {
    incident: {
      conta: { label: 'Conta invadida ou suspensa', tips: [
        'Faça capturas de tela do perfil, das mensagens enviadas em seu nome e dos e-mails de alteração de senha ou de e-mail, com data e link visíveis.',
        'Use os canais oficiais de recuperação da plataforma e anote os números de protocolo.',
        'Avise seus contatos por outro meio que a conta pode estar sendo usada por terceiros.',
        'Desconfie de “recuperadores de contas” que cobram para devolver o acesso: é um golpe comum.'
      ] },
      golpe: { label: 'Golpe, Pix ou fraude bancária', tips: [
        'Comunique o banco imediatamente pelos canais oficiais e peça a abertura do MED (Mecanismo Especial de Devolução do Pix).',
        'Registre um boletim de ocorrência. Em muitos estados, ele pode ser feito pela internet.',
        'Guarde comprovantes, conversas, números de telefone e chaves Pix envolvidas.',
        'Não apague as conversas com quem aplicou o golpe.'
      ] },
      sistemas: { label: 'Ataque a sistemas ou dispositivos', tips: [
        'Se possível, isole o equipamento afetado da rede, sem desligá-lo nem formatá-lo.',
        'Preserve logs, alertas de segurança, e-mails suspeitos e mensagens de resgate.',
        'Anote horários e tudo o que foi observado, na ordem em que aconteceu.',
        'Se houver dados pessoais de terceiros envolvidos, avalie o dever de comunicação à ANPD e aos titulares (LGPD, art. 48).'
      ] },
      dados: { label: 'Vazamento de dados / LGPD', tips: [
        'Identifique quais dados foram expostos e onde (site, grupo, fórum ou aplicativo).',
        'Registre os links e faça capturas de tela com data.',
        'Troque as senhas afetadas e ative a verificação em duas etapas.',
        'Empresas: o incidente pode exigir comunicação à ANPD e aos titulares dos dados.'
      ] },
      criador: { label: 'Questão de criador de conteúdo', tips: [
        'Reúna contratos, propostas, briefings e conversas com marcas ou agências.',
        'Separe as entregas, métricas e pagamentos ligados ao conflito.',
        'Evite se manifestar publicamente sobre o caso antes de uma orientação jurídica.'
      ] },
      anonimo: { label: 'Perfil falso ou autor anônimo', tips: [
        'Salve os links (URLs) do perfil e das publicações, além de capturas com data.',
        'Preserve as provas antes de denunciar o perfil: se ele for removido, o conteúdo pode se perder.',
        'Não interaja com o perfil nem tente identificá-lo por conta própria.',
        'Os registros de acesso costumam ser guardados por 6 meses (Marco Civil, art. 15). Agir cedo faz diferença.'
      ] },
      honra: { label: 'Ofensas, calúnia ou difamação', tips: [
        'Capture a publicação, os comentários e o perfil do autor, com data e link visíveis.',
        'Não responda nem revide publicamente.',
        'Anote quem viu ou compartilhou a publicação (possíveis testemunhas).',
        'Atenção ao prazo: a queixa-crime deve ser apresentada em até 6 meses de quando se descobre o autor (Código Penal, art. 103).'
      ] },
      remocao: { label: 'Conteúdo que precisa ser removido', tips: [
        'Preserve o conteúdo antes de pedir a remoção (capturas de tela e links).',
        'Use a denúncia da própria plataforma e guarde o protocolo.',
        'Conteúdo íntimo divulgado sem autorização deve ser removido após notificação da vítima à plataforma, sem necessidade de ordem judicial (Marco Civil, art. 21).'
      ] }
    },
    time: {
      h24: { label: 'Nas últimas 24 horas', note: 'Você está no momento mais favorável para preservar provas. Priorize as orientações abaixo.' },
      d7: { label: 'Entre 1 e 7 dias', note: 'Ainda é um bom momento para preservar registros e definir as primeiras medidas.' },
      m6: { label: 'Entre 1 semana e 6 meses', note: 'Alguns registros têm prazo de guarda limitado. Não adie a análise do caso.' },
      mais: { label: 'Há mais de 6 meses', note: 'Mesmo com mais tempo decorrido, pode haver caminhos. A análise do caso indica quais são viáveis.' }
    },
    proof: {
      sim: { label: 'Registros guardados', tip: null },
      parte: { label: 'Parte dos registros', tip: 'Complete o que faltar enquanto o conteúdo ainda está disponível: capturas com data, hora e link.' },
      nao: { label: 'Sem registros', tip: 'Comece pelas capturas de tela com data, hora e link visíveis. Em casos relevantes, a ata notarial dá mais força à prova.' }
    }
  };

  if (triage) {
    var state = { incident: null, time: null, proof: null };
    var stepEls = $$('.t-step', triage);
    var countEl = $('[data-count]', triage);
    var barEl = $('[data-bar]', triage);
    var step = 1;

    function show(n, focus) {
      step = n;
      stepEls.forEach(function (el) {
        var on = Number(el.dataset.step) === n;
        el.hidden = !on;
        if (on) { el.classList.remove('is-entering'); void el.offsetWidth; el.classList.add('is-entering'); }
      });
      $$('.opt', triage).forEach(function (o) { o.setAttribute('aria-pressed', String(state[o.dataset.q] === o.dataset.v)); });
      if (countEl) countEl.textContent = n <= 3 ? 'Etapa ' + n + ' de 3' : 'Resumo pronto';
      if (barEl) barEl.style.setProperty('--p', Math.min(100, n * 33.34) + '%');
      if (focus) { var el = $('.t-step[data-step="' + n + '"]', triage); if (el) el.focus({ preventScroll: true }); }
    }

    function buildText() {
      var i = DATA.incident[state.incident], t = DATA.time[state.time], p = DATA.proof[state.proof];
      return [
        'Olá, Dr. João Pedro. Fiz a triagem pelo site.',
        '',
        'Caso: ' + i.label,
        'Quando: ' + t.label,
        'Registros: ' + p.label,
        '',
        'Gostaria de agendar uma análise jurídica.'
      ].join('\n');
    }

    function renderResult() {
      var i = DATA.incident[state.incident], t = DATA.time[state.time], p = DATA.proof[state.proof];
      $('[data-out="incident"]', triage).textContent = i.label;
      $('[data-out="time"]', triage).textContent = t.label;
      $('[data-out="proof"]', triage).textContent = p.label;
      $('[data-out="note"]', triage).textContent = t.note;
      var list = $('[data-out="checklist"]', triage);
      list.innerHTML = '';
      var tips = i.tips.slice();
      if (p.tip) tips.unshift(p.tip);
      tips.forEach(function (tip) { var li = document.createElement('li'); li.textContent = tip; list.appendChild(li); });
      $('[data-out="wpp"]', triage).href = wppLink(buildText());
    }

    triage.addEventListener('click', function (e) {
      var opt = e.target.closest('.opt');
      if (opt) {
        state[opt.dataset.q] = opt.dataset.v;
        if (opt.dataset.q === 'incident') show(2, true);
        else if (opt.dataset.q === 'time') show(3, true);
        else { renderResult(); show(4, true); }
        return;
      }
      if (e.target.closest('[data-back]')) { show(Math.max(1, step - 1), true); return; }
      if (e.target.closest('[data-restart]')) { state = { incident: null, time: null, proof: null }; show(1, true); return; }
      var copyBtn = e.target.closest('[data-copy]');
      if (copyBtn) {
        var text = buildText();
        var done = function () { copyBtn.textContent = 'Resumo copiado ✓'; setTimeout(function () { copyBtn.textContent = 'Copiar resumo'; }, 2200); };
        if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(text).then(done, function () {});
      }
    });

    // Cards de atuação abrem a triagem já com o tipo de caso marcado
    $$('[data-incident]').forEach(function (card) {
      card.addEventListener('click', function () {
        state = { incident: card.dataset.incident, time: null, proof: null };
        show(2);
        setTimeout(function () { var el = $('.t-step[data-step="2"]', triage); if (el) el.focus({ preventScroll: true }); }, 700);
      });
    });

    show(1);
  }
  /* =========================================================
     ENFEITES
     ========================================================= */
  var finePointer = window.matchMedia('(pointer: fine) and (hover: hover)').matches;
  var pad2 = function (n) { return (n < 10 ? '0' : '') + n; };

  /* ---------- Abertura: remove a camada depois da animação ---------- */
  var introEl = $('.intro');
  if (introEl) {
    introEl.addEventListener('animationend', function (e) { if (e.target === introEl) introEl.remove(); });
    setTimeout(function () { if (introEl.parentNode) introEl.remove(); }, 4000);
  }

  /* ---------- Fio de leitura + voltar ao topo ---------- */
  var readBar = $('.read-progress i');
  var toTop = $('.to-top');
  var toTopBar = toTop ? $('.bar', toTop) : null;
  var progRaf = 0;
  function updateProgress() {
    progRaf = 0;
    var max = document.documentElement.scrollHeight - window.innerHeight;
    var p = max > 0 ? Math.min(1, Math.max(0, window.scrollY / max)) : 0;
    if (readBar) readBar.style.transform = 'scaleX(' + p.toFixed(4) + ')';
    if (toTop) {
      toTop.classList.toggle('is-visible', window.scrollY > 700);
      if (toTopBar) toTopBar.style.strokeDashoffset = (138.23 * (1 - p)).toFixed(2);
    }
  }
  window.addEventListener('scroll', function () { if (!progRaf) progRaf = requestAnimationFrame(updateProgress); }, { passive: true });
  window.addEventListener('resize', updateProgress);
  updateProgress();

  /* ---------- Rede de pontos dourados no topo ---------- */
  var net = $('.hero-bg .net');
  if (net && net.getContext && hero) {
    var nctx = net.getContext('2d');
    var pts = [], NW = 0, NH = 0, mouse = { x: -9999, y: -9999 }, netOn = false, netRaf = 0;
    var LINK = 130, MLINK = 190;
    var sizeNet = function () {
      var r = net.getBoundingClientRect(), dpr = Math.min(window.devicePixelRatio || 1, 2);
      NW = r.width; NH = r.height;
      net.width = Math.round(NW * dpr); net.height = Math.round(NH * dpr);
      nctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      var n = Math.round(Math.min(90, Math.max(28, NW * NH / 15000)));
      pts = [];
      for (var i = 0; i < n; i++) {
        pts.push({ x: Math.random() * NW, y: Math.random() * NH, vx: (Math.random() - .5) * .28, vy: (Math.random() - .5) * .28, r: Math.random() * 1.3 + .6 });
      }
    };
    var drawNet = function () {
      nctx.clearRect(0, 0, NW, NH);
      var i, j, a, b, dx, dy, d;
      for (i = 0; i < pts.length; i++) {
        a = pts[i];
        if (!reduceMotion) {
          a.x += a.vx; a.y += a.vy;
          if (a.x < 0 || a.x > NW) a.vx *= -1;
          if (a.y < 0 || a.y > NH) a.vy *= -1;
          dx = mouse.x - a.x; dy = mouse.y - a.y; d = Math.sqrt(dx * dx + dy * dy);
          if (d < MLINK && d > 1) { a.x += dx / d * .25; a.y += dy / d * .25; }
        }
      }
      nctx.lineWidth = 1;
      for (i = 0; i < pts.length; i++) {
        a = pts[i];
        for (j = i + 1; j < pts.length; j++) {
          b = pts[j]; dx = a.x - b.x; dy = a.y - b.y; d = dx * dx + dy * dy;
          if (d < LINK * LINK) {
            nctx.strokeStyle = 'rgba(201,165,92,' + ((1 - Math.sqrt(d) / LINK) * .32).toFixed(3) + ')';
            nctx.beginPath(); nctx.moveTo(a.x, a.y); nctx.lineTo(b.x, b.y); nctx.stroke();
          }
        }
        dx = a.x - mouse.x; dy = a.y - mouse.y; d = Math.sqrt(dx * dx + dy * dy);
        if (d < MLINK) {
          nctx.strokeStyle = 'rgba(234,211,155,' + ((1 - d / MLINK) * .55).toFixed(3) + ')';
          nctx.beginPath(); nctx.moveTo(a.x, a.y); nctx.lineTo(mouse.x, mouse.y); nctx.stroke();
        }
        nctx.fillStyle = 'rgba(234,211,155,.75)';
        nctx.beginPath(); nctx.arc(a.x, a.y, a.r, 0, 6.2832); nctx.fill();
      }
      if (netOn && !reduceMotion) netRaf = requestAnimationFrame(drawNet);
    };
    var setNet = function (on) {
      if (on === netOn) return;
      netOn = on;
      cancelAnimationFrame(netRaf);
      if (on) netRaf = requestAnimationFrame(drawNet);
    };
    sizeNet();
    if (reduceMotion) drawNet();
    var heroVisible = true;
    if ('IntersectionObserver' in window) {
      new IntersectionObserver(function (en) { heroVisible = en[0].isIntersecting; setNet(heroVisible && !document.hidden); }).observe(hero);
    }
    document.addEventListener('visibilitychange', function () { setNet(heroVisible && !document.hidden); });
    setNet(true);
    hero.addEventListener('pointermove', function (e) { var r = net.getBoundingClientRect(); mouse.x = e.clientX - r.left; mouse.y = e.clientY - r.top; });
    hero.addEventListener('pointerleave', function () { mouse.x = mouse.y = -9999; });
    var netResize = 0;
    window.addEventListener('resize', function () { clearTimeout(netResize); netResize = setTimeout(function () { sizeNet(); if (reduceMotion) drawNet(); }, 200); });
  }

  /* ---------- Títulos pequenos que se "decodificam" ---------- */
  if (!reduceMotion && 'IntersectionObserver' in window) {
    var GLYPHS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789#%&@';
    var decode = function (el) {
      var text = el.textContent, len = text.length, t0 = performance.now(), dur = 650 + len * 14;
      var sr = document.createElement('span'); sr.className = 'sr-only'; sr.textContent = text;
      var vis = document.createElement('span'); vis.setAttribute('aria-hidden', 'true');
      el.textContent = ''; el.appendChild(sr); el.appendChild(vis);
      var tick = function (now) {
        var k = Math.min(1, (now - t0) / dur), out = '';
        for (var i = 0; i < len; i++) {
          var c = text.charAt(i);
          out += (/[\s·\/:?]/.test(c) || i / len < k * 1.2 - .2) ? c : GLYPHS.charAt(Math.floor(Math.random() * GLYPHS.length));
        }
        vis.textContent = out;
        if (k < 1) requestAnimationFrame(tick); else el.textContent = text;
      };
      requestAnimationFrame(tick);
    };
    var decIO = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) { if (en.isIntersecting) { decIO.unobserve(en.target); decode(en.target); } });
    }, { threshold: 0.8 });
    $$('.eyebrow').forEach(function (el) { if (!el.children.length) decIO.observe(el); });
  }

  /* ---------- Cursor dourado (só mouse) ---------- */
  if (finePointer && !reduceMotion) {
    var ring = document.createElement('div'); ring.className = 'cursor-ring'; ring.setAttribute('aria-hidden', 'true');
    var dot = document.createElement('div'); dot.className = 'cursor-dot'; dot.setAttribute('aria-hidden', 'true');
    document.body.appendChild(ring); document.body.appendChild(dot);
    var cx = 0, cy = 0, rx = 0, ry = 0, cOn = false;
    var follow = function () {
      rx += (cx - rx) * .2; ry += (cy - ry) * .2;
      ring.style.transform = 'translate3d(' + rx.toFixed(1) + 'px,' + ry.toFixed(1) + 'px,0)';
      if (cOn) requestAnimationFrame(follow);
    };
    document.addEventListener('pointermove', function (e) {
      if (e.pointerType !== 'mouse') return;
      cx = e.clientX; cy = e.clientY;
      dot.style.transform = 'translate3d(' + cx + 'px,' + cy + 'px,0)';
      if (!cOn) { cOn = true; rx = cx; ry = cy; root.classList.add('cursor-on'); requestAnimationFrame(follow); }
    });
    document.documentElement.addEventListener('mouseleave', function () { cOn = false; root.classList.remove('cursor-on'); });
    document.addEventListener('pointerover', function (e) {
      ring.classList.toggle('is-hover', !!(e.target.closest && e.target.closest('a, button, summary, label, [data-tilt], .area, .golpes-track')));
    });
    document.addEventListener('pointerdown', function () { ring.classList.add('is-down'); });
    document.addEventListener('pointerup', function () { ring.classList.remove('is-down'); });
  }

  /* ---------- Cards com inclinação 3D ---------- */
  if (finePointer && !reduceMotion) {
    $$('.area, .article, [data-tilt]').forEach(function (el) {
      var leaveT = 0;
      el.addEventListener('pointermove', function (e) {
        if (e.pointerType !== 'mouse' || (el.closest('.is-dragging'))) return;
        clearTimeout(leaveT);
        var r = el.getBoundingClientRect();
        var px = (e.clientX - r.left) / r.width - .5, py = (e.clientY - r.top) / r.height - .5;
        el.style.transition = 'transform .2s ease-out';
        el.style.transform = 'perspective(900px) rotateX(' + (-py * 6).toFixed(2) + 'deg) rotateY(' + (px * 6).toFixed(2) + 'deg) translateY(-3px)';
      });
      el.addEventListener('pointerleave', function () {
        el.style.transition = 'transform .6s cubic-bezier(.2,.7,.2,1)';
        el.style.transform = '';
        leaveT = setTimeout(function () { el.style.transition = ''; }, 650);
      });
    });
  }

  /* ---------- Carrossel "Golpes do momento" ---------- */
  var track = $('[data-car-track]');
  if (track) {
    var gCards = $$('.golpe-card', track);
    var gCount = $('[data-car-count]'), gBar = $('[data-car-bar]');
    var gPrev = $('[data-car="-1"]'), gNext = $('[data-car="1"]');
    var stepW = function () { return gCards[0].getBoundingClientRect().width + 22; };
    var gRaf = 0;
    var gUpdate = function () {
      gRaf = 0;
      var max = track.scrollWidth - track.clientWidth;
      var i = Math.min(gCards.length - 1, Math.round(track.scrollLeft / stepW()));
      if (track.scrollLeft >= max - 4) i = gCards.length - 1;
      if (gCount) gCount.textContent = pad2(i + 1) + ' / ' + pad2(gCards.length);
      if (gPrev) gPrev.disabled = track.scrollLeft <= 4;
      if (gNext) gNext.disabled = track.scrollLeft >= max - 4;
      if (gBar) {
        gBar.style.width = (track.clientWidth / track.scrollWidth * 100).toFixed(2) + '%';
        gBar.style.marginLeft = (track.scrollLeft / track.scrollWidth * 100).toFixed(2) + '%';
      }
    };
    var gGo = function (dir) { track.scrollBy({ left: dir * stepW(), behavior: reduceMotion ? 'auto' : 'smooth' }); };
    [gPrev, gNext].forEach(function (b) { if (b) b.addEventListener('click', function () { gGo(Number(b.dataset.car)); }); });
    track.addEventListener('scroll', function () { if (!gRaf) gRaf = requestAnimationFrame(gUpdate); }, { passive: true });
    window.addEventListener('resize', gUpdate);
    track.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowRight') { e.preventDefault(); gGo(1); }
      if (e.key === 'ArrowLeft') { e.preventDefault(); gGo(-1); }
    });
    // arrastar com o mouse
    var dragX = 0, dragSL = 0, dragging = false, moved = false;
    track.addEventListener('pointerdown', function (e) {
      if (e.pointerType !== 'mouse' || e.button !== 0 || e.target.closest('a, button')) return;
      dragging = true; moved = false; dragX = e.clientX; dragSL = track.scrollLeft;
    });
    window.addEventListener('pointermove', function (e) {
      if (!dragging) return;
      var dx = e.clientX - dragX;
      if (!moved && Math.abs(dx) > 5) { moved = true; track.classList.add('is-dragging'); }
      if (moved) track.scrollLeft = dragSL - dx;
    });
    window.addEventListener('pointerup', function () {
      if (!dragging) return;
      dragging = false;
      if (moved) {
        track.classList.remove('is-dragging');
        var target = Math.round(track.scrollLeft / stepW()) * stepW();
        track.scrollTo({ left: target, behavior: reduceMotion ? 'auto' : 'smooth' });
      }
    });
    gUpdate();
  }

  /* ---------- Teste: isso é golpe? ---------- */
  var quiz = $('[data-quiz]');
  if (quiz) {
    var Q = [
      { ch: 'SMS', from: 'BANCO', av: 'B', ans: 'golpe',
        msg: 'BANCO: identificamos um acesso suspeito na sua conta. Para evitar o bloqueio, regularize em até 2h: atualiza-cadastro-seguro.com',
        why: 'Bancos não enviam links para “regularizar” a conta. Urgência, ameaça de bloqueio e endereço estranho são sinais clássicos de golpe.' },
      { ch: 'WhatsApp', from: '+55 11 9•••• ••••', av: '?', ans: 'golpe',
        msg: 'Oi mãe, troquei de número 😊 salva esse aqui. Preciso pagar um boleto hoje e meu app travou, consegue fazer um Pix pra mim? Amanhã te devolvo',
        why: 'É o golpe do “número novo”. Antes de qualquer transferência, ligue para o número antigo ou peça uma chamada de vídeo.' },
      { ch: 'Notificação', from: 'App do seu banco', av: '✓', ans: 'seguro',
        msg: 'Compra aprovada no cartão final 4321: R$ 32,50 em PADARIA CENTRAL. Não reconhece? Abra o aplicativo e toque em “Contestar”.',
        why: 'Notificação informativa, sem link e sem pedir dados. Ela orienta a resolver pelo próprio aplicativo, que é o caminho seguro.' },
      { ch: 'E-mail', from: 'Suporte de Direitos Autorais', av: 'M', ans: 'golpe',
        msg: 'Seu perfil do Instagram violou nossas diretrizes de direitos autorais e será excluído em 24 horas. Para recorrer, confirme seus dados: appeal-center-meta.com',
        why: 'Avisos reais aparecem dentro do aplicativo. O prazo curto e o link externo pedindo login servem para roubar a senha e o código de acesso.' },
      { ch: 'SMS', from: 'WhatsApp', av: 'W', ans: 'seguro',
        msg: 'Seu código do WhatsApp: 482-913. Não compartilhe esse código com ninguém.',
        why: 'Se foi você quem pediu o código (ao instalar o WhatsApp num celular novo), a mensagem é legítima. O perigo está em repassar o código a alguém.' },
      { ch: 'WhatsApp', from: 'Entregas Express', av: 'E', ans: 'golpe',
        msg: 'Olá! Enviei por engano um código de 6 dígitos por SMS para o seu número. Pode me dizer qual chegou para eu concluir a sua entrega?',
        why: 'Ninguém precisa do código que chega no seu celular. Repassá-lo permite que golpistas ativem o seu WhatsApp em outro aparelho.' },
      { ch: 'Ligação', from: 'Central de Segurança', av: '☎', ans: 'golpe',
        msg: '“Detectamos uma invasão na sua conta. Para proteger o seu saldo, transfira os valores para a conta segura que vou informar enquanto bloqueamos o acesso.”',
        why: 'Não existe “conta segura”. Desligue e ligue você mesmo para o número oficial do banco, que está no verso do cartão.' }
    ];
    var qi = 0, score = 0;
    var qs = function (k) { return $('[data-q-' + k + ']', quiz); };
    var stage = qs('stage'), endEl = qs('end'), fb = qs('feedback'), actions = qs('actions');
    var dots = $$('[data-q-dots] li', quiz), phone = $('.phone', quiz);
    var renderQ = function () {
      var q = Q[qi];
      qs('channel').textContent = q.ch;
      qs('count').textContent = (qi + 1) + ' de ' + Q.length;
      qs('avatar').textContent = q.av;
      qs('from').textContent = q.from;
      qs('msg').textContent = q.msg;
      actions.hidden = false; fb.hidden = true;
      stage.classList.remove('is-entering'); void stage.offsetWidth; stage.classList.add('is-entering');
      dots.forEach(function (d, i) { d.classList.toggle('is-current', i === qi); });
    };
    var answer = function (val) {
      var q = Q[qi], right = val === q.ans;
      if (right) score++;
      actions.hidden = true; fb.hidden = false;
      fb.classList.toggle('is-right', right); fb.classList.toggle('is-wrong', !right);
      qs('verdict').textContent = (right ? 'Acertou! ' : 'Quase. ') + (q.ans === 'golpe' ? 'É golpe.' : 'É seguro.');
      qs('why').textContent = q.why;
      qs('next').textContent = qi < Q.length - 1 ? 'Próxima mensagem →' : 'Ver resultado →';
      dots[qi].classList.add(right ? 'ok' : 'err');
      if (!right && !reduceMotion) { phone.classList.remove('shake'); void phone.offsetWidth; phone.classList.add('shake'); }
      qs('next').focus({ preventScroll: true });
    };
    var finish = function () {
      stage.hidden = true; endEl.hidden = false;
      dots.forEach(function (d) { d.classList.remove('is-current'); });
      qs('score').textContent = score;
      var title, text;
      if (score === Q.length) { title = 'Excelente! Você identificou todas.'; text = 'Compartilhe o teste com quem precisa ficar mais atento.'; }
      else if (score >= 5) { title = 'Muito bem!'; text = 'Você tem bom olho, mas os golpes são feitos para enganar. Os detalhes fazem diferença.'; }
      else { title = 'Atenção redobrada.'; text = 'Os golpes são cada vez mais convincentes. Releia os “Golpes do momento” e desconfie de urgência.'; }
      qs('end-title').textContent = title;
      qs('end-text').textContent = text;
      qs('share').href = 'https://wa.me/?text=' + encodeURIComponent('Fiz o teste “Isso é golpe?” e acertei ' + score + ' de ' + Q.length + '. Duvido você acertar todas: https://joaopedrogomesadvhacker.adv.br/#teste');
      qs('restart').focus({ preventScroll: true });
    };
    quiz.addEventListener('click', function (e) {
      var b = e.target.closest('[data-answer]');
      if (b) { answer(b.dataset.answer); return; }
      if (e.target.closest('[data-q-next]')) { if (qi < Q.length - 1) { qi++; renderQ(); } else finish(); return; }
      if (e.target.closest('[data-q-restart]')) {
        qi = 0; score = 0; endEl.hidden = true; stage.hidden = false;
        dots.forEach(function (d) { d.classList.remove('ok', 'err'); });
        renderQ();
      }
    });
    renderQ();
  }

  /* ---------- Vídeo de apresentação (aparece só se o arquivo existir) ---------- */
  var vBtn = $('.video-open'), vModal = $('.video-modal');
  // para ativar: coloque o nome do arquivo em data-video-src (ex.: video-apresentacao.mp4) no index.html
  if (vBtn && vModal && vBtn.dataset.videoSrc && /^https?:$/.test(location.protocol) && typeof fetch === 'function' && vModal.showModal) {
    var vSrc = vBtn.dataset.videoSrc, vEl = $('video', vModal), musicWas = false;
    fetch(vSrc, { method: 'HEAD' }).then(function (r) { if (r.ok) vBtn.hidden = false; }).catch(function () {});
    vBtn.addEventListener('click', function () {
      if (!vEl.getAttribute('src')) vEl.src = vSrc;
      var amb = $('#ambient');
      musicWas = !!(amb && !amb.paused);
      if (musicWas) amb.pause();
      vModal.showModal();
      var pr = vEl.play(); if (pr && pr.catch) pr.catch(function () {});
    });
    var closeV = function () { vModal.close(); };
    $('.video-close', vModal).addEventListener('click', closeV);
    vModal.addEventListener('click', function (e) { if (e.target === vModal) closeV(); });
    vModal.addEventListener('close', function () {
      vEl.pause();
      var amb = $('#ambient');
      if (musicWas && amb) { var p2 = amb.play(); if (p2 && p2.catch) p2.catch(function () {}); }
    });
  }

})();
