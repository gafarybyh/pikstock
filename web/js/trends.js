/* trends.js — panel pembuat link Google Trends. */

const MAX_TERMS = 5;
const GEO_KEY = 'kw.trendGeo';
const DEFAULT_GEO = 'US';
const DEFAULT_HINT = 'Google Trends terbuka di tab baru. Maksimal 5 keyword.';

const GEO_OPTIONS = [
  ['US', 'Amerika Serikat'],
  ['ID', 'Indonesia'],
  ['GB', 'Inggris'],
  ['CA', 'Kanada'],
  ['AU', 'Australia'],
  ['', 'Seluruh dunia'],
];

export function trendPanelHTML() {
  return `<section class="trend-panel" data-trend-panel hidden aria-label="Google Trends">
    <div class="trend-head">
      <div class="trend-intro">
        <div class="field-label">Google Trends · 12 bulan</div>
        <div class="trend-title">Minat pencarian relatif</div>
      </div>
      <div class="trend-controls">
        <label class="trend-field">
          <span class="field-label">Keyword (maks 5)</span>
          <input class="input trend-terms" id="trend-terms" name="trend_terms" data-trend-terms
                 type="text" maxlength="504" placeholder="pisahkan dengan koma"
                 autocomplete="off" spellcheck="false">
        </label>
        <label class="trend-field trend-field-geo">
          <span class="field-label">Negara</span>
          <select class="input" id="trend-geo" name="trend_geo" data-trend-geo autocomplete="off">
            ${GEO_OPTIONS.map(([value, label]) => `<option value="${value}">${label}</option>`).join('')}
          </select>
        </label>
        <a class="btn btn-primary" data-trend-open href="https://trends.google.com/trends/explore"
           target="_blank" rel="noopener" aria-label="Buka Google Trends di tab baru">Buka Google Trends</a>
      </div>
    </div>
    <p class="trend-status" data-trend-status role="status" aria-live="polite">${DEFAULT_HINT}</p>
  </section>`;
}

function seedTerms(data) {
  const seen = new Set();
  const out = [];
  for (const raw of [
    ...(data.etsy_tags || []),
    ...(data.canva_tags || []),
    ...(data.universal_tags || []),
    ...(data.adobe_tags || []),
    ...(data.creative_market_tags || []),
    data.subject,
    data.universal_title,
  ]) {
    const term = String(raw || '').trim();
    const key = term.toLowerCase();
    if (term && !seen.has(key)) {
      seen.add(key);
      out.push(term);
    }
    if (out.length >= MAX_TERMS) break;
  }
  return out;
}

function allTerms(value) {
  return String(value || '')
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean);
}

function parseTerms(value) {
  return allTerms(value).slice(0, MAX_TERMS);
}

function termHint(value) {
  return allTerms(value).length > MAX_TERMS
    ? 'Maksimal 5 keyword; hanya 5 pertama yang dipakai.'
    : DEFAULT_HINT;
}

function trendsUrl(terms, geo) {
  const query = terms.map((item) => encodeURIComponent(item)).join(',');
  const geoPart = geo ? `geo=${encodeURIComponent(geo)}&` : '';
  return `https://trends.google.com/trends/explore?${geoPart}q=${query}`;
}

function setStatus(panel, message, bad = false) {
  const el = panel.querySelector('[data-trend-status]');
  if (!el) return;
  el.textContent = message || '';
  el.classList.toggle('is-bad', bad);
}

function updateLink(panel) {
  const input = panel.querySelector('[data-trend-terms]');
  const select = panel.querySelector('[data-trend-geo]');
  const link = panel.querySelector('[data-trend-open]');
  if (!input || !link) return;
  const terms = parseTerms(input.value);
  link.href = terms.length
    ? trendsUrl(terms, select?.value || '')
    : 'https://trends.google.com/trends/explore';
  link.setAttribute('aria-disabled', terms.length ? 'false' : 'true');
}

function openPanel(button) {
  const host = button.closest('[data-has-result]')?.parentElement || button.closest('.drawer-body');
  const panel = host?.querySelector('[data-trend-panel]');
  if (!panel) return;
  const opening = panel.hidden;
  panel.hidden = !opening;
  button.setAttribute('aria-expanded', opening ? 'true' : 'false');
  button.textContent = opening ? 'Tutup Trend' : 'Lihat Trend';
  if (!opening) return;

  const input = panel.querySelector('[data-trend-terms]');
  if (input && !input.value.trim()) {
    input.value = seedTerms(host._data || {}).join(', ');
  }

  const select = panel.querySelector('[data-trend-geo]');
  if (select) {
    const saved = localStorage.getItem(GEO_KEY);
    if (saved != null && [...select.options].some((option) => option.value === saved)) {
      select.value = saved;
    } else if (![...select.options].some((option) => option.value === select.value)) {
      select.value = DEFAULT_GEO;
    }
  }

  if (!panel.dataset.wired) {
    input?.addEventListener('input', () => {
      setStatus(panel, termHint(input.value));
      updateLink(panel);
    });
    select?.addEventListener('change', () => {
      localStorage.setItem(GEO_KEY, select.value);
      setStatus(panel, DEFAULT_HINT);
      updateLink(panel);
    });
    panel.dataset.wired = '1';
  }

  setStatus(panel, DEFAULT_HINT);
  updateLink(panel);
}

export function handleTrendsClick(event) {
  const toggle = event.target.closest('[data-trends]');
  if (toggle) {
    openPanel(toggle);
    return true;
  }

  const open = event.target.closest('[data-trend-open]');
  if (open) {
    const panel = open.closest('[data-trend-panel]');
    const input = panel?.querySelector('[data-trend-terms]');
    const select = panel?.querySelector('[data-trend-geo]');
    const terms = parseTerms(input?.value);
    if (!terms.length) {
      event.preventDefault();
      if (panel) setStatus(panel, 'Isi minimal satu keyword dulu.', true);
      input?.focus();
      return true;
    }
    localStorage.setItem(GEO_KEY, select?.value || '');
    open.href = trendsUrl(terms, select?.value || '');
    if (panel) setStatus(panel, termHint(input?.value));
    return true;
  }
  return false;
}
