from pathlib import Path

_base_path = Path(__file__).resolve().parents[2]
_module_path = _base_path / 'writer.markdown/__init__.py'
__file__ = str(_module_path)
with _module_path.open('r', encoding='utf-8') as _fh:
    exec(compile(_fh.read(), __file__, 'exec'))
