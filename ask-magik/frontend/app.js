/**
 * PRELOADER CONTROLLER
 * Runs immediately — independent of DOMContentLoaded.
 * Sequence: brand in (0.85s) → rule draws (1.35s) → team in (1.75s) → hold → exit (2.4s)
 */
(function initPreloader() {
  const TOTAL_HOLD_MS = 2400;   // ms before fade begins (covers full animation + brief hold)
  const FADE_MS      = 650;     // must match CSS transition duration

  var prefersReduced = window.matchMedia &&
                       window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  var delay = prefersReduced ? 500 : TOTAL_HOLD_MS;

  function dismissPreloader() {
    var preloader = document.getElementById('magik-preloader');
    if (!preloader) return;

    // Trigger CSS fade-out
    preloader.classList.add('mpl-exit');

    // Reveal main app
    document.body.classList.remove('preloading');

    // Remove from DOM after transition so it can never interfere
    setTimeout(function () {
      if (preloader && preloader.parentNode) {
        preloader.parentNode.removeChild(preloader);
      }
    }, FADE_MS + 50);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () {
      setTimeout(dismissPreloader, delay);
    });
  } else {
    // DOMContentLoaded already fired (e.g. deferred / module scripts)
    setTimeout(dismissPreloader, delay);
  }
})();

/**
 * ASK MAGIK - Front-end Application Controller
 * Skyline Telecom Governed Conversational Intelligence Engine
 *
 * API_BASE: Empty string → all /api/* calls are relative, resolved by
 * Vercel rewrites (vercel.json) to https://ask-magik-production.up.railway.app
 * in production, and to localhost:8000 when running locally.
 */

