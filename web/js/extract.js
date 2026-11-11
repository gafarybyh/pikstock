import { $, M, reduced, state, esc, secs } from './core.js';
import { toast, skeletonHTML, emptyHTML, pop, showView, attrsHTML, extractCopyText, setFill } from './ui.js';
import { setHistoryScope } from './history.js';

const STAGE_EXT = /\.(png|jpe?g|webp|gif|bmp)$/i;
const MAX_BYTES = 40 * 1024 * 1024;

const staged = [];
let stagedSeq = 0;
const stagedSelected = new Set();
let loadStatsFn = () => {};

export function bindExtractHooks(hooks) {
  loadStatsFn = hooks.loadStats || loadStatsFn;
}

const stageKey = (it) => `${it.name}:${it.file.size}`;
const stageCard = (id) => $(`.thumb-card[data-sid="${id}"]`, $('#ex-staged-grid'));

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

function emptyResult() {
  $('#ex-result').innerHTML = '';
}

function setStatus(message, bad = false) {
  const el = $('#ex-status');
  el.hidden = !message;
  el.className = 'statusline' + (bad ? ' is-bad' : '');
  el.innerHTML = message || '';
}

function setProgress(i, n, name) {
  $('#ex-staged-progress').hidden = n === 0;
  setFill($('#ex-staged-fill'), n ? (i / n) * 100 : 0);
  $('#ex-staged-ptext').textContent = `${i} / ${n}`;
  $('#ex-staged-pcurrent').textContent = name || '';
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
  const box = $('#ex-staged');
  const busy = state.extractRunning;
  box.hidden = staged.length === 0;
  $('#ex-drop').classList.toggle('is-compact', staged.length > 0);
  if (!staged.length) {
    $('#ex-staged-progress').hidden = true;
    return;
  }

  box.classList.toggle('is-busy', busy);
  $('#ex-staged-count').textContent = `${staged.length} gambar`;

  const done = staged.filter((s) => s.status === 'done').length;
  const fail = staged.filter((s) => s.status === 'fail').length;
  const run = staged.filter((s) => s.status === 'running').length;
  const ready = staged.length - done - fail - run;
  const parts = [`${stagedSelected.size} dari ${staged.length} dipilih`];
  if (ready) parts.push(`${ready} siap`);
  if (run) parts.push(`${run} diproses`);
  if (done) parts.push(`<span class="s-done">${done} selesai</span>`);
  if (fail) parts.push(`<span class="s-fail">${fail} gagal</span>`);
  $('#ex-staged-summary').innerHTML = parts.join(', ');

  syncStagedSel();
}

function syncStagedSel() {
  const n = stagedSelected.size;
  const total = staged.length;
  const busy = state.extractRunning;

  const master = $('#ex-staged-all');
  master.checked = total > 0 && n === total;
  master.indeterminate = n > 0 && n < total;
  master.disabled = busy || total === 0;

  $('#ex-staged-clear').disabled = busy;

  const run = $('#ex-staged-run');
  run.disabled = busy || n === 0;
  run.title = n === 0 ? 'Centang minimal satu gambar untuk mulai.' : '';
  const hint = $('#ex-staged-hint');
  hint.hidden = n > 0 || busy;
  hint.textContent = n === 0 ? 'Centang minimal satu gambar untuk mulai.' : '';

  $('#ex-staged-run-txt').textContent = busy
    ? 'Mengekstrak…'
    : n ? `Ekstrak deskripsi (${n})` : 'Ekstrak deskripsi';

  $('#ex-staged-grid').querySelectorAll('.thumb-card').forEach((c) => {
    const on = stagedSelected.has(+c.dataset.sid);
    c.classList.toggle('is-sel', on);
    const cb = c.querySelector('.tc-input');
    if (cb) { cb.checked = on; cb.disabled = busy; }
    const x = c.querySelector('.tc-x');
    if (x) x.disabled = busy;
  });

  $('#ex-pick').disabled = busy;
  $('#ex-add').disabled = busy;
}

function addItems(items) {
  const have = new Set(staged.map(stageKey));
  const grid = $('#ex-staged-grid');
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
  if (added && !state.extractRunning) {
    emptyResult();
    setStatus('');
  }
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
  $('#ex-staged-grid').innerHTML = '';
  $('#ex-file').value = '';
  setStatus('');
  emptyResult();
  updateStaged();
}

function resultHTML(res) {
  const d = res.data || {};
  const desc = d.description || '';
  const words = d.word_count || desc.split(/\s+/).filter(Boolean).length;
  const thumb = res.thumb ? `/generate/${esc(res.thumb)}` : '';
  return `
    <div class="result-head">
      ${thumb ? `<img src="${thumb}" alt="Pratinjau ${esc(res.filename)}">` : ''}
      <div class="rh-meta">
        <div class="rh-name">${esc(res.filename)}</div>
        <div class="rh-sub">${secs(res.duration_ms || 0)}<span class="dot">•</span>${esc(d.model || '—')}</div>
      </div>
      <div class="rh-actions">
        ${res.id ? `<a class="btn btn-ghost" href="/api/history/${res.id}/image" target="_blank" rel="noopener">Buka gambar</a>` : ''}
        <button class="btn btn-primary" data-copy-desc data-copy-text="${esc(extractCopyText(d, desc))}">Salin deskripsi</button>
      </div>
    </div>
    <article class="card is-lead extract-card" data-extract-card>
      <header class="card-head">
        <span class="card-title">Deskripsi gambar</span>
        <span class="pill ok">${words} kata</span>
        <div class="spacer"></div>
      </header>
      <div class="card-body">
        <p class="extract-text">${esc(desc)}</p>
        ${attrsHTML(d)}
      </div>
    </article>`;
}

