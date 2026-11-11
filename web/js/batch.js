/* batch.js — mode batch: pilih folder, grid thumbnail dari disk, SSE progres. */

import { $, M, reduced, state, esc, secs } from './core.js';
import { toast, pop, popProgress, emptyHTML, resetFill } from './ui.js';

let requireMarkets = () => true;
let loadStatsFn = () => {};

export function bindBatchHooks(hooks) {
  requireMarkets = hooks.requireMarkets || requireMarkets;
  loadStatsFn = hooks.loadStats || loadStatsFn;
}

async function postJSON(url, body) {
  const r = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!r.ok) {
    let msg = 'Permintaan gagal';
    try { msg = (await r.json()).detail || msg; } catch {}
    throw new Error(msg);
  }
  return r.json();
}

function renderGrid() {
  const grid = $('#batch-grid');
  if (!state.files.length) {
    grid.innerHTML = emptyHTML('Belum ada gambar',
      'Klik "Pilih folder" untuk memuat thumbnail dari disk. Kamu bisa centang beberapa sekaligus.', 'folder');
    return;
  }
  grid.innerHTML = state.files.map((f, i) => `
    <div class="thumb-card${state.selected.has(i) ? ' is-sel' : ''}" data-i="${i}">
      <div class="tc-box">✓</div>
      <div class="tc-name" title="${esc(f.name)}">${esc(f.name)}</div>
    </div>`).join('');

  grid.querySelectorAll('.thumb-card').forEach((card) => {
    const f = state.files[+card.dataset.i];
    const img = new Image();
    img.alt = f.name;
    img.onload = () => card.insertBefore(img, card.firstChild);
    img.onerror = () => {};
    img.src = `/api/thumb?path=${encodeURIComponent(f.path)}`;
  });

  const nodes = [...grid.children];
  if (M.animate && !reduced) {
    M.animate(nodes, { opacity: [0, 1], transform: ['scale(.94)', 'scale(1)'] },
      { duration: .3, delay: M.stagger(.012), easing: 'ease-out' });
  }
  updateSel();
}

function updateSel() {
  const n = state.selected.size;
  const marketsOk = state.markets.length > 0;
  $('#sel-count').textContent = `${n} dipilih`;
  $('#run-batch').disabled = n === 0 || state.running || !marketsOk;
  $('#run-batch').title = !marketsOk
    ? 'Pilih minimal satu marketplace'
    : n === 0 ? 'Pilih minimal satu gambar' : '';
  $('#sel-all').checked = n === state.files.length && n > 0;
}

function setThumbState(i, cls) {
  const card = document.querySelector(`.thumb-card[data-i="${i}"]`);
  if (!card) return;
  card.classList.remove('is-done', 'is-fail');
  card.classList.add(cls);
  if (cls === 'is-done') card.querySelector('.tc-box').textContent = '✓';
}

function logRow(name, msg, cls) {
  const log = $('#batch-log');
  const row = document.createElement('div');
  row.className = 'log-row' + (cls ? ' ' + cls : '');
  row.innerHTML = `<span class="lname">${esc(name)}</span><span class="lmsg">${esc(msg)}</span>`;
  log.prepend(row);
  while (log.children.length > 120) log.lastChild.remove();
  pop(row);
}

function finishBatch(msg) {
  state.running = false;
  state.batchId = null;
  $('#cancel-batch').hidden = true;
  $('#sel-all').disabled = false;
  $('#run-batch').disabled = state.selected.size === 0;
  toast(msg);
  loadStatsFn();
}

function listenBatch() {
  const es = new EventSource('/api/events/' + state.batchId);
  state.es = es;
  let done = 0;

  es.onmessage = (ev) => {
    const m = JSON.parse(ev.data);
    const i = m.index - 1;

    if (m.type === 'start') {
      $('#prog-current').textContent = 'Memproses ' + m.filename;
      logRow(m.filename, 'diproses…', '');
    } else if (m.type === 'ok') {
      done++;
      setThumbState(i, 'is-done');
      logRow(m.filename, 'berhasil · ' + secs(m.result.duration_ms), 'is-ok');
    } else if (m.type === 'error') {
      setThumbState(i, 'is-fail');
      logRow(m.filename, 'gagal: ' + (m.error || '').slice(0, 90), 'is-fail');
    } else if (m.type === 'done' || m.type === 'cancelled') {
      const pct = m.total ? Math.round((m.done / m.total) * 100) : 100;
      popProgress(pct);
      $('#prog-text').textContent = `${m.done}/${m.total} berhasil${
        m.failed ? `, ${m.failed} gagal` : ''}`;
      $('#prog-current').textContent = m.type === 'cancelled' ? 'Dibatalkan' : 'Semua selesai';
      es.close();
      state.es = null;
      finishBatch(m.type === 'cancelled' ? 'Proses Folder dibatalkan' : 'Proses Folder selesai');
    }
  };

  es.onerror = () => {
    es.close();
    state.es = null;
    if (state.running) finishBatch('Koneksi ke server terputus');
  };
}

async function startBatch() {
  const files = [...state.selected].sort((a, b) => a - b).map((i) => state.files[i]);
  if (!files.length) return;
  if (!requireMarkets()) return;

  state.running = true;
  state.batchId = null;
  $('#sel-all').disabled = true;
  $('#run-batch').disabled = true;
  $('#cancel-batch').hidden = false;
  $('#progress').hidden = false;
  $('#batch-log').innerHTML = '';
  resetFill($('#prog-fill'));
  $('#prog-text').textContent = '0 / ' + files.length;
  $('#prog-current').textContent = 'Menyiapkan…';
  document.querySelectorAll('.thumb-card').forEach((c) =>
    c.classList.remove('is-done', 'is-fail'));

  try {
    const r = await postJSON('/api/batch', { folder: state.folder, files, marketplaces: state.markets });
    state.batchId = r.batch_id;
    listenBatch();
  } catch (e) {
    finishBatch('Gagal: ' + e.message);
  }
}

export function wireBatch() {
  $('#pick-folder').addEventListener('click', async () => {
    try {
      const r = await postJSON('/api/select-folder', {});
      if (r.cancelled) return;
      state.folder = r.folder;
      state.files = r.images;
      state.selected = new Set();
      $('#folder-label').textContent = r.folder;
      $('#folder-label').title = r.folder;
      $('#batch-staged').hidden = false;
      renderGrid();
      toast(`${r.images.length} gambar ditemukan`);
    } catch (e) { toast('Gagal: ' + e.message); }
  });

  $('#batch-grid').addEventListener('click', (e) => {
    const card = e.target.closest('.thumb-card');
    if (!card || state.running) return;
    const i = +card.dataset.i;
    state.selected.has(i) ? state.selected.delete(i) : state.selected.add(i);
    card.classList.toggle('is-sel');
    updateSel();
  });

  $('#sel-all').addEventListener('change', (e) => {
    state.selected = e.target.checked ? new Set(state.files.map((_, i) => i)) : new Set();
    document.querySelectorAll('.thumb-card').forEach((c) =>
      c.classList.toggle('is-sel', state.selected.has(+c.dataset.i)));
    updateSel();
  });

  document.addEventListener('kw:markets', updateSel);
  $('#run-batch').addEventListener('click', startBatch);
  $('#cancel-batch').addEventListener('click', async () => {
    if (state.batchId) await postJSON(`/api/batch/${state.batchId}/cancel`, {}).catch(() => {});
  });
}
