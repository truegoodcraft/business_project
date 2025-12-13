/* SPDX-License-Identifier: AGPL-3.0-or-later */
/**
 * Inventory expanded row cleanup (loop-safe).
 * - One-time enhancement per expanded panel (WeakSet guard) to avoid observer feedback loops.
 * - Convert Remaining/Original to item display unit (2 decimals) and show base values on hover.
 * - Convert Unit Cost to display unit if needed.
 * - Hide duplicate Price/Location in details.
 * - Render Notes in a tidy block.
 */
import { UNIT_DIM_INDEX, norm, factorOf, fromBaseQty, fromBaseUnitPrice, fmtQty, fmtMoney } from "../lib/units.js";

const PROCESSED = new WeakSet();

function text(el){ return (el?.textContent || "").trim(); }
function $all(sel, root=document){ return Array.from(root.querySelectorAll(sel)); }
function unitDim(u){ return UNIT_DIM_INDEX[norm(u)] || 'count'; }

function parseDisplayUnitFromHeader(row){
  if (!row) return 'ea';
  // Look in header/collapsed cells near Quantity or Price
  //  e.g., "1.969 m2" or "$29.00 / m2"
  const cells = $all('td, .cell, [role="cell"]', row);
  for (const td of cells){
    const s = text(td);
    let m = s.match(/\/\s*([a-zA-Z_²^2]+)/);          // from price
    if (m) return m[1].replace(/[²^2]/g,'2').toLowerCase();
    m = s.match(/[-\d.,]+\s*([a-zA-Z_²^2]+)$/);       // from quantity
    if (m) return m[1].replace(/[²^2]/g,'2').toLowerCase();
  }
  return 'ea';
}

function convertRemainingOriginal(panel, unit){
  const labels = $all('th, .th, .label', panel);
  const labelCell = labels.find(th => /remaining\s*\/\s*original/i.test(text(th)));
  if (!labelCell) return;
  const valCell = labelCell.parentElement?.querySelector('td, .td, .value') || labelCell.nextElementSibling;
  if (!valCell) return;
  const s = text(valCell).replace(/,/g,'');
  const m = s.match(/(-?\d+)\s*\/\s*(-?\d+)/);
  if (!m) return;
  const baseRemain = parseInt(m[1],10);
  const baseOrig   = parseInt(m[2],10);
  const dim = unitDim(unit);
  const remain = fmtQty(fromBaseQty(baseRemain, unit, dim));
  const orig   = fmtQty(fromBaseQty(baseOrig, unit, dim));
  valCell.textContent = `${remain} / ${orig} ${unit}`;
  valCell.title = `${baseRemain.toLocaleString()} / ${baseOrig.toLocaleString()} (base)`;
}

function convertUnitCost(panel, unit){
  const labels = $all('th, .th, .label', panel);
  const labelCell = labels.find(th => /unit\s*cost/i.test(text(th)));
  if (!labelCell) return;
  const valCell = labelCell.parentElement?.querySelector('td, .td, .value') || labelCell.nextElementSibling;
  if (!valCell) return;
  const s = text(valCell).replace(/,/g,'');
  // If already correct suffix, exit.
  if (new RegExp(`/\\s*${unit}\\b`).test(s)) return;
  const m = s.match(/\$?\s*([0-9.]+)\s*\/\s*([a-zA-Z_²^2]+)/);
  if (!m) return;
  const priceBase = parseFloat(m[1]);
  const baseUnit  = m[2].replace(/[²^2]/g,'2').toLowerCase();
  const dim = unitDim(unit);
  const priceDisp = fromBaseUnitPrice(priceBase, unit, dim);
  valCell.textContent = `$${fmtMoney(priceDisp)} / ${unit}`;
  valCell.title = `${priceBase} / ${baseUnit} (base)`;
}

function removeDuplicates(panel){
  // Hide duplicate Price / Location blocks in the expanded header area
  $all('*', panel).forEach(el => {
    const t = text(el).toLowerCase();
    if (t === 'price' || t === 'location') {
      const row = el.closest('.row, tr, div');
      if (row && row !== panel) row.style.display = 'none';
    }
  });
}

function tidyNotes(panel){
  // Capture long free text and render as a dedicated Notes block
  const cand = $all('div, p, span', panel).find(el =>
    el && !el.children.length &&
    text(el).length > 30 &&
    !/^\d{1,2}\/\d{1,2}\/\d{2,4}$/.test(text(el)) &&
    !/^\$/.test(text(el)) &&
    !/^\w+\s*\/\s*\w+/.test(text(el))
  );
  if (!cand) return;
  const block = document.createElement('div');
  block.className = 'inv-note';
  block.style.cssText = 'margin:8px 0 10px; padding:8px 10px; border:1px solid rgba(36,48,65,.6); border-radius:8px; background:rgba(0,0,0,.12); color:#a9b7c8; max-width:70ch;';
  const h = document.createElement('div');
  h.textContent = 'Notes';
  h.style.cssText = 'font-weight:600; margin-bottom:4px; color:#e7eef7;';
  const p = document.createElement('div');
  p.textContent = text(cand);
  block.appendChild(h); block.appendChild(p);
  cand.replaceWith(block);
}

function enhanceExpanded(panel){
  if (!panel || PROCESSED.has(panel)) return;
  // Find collapsed/header row (previous sibling row of the details panel)
  const headerRow = panel.previousElementSibling || panel.parentElement?.previousElementSibling;
  const unit = parseDisplayUnitFromHeader(headerRow);
  try {
    convertRemainingOriginal(panel, unit);
    convertUnitCost(panel, unit);
    removeDuplicates(panel);
    tidyNotes(panel);
  } catch (_) { /* fail-safe */ }
  PROCESSED.add(panel);
}

(function bootstrap(){
  const root = document.getElementById('app') || document.body;
  const isInv = () => location.hash.includes('/inventory');

  // Scan existing panels once on load/navigation
  function scanOnce(){
    if (!isInv()) return;
    const panels = $all('.expanded, .details, .batch-panel', root);
    panels.forEach(enhanceExpanded);
  }

  // Observe only for added nodes; process new expansion containers once.
  const mo = new MutationObserver((records) => {
    if (!isInv()) return;
    for (const r of records){
      r.addedNodes && r.addedNodes.forEach(node => {
        if (!(node instanceof HTMLElement)) return;
        if (node.matches?.('.expanded, .details, .batch-panel')) {
          enhanceExpanded(node);
        } else {
          const found = node.querySelectorAll?.('.expanded, .details, .batch-panel');
          found && found.forEach(enhanceExpanded);
        }
      });
    }
  });

  window.addEventListener('hashchange', () => setTimeout(scanOnce, 0));
  document.addEventListener('DOMContentLoaded', () => {
    setTimeout(scanOnce, 0);
    mo.observe(root, { childList: true, subtree: true }); // no attributes to avoid feedback loops
  });
})();