async function extractOne(item, blockEl) {
  blockEl.innerHTML = skeletonHTML();
  const fd = new FormData();
  fd.append('file', item.file, item.name);
  const res = await fetch('/api/extract', { method: 'POST', body: fd });
  if (!res.ok) {
    let message = res.statusText;
    try { message = (await res.json()).detail || message; } catch {}
    throw new Error(message);
  }
  const data = await res.json();
  blockEl.innerHTML = resultHTML(data);
  pop(blockEl.firstElementChild);
}

async function runExtract() {
  if (state.extractRunning) return;
  const queue = staged.filter((s) => stagedSelected.has(s.id));
  if (!queue.length) { toast('Pilih minimal satu gambar', 'bad'); return; }

  state.extractRunning = true;
  updateStaged();
  setStatus('');
  const box = $('#ex-result');
  box.innerHTML = '';
  $('#ex-staged').scrollIntoView({ behavior: reduced ? 'auto' : 'smooth', block: 'start' });

  let ok = 0, fail = 0;
  const total = queue.length;
  for (let i = 0; i < total; i++) {
    const it = queue[i];
    setStageStatus(it.id, 'running');
    updateStaged();
    setProgress(i, total, it.name);
    const block = document.createElement('div');
    block.className = 'result-block';
    box.appendChild(block);
    try {
      await extractOne(it, block);
      setStageStatus(it.id, 'done');
      ok++;
    } catch (e) {
      setStageStatus(it.id, 'fail');
      block.innerHTML = `<div class="statusline is-bad">${esc(it.name)} — gagal: ${esc(e.message)}</div>`;
      fail++;
    }
    setProgress(i + 1, total, it.name);
  }

  state.extractRunning = false;
  updateStaged();
  setProgress(total, total, 'Selesai');
  if (fail) setStatus(`Selesai: ${ok} berhasil, ${fail} gagal`, true);
  if (ok) toast(`Selesai — ${ok} gambar diekstrak`, 'ok', {
    label: 'Lihat riwayat',
    fn: () => {
      setHistoryScope('extract');
      showView('history');
    },
  });
  loadStatsFn();
}

export function wireExtract() {
  const drop = $('#ex-drop');
  const input = $('#ex-file');
  const view = $('#view-extract');
  const openPicker = () => { if (!state.extractRunning) input.click(); };

  drop.addEventListener('click', (e) => { if (!e.target.closest('button')) openPicker(); });
  drop.addEventListener('keydown', (e) => {
    if (e.target !== drop) return;
    if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); openPicker(); }
  });
  $('#ex-pick').addEventListener('click', openPicker);
  $('#ex-add').addEventListener('click', openPicker);
  input.addEventListener('change', () => {
    if (input.files && input.files.length) addFiles([...input.files]);
    input.value = '';
  });

  let depth = 0;
  const stop = (e) => { e.preventDefault(); e.stopPropagation(); };
  view.addEventListener('dragenter', (e) => {
    stop(e);
    depth++;
    drop.classList.add('is-drag');
  });
  view.addEventListener('dragover', (e) => { stop(e); });
  view.addEventListener('dragleave', (e) => {
    stop(e);
    if (--depth <= 0) { depth = 0; drop.classList.remove('is-drag'); }
  });
  view.addEventListener('drop', (e) => {
    stop(e);
    depth = 0;
    drop.classList.remove('is-drag');
    if (state.extractRunning) return;
    const fs = e.dataTransfer?.files;
    if (fs && fs.length) addFiles([...fs]);
  });

  document.addEventListener('paste', (e) => {
    if (view.hidden || state.extractRunning) return;
    const t = e.target;
    if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA')) return;
    const imgs = [...(e.clipboardData?.files || [])]
      .filter((f) => f.type.startsWith('image/') || STAGE_EXT.test(f.name));
    if (imgs.length) { e.preventDefault(); addFiles(imgs); }
  });

  $('#ex-staged-run').addEventListener('click', runExtract);
  $('#ex-staged-clear').addEventListener('click', clearStage);
  $('#ex-staged-all').addEventListener('change', (e) => {
    staged.forEach((s) => (e.target.checked ? stagedSelected.add(s.id) : stagedSelected.delete(s.id)));
    updateStaged();
  });

  $('#ex-staged-grid').addEventListener('click', (e) => {
    const rm = e.target.closest('[data-rm]');
    if (!rm || state.extractRunning) return;
    e.preventDefault();
    removeStaged(+rm.dataset.rm);
  });
  $('#ex-staged-grid').addEventListener('change', (e) => {
    const cb = e.target.closest('.tc-input');
    if (!cb || state.extractRunning) return;
    const id = +cb.closest('.thumb-card').dataset.sid;
    if (cb.checked) stagedSelected.add(id); else stagedSelected.delete(id);
    updateStaged();
  });

  emptyResult();
  updateStaged();
}
