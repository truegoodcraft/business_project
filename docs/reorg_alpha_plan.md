# BUS Core — Clean Base Plan (Alpha)

## 1. Architecture Diff & Cut Plan
- `core/providers/local_fs.py` → `core/adapters/fs/provider.py`
- `core/providers/google_drive.py` → `core/adapters/drive/provider.py`
- `core/broker/runtime.py` → `core/domain/broker.py`
- `core/catalog/manager.py` → `core/domain/catalog.py`
- Introduced domain-adapter layout directories under `core/`.

## 2. Refactor Worklist
See `docs/reorg_alpha_plan.md` future sections for scaffolding stubs (to be implemented).

## 3. API Contract
_Deferred: aligns with existing HTTP surface; new endpoints tracked for later implementation._

## 4. Plan Schema (v1)
_Pending integration with planner pipeline._

## 5. Journal & Recovery Spec
_Pending implementation in `core/pipeline/`._

## 6. Adapter Contracts
- Local FS adapter remains read-focused; future iterations will extend to R/W per spec.
- Drive adapter likewise retains read-focused contract awaiting pipeline integration.

## 7. Sandbox Contract
_Not yet implemented; reserved for `core/sandbox/runner.py`._

## 8. Policy Pack
_Existing policy engine unchanged; new OPA bridge planned under `core/policy/`._

## 9. Golden Test Suite
- New layout enables incremental test coverage once pipeline lands.

## 10. Migration Guide
- Initialize SQLite and supporting services after pipeline implementation.

## 11. DevOps Checklist
- Lint/test commands unchanged: `ruff .`, `black .`, `pytest -q`.
- CI updates will follow once new modules are populated.