document.addEventListener('DOMContentLoaded', () => {
  // =========================================================================
  // CENTRALIZED API CONFIGURATION
  // =========================================================================
  // Keep as empty string. Vercel rewrites /api/* → Railway backend in prod.
  // Locally, uvicorn serves both frontend and backend, so relative paths work.
  const API_BASE = '';

  /**
   * Production-safe fetch wrapper.
   * - Adds timeout (default 30 s).
   * - Throws structured errors for network failures, timeouts, and HTTP errors.
   * - Never exposes stack traces or internal URLs to users.
   * @param {string} path - Relative API path, e.g. '/api/chat'
   * @param {RequestInit} options - Standard fetch options
   * @param {number} timeoutMs - Request timeout in milliseconds
   */
  async function apiFetch(path, options = {}, timeoutMs = 30000) {
    const controller = options.signal
      ? null // caller owns the signal, no extra wrapping
      : new AbortController();
    const signal = controller ? controller.signal : options.signal;

    let timeoutId;
    if (controller) {
      timeoutId = setTimeout(() => controller.abort(), timeoutMs);
    }

    try {
      const res = await fetch(API_BASE + path, { ...options, signal });
      if (timeoutId) clearTimeout(timeoutId);

      if (!res.ok) {
        let detail = `HTTP ${res.status}`;
        try {
          const body = await res.json();
          if (body && body.detail) detail = body.detail;
        } catch (_) { /* ignore JSON parse error */ }
        const err = new Error(detail);
        err.status = res.status;
        throw err;
      }
      return res;
    } catch (err) {
      if (timeoutId) clearTimeout(timeoutId);
      if (err.name === 'AbortError' && !options.signal) {
        const te = new Error('Request timed out. Please try again.');
        te.isTimeout = true;
        throw te;
      }
      throw err;
    }
  }
  // State
  const state = {
    currentView: 'overview',
    currentQuery: '',
    lastResult: null,
    history: [],
    savedInsights: [],
    datasources: null,
    knowledge: null,
    security: null,
    auditLogs: [],
    knowledgeTabsBound: false,
    activeQueryController: null,
    preflightController: null,
  };

  // DOM Elements
  const sidebar = document.getElementById('sidebar');
  const sidebarToggle = document.getElementById('sidebar-toggle');
  const companyTrigger = document.getElementById('company-trigger');
  const companyPopover = document.getElementById('company-popover');
  const navItems = document.querySelectorAll('.nav-item');
  const viewPanels = document.querySelectorAll('.view-panel');
  const navLabel = document.getElementById('nav-label');

  // Overview View Elements
  const btnHeroAsk = document.getElementById('btn-hero-ask');
  const btnHeroUpload = document.getElementById('btn-hero-upload');

  // Ask Data Elements
  const queryInput = document.getElementById('user-query-input');
  const btnSubmitQuery = document.getElementById('btn-submit-query');
  const btnSubmitText = document.getElementById('btn-submit-text');
  const sampleCards = document.querySelectorAll('.sample-card');
  const resultPanel = document.getElementById('query-result-panel');
  const resConfidence = document.getElementById('res-confidence');
  const resKeyInsight = document.getElementById('res-key-insight');
  const resAnswerText = document.getElementById('res-answer-text');
  const resFiguresList = document.getElementById('res-figures-list');
  const chartContainer = document.getElementById('chart-container');
  const tableContainer = document.getElementById('table-container');
  const tableRowCountLabel = document.getElementById('table-row-count-label');
  const tableFilterInput = document.getElementById('table-filter-input');
  const sqlDisplayBlock = document.getElementById('sql-display-block');
  const btnCopySql = document.getElementById('btn-copy-sql');
  const evidenceDisplay = document.getElementById('evidence-display');
  const btnSaveCurrentInsight = document.getElementById('btn-save-current-insight');
  const tabBtns = document.querySelectorAll('.tab-btn');
  const tabPanes = document.querySelectorAll('.tab-pane');

  // Right Panels Elements (Screenshot 2)
  const contextGlossary = document.getElementById('context-glossary');
  const contextSchema = document.getElementById('context-schema');
  const contextRelationships = document.getElementById('context-relationships');
  const contextExamples = document.getElementById('context-examples');
  const traceToggleHeader = document.getElementById('trace-toggle-header');
  const traceToggleIcon = document.getElementById('trace-toggle-icon');
  const traceBody = document.getElementById('trace-body');

  // Modals
  const uploadModal = document.getElementById('upload-modal');
  const uploadModalClose = document.getElementById('upload-modal-close');
  const btnCancelUpload = document.getElementById('btn-cancel-upload');
  const btnConfirmUpload = document.getElementById('btn-confirm-upload');
  const uploadTargetTable = document.getElementById('upload-target-table');
  const uploadDropzone = document.getElementById('upload-dropzone');
  const uploadFileInput = document.getElementById('upload-file-input');
  const uploadStatusMsg = document.getElementById('upload-status-msg');

  const previewModal = document.getElementById('preview-modal');
  const previewModalClose = document.getElementById('preview-modal-close');
  const previewModalTitle = document.getElementById('preview-modal-title');
  const previewTableContainer = document.getElementById('preview-table-container');

  const settingsModal = document.getElementById('settings-modal');
  const settingsModalClose = document.getElementById('settings-modal-close');
  const btnOpenSettings = document.getElementById('open-settings-btn');
  const btnCancelSettings = document.getElementById('btn-cancel-settings');
  const btnSaveSettings = document.getElementById('btn-save-settings');

  // Security Sandbox Elements
  const sandboxSqlInput = document.getElementById('sandbox-sql-input');
  const btnTestSandbox = document.getElementById('btn-test-sandbox');
  const sandboxResultBox = document.getElementById('sandbox-result-box');

  // =========================================================================
  // INITIALIZATION
  // =========================================================================
  initApp();

  async function initApp() {
    setupEventListeners();
    await loadOverviewData();
    await checkSystemStatus();
  }

  // =========================================================================
  // NAVIGATION & VIEW SWITCHING
  // =========================================================================
  function switchView(viewName) {
    state.currentView = viewName;

    // Update active nav button
    navItems.forEach(item => {
      if (item.getAttribute('data-view') === viewName) {
        item.classList.add('active');
      } else {
        item.classList.remove('active');
      }
    });

    // Update active view panel
    viewPanels.forEach(panel => {
      if (panel.id === `view-${viewName}`) {
        panel.classList.add('active');
      } else {
        panel.classList.remove('active');
      }
    });

    // Lazy load data per view
    if (viewName === 'datasources') loadDataSources();
    if (viewName === 'history') loadHistory();
    if (viewName === 'saved-insights') loadSavedInsights();
    if (viewName === 'knowledge') loadKnowledge();
    if (viewName === 'security') loadSecurity();
    if (viewName === 'audit-log') loadAuditLogs();
  }

  // =========================================================================
  // EVENT LISTENERS
  // =========================================================================
  function setupEventListeners() {
    // Sidebar collapse toggle
    sidebarToggle.addEventListener('click', () => {
      sidebar.classList.toggle('collapsed');
    });

    // Company dropdown toggle (Screenshot 1)
    companyTrigger.addEventListener('click', (e) => {
      e.stopPropagation();
      companyTrigger.classList.toggle('open');
      companyPopover.classList.toggle('visible');
    });

    document.addEventListener('click', (e) => {
      if (!companyPopover.contains(e.target) && !companyTrigger.contains(e.target)) {
        companyTrigger.classList.remove('open');
        companyPopover.classList.remove('visible');
      }
    });

    // Navigation item clicks
    navItems.forEach(item => {
      item.addEventListener('click', () => {
        const view = item.getAttribute('data-view');
        switchView(view);
      });
    });

    // Overview buttons
    btnHeroAsk.addEventListener('click', () => {
      switchView('ask-data');
      queryInput.focus();
    });

    btnHeroUpload.addEventListener('click', () => {
      openModal(uploadModal);
    });

    const btnDatasourcesUpload = document.getElementById('btn-datasources-upload');
    if (btnDatasourcesUpload) {
      btnDatasourcesUpload.addEventListener('click', () => openModal(uploadModal));
    }

    // Sample query cards click (Screenshot 2)
    sampleCards.forEach(card => {
      card.addEventListener('click', () => {
        const q = card.getAttribute('data-query');
        queryInput.value = q;
        executeQuery(q);
      });
    });

    // Query textarea input with debounced preflight context retrieval
    let debounceTimer;
    queryInput.addEventListener('input', () => {
      clearTimeout(debounceTimer);
      const text = queryInput.value.trim();
      if (text.length > 5) {
        debounceTimer = setTimeout(() => {
          fetchPreflightContext(text);
        }, 150);
      }
    });

    // Submit Query button
    btnSubmitQuery.addEventListener('click', () => {
      const q = queryInput.value.trim();
      if (q) executeQuery(q);
    });

    queryInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        const q = queryInput.value.trim();
        if (q) executeQuery(q);
      }
    });

    // Result tabs
    tabBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        tabBtns.forEach(b => b.classList.remove('active'));
        tabPanes.forEach(p => p.classList.remove('active'));

        btn.classList.add('active');
        const targetId = btn.getAttribute('data-tab');
        const targetPane = document.getElementById(targetId);
        if (targetPane) targetPane.classList.add('active');
      });
    });

    // Collapsible trace toggle (Screenshot 2)
    traceToggleHeader.addEventListener('click', () => {
      const isCollapsed = traceBody.classList.toggle('collapsed');
      traceToggleIcon.textContent = isCollapsed ? '+' : '−';
    });

    // Copy SQL button
    btnCopySql.addEventListener('click', () => {
      if (state.lastResult && state.lastResult.sql) {
        navigator.clipboard.writeText(state.lastResult.sql);
        btnCopySql.textContent = 'Copied!';
        setTimeout(() => { btnCopySql.textContent = 'Copy SQL'; }, 2000);
      }
    });

    // Save insight button
    btnSaveCurrentInsight.addEventListener('click', async () => {
      if (!state.lastResult) return;

      const originalHtml = btnSaveCurrentInsight.innerHTML;
      btnSaveCurrentInsight.disabled = true;
      btnSaveCurrentInsight.innerHTML = '<span>Saving...</span>';

      try {
        const res = await apiFetch('/api/history/save', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            question: state.lastResult.question || '',
            key_insight: state.lastResult.key_insight || '',
            supporting_figures: state.lastResult.supporting_figures || [],
            sql: state.lastResult.sql || '',
            confidence: state.lastResult.confidence || 'HIGH',
            chart: state.lastResult.chart || {},
          }),
        }, 10000);

        btnSaveCurrentInsight.disabled = false;
        btnSaveCurrentInsight.innerHTML = '<span>✓ Saved</span>';
        setTimeout(() => {
          btnSaveCurrentInsight.innerHTML = originalHtml;
        }, 2500);
      } catch (err) {
        console.error('Error saving insight:', err);
        btnSaveCurrentInsight.disabled = false;
        btnSaveCurrentInsight.innerHTML = '<span>✕ Save failed</span>';
        setTimeout(() => {
          btnSaveCurrentInsight.innerHTML = originalHtml;
        }, 2500);
      }
    });

    // Filter table records
    tableFilterInput.addEventListener('input', () => {
      const filter = tableFilterInput.value.toLowerCase();
      const rows = tableContainer.querySelectorAll('tbody tr');
      rows.forEach(r => {
        r.style.display = r.textContent.toLowerCase().includes(filter) ? '' : 'none';
      });
    });

    // Modals
    uploadModalClose.addEventListener('click', () => closeModal(uploadModal));
    btnCancelUpload.addEventListener('click', () => closeModal(uploadModal));
    previewModalClose.addEventListener('click', () => closeModal(previewModal));
    btnOpenSettings.addEventListener('click', () => {
      openModal(settingsModal);
      loadSettings();
    });
    settingsModalClose.addEventListener('click', () => closeModal(settingsModal));
    btnCancelSettings.addEventListener('click', () => closeModal(settingsModal));

    // Upload Dropzone
    uploadDropzone.addEventListener('click', () => uploadFileInput.click());
    uploadFileInput.addEventListener('change', (e) => {
      if (e.target.files.length) {
        handleUploadSimulation(e.target.files[0].name);
      }
    });

    btnConfirmUpload.addEventListener('click', () => {
      handleUploadSimulation('telecom_delta_ingest.csv');
    });

    // Save Settings
    btnSaveSettings.addEventListener('click', saveSettings);

    // Security Sandbox
    btnTestSandbox.addEventListener('click', testSecuritySandbox);
  }

  // =========================================================================
  // API CALLS: OVERVIEW & SYSTEM STATUS
  // =========================================================================
  async function loadOverviewData() {
    try {
      const res = await apiFetch('/api/overview/metrics', {}, 10000);
      const data = await res.json();
      console.info('[Overview] Pilot metrics loaded:', data.status || 'OK');
      // Populate any overview-specific KPI elements if present in DOM
      const elStatus = document.getElementById('overview-status-badge');
      if (elStatus && data.status) elStatus.textContent = data.status;
    } catch (err) {
      console.warn('Overview data fetch failed:', err.message);
    }
  }

  async function checkSystemStatus() {
    const statusText = document.getElementById('sidebar-status-text');
    try {
      // Fetch both system status and RAG status in parallel
      const [sysRes, ragRes] = await Promise.allSettled([
        apiFetch('/api/system-status', {}, 10000),
        apiFetch('/api/rag/status', {}, 10000),
      ]);

      let operational = false;
      if (sysRes.status === 'fulfilled') {
        const data = await sysRes.value.json();
        operational = !!data.system_operational;
        if (statusText) {
          statusText.textContent = operational ? 'Operational' : 'Degraded';
          statusText.style.color = operational ? 'var(--accent-green)' : '#f59e0b';
        }
      } else {
        if (statusText) {
          statusText.textContent = 'Offline';
          statusText.style.color = '#ef4444';
        }
      }

      // Log RAG status to console (no UI impact needed here)
      if (ragRes.status === 'fulfilled') {
        const ragData = await ragRes.value.json();
        console.info(`[RAG] status=${ragData.status}, docs=${ragData.document_count}`);
      }
    } catch (err) {
      console.warn('System status fetch failed:', err);
      if (statusText) {
        statusText.textContent = 'Offline';
        statusText.style.color = '#ef4444';
      }
    }
  }

  // =========================================================================
  // API CALLS: ASK DATA PIPELINE (Screenshot 2)
  // =========================================================================
  async function fetchPreflightContext(question) {
    if (state.preflightController) {
      state.preflightController.abort();
    }
    state.preflightController = new AbortController();
    const signal = state.preflightController.signal;

    try {
      const res = await fetch(API_BASE + '/api/rag/context', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question }),
        signal,
      });
      if (res.ok) {
        const data = await res.json();
        renderRightPanels(data.retrieved_context, data.analysis_trace);
      }
    } catch (err) {
      if (err.name !== 'AbortError') {
        console.warn('Preflight context failed:', err.message);
      }
      // Silently ignore — preflight is non-critical
    }
  }

  async function executeQuery(question) {
    if (state.activeQueryController) {
      state.activeQueryController.abort();
    }
    if (state.preflightController) {
      state.preflightController.abort();
    }
    state.activeQueryController = new AbortController();
    const { signal } = state.activeQueryController;

    btnSubmitQuery.disabled = true;
    btnSubmitText.textContent = 'ANALYZING...';
    resultPanel.classList.remove('hidden');
    resKeyInsight.textContent = 'Running governed analytical pipeline...';
    resAnswerText.textContent = 'Retrieving context, generating SQL, validating policy, and querying DataMart...';
    resFiguresList.innerHTML = '';
    chartContainer.innerHTML = '<div style="color:var(--text-muted);font-family:var(--font-mono);font-size:12px;">Generating visualization...</div>';
    tableContainer.innerHTML = '';
    sqlDisplayBlock.textContent = '-- Processing...';
    resConfidence.textContent = 'CONFIDENCE: —';
    resConfidence.style.color = 'var(--text-muted)';
    resConfidence.style.backgroundColor = 'transparent';

    try {
      const res = await fetch(API_BASE + '/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question }),
        signal,
      });

      if (!res.ok) {
        let errDetail = `Server error (${res.status})`;
        try {
          const body = await res.json();
          if (body && body.detail) errDetail = body.detail;
        } catch (_) { /* ignore */ }
        throw new Error(errDetail);
      }

      let data;
      try {
        data = await res.json();
      } catch (_) {
        throw new Error('Received an unexpected response from the server. Please try again.');
      }

      if (!data || typeof data !== 'object') {
        throw new Error('Malformed response from analytics pipeline.');
      }

      state.lastResult = data;
      renderExecutedResult(data);

      if (data.retrieved_context || data.analysis_trace) {
        renderRightPanels(data.retrieved_context, data.analysis_trace);
      }

    } catch (err) {
      if (err.name === 'AbortError') return;

      // Professional, user-safe error display
      let userMsg;
      if (err.isTimeout || err.name === 'TimeoutError') {
        userMsg = 'The analytics pipeline timed out. Please try a simpler query or try again in a moment.';
      } else if (!navigator.onLine || err.message.toLowerCase().includes('failed to fetch') || err.message.toLowerCase().includes('networkerror')) {
        userMsg = 'Network connection unavailable. Please check your connection and try again.';
      } else if (err.status >= 500) {
        userMsg = 'The backend service encountered an error. Our team has been notified. Please try again shortly.';
      } else if (err.status >= 400) {
        userMsg = `Query could not be processed: ${err.message}`;
      } else {
        userMsg = err.message || 'An unexpected error occurred. Please try again.';
      }

      resKeyInsight.textContent = 'Pipeline execution notice';
      resAnswerText.textContent = userMsg;
      resConfidence.textContent = 'CONFIDENCE: LOW';
      resConfidence.style.color = '#ef4444';
      resConfidence.style.backgroundColor = 'rgba(239, 68, 68, 0.15)';
      chartContainer.innerHTML = '<div style="color:var(--text-muted);font-family:var(--font-mono);font-size:12px;padding:40px;">No visualization available.</div>';
      tableContainer.innerHTML = '';
      sqlDisplayBlock.textContent = '-- Query did not execute';
    } finally {
      if (!signal.aborted) {
        btnSubmitQuery.disabled = false;
        btnSubmitText.textContent = 'ASK MAGIK';
      }
    }
  }

  function renderExecutedResult(data) {
    resultPanel.classList.remove('hidden');

    // Confidence
    const conf = data.confidence || 'HIGH';
    resConfidence.textContent = `CONFIDENCE: ${conf}`;
    if (conf === 'HIGH') {
      resConfidence.style.color = 'var(--accent-green)';
      resConfidence.style.backgroundColor = 'var(--accent-green-subtle)';
    } else if (conf === 'MEDIUM') {
      resConfidence.style.color = '#f59e0b';
      resConfidence.style.backgroundColor = 'rgba(245, 158, 11, 0.15)';
    } else {
      resConfidence.style.color = '#ef4444';
      resConfidence.style.backgroundColor = 'rgba(239, 68, 68, 0.15)';
    }

    // Key Insight & Answer Prose
    resKeyInsight.textContent = data.key_insight || 'Key analytical evidence synthesized.';
    resAnswerText.textContent = data.answer || 'Query execution completed.';

    // Supporting Figures Pills
    resFiguresList.innerHTML = '';
    const figures = data.supporting_figures || [];
    figures.forEach(fig => {
      const pill = document.createElement('span');
      pill.className = 'figure-pill';
      pill.textContent = fig;
      resFiguresList.appendChild(pill);
    });

    // Chart Payload
    renderSvgChart(data.chart, data.columns, data.rows);

    // Table
    renderDataTable(data.columns, data.rows);

    // SQL Code Block
    sqlDisplayBlock.textContent = data.sql || '-- No SQL generated';

    // Evidence Grid
    renderEvidence(data);
  }

  function renderRightPanels(context, trace) {
    if (context) {
      if (context.business_glossary) {
        contextGlossary.textContent = context.business_glossary.join(' · ');
      }
      if (context.schema) {
        contextSchema.textContent = context.schema.join(' · ');
      }
      if (context.relationships) {
        contextRelationships.textContent = context.relationships.join(' · ');
      }
      if (context.validated_examples) {
        const count = context.validated_examples_count || context.validated_examples.length;
        contextExamples.textContent = `${count} similar analytical questions`;
      }
    }

    if (trace && Array.isArray(trace)) {
      traceBody.innerHTML = '';
      trace.forEach(step => {
        const item = document.createElement('div');
        item.className = 'trace-step-item';
        item.innerHTML = `
          <div class="step-head">
            <span class="step-title">${step.id} ${escapeHtml(step.name)}</span>
            <span class="step-ms">${step.duration_ms} ms</span>
          </div>
          <div class="step-detail">${escapeHtml(step.detail)}</div>
        `;
        traceBody.appendChild(item);
      });
    }
  }

  // =========================================================================
  // SVG CHART RENDERER (Clean Vanilla SVG Bar / Metric Breakdown)
  // =========================================================================
  function renderSvgChart(chartData, columns, rows) {
    if (!rows || rows.length === 0 || !columns || columns.length < 2) {
      chartContainer.innerHTML = '<div style="color:var(--text-muted);font-family:var(--font-mono);font-size:12px;padding:40px;">No tabular series available for visualization.</div>';
      return;
    }

    const items = rows.slice(0, 10);
    const labelCol = columns[0];
    const valCol = columns[1];

    const labels = items.map(r => String(r[0]));
    const values = items.map(r => {
      const num = parseFloat(r[1]);
      return isNaN(num) ? 0 : num;
    });

    const maxVal = Math.max(...values, 1);
    const svgWidth = 640;
    const svgHeight = 220;
    const padLeft = 110;
    const padBottom = 28;
    const padTop = 16;
    const padRight = 36;

    const chartW = svgWidth - padLeft - padRight;
    const chartH = svgHeight - padTop - padBottom;
    const barHeight = Math.max(14, Math.min(26, Math.floor(chartH / items.length) - 6));
    const gap = Math.floor((chartH - (barHeight * items.length)) / (items.length + 1));

    let svgHtml = `<svg class="svg-chart" viewBox="0 0 ${svgWidth} ${svgHeight}" preserveAspectRatio="xMidYMid meet">`;

    // Background horizontal grid lines
    svgHtml += `<line x1="${padLeft}" y1="${padTop}" x2="${padLeft}" y2="${padTop + chartH}" stroke="#1e2638" stroke-width="1"/>`;
    svgHtml += `<line x1="${padLeft + chartW / 2}" y1="${padTop}" x2="${padLeft + chartW / 2}" y2="${padTop + chartH}" stroke="#141c29" stroke-dasharray="3,3"/>`;
    svgHtml += `<line x1="${padLeft + chartW}" y1="${padTop}" x2="${padLeft + chartW}" y2="${padTop + chartH}" stroke="#1e2638" stroke-width="1"/>`;

    // Bars
    items.forEach((r, idx) => {
      const y = padTop + gap + idx * (barHeight + gap);
      const val = values[idx];
      const barW = Math.max(4, Math.round((val / maxVal) * chartW));
      const lbl = labels[idx].length > 16 ? labels[idx].substring(0, 14) + '..' : labels[idx];

      // Label text
      svgHtml += `<text x="${padLeft - 10}" y="${y + barHeight / 2 + 4}" fill="#94a3b8" font-size="11" font-family="var(--font-mono)" text-anchor="end">${escapeHtml(lbl)}</text>`;

      // Bar rect with gradient effect
      svgHtml += `<rect x="${padLeft}" y="${y}" width="${barW}" height="${barHeight}" rx="3" fill="#00a2ff" opacity="0.88">
        <animate attributeName="width" from="0" to="${barW}" dur="0.4s" fill="freeze" />
      </rect>`;

      // Value text
      svgHtml += `<text x="${padLeft + barW + 8}" y="${y + barHeight / 2 + 4}" fill="#ffffff" font-size="11" font-family="var(--font-mono)" font-weight="600">${val.toLocaleString()}</text>`;
    });

    // Axis label
    svgHtml += `<text x="${padLeft + chartW / 2}" y="${svgHeight - 6}" fill="#64748b" font-size="10" font-family="var(--font-mono)" text-anchor="middle">${escapeHtml(valCol)}</text>`;
    svgHtml += `</svg>`;

    chartContainer.innerHTML = svgHtml;
  }

  // =========================================================================
  // DATA TABLE RENDERER
  // =========================================================================
  function renderDataTable(columns, rows) {
    if (!rows || rows.length === 0 || !columns) {
      tableContainer.innerHTML = '<div style="color:var(--text-muted);font-family:var(--font-mono);font-size:12px;padding:30px;">0 records returned.</div>';
      tableRowCountLabel.textContent = '0 rows';
      return;
    }

    tableRowCountLabel.textContent = `${rows.length} rows returned`;

    let html = '<table class="data-table"><thead><tr>';
    columns.forEach(col => {
      html += `<th>${escapeHtml(col)}</th>`;
    });
    html += '</tr></thead><tbody>';

    rows.forEach(row => {
      html += '<tr>';
      row.forEach(cell => {
        const valStr = cell === null ? 'NULL' : String(cell);
        html += `<td>${escapeHtml(valStr)}</td>`;
      });
      html += '</tr>';
    });

    html += '</tbody></table>';
    tableContainer.innerHTML = html;
  }

  // =========================================================================
  // AUDIT EVIDENCE RENDERER
  // =========================================================================
  function renderEvidence(data) {
    const ev = data.evidence || {};
    const metrics = ev.execution_metrics || {};
    const checks = ev.validation_checks || {};

    const readOnlyStatus = checks.read_only !== false ? 'PASS' : 'FAIL';
    const firewallStatus = checks.firewall_passed ? 'VERIFIED' : 'FAILED';
    const allowlistStatus = checks.allowlisted_tables !== false ? 'PASS' : 'FAIL';

    evidenceDisplay.innerHTML = `
      <div class="evidence-card">
        <div class="evidence-title">ACCESSED TABLES</div>
        <div class="evidence-val">${(ev.tables_used || data.tables_used || []).join(', ') || '—'}</div>
      </div>
      <div class="evidence-card">
        <div class="evidence-title">EXECUTION LATENCY</div>
        <div class="evidence-val">${metrics.execution_time_ms ?? '—'} ms</div>
      </div>
      <div class="evidence-card">
        <div class="evidence-title">FIREWALL CHECKS</div>
        <div class="evidence-val">
          Read-Only: ${readOnlyStatus}<br>
          AST Safe: ${firewallStatus}<br>
          Allowlisted Tables: ${allowlistStatus}
        </div>
      </div>
      <div class="evidence-card">
        <div class="evidence-title">ANALYTICAL ASSUMPTIONS</div>
        <div class="evidence-val">${(data.assumptions || []).join('; ') || 'Standard telecom measurement boundaries.'}</div>
      </div>
    `;
  }

  // =========================================================================
  // DATA SOURCES VIEW
  // =========================================================================
  async function loadDataSources() {
    const container = document.getElementById('tables-list-container');
    container.innerHTML = '<div style="color:var(--text-muted);font-family:var(--font-mono);font-size:12px;">Loading DataMart schema and row telemetry...</div>';

    try {
      const res = await apiFetch('/api/datasources', {}, 15000);
      const data = await res.json();
      state.datasources = data;

      if (!data || !Array.isArray(data.tables)) {
        throw new Error('Unexpected response format from DataSources endpoint.');
      }

      container.innerHTML = '';
      data.tables.forEach(table => {
        const card = document.createElement('div');
        card.className = 'table-meta-card';

        const colsChips = table.columns.slice(0, 6).map(c => `<span class="tm-col-chip">${c.name}</span>`).join('');
        const extraCount = table.columns.length > 6 ? `<span class="tm-col-chip">+${table.columns.length - 6} more</span>` : '';

        card.innerHTML = `
          <div class="tm-header">
            <span class="tm-title">${table.name}</span>
            <span class="tm-count">${typeof table.row_count === 'number' ? table.row_count.toLocaleString() + ' rows' : 'Connected'}</span>
          </div>
          <p class="tm-desc">${table.description}</p>
          <div class="tm-cols-title">COLUMNS (${table.columns.length})</div>
          <div class="tm-cols-chips">${colsChips}${extraCount}</div>
          <div class="tm-footer">
            <button class="btn-preview-table" data-table="${table.name}">Preview Table Data</button>
          </div>
        `;

        card.querySelector('.btn-preview-table').addEventListener('click', () => {
          previewTable(table.name);
        });

        container.appendChild(card);
      });
    } catch (err) {
      container.innerHTML = `<div style="color:#ef4444;font-size:13px;">Error loading data sources: ${err.message}</div>`;
    }
  }

  async function previewTable(tableName) {
    previewModalTitle.textContent = `DataMart Preview: ${tableName}`;
    previewTableContainer.innerHTML = '<div style="color:var(--text-muted);font-family:var(--font-mono);font-size:12px;padding:30px;">Loading live records from SQLite...</div>';
    openModal(previewModal);

    try {
      const res = await apiFetch(`/api/datasources/${encodeURIComponent(tableName)}/preview?limit=15`, {}, 15000);
      const data = await res.json();

      if (!data || !Array.isArray(data.columns) || !Array.isArray(data.rows)) {
        throw new Error('Unexpected preview response format.');
      }

      let html = '<table class="data-table"><thead><tr>';
      data.columns.forEach(col => { html += `<th>${escapeHtml(col)}</th>`; });
      html += '</tr></thead><tbody>';

      data.rows.forEach(r => {
        html += '<tr>';
        r.forEach(c => { html += `<td>${escapeHtml(String(c))}</td>`; });
        html += '</tr>';
      });
      html += '</tbody></table>';

      previewTableContainer.innerHTML = html;
    } catch (err) {
      previewTableContainer.innerHTML = `<div style="color:#ef4444;padding:20px;">Error: ${err.message}</div>`;
    }
  }

  async function handleUploadSimulation(filename) {
    const table = uploadTargetTable.value;
    uploadStatusMsg.classList.remove('hidden');
    uploadStatusMsg.style.backgroundColor = 'rgba(0, 162, 255, 0.15)';
    uploadStatusMsg.style.color = '#38bdf8';
    uploadStatusMsg.textContent = `Validating schema and zero PII policies for '${filename}'...`;

    try {
      const res = await apiFetch('/api/datasources/upload', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          table_name: table,
          file_name: filename,
          records_count: 250,
        }),
      }, 20000);

      const data = await res.json();
      uploadStatusMsg.style.backgroundColor = 'var(--accent-green-subtle)';
      uploadStatusMsg.style.color = 'var(--accent-green)';
      uploadStatusMsg.textContent = data.message || 'Upload staged successfully.';
      setTimeout(() => {
        closeModal(uploadModal);
        uploadStatusMsg.classList.add('hidden');
        if (state.currentView === 'datasources') loadDataSources();
      }, 1800);
    } catch (err) {
      uploadStatusMsg.style.color = '#ef4444';
      uploadStatusMsg.style.backgroundColor = 'rgba(239, 68, 68, 0.1)';
      if (err.isTimeout) {
        uploadStatusMsg.textContent = 'Upload timed out. Please try again.';
      } else {
        uploadStatusMsg.textContent = `Upload failed: ${err.message}`;
      }
    }
  }

  // =========================================================================
  // QUERY HISTORY VIEW
  // =========================================================================
  async function loadHistory() {
    const tbody = document.getElementById('history-table-body');
    tbody.innerHTML = '<tr><td colspan="7" style="color:var(--text-muted);font-family:var(--font-mono);padding:20px;">Loading history...</td></tr>';

    try {
      const res = await apiFetch('/api/history', {}, 15000);
      const data = await res.json();
      state.history = data;

      if (!Array.isArray(data) || data.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" style="color:var(--text-muted);padding:20px;">No queries run yet in this session.</td></tr>';
        return;
      }

      tbody.innerHTML = '';
      data.forEach(item => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td style="font-family:var(--font-mono);font-size:11px;">${escapeHtml(String(item.timestamp || '—'))}</td>
          <td style="font-weight:500;color:#ffffff;">${escapeHtml(item.question || '—')}</td>
          <td style="font-family:var(--font-mono);font-size:11px;">${escapeHtml((item.tables_used || []).join(', '))}</td>
          <td style="font-family:var(--font-mono);font-size:11px;">${item.row_count || 0}</td>
          <td style="font-family:var(--font-mono);font-size:11px;">${item.execution_time_ms || 0} ms</td>
          <td><span class="badge-confidence" style="font-size:10px;">${escapeHtml(item.confidence || 'HIGH')}</span></td>
          <td><button class="btn-icon-subtle btn-rerun-query">Re-run</button></td>
        `;

        tr.querySelector('.btn-rerun-query').addEventListener('click', () => {
          switchView('ask-data');
          queryInput.value = item.question;
          executeQuery(item.question);
        });

        tbody.appendChild(tr);
      });
    } catch (err) {
      const msg = err.isTimeout
        ? 'Request timed out loading history.'
        : err.message || 'Failed to load history.';
      tbody.innerHTML = `<tr><td colspan="7" style="color:#ef4444;padding:16px;">
        <strong>Could not load query history.</strong><br>
        <span style="font-size:11px;color:#fca5a5;">${escapeHtml(msg)}</span>
      </td></tr>`;
    }
  }

  // =========================================================================
  // SAVED INSIGHTS VIEW
  // =========================================================================
  async function loadSavedInsights() {
    const container = document.getElementById('saved-insights-container');
    container.innerHTML = '<div style="color:var(--text-muted);font-family:var(--font-mono);font-size:12px;">Loading saved insights...</div>';

    try {
      const res = await apiFetch('/api/insights/saved', {}, 15000);
      const data = await res.json();
      state.savedInsights = data;

      if (!Array.isArray(data) || data.length === 0) {
        container.innerHTML = '<div style="color:var(--text-muted);padding:30px;">No saved insights yet. Bookmark any answer from Ask Data.</div>';
        return;
      }

      container.innerHTML = '';
      data.forEach(item => {
        const card = document.createElement('div');
        card.className = 'insight-card';
        card.innerHTML = `
          <div class="ic-header">
            <span class="ic-title">${escapeHtml(item.title || item.question || 'Insight')}</span>
            <span class="ic-date">${escapeHtml(item.saved_at || 'Saved')}</span>
          </div>
          <div class="ic-q">"${escapeHtml(item.question || '')}"</div>
          <div class="ic-insight">${escapeHtml(item.key_insight || '')}</div>
          <div class="ic-footer">
            <button class="btn-primary btn-inspect-insight" style="padding:4px 12px;font-size:11px;">Inspect Query</button>
            <button class="btn-del-insight" data-id="${escapeHtml(item.id)}">Remove</button>
          </div>
        `;

        card.querySelector('.btn-inspect-insight').addEventListener('click', () => {
          switchView('ask-data');
          queryInput.value = item.question || '';
          if (item.question) executeQuery(item.question);
        });

        card.querySelector('.btn-del-insight').addEventListener('click', async (e) => {
          const btn = e.currentTarget;
          btn.disabled = true;
          btn.textContent = 'Removing...';
          try {
            await apiFetch(`/api/insights/saved/${encodeURIComponent(item.id)}`, { method: 'DELETE' }, 10000);
            loadSavedInsights();
          } catch (delErr) {
            btn.disabled = false;
            btn.textContent = 'Remove';
            console.error('Failed to delete insight:', delErr);
          }
        });

        container.appendChild(card);
      });
    } catch (err) {
      const msg = err.isTimeout
        ? 'Request timed out loading insights.'
        : err.message || 'Failed to load saved insights.';
      container.innerHTML = `
        <div style="color:#ef4444;padding:20px;">
          <strong>Could not load saved insights.</strong><br>
          <span style="font-size:12px;color:#fca5a5;">${escapeHtml(msg)}</span>
        </div>`;
    }
  }

  // =========================================================================
  // KNOWLEDGE LAYER VIEW
  // =========================================================================
  async function loadKnowledge() {
    const vectorStatus = document.getElementById('knowledge-vector-status');
    const glossaryContainer = document.getElementById('glossary-items-container');
    const goldenContainer = document.getElementById('golden-items-container');
    const relContainer = document.getElementById('relationships-container');

    try {
      const res = await apiFetch('/api/knowledge', {}, 15000);
      const data = await res.json();
      state.knowledge = data;

      vectorStatus.textContent = `✓ Vector Store: ${data.vector_store_documents || 0} docs (${data.embedding_model || 'N/A'})`;

      // Render Glossary
      glossaryContainer.innerHTML = '';
      data.glossary.forEach(item => {
        const card = document.createElement('div');
        card.className = 'glossary-card';
        card.innerHTML = `
          <div class="gc-term">${escapeHtml(item.term)}</div>
          <p class="gc-def">${escapeHtml(item.definition)}</p>
          <div class="gc-calc">Formula: ${escapeHtml(item.calculation)}</div>
        `;
        glossaryContainer.appendChild(card);
      });

      // Render Golden Queries
      goldenContainer.innerHTML = '';
      data.golden_examples.forEach(item => {
        const card = document.createElement('div');
        card.className = 'golden-card';
        card.innerHTML = `
          <div class="golden-title">${escapeHtml(item.title)}</div>
          <div class="golden-q">"${escapeHtml(item.question)}"</div>
          <pre class="sql-code-block"><code>${escapeHtml(item.sql)}</code></pre>
        `;
        goldenContainer.appendChild(card);
      });

      // Render Relationships
      relContainer.innerHTML = '<div style="display:flex;flex-direction:column;gap:12px;">';
      data.relationships.forEach(rel => {
        relContainer.innerHTML += `
          <div class="rule-item-card">
            <div class="rule-name" style="font-family:var(--font-mono);font-size:12px;">${rel.from} → ${rel.to}</div>
            <div class="rule-desc">Relational Join Cardinality: ${rel.type}</div>
          </div>
        `;
      });
      relContainer.innerHTML += '</div>';

      if (!state.knowledgeTabsBound) {
        const ktabBtns = document.querySelectorAll('.ktab-btn');
        const ktabContents = document.querySelectorAll('.ktab-content');
        ktabBtns.forEach(btn => {
          btn.addEventListener('click', () => {
            ktabBtns.forEach(b => b.classList.remove('active'));
            ktabContents.forEach(c => c.classList.remove('active'));
            btn.classList.add('active');
            const target = document.getElementById(btn.getAttribute('data-ktab'));
            if (target) target.classList.add('active');
          });
        });
        state.knowledgeTabsBound = true;
      }

    } catch (err) {
      vectorStatus.textContent = 'Vector Store: Offline';
    }
  }

  // =========================================================================
  // SECURITY VIEW & SANDBOX
  // =========================================================================
  async function loadSecurity() {
    const list = document.getElementById('security-rules-list');
    list.innerHTML = '<div style="color:var(--text-muted);font-family:var(--font-mono);font-size:12px;">Loading policies...</div>';

    try {
      const res = await apiFetch('/api/security/policies', {}, 15000);
      const data = await res.json();
      state.security = data;

      if (!data || !Array.isArray(data.rules)) {
        throw new Error('Unexpected response from security policies endpoint.');
      }

      list.innerHTML = '';
      data.rules.forEach(r => {
        const item = document.createElement('div');
        item.className = 'rule-item-card';
        item.innerHTML = `
          <div class="rule-head">
            <span class="rule-name">${escapeHtml(r.name)}</span>
            <span class="rule-id">${r.rule_id}</span>
          </div>
          <p class="rule-desc">${escapeHtml(r.description)}</p>
        `;
        list.appendChild(item);
      });
    } catch (err) {
      list.innerHTML = `<div style="color:#ef4444;">Error: ${err.message}</div>`;
    }
  }

  async function testSecuritySandbox() {
    const sql = sandboxSqlInput.value.trim();
    if (!sql) return;

    btnTestSandbox.disabled = true;
    btnTestSandbox.innerHTML = '<span>VALIDATING...</span>';

    try {
      const res = await apiFetch('/api/security/validate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sql }),
      }, 15000);
      const data = await res.json();

      sandboxResultBox.classList.remove('hidden');
      if (data.is_valid) {
        sandboxResultBox.style.borderColor = 'var(--accent-green)';
        sandboxResultBox.innerHTML = `
          <div style="color:var(--accent-green);font-weight:700;margin-bottom:6px;">✓ PASSED FIREWALL VALIDATION</div>
          <div style="color:var(--text-secondary);margin-bottom:4px;">Tables Accessed: ${(data.tables_used || []).join(', ') || 'None'}</div>
          <div style="color:var(--text-muted);">${data.warnings.length ? data.warnings.join('; ') : 'No warnings. Pure read-only query.'}</div>
        `;
      } else {
        sandboxResultBox.style.borderColor = '#ef4444';
        sandboxResultBox.innerHTML = `
          <div style="color:#ef4444;font-weight:700;margin-bottom:6px;">✕ BLOCKED BY SQL FIREWALL</div>
          <div style="color:#fca5a5;">${data.errors.join('<br>')}</div>
        `;
      }
    } catch (err) {
      sandboxResultBox.classList.remove('hidden');
      sandboxResultBox.style.borderColor = '#ef4444';
      sandboxResultBox.innerHTML = `<div style="color:#ef4444;">Error: ${err.message}</div>`;
    } finally {
      btnTestSandbox.disabled = false;
      btnTestSandbox.innerHTML = '<span>VALIDATE SQL</span><span class="btn-arrow">→</span>';
    }
  }

  // =========================================================================
  // AUDIT LOG VIEW
  // =========================================================================
  async function loadAuditLogs() {
    const tbody = document.getElementById('audit-table-body');
    tbody.innerHTML = '<tr><td colspan="8" style="color:var(--text-muted);font-family:var(--font-mono);padding:20px;">Loading audit trail...</td></tr>';

    try {
      const res = await apiFetch('/api/audit/logs', {}, 15000);
      const data = await res.json();
      state.auditLogs = data;

      if (!Array.isArray(data) || data.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" style="color:var(--text-muted);padding:20px;">No audit events recorded yet.</td></tr>';
        return;
      }

      tbody.innerHTML = '';
      data.forEach(log => {
        const tr = document.createElement('tr');
        const decisionColor = log.firewall_decision === 'ALLOWED' ? 'var(--accent-green)' : '#ef4444';
        tr.innerHTML = `
          <td style="font-family:var(--font-mono);font-size:11px;">${log.audit_id}</td>
          <td style="font-family:var(--font-mono);font-size:11px;">${log.timestamp}</td>
          <td style="font-size:12px;">${escapeHtml(log.user)}</td>
          <td style="font-family:var(--font-mono);font-size:11px;">${log.action}</td>
          <td style="font-family:var(--font-mono);font-size:11px;font-weight:700;color:${decisionColor}">${log.firewall_decision}</td>
          <td style="font-family:var(--font-mono);font-size:11px;">${(log.tables_accessed || []).join(', ')}</td>
          <td style="font-family:var(--font-mono);font-size:11px;">${log.execution_ms} ms</td>
          <td><span class="badge-confidence" style="font-size:10px;">${log.confidence || 'HIGH'}</span></td>
        `;
        tbody.appendChild(tr);
      });
    } catch (err) {
      const msg = err.isTimeout
        ? 'Request timed out loading audit logs.'
        : err.message || 'Failed to load audit logs.';
      tbody.innerHTML = `<tr><td colspan="8" style="color:#ef4444;padding:16px;">
        <strong>Could not load audit trail.</strong><br>
        <span style="font-size:11px;color:#fca5a5;">${escapeHtml(msg)}</span>
      </td></tr>`;
    }
  }

  // =========================================================================
  // SETTINGS MODAL
  // =========================================================================
  async function loadSettings() {
    try {
      const res = await apiFetch('/api/settings', {}, 10000);
      const data = await res.json();
      const ollamaUrlEl = document.getElementById('setting-ollama-url');
      const ollamaModelEl = document.getElementById('setting-ollama-model');
      const ragTopkEl = document.getElementById('setting-rag-topk');
      const freshnessEl = document.getElementById('setting-freshness-note');
      if (ollamaUrlEl) ollamaUrlEl.value = data.ollama_base_url || 'http://localhost:11434';
      if (ollamaModelEl) ollamaModelEl.value = data.ollama_model || 'llama3:latest';
      if (ragTopkEl) ragTopkEl.value = data.rag_top_k || 4;
      if (freshnessEl) freshnessEl.value = data.data_freshness || 'UPDATED TODAY';
    } catch (err) {
      console.warn('Load settings failed:', err.message);
    }
  }

  async function saveSettings() {
    btnSaveSettings.disabled = true;
    btnSaveSettings.textContent = 'Saving...';

    try {
      const payload = {
        ollama_base_url: document.getElementById('setting-ollama-url').value.trim(),
        ollama_model: document.getElementById('setting-ollama-model').value.trim(),
        rag_top_k: parseInt(document.getElementById('setting-rag-topk').value, 10),
        data_refresh_note: document.getElementById('setting-freshness-note').value.trim(),
      };

      await apiFetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      }, 10000);

      closeModal(settingsModal);
      checkSystemStatus();
    } catch (err) {
      // Show error in the modal rather than a disruptive alert
      const errEl = document.getElementById('settings-error-msg');
      if (errEl) {
        errEl.textContent = `Failed to save: ${err.message}`;
        errEl.style.display = 'block';
        setTimeout(() => { errEl.style.display = 'none'; }, 4000);
      } else {
        console.error('Failed to save settings:', err.message);
      }
    } finally {
      btnSaveSettings.disabled = false;
      btnSaveSettings.innerHTML = '<span>SAVE CONFIG</span><span class="btn-arrow">→</span>';
    }
  }

  // =========================================================================
  // MODAL HELPERS
  // =========================================================================
  function openModal(modal) {
    modal.classList.add('open');
  }

  function closeModal(modal) {
    modal.classList.remove('open');
  }

  function escapeHtml(str) {
    if (typeof str !== 'string') return String(str);
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }
});
