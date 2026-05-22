/**
 * POC Dashboard - Sentimiento de reviews hotel
 * Línea de tiempo interactiva, tópicos y Top 5 con detalle
 */

(function () {
  'use strict';

  // --- Datos de ejemplo ---
  const MESES = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'];
  // Tópicos clave para el cliente (categorías prioritarias del negocio)
  const TOPICOS_CLAVE = [
    { id: 'atencion_personal', nombre: 'Atención del personal', score: 82, cambio: 2.1, alerta: false },
    { id: 'limpieza', nombre: 'Limpieza', score: 75, cambio: -1.2, alerta: false },
    { id: 'ubicacion', nombre: 'Ubicación', score: 88, cambio: 0.5, alerta: false },
    { id: 'instalaciones_servicios', nombre: 'Instalaciones y servicios', score: 70, cambio: -3.0, alerta: true },
    { id: 'alimentacion', nombre: 'Alimentación', score: 74, cambio: 1.8, alerta: false },
    { id: 'confort_habitacion', nombre: 'Confort de la habitación', score: 78, cambio: 2.4, alerta: false },
    { id: 'relacion_calidad_precio', nombre: 'Relación calidad-precio', score: 65, cambio: -4.2, alerta: true },
  ];

  // Tópicos adicionales identificados en el análisis de sentimiento
  const TOPICOS_ADICIONALES = [
    { id: 'ruido', nombre: 'Ruido', score: 58, cambio: -5.2, alerta: true },
    { id: 'wifi', nombre: 'WiFi', score: 61, cambio: -2.0, alerta: true },
    { id: 'estacionamiento', nombre: 'Estacionamiento', score: 72, cambio: 1.0, alerta: false },
    { id: 'piscina_spa', nombre: 'Piscina / zona común', score: 80, cambio: 3.2, alerta: false },
  ];

  const TODOS_TOPICOS = [...TOPICOS_CLAVE, ...TOPICOS_ADICIONALES];

  const EJEMPLOS_TOPICO = {
    atencion_personal: ['El personal muy amable y atento en todo momento.', 'Recepción nos ayudó con las maletas y recomendaciones.'],
    limpieza: ['Habitación impecable cada día.', 'Limpieza correcta, sin quejas.'],
    ubicacion: ['Excelente ubicación, todo cerca a pie.', 'Muy bien conectado con transporte público.'],
    instalaciones_servicios: ['El gimnasio y el negocio bien equipados.', 'Faltaron horarios más amplios en el spa.'],
    alimentacion: ['Desayuno variado y fresco, muy buen café.', 'El restaurante cierra muy temprano.'],
    confort_habitacion: ['La cama muy cómoda y las almohadas geniales.', 'Buen espacio en la habitación para trabajar.'],
    relacion_calidad_precio: ['Por el precio esperaba más.', 'Buen valor considerando la ubicación.'],
    ruido: ['El ruido de la calle no nos dejó descansar bien.', 'Se escucha todo del pasillo.'],
    wifi: ['La WiFi fallaba en la habitación.', 'Conexión lenta para videollamadas.'],
    estacionamiento: ['Aparcar fue fácil y seguro.', 'El parking es de pago y algo caro.'],
    piscina_spa: ['La piscina y la terraza son un plus.', 'Zona de spa muy tranquila.'],
  };

  // Sentimiento mensual (12 meses)
  const SENTIMENT_MENSUAL = [65, 68, 70, 69, 72, 71, 73, 74, 72, 75, 76, 74];
  const SENTIMENT_MESES = (function () {
    const d = new Date();
    return Array.from({ length: 12 }, (_, i) => {
      const m = new Date(d.getFullYear(), d.getMonth() - 11 + i, 1);
      return MESES[m.getMonth()] + " '" + String(m.getFullYear()).slice(2);
    });
  })();

  // Resumen de tópicos por mes (para tooltip del gráfico)
  const NOMBRES_TOPICO = Object.fromEntries(TODOS_TOPICOS.map((t) => [t.id, t.nombre]));
  const TOPICOS_POR_MES = (function () {
    return Array.from({ length: 12 }, (_, i) => {
      const obj = {};
      TODOS_TOPICOS.forEach((t) => {
        const variacion = (i - 6) * 0.5 + Math.round((t.score % 3) - 1);
        obj[t.id] = Math.min(95, Math.max(45, t.score + variacion));
      });
      return obj;
    });
  })();

  let chartSentiment = null;
  let rangoMeses = 12;
  let indiceInicioGrafico = 0; // para mapear dataIndex del tooltip al mes correcto

  // --- Utilidades ---
  function $(sel, ctx = document) {
    return ctx.querySelector(sel);
  }
  function $$(sel, ctx = document) {
    return Array.from(ctx.querySelectorAll(sel));
  }

  function formatPercent(n) {
    return (n >= 0 ? '+' : '') + n.toFixed(1) + '%';
  }

  function getMesLabel(idx) {
    return SENTIMENT_MESES[idx] || '';
  }

  // --- Gráfico de sentimiento ---
  function crearGraficoSentimiento() {
    const canvas = document.getElementById('chartSentiment');
    if (!canvas) return;

    const n = Math.min(rangoMeses, 12);
    const desde = 12 - n;
    indiceInicioGrafico = desde;
    const labels = SENTIMENT_MESES.slice(desde, 12);
    const data = SENTIMENT_MENSUAL.slice(desde, 12);

    const ctx = canvas.getContext('2d');
    if (chartSentiment) chartSentiment.destroy();

    chartSentiment = new Chart(ctx, {
      type: 'line',
      data: {
        labels,
        datasets: [
          {
            label: 'Sentimiento promedio (%)',
            data,
            borderColor: '#c9a227',
            backgroundColor: 'rgba(201, 162, 39, 0.15)',
            fill: true,
            tension: 0.3,
            pointBackgroundColor: '#c9a227',
            pointRadius: 4,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          intersect: false,
          mode: 'index',
        },
        plugins: {
          legend: { display: false },
          tooltip: {
            enabled: true,
            backgroundColor: 'rgba(13, 27, 42, 0.96)',
            titleColor: '#d4af37',
            bodyColor: '#e5e7eb',
            borderColor: 'rgba(201, 162, 39, 0.5)',
            borderWidth: 1,
            padding: 14,
            titleFont: { size: 13, weight: 'bold' },
            bodyFont: { size: 12 },
            callbacks: {
              afterBody: function (tooltipItems) {
                const idx = tooltipItems[0]?.dataIndex ?? 0;
                const mesIdx = indiceInicioGrafico + idx;
                const topicosMes = TOPICOS_POR_MES[mesIdx];
                if (!topicosMes) return '';
                const lineas = Object.entries(topicosMes).map(function (entry) {
                  const nombre = NOMBRES_TOPICO[entry[0]] || entry[0];
                  const score = entry[1];
                  const clase = score >= 70 ? 'positive' : (score >= 55 ? 'warn' : 'negative');
                  return nombre + ': ' + score + '%';
                });
                return '\n\nResumen por tópico en esta fecha:\n' + lineas.join('\n');
              },
            },
          },
        },
        scales: {
          y: {
            min: 50,
            max: 100,
            ticks: { callback: (v) => v + '%' },
            grid: { color: 'rgba(0,0,0,0.06)' },
          },
          x: {
            grid: { display: false },
          },
        },
      },
    });
  }

  // --- Timeline: botones y fechas ---
  function initTimeline() {
    const hoy = new Date();
    const hace = (meses) => {
      const d = new Date(hoy);
      d.setMonth(d.getMonth() - meses);
      return d;
    };

    const dateFrom = document.getElementById('dateFrom');
    const dateTo = document.getElementById('dateTo');
    if (dateFrom) dateFrom.value = formatDateInput(hace(rangoMeses));
    if (dateTo) dateTo.value = formatDateInput(hoy);

    $$('.btn-range').forEach((btn) => {
      btn.addEventListener('click', function () {
        $$('.btn-range').forEach((b) => b.classList.remove('active'));
        this.classList.add('active');
        rangoMeses = parseInt(this.dataset.range, 10);
        if (dateFrom) dateFrom.value = formatDateInput(hace(rangoMeses));
        crearGraficoSentimiento();
      });
    });

    function formatDateInput(d) {
      return d.toISOString().slice(0, 10);
    }

    [dateFrom, dateTo].forEach((input) => {
      if (!input) return;
      input.addEventListener('change', () => {
        const from = dateFrom ? new Date(dateFrom.value) : hace(12);
        const to = dateTo ? new Date(dateTo.value) : hoy;
        const meses = Math.round((to - from) / (30 * 24 * 60 * 60 * 1000));
        rangoMeses = Math.min(12, Math.max(1, meses));
        $$('.btn-range').forEach((b) => {
          b.classList.toggle('active', parseInt(b.dataset.range, 10) === rangoMeses);
        });
        crearGraficoSentimiento();
      });
    });
  }

  function renderTopicCards(gridId, topicos) {
    const grid = document.getElementById(gridId);
    if (!grid) return;

    grid.innerHTML = topicos.map((t) => {
      const clase = t.alerta ? 'alert' : 'good';
      const scoreClase = t.score >= 70 ? 'positive' : 'negative';
      const changeClase = t.cambio >= 0 ? 'up' : 'down';
      const changeText = formatPercent(t.cambio);
      return `
        <div class="topic-card ${clase}" data-topic-id="${t.id}">
          <div class="topic-name">${t.nombre}</div>
          <div class="topic-score ${scoreClase}">${t.score}%</div>
          <div class="topic-change ${changeClase}">${changeText} vs anterior</div>
        </div>
      `;
    }).join('');

    grid.querySelectorAll('.topic-card').forEach((el) => {
      el.addEventListener('click', () => abrirDetalle(el.dataset.topicId));
    });
  }

  function renderTopicsClave() {
    renderTopicCards('topicsClaveGrid', TOPICOS_CLAVE);
  }

  function renderTopicsAdicionales() {
    renderTopicCards('topicsAdicionalesGrid', TOPICOS_ADICIONALES);
  }

  // --- Top 5 tópicos (lista con detalle, sobre tópicos clave) ---
  function renderTop5() {
    const list = document.getElementById('top5List');
    if (!list) return;

    const top5 = [...TOPICOS_CLAVE].sort((a, b) => a.score - b.score).slice(0, 5).reverse();

    list.innerHTML = top5.map((t, i) => {
      const badge = t.alerta ? 'alert' : 'good';
      return `
        <li data-topic-id="${t.id}" tabindex="0" role="button">
          <span class="topic-rank">${i + 1}</span>
          <span class="topic-title">${t.nombre}</span>
          <span class="topic-badge ${badge}">${t.score}%</span>
        </li>
      `;
    }).join('');

    list.querySelectorAll('li').forEach((el) => {
      el.addEventListener('click', () => abrirDetalle(el.dataset.topicId));
      el.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          abrirDetalle(el.dataset.topicId);
        }
      });
    });
  }

  // --- Tabla de rendimiento (tópicos clave + adicionales) ---
  function renderPerfTable() {
    const tbody = document.getElementById('perfTableBody');
    if (!tbody) return;

    tbody.innerHTML = TODOS_TOPICOS.map((t) => {
      const perfClass = t.cambio >= 0 ? 'perf-up' : 'perf-down';
      const icon = t.cambio >= 0 ? '↑' : '↓';
      return `
        <tr>
          <td><strong>${t.nombre}</strong></td>
          <td>${t.score}%</td>
          <td class="${perfClass}">${formatPercent(t.cambio)}</td>
          <td class="${perfClass}"><span class="perf-icon">${icon}</span></td>
        </tr>
      `;
    }).join('');
  }

  // --- Modal detalle ---
  function abrirDetalle(topicId) {
    const t = TODOS_TOPICOS.find((x) => x.id === topicId);
    if (!t) return;

    const overlay = document.getElementById('modalOverlay');
    const title = document.getElementById('modalTitle');
    const body = document.getElementById('modalBody');

    title.textContent = t.nombre;
    const scoreClase = t.score >= 70 ? 'positive' : 'negative';
    const ejemplos = (EJEMPLOS_TOPICO[t.id] || ['Sin ejemplos cargados.']).map((e) => `<li>\"${e}\"</li>`).join('');
    body.innerHTML = `
      <div class="detail-score ${scoreClase}">${t.score}%</div>
      <div class="detail-meta">
        Cambio vs período anterior: <strong class="${t.cambio >= 0 ? 'positive' : 'negative'}">${formatPercent(t.cambio)}</strong><br>
        ${t.alerta ? '<span class="topic-badge alert">Requiere atención</span>' : 'Dentro del rango esperado.'}
      </div>
      <p>Ejemplos de menciones en reseñas (POC):</p>
      <ul style="margin-top:0.5rem; padding-left:1.2rem; color: var(--text-secondary); font-size:0.9rem;">
        ${ejemplos}
      </ul>
    `;

    overlay.setAttribute('aria-hidden', 'false');
    document.getElementById('modalClose').focus();
  }

  function cerrarModal() {
    document.getElementById('modalOverlay').setAttribute('aria-hidden', 'true');
  }

  document.getElementById('modalClose').addEventListener('click', cerrarModal);
  document.getElementById('modalOverlay').addEventListener('click', function (e) {
    if (e.target === this) cerrarModal();
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') cerrarModal();
  });

  // --- Sidebar y navegación entre vistas ---
  function initSidebar() {
    const sidebar = document.getElementById('sidebar');
    const toggle = document.getElementById('sidebarToggle');
    const mobileBtn = document.getElementById('mobileMenuBtn');
    const backdrop = document.getElementById('sidebarBackdrop');

    function showOnlyPanel(viewId) {
      document.querySelectorAll('.main-content .panel-view').forEach(function (p) {
        var match = p.getAttribute('data-panel') === viewId;
        p.hidden = !match;
        p.setAttribute('aria-hidden', match ? 'false' : 'true');
      });
    }

    function closeMobileSidebar() {
      if (!sidebar) return;
      sidebar.classList.remove('mobile-open');
      if (backdrop) {
        backdrop.classList.remove('is-open');
        backdrop.setAttribute('aria-hidden', 'true');
      }
      if (mobileBtn) mobileBtn.setAttribute('aria-expanded', 'false');
    }

    function openMobileSidebar() {
      if (!sidebar) return;
      sidebar.classList.add('mobile-open');
      if (backdrop) {
        backdrop.classList.add('is-open');
        backdrop.setAttribute('aria-hidden', 'false');
      }
      if (mobileBtn) mobileBtn.setAttribute('aria-expanded', 'true');
    }

    if (toggle && sidebar) {
      toggle.addEventListener('click', function () {
        sidebar.classList.toggle('collapsed');
        const collapsed = sidebar.classList.contains('collapsed');
        toggle.setAttribute('title', collapsed ? 'Expandir menú' : 'Contraer menú');
        toggle.setAttribute('aria-label', collapsed ? 'Expandir menú' : 'Contraer menú');
        try {
          localStorage.setItem('olh_sidebar_collapsed', collapsed ? '1' : '0');
        } catch (err) { /* ignore */ }
      });
      try {
        if (localStorage.getItem('olh_sidebar_collapsed') === '1') {
          sidebar.classList.add('collapsed');
          toggle.setAttribute('title', 'Expandir menú');
          toggle.setAttribute('aria-label', 'Expandir menú');
        }
      } catch (err) { /* ignore */ }
    }

    showOnlyPanel('dashboard');

    document.querySelectorAll('.sidebar-nav .nav-item').forEach(function (link) {
      var label = link.querySelector('.nav-label');
      if (label) link.setAttribute('title', label.textContent.trim());
      link.addEventListener('click', function (e) {
        e.preventDefault();
        var view = link.dataset.view;
        document.querySelectorAll('.sidebar-nav .nav-item').forEach(function (l) {
          l.classList.remove('active');
          l.removeAttribute('aria-current');
        });
        link.classList.add('active');
        link.setAttribute('aria-current', 'page');
        showOnlyPanel(view);
        closeMobileSidebar();
        if (view === 'dashboard' && chartSentiment) {
          setTimeout(function () {
            chartSentiment.resize();
          }, 150);
        }
        var mainEl = document.querySelector('.main-content');
        if (mainEl) mainEl.scrollTop = 0;
      });
    });

    if (mobileBtn && sidebar && backdrop) {
      mobileBtn.addEventListener('click', function () {
        if (sidebar.classList.contains('mobile-open')) closeMobileSidebar();
        else openMobileSidebar();
      });
      backdrop.addEventListener('click', closeMobileSidebar);
    }

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && sidebar && sidebar.classList.contains('mobile-open')) {
        closeMobileSidebar();
      }
    });
  }

  // --- Usuario conectado (POC) ---
  // Otros módulos pueden setear estos valores:
  // localStorage.setItem('olh_connected_user_name', 'Nombre');
  // localStorage.setItem('olh_connected_user_email', 'email@dominio.com');
  function initUserConectado() {
    const nameEl = document.getElementById('sidebarUserName');
    const emailEl = document.getElementById('sidebarUserEmail');
    if (!nameEl && !emailEl) return;

    let name = '';
    let email = '';
    try {
      name = localStorage.getItem('olh_connected_user_name') || localStorage.getItem('olh_connected_user') || '';
      email = localStorage.getItem('olh_connected_user_email') || '';
    } catch (err) {
      // Ignorar si localStorage no está disponible
    }

    if (!name) name = 'Admin';
    if (!email) email = 'admin@olh.com';

    if (nameEl) nameEl.textContent = name;
    if (emailEl) emailEl.textContent = email;
  }

  // --- Inicio ---
  function init() {
    crearGraficoSentimiento();
    initTimeline();
    initSidebar();
    initUserConectado();
    renderTopicsClave();
    renderTopicsAdicionales();
    renderTop5();
    renderPerfTable();
    const numAlertas = TODOS_TOPICOS.filter((t) => t.alerta).length;
    const kpiAlerts = document.getElementById('kpiAlerts');
    if (kpiAlerts) kpiAlerts.textContent = String(numAlertas);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
