# Bounded security fuzzing

BUS Core keeps exactly two Atheris harnesses:

- `fuzz_manifest.py` exercises the bounded JSON reader, signed-manifest trust boundary,
  and release-schema selection using both raw and deterministically signed structured inputs.
- `fuzz_paths_zip.py` exercises allowed-root resolution and ZIP-entry validation with raw
  names plus safe, traversal, absolute, Windows-drive, colon, control-character, UNC,
  and symlink shapes. It does not create or extract files.

Atheris is Linux/macOS-only. BUS Core governs it as a Linux Python 3.12 development tool
in `requirements-fuzz-linux.lock.txt`; it is not part of the Windows, runtime, build,
PyInstaller, Docker, signing, or release-publication dependency graphs.

CI runs each harness for 512 deterministic inputs with a five-second per-input timeout,
a 1 GiB RSS ceiling, and a hard input-length bound. Direct runs also receive finite defaults
when those flags are omitted. Example:

```bash
python -m pip install --only-binary=:all: --require-hashes -r requirements-fuzz-linux.lock.txt
python fuzz/fuzz_manifest.py -atheris_runs=10000 -max_len=65537 -timeout=5 -rss_limit_mb=1024 -seed=1
python fuzz/fuzz_paths_zip.py -atheris_runs=10000 -max_len=1027 -timeout=5 -rss_limit_mb=1024 -seed=1
```

These bounded runs improve real parser coverage but are not an OSS-Fuzz or ClusterFuzzLite
integration, so they may not satisfy OpenSSF Scorecard's fuzzing detector. Persistent fuzzing,
corpus hosting, and deeper stateful API fuzzing remain outside this pre-release scope.
