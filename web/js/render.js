/* render.js — kartu hasil marketplace & mount hasil ke DOM. */

import { esc, secs } from './core.js';
import { chipHTML, popStagger, popChips } from './ui.js';
import { trendPanelHTML } from './trends.js';

export function cardHTML(title, pill, pillClass, bodyHTML, copyLabel, extraClass = '') {
  return `<article class="card${extraClass ? ' ' + extraClass : ''}">
    <header class="card-head">
      <span class="card-title">${title}</span>
      ${pill ? `<span class="pill ${pillClass}">${pill}</span>` : ''}
      <div class="spacer"></div>
    </header>
    <div class="card-body">
      ${bodyHTML}
      ${copyLabel ? `<button class="btn btn-ghost" data-copy="${esc(copyLabel)}">Salin ${esc(copyLabel)}</button>` : ''}
    </div>
  </article>`;
}

export function buildCards(d) {
  const etsy = d.etsy_tags || [];
  const canvaTags = d.canva_tags || [];
  const cmTags = d.creative_market_tags || [];
  const uni = d.universal_tags || [];
  const adobeTags = d.adobe_tags || [];

  const etsyBody = `<div class="chips">${
    etsy.map((t) => chipHTML(t, 20)).join('') || '<span class="field-val">—</span>'}</div>`;

  const canvaBody = `
    <div><div class="field-label">Judul</div><div class="field-val">${esc(d.canva_title) || '—'}</div></div>
    ${(d.alt_titles || []).length ? `<div><div class="field-label">Judul alternatif</div>
      <div class="chips">${d.alt_titles.map((t) => chipHTML(t, 0, true)).join('')}</div></div>` : ''}
    <div><div class="field-label">Tag (${canvaTags.length})</div>
      <div class="chips">${canvaTags.map((t) => chipHTML(t, 0)).join('') || '<span class="field-val">—</span>'}</div></div>`;

  const cmBody = `
    <div><div class="field-label">Judul</div><div class="field-val">${esc(d.creative_market_title) || '—'}</div></div>
    <div><div class="field-label">Deskripsi</div><div class="field-val">${esc(d.creative_market_description) || '—'}</div></div>
    ${cmTags.length ? `    <div><div class="field-label">Tag (${cmTags.length})</div>
      <div class="chips">${cmTags.map((t) => chipHTML(t, 0)).join('')}</div></div>` : ''}
    ${(d.style || []).length ? `<div><div class="field-label">Style</div>
      <div class="chips">${d.style.map((t) => chipHTML(t, 0, true)).join('')}</div></div>` : ''}
    ${(d.use_cases || []).length ? `<div><div class="field-label">Kasus penggunaan</div>
      <div class="chips">${d.use_cases.map((t) => chipHTML(t, 0, true)).join('')}</div></div>` : ''}`;

  const uniBody = `
    <div><div class="field-label">Judul</div><div class="field-val">${esc(d.universal_title) || '—'}</div></div>
    <div><div class="field-label">Subjek</div><div class="field-val">${esc(d.subject) || '—'}</div></div>
    <div><div class="field-label">Media</div><div class="field-val">${esc(d.medium) || '—'}</div></div>
    <div><div class="field-label">Tag (${uni.length})</div>
      <div class="chips">${uni.map((t) => chipHTML(t, 0)).join('') || '<span class="field-val">—</span>'}</div></div>`;

  const adobeBody = `
    <div><div class="field-label">Judul</div><div class="field-val">${esc(d.adobe_title) || '—'}</div></div>
    <div><div class="field-label">Kata kunci (${adobeTags.length})</div>
      <div class="chips">${adobeTags.map((t) => chipHTML(t, 0)).join('') || '<span class="field-val">—</span>'}</div></div>`;

  const cards = [
    ['etsy', cardHTML('Etsy', `${etsy.length} tags`, '', etsyBody, 'Etsy tags', 'is-lead')],
    ['canva', cardHTML('Canva', `${canvaTags.length} tags`, '', canvaBody, 'Canva')],
    ['creative_market', cardHTML('Creative Market', `${cmTags.length} tags`, '', cmBody, 'Creative Market')],
    ['universal', cardHTML('Universal', `${uni.length} tags`, '', uniBody, 'Universal')],
    ['adobe', cardHTML('Adobe Stock', `${adobeTags.length} keywords`, '', adobeBody, 'Adobe Stock')],
  ];
  const picked = Array.isArray(d._marketplaces) ? d._marketplaces : null;
  return (picked ? cards.filter(([k]) => picked.includes(k)) : cards).map(([, html]) => html).join('');
}

export function resultHTML(res, d) {
  const thumb = res.thumb ? `/generate/${res.thumb}` : '';
  const errs = d._errors || [];
  const warns = d._warnings || [];
  return `
    <div class="result-head" data-has-result>
      ${thumb ? `<img src="${thumb}" alt="Pratinjau ${esc(res.filename)}">` : ''}
      <div class="rh-meta">
        <div class="rh-name">${esc(res.filename)}</div>
        <div class="rh-sub">${secs(res.duration_ms || 0)}<span class="dot">•</span>${esc(d.model || '—')}${
          errs.length ? `<span class="dot">•</span><span class="rh-warn">${errs.length} bagian gagal</span>` : ''}${
          warns.length ? `<span class="dot">•</span><span class="rh-warn" title="${esc(warns.join(' · '))}">${warns.length} catatan</span>` : ''}</div>
        ${warns.length ? `<div class="rh-warn rh-warn-list">${warns.map((w) => esc(w)).join(' · ')}</div>` : ''}
        ${d.description ? `<div class="rh-desc">${esc(d.description)}</div>` : ''}
      </div>
      <div class="rh-actions">
        <button class="btn btn-primary" data-signals>Cek Google Suggest</button>
        <button class="btn btn-ghost" data-trends aria-expanded="false">Lihat Trend</button>
        <details class="rh-menu">
          <summary class="btn btn-ghost">Unduh &amp; salin</summary>
          <div class="rh-menu-list" role="menu">
            ${res.id ? `<a role="menuitem" href="/api/history/${res.id}/export.txt" download>Unduh TXT</a>` : ''}
            ${res.id ? `<a role="menuitem" href="/api/history/${res.id}/export.json" download>Unduh JSON</a>` : ''}
            ${res.id ? `<a role="menuitem" href="/api/history/${res.id}/export.csv">Ekspor CSV</a>` : ''}
            <button role="menuitem" type="button" data-copy="Semua">Salin semua</button>
          </div>
        </details>
      </div>
    </div>
    ${trendPanelHTML()}
    <div class="sig-legend" aria-hidden="true">
      <span class="lg kuat"><i></i>kuat</span>
      <span class="lg sedang"><i></i>sedang</span>
      <span class="lg lemah"><i></i>lemah</span>
      <span>— sinyal demand Google Suggest (kelima marketplace). Klik “Cek Google Suggest”.</span>
    </div>
    <div class="cards" data-cards>${buildCards(d)}</div>`;
}

export function mountResult(container, res, d) {
  container.innerHTML = resultHTML(res, d);
  container._data = d;
  popStagger([...container.children]);
  popChips(container);
}
