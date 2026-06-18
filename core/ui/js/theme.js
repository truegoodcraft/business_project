// SPDX-License-Identifier: AGPL-3.0-or-later

export const THEME_STORAGE_KEY = 'bus.ui.themeVariant';
export const DEFAULT_THEME = 'forge-dark';

export const THEME_OPTIONS = [
  { value: 'forge-dark', label: 'BUS Core Default / Forge Dark' },
  { value: 'clean-light', label: 'Clean Light' },
  { value: 'workshop-slate', label: 'Workshop Slate' },
  { value: 'high-contrast', label: 'High Contrast' },
];

const LEGACY_THEME_MAP = {
  current: DEFAULT_THEME,
  dark: DEFAULT_THEME,
  default: DEFAULT_THEME,
  forge: DEFAULT_THEME,
  'forge-dark': DEFAULT_THEME,
  system: DEFAULT_THEME,
  light: 'clean-light',
  'clean-light': 'clean-light',
  slate: 'workshop-slate',
  'workshop-slate': 'workshop-slate',
  contrast: 'high-contrast',
  'high-contrast': 'high-contrast',
};

const STORAGE_KEYS = [
  THEME_STORAGE_KEY,
  'bus.ui.theme',
  'bus.ui.style',
  'bus.theme',
];

export function normalizeTheme(value) {
  const key = String(value || '').trim().toLowerCase();
  return LEGACY_THEME_MAP[key] || DEFAULT_THEME;
}

export function getStoredTheme() {
  return normalizeTheme(getStoredThemeValue());
}

export function getStoredThemeValue() {
  try {
    for (const key of STORAGE_KEYS) {
      const value = localStorage.getItem(key);
      if (value) return value;
    }
  } catch {
    // Fall through to default.
  }
  return null;
}

export function applyTheme(value, options = {}) {
  const theme = normalizeTheme(value);
  document.documentElement.dataset.busTheme = theme;
  if (options.persist !== false) {
    try {
      localStorage.setItem(THEME_STORAGE_KEY, theme);
    } catch {}
  }
  document.dispatchEvent(new CustomEvent('bus:theme-change', { detail: { theme } }));
  return theme;
}

export function initTheme() {
  return applyTheme(getStoredTheme(), { persist: false });
}
