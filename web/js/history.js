/* history.js — riwayat: daftar, filter, bulk delete, drawer detail. */

import { $, M, reduced, state, esc, secs, fmtDate, fmtTime, dayLabel, srcLabel } from './core.js';
import { toast, popStagger, emptyHTML, attrsHTML, extractCopyText } from './ui.js';
import { mountResult } from './render.js';

let loadStatsFn = () => {};
let drawerReturnFocus = null;

const FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]), select, textarea, [tabindex]:not([tabindex="-1"])';
let confirmOnOk = null;
let confirmReturn = null;

function confirmDialog(title, text, onOk) {
  confirmOnOk = onOk;
  confirmReturn = document.activeElement instanceof HTMLElement ? document.activeElement : null;
  $('#confirm-title').textContent = title;
  $('#confirm-text').textContent = text;
  $('#confirm').hidden = false;
  $('#confirm-ok').focus({ preventScroll: true });
}

function closeConfirm() {
  $('#confirm').hidden = true;
  confirmOnOk = null;
  if (confirmReturn && document.contains(confirmReturn)) confirmReturn.focus({ preventScroll: true });
  confirmReturn = null;
}

function wireConfirm() {
  $('#confirm-ok').addEventListener('click', () => {
    const fn = confirmOnOk;
    closeConfirm();
    if (fn) fn();
  });
  $('#confirm-cancel').addEventListener('click', closeConfirm);
  $('#confirm-scrim').addEventListener('click', closeConfirm);
  document.addEventListener('keydown', (e) => {
    if ($('#confirm').hidden) return;
    if (e.key === 'Escape') { e.preventDefault(); closeConfirm(); return; }
    if (e.key !== 'Tab') return;
    const nodes = [...$('#confirm').querySelectorAll(FOCUSABLE)].filter((n) => n.offsetParent !== null);
    if (!nodes.length) return;
    const first = nodes[0], last = nodes[nodes.length - 1];
    if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus({ preventScroll: true }); }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus({ preventScroll: true }); }
  });
}

export function bindHistoryHooks(hooks) {
  loadStatsFn = hooks.loadStats || loadStatsFn;
}

function resetScopeFilters() {
  $('#hist-status').querySelectorAll('.seg-btn').forEach((b) => {
    b.classList.toggle('is-on', b.dataset.status === 'all');
  });
  $('#hist-source').querySelectorAll('.seg-btn').forEach((b) => {
    b.classList.toggle('is-on', b.dataset.source === 'all');
  });
  $('#hist-market').value = 'all';
}

export function setHistoryScope(scope) {
  const next = scope === 'extract' || scope === 'image' ? scope : 'keyword';
  if (state.histScope === next) return;
  state.histScope = next;
  state.histPage = 1;
  state.histTotal = 0;
  state.histStatus = 'all';
  state.histSource = 'all';
  state.histMarket = 'all';
  state.histRuns = [];
  state.histSelect = false;
  state.histSelected.clear();
  state.histBatchOpen.clear();
  closeDrawer();

  const extract = next === 'extract';
  const image = next === 'image';
  const plain = next === 'keyword';
  $('#history-title').textContent = image ? 'Riwayat Gambar' : extract ? 'Riwayat Ekstrak' : 'Riwayat Keyword';
  $('#history-desc').textContent = image
    ? 'Semua hasil generate gambar tersimpan otomatis. Bisa dibuka ulang atau dihapus.'
    : extract
      ? 'Semua hasil ekstraksi gambar tersimpan otomatis. Bisa dicari, dibuka ulang, atau dihapus.'
      : 'Semua hasil generate keyword tersimpan otomatis. Bisa dicari, dibuka ulang, atau dihapus.';
  $('#history-q').value = '';
  $('#history-q').placeholder = image
    ? 'Cari prompt…'
    : extract
      ? 'Cari nama file atau isi deskripsi…'
      : 'Cari nama file atau isi keyword…';
  $('#hist-source').hidden = !plain;
  $('#hist-market').hidden = !plain;
  $('#history-export').hidden = !plain;
  $('#history-list').innerHTML = '';
  $('#history-pager').hidden = true;
  $('#history-count').textContent = '';
  resetScopeFilters();
  syncBulkUI();
}

function mkListHTML(markets) {
  if (!Array.isArray(markets) || !markets.length) return '';
  const labels = MK_LABELS.filter(([k]) => markets.includes(k)).map(([, label]) => label);
  return `<div class="hmk" aria-label="Marketplace">${labels.map((l) => `<span class="chip plain">${esc(l)}</span>`).join('')}</div>`;
}

