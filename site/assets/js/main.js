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
  requestAnimationFrame(function () { document.body.classList.add('is-loaded'); });

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
})();
