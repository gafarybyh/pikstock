/* upload.js — mode unggah (single): staging daftar gambar + generate berurutan. */

import { $, M, reduced, state, esc } from './core.js';
import { toast, pop, skeletonHTML, setFill } from './ui.js';
import { mountResult } from './render.js';

let requireMarkets = () => true;
let setStatusFn = () => {};
let hideStatusFn = () => {};
let loadStatsFn = () => {};

export function bindUploadHooks(hooks) {
  requireMarkets = hooks.requireMarkets || requireMarkets;
  setStatusFn = hooks.setStatus || setStatusFn;
  hideStatusFn = hooks.hideStatus || hideStatusFn;
  loadStatsFn = hooks.loadStats || loadStatsFn;
}

const staged = [];
let stagedSeq = 0;
const stagedSelected = new Set();

const STAGE_EXT = /\.(png|jpe?g|webp|gif|bmp)$/i;
const MAX_BYTES = 40 * 1024 * 1024;
export const stageKey = (it) => `${it.name}:${it.file.size}`;

function revokeItem(it) {
  if (it.url && it.url.startsWith('blob:')) URL.revokeObjectURL(it.url);
}

function cardEl(it) {
  const d = document.createElement('div');
  d.className = 'thumb-card is-sel';
  d.dataset.sid = it.id;
  d.innerHTML =
    `<button class="tc-x" data-rm="${it.id}" type="button" title="Hapus ${esc(it.name)}" aria-label="Hapus ${esc(it.name)}">&times;</button>` +
    `<label class="tc-pick">` +
      `<input class="tc-input" type="checkbox" checked aria-label="Pilih ${esc(it.name)}">` +
      `<img loading="lazy" decoding="async" src="${it.url}" alt="">` +
      `<span class="tc-box" aria-hidden="true">&#10003;</span>` +
      `<span class="tc-state" aria-hidden="true"><span class="st-ic"></span></span>` +
    `</label>` +
    `<div class="tc-name" title="${esc(it.name)}">${esc(it.name)}</div>`;
  return d;
}

const stageCard = (id) => $(`.thumb-card[data-sid="${id}"]`, $('#staged-grid'));

function addItems(items) {
  const have = new Set(staged.map(stageKey));
  const grid = $('#staged-grid');
  let dup = 0, bad = 0, big = 0, added = 0;
  for (const it of items) {
    if (!STAGE_EXT.test(it.name)) { bad++; revokeItem(it); continue; }
    if (it.file.size > MAX_BYTES) { big++; revokeItem(it); continue; }
    const k = stageKey(it);
    if (have.has(k)) { revokeItem(it); dup++; continue; }
    have.add(k);
    it.id = ++stagedSeq;
    it.status = 'idle';
    staged.push(it);
    stagedSelected.add(it.id);
    grid.appendChild(cardEl(it));
    if (M.animate && !reduced) {
      M.animate(grid.lastElementChild,
        { opacity: [0, 1], transform: ['scale(.94)', 'scale(1)'] },
        { duration: .28, easing: 'ease-out' });
    }
    added++;
  }
  if (added) updateStaged();
  const notes = [];
  if (bad) notes.push(`${bad} file bukan gambar, dilewati`);
  if (big) notes.push(`${big} gambar lebih dari 40 MB, dilewati`);
  if (dup) notes.push(`${dup} gambar sudah ada, dilewati`);
  if (notes.length) toast(notes.join('; '), bad || big ? 'bad' : '');
  return added;
}

function addFiles(files) {
  return addItems([...files].map((f) => ({
    file: f, name: f.name, url: URL.createObjectURL(f) })));
}

function removeStaged(id) {
  const i = staged.findIndex((s) => s.id === id);
  if (i < 0) return;
  revokeItem(staged[i]);
  staged.splice(i, 1);
  stagedSelected.delete(id);
  stageCard(id)?.remove();
  updateStaged();
}

function clearStage() {
  staged.forEach(revokeItem);
  staged.length = 0;
  stagedSelected.clear();
  $('#staged-grid').innerHTML = '';
  updateStaged();
}

