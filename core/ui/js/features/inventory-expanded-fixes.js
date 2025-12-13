/* SPDX-License-Identifier: AGPL-3.0-or-later */
/**
 * Inventory expanded row cleanup (loop-safe, robust selectors).
 * - One-time enhancement per expanded panel (WeakSet guard).
 * - Remaining/Original rendered in display unit (2 decimals); base numbers on hover.
 * - Hide duplicate Price/Location rows (label + value).
 * - Notes rendered in a constrained block; original long text hidden.
 */
import {
  UNIT_DIM_INDEX, norm,
  fromBaseQty, fromBaseUnitPrice,
  fmtQty, fmtMoney
} from "../lib/units.js";

const PROCESSED = new WeakSet();

const t = (el)=> (el?.textContent || "").trim();
const $ = (sel, root=document)=> root.querySelector(sel);
const $$ = (sel, root=document)=> Array.from(root.querySelectorAll(sel));
const unitDim = (u)=> UNIT_DIM_INDEX[norm(u)] || 'count';

function parseDisplayUnitFromHeader(row){
  if (!row) return 'ea';
  const cells = $$('td, .cell, [role="cell"], .kv-value', row);
  for (const td of cells){
    const s = t(td);
    // try Price suffix first: "$.. / m2"
    let m = s.match(/\/\s*([a-zA-Z_²^2]+)/);
    if (m) return m[1].replace(/[²^2]/g,'2').toLowerCase();
    // then Quantity suffix: "1.969 m2"
    m = s.match(/[-\d.,]+\s*([a-zA-Z_²^2]+)$/);
    if (m) return m[1].replace(/[²^2]/g,'2').toLowerCase();
  }
  return 'ea';
}

function hideDuplicateKv(panel){
  // Hide any KV rows where label is exactly "Price" or "Location"
  const labels = $$('*', panel).filter(n=>/^(price|location)$/i.test(t(n)));
  for (const lab of labels){
    const row = lab.closest('.row, tr, .kv, .grid, div');
    if (row){
      row.style.display = 'none';
    } else {
      // Fallback: hide label and its next sibling (value)
      lab.style.display = 'none';
      if (lab.nextElementSibling) lab.nextElementSibling.style.display = 'none';
    }
  }
}

function convertRemainingOriginal(panel, unit){
  // Strategy: find the FIRST text in panel that looks like "<int> / <int>"
  // (this is the "Remaining / Original" cell), then rewrite it.
  const candidates = $$('td, .td, .value, div, span', panel);
  for (const el of candidates){
    const s = t(el).replace(/,/g,'');
    const m = s.match(/^\s*(-?\d+)\s*\/\s*(-?\d+)\s*$/);
    if (!m) continue;
    const baseRemain = parseInt(m[1],10);
    const baseOrig   = parseInt(m[2],10);
    if (Number.isNaN(baseRemain) || Number.isNaN(baseOrig)) continue;

    const dim = unitDim(unit);
    const remain = fmtQty(fromBaseQty(baseRemain, unit, dim));
    const orig   = fmtQty(fromBaseQty(baseOrig, unit, dim));
    el.textContent = `${remain} / ${orig} ${unit}`;
    el.title = `${baseRemain.toLocaleString()} / ${baseOrig.toLocaleString()} (base)`;
    return; // only rewrite the first match
  }
}

function convertUnitCost(panel, unit){
  // Find a money-per-unit pattern and normalize it to display unit if needed.
  const cells = $$('td, .td, .value, div, span', panel);
  for (const el of cells){
    const s = t(el).replace(/,/g,'');
    const m = s.match(/^\$?\s*([0-9.]+)\s*\/\s*([a-zA-Z_²^2]+)\s*$/);
    if (!m) continue;
    const val = parseFloat(m[1]);
    const unitShown = m[2].replace(/[²^2]/g,'2').toLowerCase();
    // If already display unit, keep as is (but ensure formatting)
    if (unitShown === unit){
      el.textContent = `$${fmtMoney(val)} / ${unit}`;
      return;
    }
    // Otherwise treat as base-unit price and convert to display unit
    const dim = unitDim(unit);
    const converted = fromBaseUnitPrice(val, unit, dim);
    el.textContent = `$${fmtMoney(converted)} / ${unit}`;
    el.title = `${m[1]} / ${unitShown} (base)`;
    return;
  }
}

function renderNotes(panel){
  // Find any long, free text and wrap it into a styled note block (max-width).
  const long = $$('div, p, span', panel).find(el =>
    !el.children.length &&
    t(el).length > 30 &&
    !/^\d{1,2}\/\d{1,2}\/\d{2,4}$/.test(t(el)) &&
    !/^\$/.test(t(el)) &&
    !/^\w+\s*\/\s*\w+/.test(t(el))
  );
  if (!long) return;

  const original = t(long);
  const block = document.createElement('div');
  block.className = 'inv-note';
  block.style.cssText = 'margin:8px 0 10px; padding:8px 10px; border:1px solid rgba(36,48,65,.6); border-radius:8px; background:rgba(0,0,0,.12); color:#a9b7c8; max-width:70ch;';
  const h = document.createElement('div');
  h.textContent = 'Notes';
  h.style.cssText = 'font-weight:600; margin-bottom:4px; color:#e7eef7;';
  const p = document.createElement('div');
  p.textContent = original;
  p.style.cssText = 'white-space:normal; overflow-wrap:anywhere;';
  block.appendChild(h); block.appendChild(p);

  // Replace the original node entirely so the text is contained
  long.replaceWith(block);

  // Remove any sibling that duplicates the same long text (paranoid guard)
  $$('div, p, span', panel).forEach(el => {
    if (el !== block && t(el) === original) el.style.display = 'none';
  });
}

function enhance(panel){
  if (!panel || PROCESSED.has(panel)) return;

  const headerRow = panel.previousElementSibling || panel.parentElement?.previousElementSibling;
  const displayUnit = parseDisplayUnitFromHeader(headerRow);

  try {
    hideDuplicateKv(panel);
    convertRemainingOriginal(panel, displayUnit);
    convertUnitCost(panel, displayUnit);
    renderNotes(panel);
  } catch (_) { /* fail-safe */ }

  PROCESSED.add(panel);
}

(function bootstrap(){
  const root = document.getElementById('app') || document.body;
  const isInv = ()=> location.hash.includes('/inventory');

  function scan(){
    if (!isInv()) return;
    $$('.expanded, .details, .batch-panel', root).forEach(enhance);
  }

  const mo = new MutationObserver(records => {
    if (!isInv()) return;
    for (const r of records){
      r.addedNodes?.forEach(node => {
        if (!(node instanceof HTMLElement)) return;
        if (node.matches?.('.expanded, .details, .batch-panel')) enhance(node);
        else node.querySelectorAll?.('.expanded, .details, .batch-panel')?.forEach(enhance);
      });
    }
  });

  window.addEventListener('hashchange', ()=> setTimeout(scan, 0));
  document.addEventListener('DOMContentLoaded', ()=>{
    setTimeout(scan, 0);
    mo.observe(root, { childList:true, subtree:true });
  });
})();
