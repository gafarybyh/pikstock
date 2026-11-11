import { $, esc, secs } from './core.js';
import { toast, emptyHTML, skeletonHTML, pop } from './ui.js';

const MAX_PROMPT = 4000;
let hooks = { loadStats: () => {} };
let busy = false;

export function bindImageHooks(h) {
  hooks = { ...hooks, ...h };
}

function setStatus(msg, bad = false) {
  const el = $('#img-status');
  el.textContent = msg || '';
  el.classList.toggle('is-bad', bad);
}

function syncCount() {
  const len = $('#img-prompt').value.length;
  $('#img-count').textContent = len;
  $('#img-count').closest('.set-hint').classList.toggle('is-over', len > MAX_PROMPT * 0.9);
}

function imageCardHTML(file, i, d, res) {
  const src = `/generate/${encodeURIComponent(file)}`;
  const size = d.sizes?.[i] || '';
  return `<article class="card img-gen-card">
    <a class="img-gen-link" href="${src}" target="_blank" rel="noopener">
      <img src="${src}" alt="Hasil generate: ${esc(d.prompt || '')}" loading="lazy"></a>
    <div class="card-body">
      <p class="field-val">${esc(d.prompt || '')}</p>
      <div class="img-gen-foot">
        <span class="img-gen-meta">${esc(secs(res.duration_ms || 0))}${size ? ' · ' + esc(size) : ''}${d.model ? ' · ' + esc(d.model) : ''}</span>
        <a class="btn btn-ghost" href="${src}" download>Unduh</a>
      </div>
    </div>
  </article>`;
}

function errorCardHTML(message) {
  return `<article class="card img-gen-card is-bad"><div class="card-body">
    <p class="field-val">Gagal: ${esc(message || 'tidak diketahui')}</p>
  </div></article>`;
}

function renderResults(res) {
  const area = $('#img-result');
  if (res.status !== 'ok') {
    area.innerHTML = `<div class="img-gen-grid">${errorCardHTML(res.error)}</div>`;
    pop(area.querySelector('.img-gen-card'));
    return;
  }
  const d = res.data || {};
  area.innerHTML = `<div class="img-gen-grid">${
    (d.images || []).map((file, i) => imageCardHTML(file, i, d, res)).join('')}</div>`;
  area.querySelectorAll('.img-gen-card').forEach((n, i) => pop(n, i * .06));
}

async function generate(e) {
  e.preventDefault();
  if (busy) return;
  const prompt = $('#img-prompt').value.trim();
  if (!prompt) {
    setStatus('Prompt wajib diisi.', true);
    return;
  }
  if (prompt.length > MAX_PROMPT) {
    setStatus(`Prompt maksimal ${MAX_PROMPT} karakter.`, true);
    return;
  }
  const body = {
    prompt,
    n: Number($('#img-n').value),
    size: $('#img-size').value || null,
  };
  busy = true;
  $('#img-run').disabled = true;
  $('#img-result').innerHTML = skeletonHTML();
  setStatus('Sedang generate…');
  try {
    const r = await fetch('/api/image/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const res = await r.json().catch(() => ({}));
    if (!r.ok) {
      renderResults({ status: 'error', error: res.detail || 'Permintaan gagal' });
      setStatus('Generate gagal.', true);
      return;
    }
    renderResults(res);
    setStatus('Selesai. Tersimpan di Riwayat Gambar.');
    toast('Gambar selesai dibuat');
    hooks.loadStats();
  } catch (err) {
    renderResults({ status: 'error', error: err.message });
    setStatus('Generate gagal.', true);
  } finally {
    busy = false;
    $('#img-run').disabled = false;
  }
}

export function wireImage() {
  $('#img-prompt').addEventListener('input', syncCount);
  $('#img-result').innerHTML = emptyHTML('Belum ada gambar',
    'Tulis prompt di atas lalu klik Generate. Hasil muncul di sini dan tersimpan di Riwayat Gambar.', 'image');
  syncCount();
  $('#img-form').addEventListener('submit', generate);
}