function imageMetaHTML(h) {
  const sizes = Array.isArray(h.sizes) ? h.sizes.filter(Boolean) : [];
  const count = Array.isArray(h.images) ? h.images.length : sizes.length;
  if (!count) return '';
  const uniq = [...new Set(sizes)];
  const res = uniq.length === 1 ? uniq[0] : uniq.length ? uniq.join(' · ') : '—';
  return `<span>${count} gambar</span><span class="dot">•</span><span>${esc(res)}</span>`;
}

function hrowHTML(h, nested) {
  const ok = h.status === 'ok';
  const sel = state.histSelected.has(h.id);
  const fav = !!h.favorite;
  const pick = state.histSelect
    ? `<span class="hcheck"><input type="checkbox" data-pick="${h.id}" ${sel ? 'checked' : ''}
         tabindex="-1" aria-label="Pilih ${esc(h.filename)}"></span>` : '';
  return `
    <div class="hrow${sel ? ' is-sel' : ''}${nested ? ' is-nested' : ''}" data-id="${h.id}" role="button" tabindex="0">
      ${pick}
      ${h.thumb ? `<img src="/generate/${esc(h.thumb)}" alt="" loading="lazy" onerror="this.replaceWith(Object.assign(document.createElement('div'),{className:'ph',textContent:'!'}))">` : '<div class="ph">!</div>'}
      <div class="hmeta">
        <div class="hname">${esc(h.filename)}</div>
        <div class="hsub">
          <span>${fmtTime(h.created_at)}</span>
          <span class="dot">•</span><span>${secs(h.duration_ms || 0)}</span>
          <span class="dot">•</span><span>${esc(h.model || '—')}</span>
          ${state.histScope === 'image' ? '' : `<span class="hsrc">${srcLabel(h.source)}</span>`}
        </div>
        ${state.histScope === 'image' ? `<div class="hsub">${imageMetaHTML(h)}</div>` : ''}
        ${mkListHTML(h.markets)}
      </div>
      <span class="hbadge ${ok ? 'ok' : 'bad'}">${ok ? 'berhasil' : 'gagal'}</span>
      <button class="icon-btn fav-btn${fav ? ' is-on' : ''}" data-fav="${h.id}" aria-pressed="${fav}"
        title="${fav ? 'Hapus dari favorit' : 'Tandai favorit'}" aria-label="${fav ? 'Hapus dari favorit' : 'Tandai favorit'} ${esc(h.filename)}">
        <svg viewBox="0 0 24 24"><path d="M12 3.5l2.6 5.3 5.9.9-4.3 4.1 1 5.8L12 16.8l-5.2 2.8 1-5.8-4.3-4.1 5.9-.9z"/></svg>
      </button>
      <button class="icon-btn" data-del="${h.id}" title="Hapus" aria-label="Hapus ${esc(h.filename)}">
        <svg viewBox="0 0 24 24"><path d="M4 7h16"/><path d="M9 7V5h6v2"/><path d="M6 7l1 13h10l1-13"/></svg>
      </button>
      <span class="hchev" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M9 6l6 6-6 6"/></svg></span>
    </div>`;
}

function batchHeaderHTML(runs, batchId, isOpen) {
  const okN = runs.filter((h) => h.status === 'ok').length;
  const badN = runs.length - okN;
  const thumbs = runs.filter((h) => h.thumb).slice(0, 4);
  const stack = thumbs.map((h) => `<img src="/generate/${esc(h.thumb)}" alt="" loading="lazy"
      onerror="this.replaceWith(Object.assign(document.createElement('div'),{className:'ph',textContent:'!'}))">`).join('');
  const total = runs.reduce((s, h) => s + (h.duration_ms || 0), 0);
  const parts = [`${runs.length} gambar`, `${okN} berhasil`];
  if (badN) parts.push(`${badN} gagal`);
  if (total) parts.push(`${secs(total)} total`);
  return `
    <div class="hbatch${isOpen ? ' is-open' : ''}" data-batch="${batchId}" role="button" tabindex="0"
         aria-expanded="${isOpen}">
      <span class="hbatch-stack" aria-hidden="true">${stack || '<span class="hbatch-ico"><svg viewBox="0 0 24 24"><rect x="3" y="3" width="18" height="18" rx="3"/><circle cx="8.5" cy="8.5" r="1.6"/><path d="M21 15l-5-5L5 21"/></svg></span>'}</span>
      <div class="hmeta">
        <div class="hname">Kelompok batch ${esc(batchId)}</div>
        <div class="hsub">${parts.filter(Boolean).join('<span class="dot">•</span>')}</div>
      </div>
      ${badN ? `<span class="hbadge bad">${badN} gagal</span>` : '<span class="hbadge ok">berhasil</span>'}
      <span class="hchev hbatch-toggle" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M6 9l6 6 6-6"/></svg></span>
    </div>`;
}

