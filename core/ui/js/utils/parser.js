// Copyright (C) 2025 BUS Core Authors
// SPDX-License-Identifier: AGPL-3.0-or-later

export function parseSmartInput(str) {
  const text = (str || '').trim();
  if (!text) return null;
  const match = /^(\d+(?:\.\d+)?)\s*([a-zA-Z"']+)?$/u.exec(text.replace(/,/g, ''));
  if (!match) return null;
  const qty = Number(match[1]);
  let unitRaw = (match[2] || '').toLowerCase();
  if (unitRaw === '"') unitRaw = 'inch';
  if (unitRaw === "'") unitRaw = 'ft';
  if (unitRaw === 'kg') unitRaw = 'kg';
  const normalized = unitRaw ? unitRaw.replace(/\"|\'/g, '').toUpperCase() : '';
  const system = ['KG', 'G', 'MG'].includes(normalized)
    ? 'metric'
    : ['INCH', 'FT'].includes(normalized)
      ? 'imperial'
      : 'each';
  return { qty, unit: normalized || null, system };
}

export function parseApiError(body) {
  if (!body) return { message: 'Unknown error', fields: null };

  // 1. List (Pydantic): { "detail": [ { "msg": "...", "loc": [...], "type": "..." }, ... ] }
  if (body.detail && Array.isArray(body.detail)) {
    const lines = body.detail.map(d => `• ${d.msg}`);
    return { message: lines.join('\n'), fields: null };
  }

  // 2. Structured: { "detail": "message", "fields": { ... } }
  // 3. Simple: { "detail": "message" }
  if (typeof body.detail === 'string') {
    return { message: body.detail, fields: body.fields || null };
  }

  // Fallbacks
  const msg = body.message || body.error || (typeof body === 'string' ? body : JSON.stringify(body));
  return { message: msg, fields: null };
}
