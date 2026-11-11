/* signals.js — cek sinyal demand Google Suggest lewat stream NDJSON. */

import { $, state } from './core.js';
import { toast, pulse } from './ui.js';

async function checkSignals(btn, host) {
  const d = host._data;
  if (!d) return;
  const seen = new Set();
  const tags = [];
  for (const raw of [
    ...(d.etsy_tags || []), ...(d.canva_tags || []), ...(d.universal_tags || []),
    ...(d.adobe_tags || []), ...(d.creative_market_tags || []),
  ]) {
    const t = String(raw).trim();
    const k = t.toLowerCase();
    if (t && !seen.has(k)) { seen.add(k); tags.push(t); }
  }
  if (!tags.length) { toast('Tidak ada tag untuk dicek'); return; }

  const chips = new Map();
  host.querySelectorAll('.chip[data-tag]').forEach((chip) => {
    const k = chip.dataset.tag.trim().toLowerCase();
    if (!chips.has(k)) chips.set(k, []);
    chips.get(k).push(chip);
    chip.classList.remove('sig-kuat', 'sig-sedang', 'sig-lemah', 'sig-na');
    chip.classList.remove('is-checking');
  });
  tags.forEach((t) =>
    (chips.get(t.toLowerCase()) || []).forEach((c) => c.classList.add('is-checking')));

  btn.disabled = true;
  btn.textContent = 'Cek Google Suggest…';
  const total = tags.length;
  let done = 0, kuat = 0, sedang = 0;

  const apply = (s) => {
    const els = chips.get(String(s.term || '').trim().toLowerCase()) || [];
    if (!els.length) return;
    els.forEach((chip) => {
      chip.classList.remove('is-checking');
      chip.classList.add(s.status === 'n/a' ? 'sig-na' : 'sig-' + s.status);
      chip.title = `${s.note || s.status} · klik untuk menyalin`;
      pulse(chip);
    });
    if (s.status === 'kuat') kuat++;
    else if (s.status === 'sedang') sedang++;
  };

  try {
    const r = await fetch('/api/signals/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ terms: tags }),
    });
    if (!r.ok) {
      let msg = 'Permintaan gagal';
      try { msg = (await r.json()).detail || msg; } catch {}
      throw new Error(msg);
    }
    if (!r.body) throw new Error('Stream tidak didukung browser');

    const reader = r.body.getReader();
    const dec = new TextDecoder();
    let buf = '';
    let truncated = false, requested = total;
    for (;;) {
      const { value, done: end } = await reader.read();
      if (end) break;
      buf += dec.decode(value, { stream: true });
      let nl;
      while ((nl = buf.indexOf('\n')) >= 0) {
        const line = buf.slice(0, nl).trim();
        buf = buf.slice(nl + 1);
        if (!line) continue;
        const msg = JSON.parse(line);
        if (msg.done) {
          truncated = !!msg.truncated;
          requested = msg.requested ?? total;
          continue;
        }
        done++;
        apply(msg);
        btn.textContent = `Cek Google Suggest… ${done}/${total}`;
      }
    }
    const lain = total - kuat - sedang;
    const cut = truncated ? ` · diperiksa ${total} dari ${requested}` : '';
    toast(`Sinyal: ${kuat} kuat · ${sedang} sedang${lain ? ` · ${lain} lainnya` : ''}${cut}`, 'ok');
  } catch (e) {
    toast('Cek Google Suggest gagal: ' + e.message, 'bad');
  } finally {
    host.querySelectorAll('.chip.is-checking').forEach((c) => c.classList.remove('is-checking'));
    btn.disabled = false;
    btn.textContent = 'Cek Google Suggest';
  }
}

export function handleSignalsClick(e) {
  const sg = e.target.closest('[data-signals]');
  if (!sg) return false;
  const host = sg.closest('[data-has-result]')?.parentElement || sg.closest('.drawer-body');
  if (host) checkSignals(sg, host);
  return true;
}

export function payloadFor(label, d) {
  const join = (xs) => (xs || []).join(', ');
  const block = (...parts) => parts.filter((p) => p !== undefined && p !== null && p !== '').join('\n');
  switch (label) {
    case 'Etsy tags': return (d.etsy_tags || []).join('\n');
    case 'Canva':
      return block(d.canva_title, join(d.canva_tags), ...(d.alt_titles || []));
    case 'Creative Market':
      return block(d.creative_market_title, join(d.creative_market_tags), d.creative_market_description);
    case 'Universal':
      return block(d.universal_title, join(d.universal_tags));
    case 'Adobe Stock':
      return block(d.adobe_title, join(d.adobe_tags));
    case 'Semua':
      return [
        block(d.subject),
        block('Etsy', join(d.etsy_tags)),
        block('Canva', d.canva_title, join(d.canva_tags)),
        block('Creative Market', d.creative_market_title, join(d.creative_market_tags), d.creative_market_description),
        block('Universal', d.universal_title, join(d.universal_tags)),
        block('Adobe Stock', d.adobe_title, join(d.adobe_tags)),
      ].filter(Boolean).join('\n\n');
    default: return '';
  }
}
