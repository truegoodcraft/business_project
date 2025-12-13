/* SPDX-License-Identifier: AGPL-3.0-or-later */
/**
 * Inventory expanded row cleanup:
 * - Remove duplicate "Price" & "Location" blocks inside expansion (already shown in header row)
 * - Convert Remaining/Original from base units to the item's display unit (2 decimals)
 * - Convert Unit Cost to the item's display unit if shown in base units
 * - Render Notes in a dedicated block
 * - Show base values in a tooltip (title) on hover
 */
import { UNIT_DIM_INDEX, norm } from "../lib/units.js";
import { fromBaseQty, fromBaseUnitPrice, fmtQty, fmtMoney } from "../lib/units.js";

function text(el){ return (el?.textContent || "").trim(); }
function $(sel, root=document){ return root.querySelector(sel); }
function $all(sel, root=document){ return Array.from(root.querySelectorAll(sel)); }

function dimForUnit(u){ return UNIT_DIM_INDEX[norm(u)] || 'count'; }

function parseHeaderDisplayUnit(row){
  // Try to read unit from Quantity cell like "1.969 m2", else from Price like "$29.00 / m2"
  const qtyCell = $all('td, .cell', row).find(td => /quantity/i.test(td?.previousElementSibling?.textContent||""));
  const priceCell = $all('td, .cell', row).find(td => /price/i.test(td?.previousElementSibling?.textContent||""));
  let unit = null;
  if (qtyCell){
    const m = text(qtyCell).match(/[-\d.,]+\s*([a-zA-Z_²^2]+)$/);
    if (m) unit = m[1].replace(/[²^2]/g,'2').toLowerCase();
  }
  if (!unit && priceCell){
    const m = text(priceCell).match(/\/\s*([a-zA-Z_²^2]+)/);
    if (m) unit = m[1].replace(/[²^2]/g,'2').toLowerCase();
  }
  return unit || 'ea';
}

function convertRemainingOriginal(panel, unit){
  // Find remaining/original cell and rewrite it as "{remain} / {orig} {unit}" with tooltip showing base
  const labelCell = $all('th, .th, .label', panel).find(th => /remaining\s*\/\s*original/i.test(text(th)));
  if (!labelCell) return;
  const valCell = labelCell.parentElement?.querySelector('td, .td, .value') || labelCell.nextElementSibling;
  if (!valCell) return;
  const s = text(valCell);
  const m = s.replace(/,/g,'').match(/(-?\d+)\s*\/\s*(-?\d+)/);
  if (!m) return;
  const baseRemain = parseInt(m[1],10);
  const baseOrig   = parseInt(m[2],10);
  const dim = dimForUnit(unit);
  const remain = fmtQty(fromBaseQty(baseRemain, unit, dim));
  const orig   = fmtQty(fromBaseQty(baseOrig, unit, dim));
  valCell.textContent = `${remain} / ${orig} ${unit}`;
  valCell.setAttribute('title', `${baseRemain.toLocaleString()} / ${baseOrig.toLocaleString()} (base)`);
}

function convertUnitCost(panel, unit){
  // Find "Unit Cost" cell and ensure "/ unit" matches display unit
  const labelCell = $all('th, .th, .label', panel).find(th => /unit\s*cost/i.test(text(th)));
  if (!labelCell) return;
  const valCell = labelCell.parentElement?.querySelector('td, .td, .value') || labelCell.nextElementSibling;
  if (!valCell) return;
  const s = text(valCell);
  // If already shows "/ unit" matching display unit, leave as is.
  if (new RegExp(`/\\s*${unit}\\b`).test(s)) return;
  // Else try to parse "$x.xx / <baseUnit>" and convert
  const m = s.replace(/,/g,'').match(/\$?\s*([0-9.]+)\s*\/\s*([a-zA-Z_²^2]+)/);
  if (!m) return;
  const price = parseFloat(m[1]);
  const baseUnit = m[2].replace(/[²^2]/g,'2').toLowerCase();
  const dim = dimForUnit(unit);
  // If baseUnit is a metric base unit in same dimension, convert; otherwise just rewrite suffix
  const converted = fromBaseUnitPrice(price, unit, dim);
  valCell.textContent = `$${fmtMoney(converted)} / ${unit}`;
  valCell.setAttribute('title', `${price} / ${baseUnit} (base)`);
}

function removeDuplicates(panel){
  // Inside the expanded content, hide redundant "Price" and "Location" blocks
  $all('*', panel).forEach(el => {
    const t = text(el).toLowerCase();
    if (t === 'price' || t === 'location'){
      // hide the label+value row if it is in the detail header area
      const row = el.closest('.row, tr, div');
      if (row && row !== panel) row.style.display = 'none';
    }
  });
}

function tidyNotes(panel){
  // Hoist free text note into a dedicated block
  const note = $all('div, p, span', panel).find(el =>
    el && !el.children.length &&
    text(el).length > 30 && !/^\d{1,2}\/\d{1,2}\/\d{2,4}$/.test(text(el)) &&
    !/^\$/.test(text(el)) &&
    !/^\w+\s*\/\s*\w+/.test(text(el))
  );
  if (!note) return;
  const block = document.createElement('div');
  block.className = 'inv-note';
  block.style.cssText = 'margin:8px 0 10px; padding:8px 10px; border:1px solid rgba(36,48,65,.6); border-radius:8px; background:rgba(0,0,0,.12); color:#a9b7c8; max-width:70ch;';
  const h = document.createElement('div');
  h.textContent = 'Notes';
  h.style.cssText = 'font-weight:600; margin-bottom:4px; color:#e7eef7;';
  const p = document.createElement('div');
  p.textContent = text(note);
  block.appendChild(h); block.appendChild(p);
  note.replaceWith(block);
}

function enhanceExpanded(expandedRoot){
  const parentRow = expandedRoot.closest('tr, .row, .item')?.previousElementSibling || document.querySelector('[data-role="inventory-row-current"]');
  const unit = parseHeaderDisplayUnit(parentRow || document);
  convertRemainingOriginal(expandedRoot, unit);
  convertUnitCost(expandedRoot, unit);
  removeDuplicates(expandedRoot);
  tidyNotes(expandedRoot);
}

(function bootstrap(){
  function onPage(){
    if (!location.hash.match(/#\/inventory/)) return;
    // Observe for expansions
    const root = document.getElementById('app') || document.body;
    const mo = new MutationObserver((muts) => {
      muts.forEach(() => {
        $all('.expanded, .details, .batch-panel', root).forEach(enhanceExpanded);
      });
    });
    mo.observe(root, { childList:true, subtree:true });
    // Initial pass
    $all('.expanded, .details, .batch-panel', root).forEach(enhanceExpanded);
    document.addEventListener('bus:units-mode', () => {
      $all('.expanded, .details, .batch-panel', root).forEach(enhanceExpanded);
    });
  }
  window.addEventListener('hashchange', () => setTimeout(onPage, 0));
  document.addEventListener('DOMContentLoaded', () => setTimeout(onPage, 0));
})();
