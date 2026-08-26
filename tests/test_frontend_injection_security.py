from __future__ import annotations

import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


DOM_STUB = r"""
import assert from 'node:assert/strict';

class TestNode {
  constructor(tagName) {
    this.tagName = String(tagName).toUpperCase();
    this.children = [];
    this.attributes = Object.create(null);
    this.className = '';
    this.textContent = '';
    this.innerHTMLWrites = 0;
    const classes = new Set();
    this.classList = {
      add: (...names) => names.forEach((name) => classes.add(name)),
      remove: (...names) => names.forEach((name) => classes.delete(name)),
      contains: (name) => classes.has(name),
      toggle: (name, force) => {
        const enabled = force === undefined ? !classes.has(name) : Boolean(force);
        if (enabled) classes.add(name);
        else classes.delete(name);
        return enabled;
      },
    };
  }

  append(...children) {
    this.children.push(...children);
  }

  appendChild(child) {
    this.children.push(child);
    return child;
  }

  replaceChildren(...children) {
    this.children = [];
    this.append(...children);
  }

  setAttribute(name, value) {
    this.attributes[name] = String(value);
  }

  getAttribute(name) {
    return this.attributes[name] ?? null;
  }

  set innerHTML(value) {
    this._innerHTML = String(value);
    this.innerHTMLWrites += 1;
  }

  get innerHTML() {
    return this._innerHTML || '';
  }
}

function descendants(node) {
  return [node, ...(node.children || []).flatMap(descendants)];
}

function byTag(node, tagName) {
  return descendants(node).filter((entry) => entry.tagName === String(tagName).toUpperCase());
}

const documentStub = {
  createElement: (tagName) => new TestNode(tagName),
  createDocumentFragment: () => new TestNode('#fragment'),
};
"""


def _run_node(script: str) -> None:
    subprocess.run(
        ["node", "--input-type=module", "-e", script],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )


def test_unknown_route_hash_is_rendered_as_text_not_markup() -> None:
    script = DOM_STUB + r"""
import fs from 'node:fs';
import vm from 'node:vm';

const source = fs.readFileSync('core/ui/app.js', 'utf8');
const start = source.indexOf('function renderInlinePanel(');
const end = source.indexOf('\nasync function showNotFound(', start);
assert.notEqual(start, -1);
assert.notEqual(end, -1);
const implementation = source.slice(start, end);

const screen = new TestNode('section');
const maliciousHash = '#/missing"><img src=x onerror=globalThis.routePwned=true>';
const context = {
  document: {
    ...documentStub,
    querySelector: (selector) => selector === '[data-role="home-screen"]' ? screen : null,
  },
  maliciousHash,
};
vm.runInNewContext(
  `${implementation}\nrenderInlinePanel('404 — Not Found', 'The requested route does not exist.', maliciousHash);`,
  context,
);

assert.equal(screen.innerHTMLWrites, 0);
assert.equal(byTag(screen, 'code').length, 1);
assert.equal(byTag(screen, 'code')[0].textContent, maliciousHash);
assert.equal(byTag(screen, 'img').length, 0);
assert.equal(context.routePwned, undefined);
"""
    _run_node(script)


def test_manufacturing_history_values_are_rendered_as_text_not_markup() -> None:
    script = DOM_STUB + r"""
globalThis.document = documentStub;
globalThis.window = {
  fetch: async () => { throw new Error('network not expected'); },
  BUS_UNITS: { american: false },
};

const { buildRecentRunRow } = await import('./core/ui/js/cards/manufacturing.js');
const maliciousName = '<img src=x onerror=globalThis.namePwned=true>';
const maliciousQuantity = '<svg onload=globalThis.quantityPwned=true>';
const maliciousUnit = '</div><script>globalThis.unitPwned=true</script>';
const row = buildRecentRunRow({
  source_kind: maliciousName,
  quantity_decimal: maliciousQuantity,
  uom: maliciousUnit,
  created_at: '2026-08-25T12:00:00Z',
});

assert.equal(row.innerHTMLWrites, 0);
assert.equal(row.children[0].textContent, maliciousName);
assert.equal(row.children[0].getAttribute('title'), maliciousName);
assert.equal(row.children[2].textContent, `${maliciousQuantity} ${maliciousUnit}`);
for (const tagName of ['img', 'svg', 'script']) {
  assert.equal(byTag(row, tagName).length, 0);
}
assert.equal(globalThis.namePwned, undefined);
assert.equal(globalThis.quantityPwned, undefined);
assert.equal(globalThis.unitPwned, undefined);

const maliciousId = '<img src=x onerror=globalThis.idPwned=true>';
const idRow = buildRecentRunRow({ source_id: maliciousId, quantity_decimal: '1', uom: 'ea' });
assert.equal(idRow.children[0].textContent, `Run #${maliciousId}`);
assert.equal(byTag(idRow, 'img').length, 0);
assert.equal(globalThis.idPwned, undefined);
"""
    _run_node(script)


def test_jobs_api_error_is_rendered_as_text_not_markup() -> None:
    script = DOM_STUB + r"""
globalThis.document = documentStub;
globalThis.window = {
  fetch: async () => { throw new Error('network not expected'); },
  BUS_UNITS: { american: false },
};

const { renderJobsLoadError } = await import('./core/ui/js/cards/jobs.js');
const maliciousDetail = '<img src=x onerror=globalThis.errorPwned=true>';
const root = new TestNode('section');
renderJobsLoadError(root, { payload: { detail: maliciousDetail } });

assert.equal(root.innerHTMLWrites, 0);
assert.equal(byTag(root, 'h2')[0].textContent, 'Jobs unavailable');
assert.equal(byTag(root, 'p')[0].textContent, maliciousDetail);
assert.equal(byTag(root, 'img').length, 0);
assert.equal(globalThis.errorPwned, undefined);
"""
    _run_node(script)