function setStageStatus(id, status) {
  const it = staged.find((s) => s.id === id);
  if (it) it.status = status;
  const card = stageCard(id);
  if (!card) return;
  card.classList.remove('is-running', 'is-done', 'is-fail');
  const ic = card.querySelector('.st-ic');
  if (status === 'running') { card.classList.add('is-running'); ic.textContent = ''; }
  else if (status === 'done') { card.classList.add('is-done'); ic.textContent = '\u2713'; }
  else if (status === 'fail') { card.classList.add('is-fail'); ic.textContent = '\u00d7'; }
}

function updateStaged() {
  const box = $('#staged');
  const busy = state.singleRunning;
  box.hidden = staged.length === 0;
  $('#drop').classList.toggle('is-compact', staged.length > 0);
  if (!staged.length) {
    $('#staged-progress').hidden = true;
    return;
  }

  box.classList.toggle('is-busy', busy);
  $('#staged-count').textContent = `${staged.length} gambar`;

  const done = staged.filter((s) => s.status === 'done').length;
  const fail = staged.filter((s) => s.status === 'fail').length;
  const run = staged.filter((s) => s.status === 'running').length;
  const ready = staged.length - done - fail - run;
  const parts = [`${stagedSelected.size} dari ${staged.length} dipilih`];
  if (ready) parts.push(`${ready} siap`);
  if (run) parts.push(`${run} diproses`);
  if (done) parts.push(`<span class="s-done">${done} selesai</span>`);
  if (fail) parts.push(`<span class="s-fail">${fail} gagal</span>`);
  $('#staged-summary').innerHTML = parts.join(', ');

  syncStagedSel();
}

function syncStagedSel() {
  const n = stagedSelected.size;
  const total = staged.length;
  const busy = state.singleRunning;
  const marketsOk = state.markets.length > 0;

  const master = $('#staged-all');
  master.checked = total > 0 && n === total;
  master.indeterminate = n > 0 && n < total;
  master.disabled = busy || total === 0;

  $('#staged-clear').disabled = busy;

  const run = $('#staged-run');
  run.disabled = busy || n === 0 || !marketsOk;
  const reason = !marketsOk
    ? 'Pilih minimal satu marketplace di atas untuk mulai.'
    : n === 0
      ? 'Centang minimal satu gambar untuk mulai.'
      : '';
  run.title = reason;
  const hint = $('#staged-hint');
  hint.hidden = !reason || busy;
  hint.textContent = reason;

  $('#staged-run-txt').textContent = n ? `Mulai generate (${n})` : 'Mulai generate';

  $('#staged-grid').querySelectorAll('.thumb-card').forEach((c) => {
    const on = stagedSelected.has(+c.dataset.sid);
    c.classList.toggle('is-sel', on);
    const cb = c.querySelector('.tc-input');
    if (cb) { cb.checked = on; cb.disabled = busy; }
    const x = c.querySelector('.tc-x');
    if (x) x.disabled = busy;
  });
}

function toggleStagedSel(id, on) {
  if (on === undefined) on = !stagedSelected.has(id);
  if (on) stagedSelected.add(id); else stagedSelected.delete(id);
  updateStaged();
}

function unselectAll() {
  stagedSelected.clear();
  updateStaged();
}

function selectAll() {
  staged.forEach((s) => stagedSelected.add(s.id));
  updateStaged();
}

