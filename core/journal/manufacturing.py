# core/journal/manufacturing.py
import json, os, time

PATH = os.environ.get('BUS_MANUFACTURING_JOURNAL', 'data/journals/manufacturing.jsonl')

os.makedirs(os.path.dirname(PATH), exist_ok=True)

def append_journal(recipe, multiplier, deltas):
    entry = {
        'ts': int(time.time()),
        'recipe': {'id': recipe.id, 'name': recipe.name},
        'multiplier': multiplier,
        'deltas': deltas,
    }
    with open(PATH, 'a', encoding='utf-8') as f:
        f.write(json.dumps(entry) + "\n")
