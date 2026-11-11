/* markets.js — pilihan marketplace, dipakai bersama oleh view Single & Batch. */

import { state, MARKETS, MK_KEY } from './core.js';
import { toast } from './ui.js';

function loadMarkets() {
  let raw = null;
  try { raw = localStorage.getItem(MK_KEY); } catch { return [...MARKETS]; }
  if (raw === null) return [...MARKETS];
  try {
    const v = JSON.parse(raw);
    if (!Array.isArray(v)) return [...MARKETS];
    const picked = v.filter((m) => MARKETS.includes(m));
    return !picked.length && v.length ? [...MARKETS] : picked;
  } catch { return [...MARKETS]; }
}

function saveMarkets(list) {
  try { localStorage.setItem(MK_KEY, JSON.stringify(list)); } catch {}
}

function syncMarkets() {
  const set = new Set(state.markets);
  document.querySelectorAll('input[data-mk]').forEach((cb) => { cb.checked = set.has(cb.dataset.mk); });
}

function syncMarketState() {
  const n = state.markets.length;
  const total = MARKETS.length;
  const label = n === 0
    ? 'Belum ada marketplace dipilih — pilih minimal satu.'
    : n === total
      ? 'Semua marketplace dipilih.'
      : `${n} dari ${total} marketplace dipilih.`;
  document.querySelectorAll('[data-mk-state]').forEach((el) => {
    el.textContent = label;
    el.classList.toggle('is-warn', n === 0);
  });
  document.dispatchEvent(new CustomEvent('kw:markets', { detail: state.markets }));
}

export function requireMarkets() {
  if (!state.markets.length) { toast('Pilih minimal satu marketplace', 'bad'); return false; }
  return true;
}

export function wireMarkets() {
  state.markets = loadMarkets();
  syncMarkets();
  document.querySelectorAll('input[data-mk]').forEach((cb) => {
    cb.addEventListener('change', () => {
      const k = cb.dataset.mk;
      const set = new Set(state.markets);
      if (cb.checked) set.add(k); else set.delete(k);
      state.markets = MARKETS.filter((m) => set.has(m));
      saveMarkets(state.markets);
      syncMarkets();
      syncMarketState();
    });
  });
  syncMarketState();
}
