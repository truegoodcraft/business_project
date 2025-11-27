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