function groupRuns(runs) {
  const out = [];
  for (let i = 0; i < runs.length; i++) {
    const h = runs[i];
    const bid = h.batch_id;
    if (!bid) { out.push({ kind: 'run', run: h }); continue; }
    if (out.length && out[out.length - 1].kind === 'batch' && out[out.length - 1].batchId === bid) {
      out[out.length - 1].runs.push(h);
      continue;
    }
    let j = i + 1;
    const group = [h];
    while (j < runs.length && runs[j].batch_id === bid) { group.push(runs[j]); j++; }
    if (group.length === 1) { out.push({ kind: 'run', run: h }); continue; }
    group.batchId = bid;
    out.push({ kind: 'batch', batchId: bid, runs: group });
    i = j - 1;
  }
  return out;
}


function updateCount() {
  const from = state.histTotal ? (state.histPage - 1) * state.histPageSize + 1 : 0;
  const to = from ? from + state.histRuns.length - 1 : 0;
  $('#history-count').textContent = state.histTotal
    ? `Menampilkan ${from}–${to} dari ${state.histTotal}` : '';
}

function renderPager() {
  const pages = Math.max(1, Math.ceil(state.histTotal / state.histPageSize));
  const pager = $('#history-pager');
  pager.hidden = pages <= 1;
  if (pages <= 1) return;
  const cur = state.histPage;
  const nums = new Set([1, pages, cur - 1, cur, cur + 1]);
  const list = [...nums].filter((n) => n >= 1 && n <= pages).sort((a, b) => a - b);
  let html = `<button class="btn btn-ghost" data-page="${cur - 1}" ${cur <= 1 ? 'disabled' : ''}>Sebelumnya</button>`;
  let prev = 0;
  for (const n of list) {
    if (n - prev > 1) html += '<span class="pager-gap" aria-hidden="true">…</span>';
    html += `<button class="btn btn-ghost pager-num${n === cur ? ' is-on' : ''}" data-page="${n}"
      ${n === cur ? 'aria-current="page"' : ''} aria-label="Halaman ${n}">${n}</button>`;
    prev = n;
  }
  html += `<button class="btn btn-ghost" data-page="${cur + 1}" ${cur >= pages ? 'disabled' : ''}>Berikutnya</button>`;
  pager.innerHTML = html;
}

function renderHistoryList() {
  const list = $('#history-list');
  if (!state.histRuns.length) {
    const extract = state.histScope === 'extract';
    const q = $('#history-q').value.trim();
    const filtered = state.histStatus !== 'all' || state.histSource !== 'all' || state.histMarket !== 'all';
    list.innerHTML = q
      ? emptyHTML('Tidak ada hasil', `Tidak ada proses yang cocok dengan “${q}”.`, 'info')
      : filtered
        ? emptyHTML('Tidak ada hasil', 'Tidak ada proses dengan filter ini. Coba ubah filter.', 'info')
        : extract
          ? emptyHTML('Riwayat ekstrak gambar masih kosong',
            'Setiap gambar yang diekstrak tersimpan otomatis di sini, lengkap dengan deskripsi dan thumbnail.', 'image')
          : state.histScope === 'image'
            ? emptyHTML('Riwayat gambar masih kosong',
              'Setiap hasil generate gambar tersimpan otomatis di sini.', 'image')
            : emptyHTML('Riwayat generate keyword masih kosong',
              'Setiap generate tersimpan otomatis di sini, lengkap dengan thumbnail dan hasil lengkapnya.', 'clock');
    $('#history-pager').hidden = true;
    updateCount();
    return;
  }
  let html = '', last = '';
  let day = '';
  for (const g of groupRuns(state.histRuns)) {
    const first = g.kind === 'run' ? g.run : g.runs[0];
    const lab = dayLabel(first.created_at);
    if (lab !== last) { html += `<div class="hgroup">${lab}</div>`; last = lab; }
    if (g.kind === 'run') { html += hrowHTML(g.run); continue; }
    const open = state.histSelect || state.histBatchOpen.has(g.batchId);
    html += `<div class="hbatch-wrap">${batchHeaderHTML(g.runs, g.batchId, open)}`;
    if (open) html += `<div class="hbatch-body">${g.runs.map((h) => hrowHTML(h, true)).join('')}</div>`;
    html += '</div>';
  }
  list.innerHTML = html;
}

