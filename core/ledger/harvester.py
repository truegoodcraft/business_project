# core/ledger/harvester.py
import json, os, hashlib, time
from .service import stock_in, stock_out_fifo

MANUFACTURING_JOURNAL = os.environ.get('BUS_MANUFACTURING_JOURNAL', 'data/journals/manufacturing.jsonl')
INVENTORY_JOURNAL = os.environ.get('BUS_INVENTORY_JOURNAL', 'data/journals/inventory.jsonl')
CURSOR_PATH = os.environ.get('BUS_LEDGER_CURSOR', 'data/ledger_cursor.json')

os.makedirs('data', exist_ok=True)

def _hash_line(line: str) -> str:
    return hashlib.sha1(line.encode('utf-8')).hexdigest()

def _load_cursor():
    if not os.path.exists(CURSOR_PATH):
        return {MANUFACTURING_JOURNAL: 0, INVENTORY_JOURNAL: 0}
    try:
        with open(CURSOR_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {MANUFACTURING_JOURNAL: 0, INVENTORY_JOURNAL: 0}

def _save_cursor(cur):
    with open(CURSOR_PATH, 'w', encoding='utf-8') as f:
        json.dump(cur, f)

# Idempotent line apply using source_id = sha1(line)

def _apply_line(obj: dict, source_kind: str, raw_line: str):
    sid = f"harvest:{source_kind}:{_hash_line(raw_line)}"
    # manufacturing journal schema (assumed): list of item deltas per run
    if source_kind == 'manufacturing':
        for d in obj.get('deltas', []):
            item_id = int(d['item_id'])
            qty = float(d['qty'])
            if qty > 0:
                # outputs: we do not know unit cost here → 0; later a manual adjust can set cost or Phase 5 inherits cost
                stock_in(item_id, qty, 0, 'production', sid)
            elif qty < 0:
                stock_out_fifo(item_id, -qty, 'manufacturing', sid)
    elif source_kind == 'inventory':
        # inventory adjustments: expect {item_id, delta, maybe unit_cost_cents}
        item_id = int(obj['item_id'])
        delta = float(obj['delta'])
        ucc = int(obj.get('unit_cost_cents', 0))
        if delta > 0:
            stock_in(item_id, delta, ucc, 'adjustment', sid)
        elif delta < 0:
            stock_out_fifo(item_id, -delta, 'adjustment', sid)


def run_once():
    cur = _load_cursor()
    for path, kind in ((MANUFACTURING_JOURNAL, 'manufacturing'), (INVENTORY_JOURNAL, 'inventory')):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                f.seek(cur.get(path, 0))
                while True:
                    line = f.readline()
                    if not line:
                        break
                    pos = f.tell()
                    try:
                        obj = json.loads(line)
                        _apply_line(obj, kind, line)
                    except Exception:
                        pass  # ignore malformed lines
                    cur[path] = pos
        except FileNotFoundError:
            # journal may not exist yet
            pass
    _save_cursor(cur)

