/* settings.js — form pengaturan: muat, simpan, status inline. */

import { $ } from './core.js';
import { toast } from './ui.js';

let loadStatsFn = () => {};

export function bindSettingsHooks(hooks) {
  loadStatsFn = hooks.loadStats || loadStatsFn;
}

function setSettingsStatus(msg, bad = false) {
  const el = $('#set-status');
  el.textContent = msg || '';
  el.classList.toggle('is-bad', bad);
}

export async function loadSettings() {
  setSettingsStatus('Memuat…');
  try {
    const c = await (await fetch('/api/config')).json();
    $('#set-router').value = c.router_url || '';
    $('#set-model').value = c.model || '';
    $('#set-fallbacks').value = (c.fallback_models || []).join('\n');
    $('#set-max-side').value = c.max_image_side ?? 1024;
    $('#set-timeout').value = c.timeout_seconds ?? 120;
    $('#set-max-kw').value = c.max_keywords ?? 30;
    $('#set-max-sig').value = c.max_signal_terms ?? 150;
    $('#set-temp').value = c.temp_dir || 'tmp';
    $('#set-key').value = '';
    $('#set-key-hint').textContent = c.has_key
      ? `Tersimpan: ${c.key_hint} — biarkan kosong kalau tidak ingin mengubah.`
      : 'Belum ada kunci API tersimpan.';
    $('#set-image-url').value = c.image_base_url || '';
    $('#set-image-model').value = c.image_model || 'flux-2-flex';
    $('#set-image-size').value = c.image_size || '1024x1024';
    $('#set-image-key').value = '';
    $('#set-image-key-hint').textContent = c.image_has_key
      ? `Tersimpan: ${c.image_key_hint} — biarkan kosong kalau tidak ingin mengubah.`
      : 'Belum ada kunci API tersimpan.';
    setSettingsStatus('');
  } catch (e) {
    setSettingsStatus('Gagal memuat: ' + e.message, true);
  }
}

async function saveSettings(e) {
  e.preventDefault();
  const btn = $('#set-save');
  const body = {
    router_url: $('#set-router').value.trim(),
    model: $('#set-model').value.trim(),
    fallback_models: $('#set-fallbacks').value.split('\n').map((s) => s.trim()).filter(Boolean),
    max_image_side: Number($('#set-max-side').value),
    timeout_seconds: Number($('#set-timeout').value),
    max_keywords: Number($('#set-max-kw').value),
    max_signal_terms: Number($('#set-max-sig').value),
    temp_dir: $('#set-temp').value.trim(),
    api_key: $('#set-key').value.trim(),
    image_base_url: $('#set-image-url').value.trim(),
    image_model: $('#set-image-model').value.trim(),
    image_size: $('#set-image-size').value,
    image_api_key: $('#set-image-key').value.trim(),
  };

  btn.disabled = true;
  setSettingsStatus('Menyimpan…');
  try {
    const r = await fetch('/api/config', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!r.ok) {
      let msg = 'Permintaan gagal';
      try { msg = (await r.json()).detail || msg; } catch {}
      throw new Error(msg);
    }
    const c = await r.json();
    $('#set-key').value = '';
    $('#set-key-hint').textContent = c.has_key
      ? `Tersimpan: ${c.key_hint} — biarkan kosong kalau tidak ingin mengubah.`
      : 'Belum ada kunci API tersimpan.';
    $('#set-image-key').value = '';
    $('#set-image-key-hint').textContent = c.image_has_key
      ? `Tersimpan: ${c.image_key_hint} — biarkan kosong kalau tidak ingin mengubah.`
      : 'Belum ada kunci API tersimpan.';
    setSettingsStatus('Tersimpan — langsung dipakai, tanpa restart.');
    toast('Pengaturan disimpan');
    loadStatsFn();
  } catch (err) {
    setSettingsStatus('Gagal menyimpan: ' + err.message, true);
  } finally {
    btn.disabled = false;
  }
}

export function wireSettings() {
  $('#settings-form').addEventListener('submit', saveSettings);
  $('#set-reload').addEventListener('click', loadSettings);
}
