/* core.js — utilitas bersama: state global, DOM helper, format, escape. */

export const $ = (s, r = document) => r.querySelector(s);
export const M = globalThis.Motion || {};
export const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;

export const state = {
  folder: null,
  files: [],
  selected: new Set(),
  batchId: null,
  es: null,
  running: false,
  histPage: 1,
  histPageSize: 30,
  histTotal: 0,
  histScope: 'keyword',
  histStatus: 'all',
  histSource: 'all',
  histMarket: 'all',
  histRuns: [],
  histSelect: false,
  histSelected: new Set(),
  histPending: new Map(),
  histBatchOpen: new Set(),
  drawerIndex: -1,
  drawerRunId: null,
  drawerIsExtract: false,
  markets: [],
  singleRunning: false,
  extractRunning: false,
};

export const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) =>
  ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

export const secs = (ms) => ms >= 1000 ? (ms / 1000).toFixed(1) + 's' : Math.round(ms) + 'ms';

export const MARKETS = ['etsy', 'canva', 'creative_market', 'universal', 'adobe'];
export const MK_KEY = 'kw.marketplaces';

export function fmtDate(iso) {
  const d = new Date(iso);
  return d.toLocaleDateString('id-ID', { day: '2-digit', month: 'short' }) + ' ' +
         d.toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' });
}

export const SRC_LABEL = { upload: 'Unggah', path: 'Folder', batch: 'Batch', extract: 'Ekstrak' };
export const srcLabel = (s) => SRC_LABEL[s] || 'Unggah';

export function fmtTime(iso) {
  return new Date(iso).toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' });
}

export function dayLabel(iso) {
  const d = new Date(iso);
  const a = new Date(); a.setHours(0, 0, 0, 0);
  const b = new Date(d); b.setHours(0, 0, 0, 0);
  const diff = Math.round((a - b) / 86400000);
  if (diff === 0) return 'Hari ini';
  if (diff === 1) return 'Kemarin';
  return d.toLocaleDateString('id-ID', { day: '2-digit', month: 'short', year: 'numeric' });
}