function syncBulkUI() {
  const on = state.histSelect;
  $('#bulkbar').hidden = !on;
  const btn = $('#history-select');
  btn.classList.toggle('is-on', on);
  btn.textContent = on ? 'Selesai' : 'Pilih';
  const n = state.histSelected.size;
  $('#bulk-count').textContent = n + ' dipilih';
  $('#bulk-del').disabled = n === 0;
  const all = state.histRuns.length && state.histRuns.every((h) => state.histSelected.has(h.id));
  $('#bulk-all').textContent = all ? 'Batal pilih' : 'Pilih semua';
}

function togglePick(row) {
  const id = +row.dataset.id;
  if (state.histSelected.has(id)) state.histSelected.delete(id);
  else state.histSelected.add(id);
  const on = state.histSelected.has(id);
  row.classList.toggle('is-sel', on);
  const cb = row.querySelector('[data-pick]');
  if (cb) cb.checked = on;
  syncBulkUI();
}

function deleteWithUndo(ids, rows) {
  ids = ids.map(Number).filter((n) => !Number.isNaN(n));
  if (!ids.length) return;
  const key = ids.join(',');
  rows.forEach((r) => { r.style.display = 'none'; });
  ids.forEach((id) => state.histSelected.delete(id));
  syncBulkUI();
  state.histPending.set(key, true);
  const restore = () => { rows.forEach((r) => { r.style.display = ''; }); };
  const commit = async () => {
    if (!state.histPending.has(key)) return;
    state.histPending.delete(key);
    try { await fetch('/api/history?ids=' + ids.join(','), { method: 'DELETE' }); } catch {}
    rows.forEach((r) => r.remove());
    await loadHistory(false);
    loadStatsFn();
  };
  toast(ids.length > 1 ? `${ids.length} proses dihapus` : 'Proses dihapus', '', {
    label: 'Urungkan',
    fn: () => { if (state.histPending.has(key)) { state.histPending.delete(key); restore(); } },
  });
  setTimeout(commit, 5200);
}

export async function loadHistory(reset) {
  if (reset) state.histPage = 1;
  const q = $('#history-q').value.trim();
  const p = new URLSearchParams({
    limit: state.histPageSize,
    offset: (state.histPage - 1) * state.histPageSize,
    scope: state.histScope,
  });
  if (q) p.set('q', q);
  if (state.histStatus === 'fav') p.set('favorite', 'true');
  else if (state.histStatus !== 'all') p.set('status', state.histStatus);
  if (state.histScope === 'keyword' && state.histSource !== 'all') p.set('source', state.histSource);
  if (state.histScope === 'keyword' && state.histMarket !== 'all') p.set('market', state.histMarket);
  const list = $('#history-list');

  try {
    const r = await (await fetch('/api/history?' + p)).json();
    state.histTotal = r.total;
    const pages = Math.max(1, Math.ceil(state.histTotal / state.histPageSize));
    if (state.histPage > pages) {
      state.histPage = pages;
      return loadHistory(false);
    }
    state.histRuns = r.runs;
    state.histSelected.forEach((id) => {
      if (!state.histRuns.some((h) => h.id === id)) state.histSelected.delete(id);
    });
    renderHistoryList();
    renderPager();
    updateCount();
    syncBulkUI();
    if (reset) popStagger([...list.querySelectorAll('.hrow')]);
  } catch (e) {
    list.innerHTML = `<div class="log-row">Gagal memuat: ${esc(e.message)}</div>`;
  }
}

function stepDrawer(d) {
  const i = state.drawerIndex + d;
  if (i < 0 || i >= state.histRuns.length) return;
  openDrawer(state.histRuns[i].id);
}

function updateDrawerNav() {
  $('#drawer-prev').disabled = state.drawerIndex <= 0;
  $('#drawer-next').disabled = state.drawerIndex < 0 || state.drawerIndex >= state.histRuns.length - 1;
}

const MK_LABELS = [
  ['etsy', 'Etsy'],
  ['canva', 'Canva'],
  ['creative_market', 'Creative Market'],
  ['universal', 'Universal'],
  ['adobe', 'Adobe Stock'],
];

function syncRegenChips(preselect) {
  const known = new Set(MK_LABELS.map(([k]) => k));
  const fromRun = Array.isArray(preselect) ? preselect.filter((m) => known.has(m)) : [];
  const picked = new Set(fromRun.length ? fromRun : state.markets);
  const host = $('#dact-mk');
  host.innerHTML = MK_LABELS.map(([k, label]) => {
    const on = picked.has(k);
    return `<button type="button" class="dact-chip${on ? ' is-on' : ''}"
      data-regen-mk="${k}" aria-pressed="${on}">${label}</button>`;
  }).join('');
  syncRegenBtn();
}

