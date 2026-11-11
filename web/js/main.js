/* main.js — bootstrap SPA Keyword Studio. Modul lain berisi fitur per view. */

import { $, state, secs } from './core.js';
import { copy, showView } from './ui.js';
import { wireMarkets, requireMarkets } from './markets.js';
import { wireSingle, bindUploadHooks } from './upload.js';
import { wireBatch, bindBatchHooks } from './batch.js';
import { wireExtract, bindExtractHooks } from './extract.js';
import { wireHistory, bindHistoryHooks, loadHistory, setHistoryScope } from './history.js';
import { wireSettings, bindSettingsHooks, loadSettings } from './settings.js';
import { wireImage, bindImageHooks } from './image.js';
import { handleSignalsClick, payloadFor } from './signals.js';
import { handleTrendsClick } from './trends.js';

async function loadStats() {
  try {
    const [s, c] = await Promise.all([
      (await fetch('/api/stats')).json(),
      (await fetch('/api/config')).json(),
    ]);
    $('#stat-total').textContent = s.total ?? 0;
    $('#stat-avg').textContent = s.avg_ms ? secs(s.avg_ms) : '—';
    $('#stat-model').textContent = c.model || '—';
    $('#stat-model').title = c.model + (c.fallbacks?.length ? ' (+' + c.fallbacks.length + ' fallback)' : '');
    $('#stat-image-model').textContent = c.image_model || '—';
    $('#stat-image-model').title = c.image_model || '';
  } catch {}
}

function wireChrome() {
  $('#nav').addEventListener('click', (e) => {
    const b = e.target.closest('.nav-item');
    if (!b) return;
    if (b.dataset.view === 'history') {
      setHistoryScope(b.dataset.scope || 'keyword');
    }
    showView(b.dataset.view);
  });
}

function wireCopyHandlers() {
  document.addEventListener('click', (e) => {
    const chip = e.target.closest('.chip[data-tag]');
    if (chip) {
      copy(chip.dataset.tag, 'Tag disalin');
      if (!chip.classList.contains('plain')) {
        chip.classList.add('is-copied');
        setTimeout(() => chip.classList.remove('is-copied'), 900);
      }
      return;
    }

    if (handleTrendsClick(e)) return;
    if (handleSignalsClick(e)) return;

    const descBtn = e.target.closest('[data-copy-desc]');
    if (descBtn) {
      copy(descBtn.dataset.copyText || '', 'Deskripsi disalin');
      return;
    }

    const cb = e.target.closest('[data-copy]');
    if (!cb) return;
    const host = cb.closest('[data-has-result]')?.parentElement || cb.closest('.drawer-body');
    const d = host && host._data;
    if (!d) return;
    const text = payloadFor(cb.dataset.copy, d);
    copy(text, cb.dataset.copy === 'Semua' ? 'Semua disalin' : cb.dataset.copy + ' disalin');
  });
}

window.__kwLoadHistory = loadHistory;
window.__kwLoadSettings = loadSettings;
window.__kwSetHistoryScope = setHistoryScope;

bindUploadHooks({ requireMarkets, hideStatus: () => { $('#single-status').hidden = true; }, loadStats });
bindBatchHooks({ requireMarkets, loadStats });
bindExtractHooks({ loadStats });
bindHistoryHooks({ loadStats });
bindSettingsHooks({ loadStats });
bindImageHooks({ loadStats });

wireChrome();
wireCopyHandlers();
wireMarkets();
wireSingle();
wireBatch();
wireExtract();
wireHistory();
wireSettings();
wireImage();
showView('single');
loadStats();
