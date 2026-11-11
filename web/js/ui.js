/* ui.js — toast, clipboard, animasi, empty/skeleton, view switcher, chip. */

import { $, M, reduced, esc, state } from './core.js';

let toastTimer;
export function toast(msg, kind = '', action = null) {
  const t = $('#toast');
  clearTimeout(toastTimer);
  t.className = 'toast show' + (kind ? ' is-' + kind : '');
  t.innerHTML = '';
  t.append(document.createTextNode(msg));
  if (action) {
    const b = document.createElement('button');
    b.className = 'toast-act';
    b.textContent = action.label;
    b.addEventListener('click', () => { t.classList.remove('show'); action.fn(); });
    t.append(b);
  }
  const ms = action ? 5200 : (kind === 'bad' ? 3200 : 1900);
  toastTimer = setTimeout(() => t.classList.remove('show'), ms);
}

export async function copy(text, label = 'Disalin') {
  if (!text) return false;
  let ok = false;
  try {
    await navigator.clipboard.writeText(text);
    ok = true;
  } catch {
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.style.cssText = 'position:fixed;opacity:0';
    document.body.appendChild(ta);
    ta.select();
    ok = document.execCommand('copy');
    ta.remove();
  }
  toast(ok ? label : 'Gagal menyalin, coba lagi', ok ? 'ok' : 'bad');
  return ok;
}

export function pop(node, delay = 0) {
  if (!M.animate || reduced) return;
  M.animate(node, { opacity: [0, 1], transform: ['translateY(14px)', 'translateY(0)'] },
    { duration: .42, delay, easing: [.22, 1, .36, 1] });
}

export function popStagger(nodes, gap = .05) {
  if (!M.animate || reduced || !nodes.length) return;
  nodes.forEach((n, i) => pop(n, i * gap));
}

export function popChips(root) {
  if (!M.animate || reduced) return;
  const chips = root.querySelectorAll('.chip');
  if (!chips.length) return;
  M.animate(chips, { opacity: [0, 1], transform: ['scale(.86)', 'scale(1)'] },
    { duration: .3, delay: M.stagger(.014), easing: 'ease-out' });
}

export function setFill(fill, pct, animate = true) {
  if (!fill) return;
  const scale = Math.max(0, Math.min(1, pct / 100));
  const from = fill._scale ?? 0;
  fill._scale = scale;
  if (!animate || !M.animate || reduced) {
    fill.style.transform = `scaleX(${scale})`;
    return;
  }
  M.animate(fill, { transform: [`scaleX(${from})`, `scaleX(${scale})`] },
    { duration: .45, easing: [.22, 1, .36, 1] });
}

export function popProgress(pct) {
  setFill($('#prog-fill'), pct);
}

export function resetFill(fill) {
  if (!fill) return;
  fill._scale = 0;
  fill.style.transform = 'scaleX(0)';
}

export function pulse(node) {
  if (!M.animate || reduced) return;
  M.animate(node, { transform: ['scale(.94)', 'scale(1)'] },
    { duration: .28, easing: [.22, 1, .36, 1] });
}

export function emptyHTML(title, hint, icon = 'info') {
  const icons = {
    image: '<path d="M3 5h18v14H3z"/><circle cx="8.5" cy="9.5" r="1.4"/><path d="M21 15l-5-5L6 19"/>',
    folder: '<path d="M3 7a2 2 0 012-2h4l2 2h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2z"/>',
    clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3.5 2"/>',
    info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v5"/><path d="M12 8h.01"/>',
  };
  return `<div class="empty">
    <div class="empty-ico"><svg viewBox="0 0 24 24" aria-hidden="true">${icons[icon] || icons.info}</svg></div>
    <div class="empty-title">${esc(title)}</div>
    ${hint ? `<div class="empty-hint">${esc(hint)}</div>` : ''}
  </div>`;
}

export function skeletonHTML() {
  return `<div class="skel" aria-hidden="true">
    <div class="skel-head">
      <div class="skel-img"></div>
      <div class="skel-meta">
        <div class="skel-line skel-w-42"></div>
        <div class="skel-line skel-w-64 skel-h-sm"></div>
      </div>
    </div>
    <div class="skel-cards">
      <div class="skel-card"></div><div class="skel-card"></div>
      <div class="skel-card"></div><div class="skel-card"></div>
    </div>
  </div>`;
}

export function showView(name) {
  document.querySelectorAll('.view').forEach((v) => {
    v.hidden = v.id !== 'view-' + name;
  });
  document.querySelectorAll('.nav-item').forEach((b) => {
    const scopeOk = b.dataset.view !== 'history' || !b.dataset.scope || b.dataset.scope === state.histScope;
    b.classList.toggle('is-active', b.dataset.view === name && scopeOk);
  });
  $('.main').scrollTop = 0;
  if (name === 'history') window.__kwLoadHistory?.(true);
  if (name === 'settings') window.__kwLoadSettings?.();
  if (M.animate && !reduced) {
    const v = $('#view-' + name);
    const parts = [v.querySelector('.view-head'), ...v.querySelectorAll('.view-head ~ *')];
    parts.filter(Boolean).forEach((n, i) => pop(n, i * .04));
  }
}

export function chipHTML(t, limit, plain = false) {
  const over = limit && t.length > limit;
  const cls = ['chip', over && 'is-over', plain && 'plain'].filter(Boolean).join(' ');
  return `<button type="button" class="${cls}" data-tag="${esc(t)}" title="Klik untuk menyalin">${
    esc(t)}${limit ? `<span class="n">${t.length}</span>` : ''}</button>`;
}

const ATTR_LABELS = [
  ['asset_type', 'Jenis gambar'],
  ['style', 'Style'],
  ['mood', 'Mood'],
  ['tone', 'Tone'],
  ['colors', 'Warna dominan'],
  ['lighting', 'Pencahayaan'],
  ['composition', 'Komposisi'],
  ['product_type', 'Jenis produk'],
];

export function attrsHTML(d) {
  const rows = attrRows(d).map(([label, vals]) => `<div class="attr-row"><span class="attr-key">${label}</span><div class="chips">${
    vals.map((v) => chipHTML(v, 0, true)).join('')}</div></div>`).join('');
  return rows ? `<div class="attr-list">${rows}</div>` : '';
}

export function extractCopyText(d, desc) {
  const lines = attrRows(d).map(([label, vals]) => `${label}: ${vals.join(', ')}`);
  return [desc, ...lines].filter(Boolean).join('\n');
}

function attrRows(d) {
  return ATTR_LABELS.map(([key, label]) => {
    const raw = d[key];
    return [label, (Array.isArray(raw) ? raw : [raw]).filter(Boolean)];
  }).filter(([, vals]) => vals.length);
}