function setProgress(i, n, name) {
  $('#staged-progress').hidden = n === 0;
  setFill($('#staged-fill'), n ? (i / n) * 100 : 0);
  $('#staged-ptext').textContent = `${i} / ${n}`;
  $('#staged-pcurrent').textContent = name || '';
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

async function generateOne(item, blockEl) {
  blockEl.innerHTML = skeletonHTML();
  const fd = new FormData();
  fd.append('file', item.file, item.name);
  fd.append('marketplaces', state.markets.join(','));
  const res = await fetch('/api/generate', { method: 'POST', body: fd });
  if (!res.ok) {
    let m = res.statusText;
    try { m = (await res.json()).detail || m; } catch {}
    throw new Error(m);
  }
  const data = await res.json();
  mountResult(blockEl, data, data.data);
}

async function runAll() {
  if (!staged.length || state.singleRunning) return;
  if (!requireMarkets()) return;

  let queue = staged.filter((s) => stagedSelected.has(s.id));
  if (!queue.length) { toast('Pilih minimal satu gambar', 'bad'); return; }

  try {
    const names = [...new Set(queue.map((s) => s.name.toLowerCase()))];
    const r = await postJSON('/api/history/seen', { filenames: names });
    const seen = new Set(r.seen || []);
    const dup = queue.filter((s) => seen.has(s.name.toLowerCase()));
    if (dup.length && confirm(`${dup.length} gambar sudah pernah diproses.\n\nOK = lewati yang sudah ada\nBatal = proses ulang semua`)) {
      queue = queue.filter((s) => !seen.has(s.name.toLowerCase()));
    }
  } catch {}
  if (!queue.length) { toast('Semua gambar sudah ada di riwayat'); return; }

  state.singleRunning = true;
  updateStaged();

  const box = $('#single-result');
  box.innerHTML = '';
  hideStatusFn();
  $('#staged').scrollIntoView({ behavior: reduced ? 'auto' : 'smooth', block: 'start' });

  let ok = 0, fail = 0;
  const total = queue.length;
  for (let i = 0; i < queue.length; i++) {
    const it = queue[i];
    setStageStatus(it.id, 'running');
    updateStaged();
    setProgress(i, total, it.name);
    const block = document.createElement('div');
    block.className = 'result-block';
    box.appendChild(block);
    pop(block);
    try {
      await generateOne(it, block);
      setStageStatus(it.id, 'done');
      ok++;
    } catch (e) {
      setStageStatus(it.id, 'fail');
      block.innerHTML = `<div class="statusline is-bad">${esc(it.name)} — gagal: ${esc(e.message)}</div>`;
      fail++;
    }
    setProgress(i + 1, total, it.name);
  }

  state.singleRunning = false;
  updateStaged();
  setProgress(total, total, 'Selesai');
  if (fail) setStatusFn(`Selesai: ${ok} berhasil, ${fail} gagal`, true);
  else hideStatusFn();
  if (ok) toast(`Selesai — ${ok} gambar diproses`, 'ok',
    { label: 'Lihat hasil', fn: () => $('#single-result').scrollIntoView({ behavior: 'smooth', block: 'start' }) });
  loadStatsFn();
}

export function hasStaged() { return staged.length > 0; }

export function wireSingle() {
  const drop = $('#drop');
  const input = $('#file');
  const view = $('#view-single');

  const openPicker = () => input.click();
  drop.addEventListener('click', (e) => { if (!e.target.closest('button')) openPicker(); });
  $('#drop-pick').addEventListener('click', openPicker);
  $('#drop-add').addEventListener('click', openPicker);

  input.addEventListener('change', () => {
    if (input.files && input.files.length) addFiles([...input.files]);
    input.value = '';
  });

  let depth = 0;
  const stop = (e) => { e.preventDefault(); e.stopPropagation(); };
  view.addEventListener('dragenter', (e) => { stop(e); depth++; drop.classList.add('is-drag'); });
  view.addEventListener('dragover', (e) => { stop(e); });
  view.addEventListener('dragleave', (e) => {
    stop(e);
    if (--depth <= 0) { depth = 0; drop.classList.remove('is-drag'); }
  });
  view.addEventListener('drop', (e) => {
    stop(e);
    depth = 0;
    drop.classList.remove('is-drag');
    const fs = e.dataTransfer?.files;
    if (fs && fs.length) addFiles([...fs]);
  });

  document.addEventListener('paste', (e) => {
    if (view.hidden) return;
    const t = e.target;
    if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA')) return;
    const imgs = [...(e.clipboardData?.files || [])]
      .filter((f) => f.type.startsWith('image/') || STAGE_EXT.test(f.name));
    if (imgs.length) { e.preventDefault(); addFiles(imgs); }
  });

  $('#staged-run').addEventListener('click', runAll);
  $('#staged-clear').addEventListener('click', clearStage);
  $('#staged-all').addEventListener('change', (e) => {
    if (e.target.checked) selectAll(); else unselectAll();
  });
  document.addEventListener('kw:markets', () => { if (staged.length) updateStaged(); });

  $('#staged-grid').addEventListener('click', (e) => {
    const rm = e.target.closest('[data-rm]');
    if (!rm || state.singleRunning) return;
    e.preventDefault();
    removeStaged(+rm.dataset.rm);
  });
  $('#staged-grid').addEventListener('change', (e) => {
    const cb = e.target.closest('.tc-input');
    if (!cb || state.singleRunning) return;
    toggleStagedSel(+cb.closest('.thumb-card').dataset.sid, cb.checked);
  });
}