function syncRegenBtn() {
  const btn = $('#drawer-regen');
  if (!btn) return;
  if (state.drawerIsExtract) {
    btn.disabled = false;
    btn.title = 'Ekstrak ulang gambar ini, hasil baru menimpa run yang sama';
    return;
  }
  const any = [...document.querySelectorAll('#dact-mk [data-regen-mk]')]
    .some((c) => c.getAttribute('aria-pressed') === 'true');
  btn.disabled = !any;
  btn.title = any ? 'Proses ulang gambar ini, hasil baru menimpa run yang sama' : 'Pilih minimal satu marketplace';
}

async function regenerateRun(id, btn) {
  const isExtract = state.drawerIsExtract;
  const picked = isExtract ? null : [...document.querySelectorAll('#dact-mk [data-regen-mk]')]
    .filter((c) => c.getAttribute('aria-pressed') === 'true')
    .map((c) => c.dataset.regenMk);
  if (!isExtract && !picked.length) { toast('Pilih minimal satu marketplace', 'bad'); return; }
  const label = btn.textContent;
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span>' + (isExtract ? 'Ekstrak…' : 'Generate…');
  try {
    const res = await fetch(`/api/history/${id}/regenerate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(isExtract ? {} : { marketplaces: picked }),
    });
    let r = null;
    try { r = await res.json(); } catch { r = null; }
    if (!res.ok) {
      let msg = (r && (r.detail || r.error)) || 'Generate ulang gagal';
      if (res.status === 404 && (!r || !r.detail || r.detail === 'not found')) {
        msg = 'Server ini versi lama dan belum punya fitur Generate ulang. Tutup semua jendela server, lalu jalankan app.py sekali lagi.';
      }
      toast(msg, 'bad');
      return;
    }
    if (!r || typeof r.id !== 'number') {
      toast('Jawaban server tidak dikenali. Coba muat ulang halaman.', 'bad');
      return;
    }
    toast('Generate ulang selesai — data proses ini sudah diperbarui', 'ok');
    await loadHistory(true);
    loadStatsFn();
    openDrawer(r.id);
  } catch (e) {
    toast(e.message || 'Generate ulang gagal', 'bad');
  } finally {
    if (btn.isConnected) {
      btn.disabled = false;
      btn.textContent = label;
      syncRegenBtn();
    }
  }
}

export async function openDrawer(id) {
  id = Number(id);
  state.drawerIndex = state.histRuns.findIndex((h) => h.id === id);
  updateDrawerNav();
  const wrap = $('#drawer');
  if (wrap.hidden) {
    drawerReturnFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null;
  }
  $('#drawer-body').innerHTML = '<div class="statusline"><span class="spinner"></span>memuat…</div>';
  $('#drawer-act').hidden = true;
  $('#drawer-title').textContent = 'Memuat…';
  wrap.hidden = false;
  $('#drawer-close').focus({ preventScroll: true });
  if (M.animate && !reduced) {
    M.animate('#drawer-scrim', { opacity: [0, 1] }, { duration: .2 });
    M.animate('#drawer-panel', { transform: ['translateX(100%)', 'translateX(0)'] },
      { duration: .38, easing: [.22, 1, .36, 1] });
  }

  try {
    const r = await (await fetch('/api/history/' + id)).json();
    if (r.id !== id) return;
    state.drawerRunId = r.id;
    const isExtract = r.data?.kind === 'extract' || String(r.source || '').startsWith('extract');
    const isImage = r.data?.kind === 'image' || r.source === 'image';
    state.drawerIsExtract = isExtract;
    $('#drawer-title').textContent = r.filename;

    if (isImage) {
      $('#drawer-act').hidden = true;
      $('#drawer-body').innerHTML = imageDetailHTML(r);
      return;
    }

    const metaInner = `<span class="hsrc">${srcLabel(r.source)}</span>
      <span class="dot">•</span>${fmtDate(r.created_at)}<span class="dot">•</span>${secs(r.duration_ms || 0)}
      <span class="spacer"></span>
      ${r.thumb ? `<a class="btn btn-ghost" href="/api/history/${r.id}/image" target="_blank" rel="noopener">Buka gambar</a>` : ''}`;
    const metaHTML = `<div class="drawer-meta">${metaInner}</div>`;

    if (isExtract) {
      $('#drawer-act').hidden = false;
      $('#dact-mk').hidden = true;
      $('#dact-label').hidden = true;
      syncRegenBtn();
      const openImg = r.thumb ? `<a class="btn btn-ghost" href="/api/history/${r.id}/image" target="_blank" rel="noopener">Buka gambar</a>` : '';
      if (r.status !== 'ok' || !r.data) {
        $('#drawer-body').innerHTML = `${extractHeadHTML(r, openImg)}
          <div class="statusline is-bad">Gagal: ${esc(r.error || 'penyebab tidak tercatat')}</div>`;
        return;
      }
      const desc = r.data.description || '';
      const words = r.data.word_count || desc.split(/\s+/).filter(Boolean).length;
      const copyBtn = `<button class="btn btn-ghost" data-copy-desc data-copy-text="${esc(extractCopyText(r.data, desc))}">Salin deskripsi</button>`;
      $('#drawer-body').innerHTML = `${extractHeadHTML(r, openImg)}
        <article class="card is-lead extract-card" data-extract-card>
          <header class="card-head">
            <span class="card-title">Deskripsi gambar</span>
            <span class="pill ok">${words} kata</span>
            <div class="spacer"></div>
          </header>
          <div class="card-body">
            <p class="field-val extract-text">${esc(desc)}</p>
            ${attrsHTML(r.data)}
            ${copyBtn}
          </div>
        </article>`;
      return;
    }

    if (r.status !== 'ok' || !r.data) {
      $('#drawer-body').innerHTML = `${metaHTML}
        <div class="statusline is-bad">Gagal: ${esc(r.error || 'penyebab tidak tercatat')}</div>
        ${r.thumb ? `<div class="drawer-thumb"><img src="/generate/${esc(r.thumb)}" alt="Pratinjau ${esc(r.filename)}" loading="lazy"></div>` : ''}`;
    } else {
      mountResult($('#drawer-body'),
        { id: r.id, thumb: r.thumb, filename: r.filename, duration_ms: r.duration_ms }, r.data);
      const meta = document.createElement('div');
      meta.className = 'drawer-meta';
      meta.innerHTML = metaInner;
      $('#drawer-body').prepend(meta);
    }
    $('#drawer-act').hidden = false;
    $('#dact-mk').hidden = false;
    $('#dact-label').hidden = false;
    syncRegenChips(r.data?._marketplaces);
  } catch (e) {
    $('#drawer-body').innerHTML = `<div class="statusline is-bad">${esc(e.message)}</div>`;
  }
}

function imageDetailHTML(r) {
  const d = r.data || {};
  const meta = `<span>${fmtDate(r.created_at)}</span><span class="dot">•</span>${secs(r.duration_ms || 0)}`;
  if (r.status !== 'ok' || !d.images?.length) {
    return `<div class="drawer-meta">${meta}</div>
      <div class="statusline is-bad">Gagal: ${esc(r.error || 'penyebab tidak tercatat')}</div>`;
  }
  const shots = d.images.map((name) => {
    const src = `/generate/${encodeURIComponent(name)}`;
    return `<a class="img-gen-link" href="${src}" target="_blank" rel="noopener">
      <img src="${src}" alt="Hasil generate: ${esc(d.prompt || '')}" loading="lazy"></a>`;
  }).join('');
  const copyBtn = `<button class="btn btn-ghost" data-copy-desc data-copy-text="${esc(d.prompt || '')}">Salin prompt</button>`;
  const sizes = d.sizes?.length ? [...new Set(d.sizes.filter(Boolean))] : [];
  const facts = [
    ['Model', d.model || '—'],
    ['Ukuran', sizes.length ? sizes.join(', ') : '—'],
    ['Jumlah', `${d.images.length} gambar`],
  ];
  return `<div class="drawer-meta">${meta}</div>
    <div class="img-gen-grid img-detail">${shots}</div>
    <article class="card is-lead">
      <header class="card-head"><span class="card-title">Prompt</span><div class="spacer"></div></header>
      <div class="card-body">
        <p class="field-val">${esc(d.prompt || '')}</p>
        <dl class="img-facts">${facts.map(([k, v]) => `<div><dt>${k}</dt><dd>${esc(v)}</dd></div>`).join('')}</dl>
        ${copyBtn}
      </div>
    </article>`;
}

function extractHeadHTML(r, openImgHTML) {
  const thumb = r.thumb ? `<img src="/generate/${esc(r.thumb)}" alt="Pratinjau ${esc(r.filename)}" loading="lazy">` : '';
  return `<div class="result-head">
    ${thumb}
    <div class="rh-meta">
      <div class="rh-name">${esc(r.filename)}</div>
      <div class="rh-sub">${srcLabel(r.source)}<span class="dot">•</span>${fmtDate(r.created_at)}<span class="dot">•</span>${secs(r.duration_ms || 0)}</div>
    </div>
    ${openImgHTML ? `<div class="rh-open">${openImgHTML}</div>` : ''}
  </div>`;
}

function restoreFocus() {
  const el = drawerReturnFocus;
  drawerReturnFocus = null;
  if (el && document.contains(el)) el.focus({ preventScroll: true });
}

export function closeDrawer() {
  const wrap = $('#drawer');
  if (wrap.hidden) return;
  if (!M.animate || reduced) { wrap.hidden = true; restoreFocus(); return; }
  M.animate('#drawer-scrim', { opacity: [1, 0] }, { duration: .18 });
  const anim = M.animate('#drawer-panel', { transform: ['translateX(0)', 'translateX(100%)'] },
    { duration: .26, easing: [.4, 0, 1, 1] });
  const hide = () => { wrap.hidden = true; restoreFocus(); };
  if (anim && typeof anim.finished === 'object' && anim.finished.then) anim.finished.then(hide).catch(hide);
  else setTimeout(hide, 280);
}

function trapFocus(e) {
  const wrap = $('#drawer');
  if (wrap.hidden) return false;
  if (e.key === 'Escape') {
    e.preventDefault();
    closeDrawer();
    return true;
  }
  if (e.key !== 'Tab') return false;
  const nodes = [...wrap.querySelectorAll(FOCUSABLE)].filter((n) => n.offsetParent !== null);
  if (!nodes.length) return false;
  const first = nodes[0];
  const last = nodes[nodes.length - 1];
  const act = document.activeElement;
  if (e.shiftKey && (act === first || !wrap.contains(act))) {
    e.preventDefault();
    last.focus({ preventScroll: true });
    return true;
  }
  if (!e.shiftKey && (act === last || !wrap.contains(act))) {
    e.preventDefault();
    first.focus({ preventScroll: true });
    return true;
  }
  return false;
}

async function toggleFavorite(id, btn) {
  const on = btn.getAttribute('aria-pressed') !== 'true';
  btn.disabled = true;
  try {
    const res = await fetch(`/api/history/${id}/favorite`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ favorite: on }),
    });
    if (!res.ok) throw new Error('Gagal menyimpan favorit');
    const run = state.histRuns.find((h) => h.id === Number(id));
    if (run) run.favorite = on ? 1 : 0;
    if (state.histStatus === 'fav' && !on) {
      await loadHistory(true);
      return;
    }
    renderHistoryList();
  } catch (e) {
    toast(e.message || 'Gagal menyimpan favorit', 'bad');
  } finally {
    btn.disabled = false;
  }
}

function toggleBatch(batchId) {
  if (state.histSelect) return;
  const id = Number(batchId);
  if (!Number.isFinite(id)) return;
  if (state.histBatchOpen.has(id)) state.histBatchOpen.delete(id);
  else state.histBatchOpen.add(id);
  renderHistoryList();
}

export function wireHistory() {
  wireConfirm();
  let t;
  $('#history-q').addEventListener('input', () => {
    clearTimeout(t);
    t = setTimeout(() => loadHistory(true), 260);
  });
  $('#history-refresh').addEventListener('click', () => loadHistory(true));
  $('#history-pager').addEventListener('click', (e) => {
    const b = e.target.closest('[data-page]');
    if (!b || b.disabled) return;
    state.histPage = Number(b.dataset.page);
    loadHistory(false);
    $('#view-history').scrollIntoView({ block: 'start', behavior: reduced ? 'auto' : 'smooth' });
  });

  $('#hist-status').addEventListener('click', (e) => {
    const b = e.target.closest('.seg-btn');
    if (!b) return;
    $('#hist-status').querySelectorAll('.seg-btn').forEach((x) => x.classList.toggle('is-on', x === b));
    state.histStatus = b.dataset.status;
    loadHistory(true);
  });
  $('#hist-source').addEventListener('click', (e) => {
    const b = e.target.closest('.seg-btn');
    if (!b) return;
    $('#hist-source').querySelectorAll('.seg-btn').forEach((x) => x.classList.toggle('is-on', x === b));
    state.histSource = b.dataset.source;
    loadHistory(true);
  });
  $('#hist-market').addEventListener('change', (e) => {
    state.histMarket = e.target.value;
    loadHistory(true);
  });

  $('#history-select').addEventListener('click', () => {
    state.histSelect = !state.histSelect;
    if (!state.histSelect) state.histSelected.clear();
    renderHistoryList();
    syncBulkUI();
  });
  $('#history-export').addEventListener('click', () => {
    if (state.histScope === 'extract') return;
    if (state.histStatus === 'bad') {
      toast('Proses yang gagal tidak punya data untuk diekspor', 'bad');
      return;
    }
    const p = new URLSearchParams();
    const q = $('#history-q').value.trim();
    if (q) p.set('q', q);
    if (state.histSource !== 'all') p.set('source', state.histSource);
    window.location.href = '/api/export.csv' + (p.toString() ? '?' + p : '');
  });
  $('#bulk-all').addEventListener('click', () => {
    const all = state.histRuns.length && state.histRuns.every((h) => state.histSelected.has(h.id));
    if (all) state.histSelected.clear();
    else state.histRuns.forEach((h) => state.histSelected.add(h.id));
    document.querySelectorAll('#history-list .hrow').forEach((r) => {
      const on = state.histSelected.has(+r.dataset.id);
      r.classList.toggle('is-sel', on);
      const cb = r.querySelector('[data-pick]');
      if (cb) cb.checked = on;
    });
    syncBulkUI();
  });
  $('#bulk-del').addEventListener('click', () => {
    if (!state.histSelected.size) return;
    const ids = [...state.histSelected];
    const rows = ids.map((id) => $(`#history-list .hrow[data-id="${id}"]`)).filter(Boolean);
    confirmDialog(
      ids.length > 1 ? `Hapus ${ids.length} proses dari riwayat?` : 'Hapus proses ini dari riwayat?',
      ids.length > 1
        ? `${ids.length} proses beserta thumbnail-nya akan dihapus. Kamu bisa membatalkan dalam beberapa detik setelah menghapus.`
        : 'Proses beserta thumbnail-nya akan dihapus. Kamu bisa membatalkan dalam beberapa detik setelah menghapus.',
      () => deleteWithUndo(ids, rows),
    );
  });

  $('#history-list').addEventListener('keydown', (e) => {
    if (e.key !== 'Enter' && e.key !== ' ') return;
    const head = e.target.closest('.hbatch');
    if (head) { e.preventDefault(); toggleBatch(head.dataset.batch); return; }
    const row = e.target.closest('.hrow');
    if (!row || e.target.closest('[data-del]')) return;
    e.preventDefault();
    if (state.histSelect) togglePick(row);
    else openDrawer(row.dataset.id);
  });

  $('#history-list').addEventListener('click', (e) => {
    const fav = e.target.closest('[data-fav]');
    if (fav) { e.stopPropagation(); toggleFavorite(fav.dataset.fav, fav); return; }
    const del = e.target.closest('[data-del]');
    if (del) {
      e.stopPropagation();
      const row = del.closest('.hrow');
      confirmDialog('Hapus proses ini dari riwayat?',
        'Proses beserta thumbnail-nya akan dihapus. Kamu bisa membatalkan dalam beberapa detik setelah menghapus.',
        () => deleteWithUndo([del.dataset.del], [row]));
      return;
    }
    const head = e.target.closest('.hbatch');
    if (head) { toggleBatch(head.dataset.batch); return; }
    const row = e.target.closest('.hrow');
    if (!row) return;
    if (state.histSelect) togglePick(row);
    else openDrawer(row.dataset.id);
  });

  $('#drawer-prev').addEventListener('click', () => stepDrawer(-1));
  $('#drawer-next').addEventListener('click', () => stepDrawer(1));
  $('#drawer-close').addEventListener('click', closeDrawer);
  $('#drawer-scrim').addEventListener('click', closeDrawer);
  $('#dact-mk').addEventListener('click', (e) => {
    const chip = e.target.closest('[data-regen-mk]');
    if (!chip) return;
    const on = chip.getAttribute('aria-pressed') === 'true';
    chip.setAttribute('aria-pressed', String(!on));
    chip.classList.toggle('is-on', !on);
    syncRegenBtn();
  });
  $('#drawer-regen').addEventListener('click', (ev) => {
    if (state.drawerRunId == null) return;
    regenerateRun(state.drawerRunId, ev.currentTarget);
  });
  document.addEventListener('keydown', (e) => {
    if (trapFocus(e)) return;
    if ($('#drawer').hidden) return;
    if (e.key === 'ArrowLeft') stepDrawer(-1);
    else if (e.key === 'ArrowRight') stepDrawer(1);
  });
}
