# Dependency management

BUS Core separates dependency policy from deployable dependency graphs:

- `requirements.txt` defines bounded direct runtime dependencies and minimum security floors.
- `requirements-build.txt` adds the governed Windows/PyInstaller toolchain.
- `requirements-linux.lock.txt` is the complete Python 3.12 Linux runtime graph used by Docker and Linux CI.
- `requirements-windows.lock.txt` is the complete Python 3.11 Windows runtime and release-build graph.

The lock files pin every package and include PyPI distribution hashes. Do not edit them by hand.
Their `.txt` suffix is deliberate: GitHub Dependabot's pip updater scans text requirement files and can maintain the locked pins and hashes.

## Refresh the locks

Use `uv` 0.11.33 from the repository root:

```powershell
py -3.11 -m pip install uv==0.11.33
uv pip compile requirements.txt --python-platform linux --python-version 3.12 --generate-hashes --upgrade --output-file requirements-linux.lock.txt
uv pip compile requirements-build.txt --python-platform windows --python-version 3.11 --generate-hashes --upgrade --output-file requirements-windows.lock.txt
```

Review direct-dependency bounds before accepting a major-version update. Commit each input change and both regenerated locks together.

## Verify a refresh

On Linux/Python 3.12:

```bash
python -m pip install --require-hashes -r requirements-linux.lock.txt
python -m pip check
pip-audit --require-hashes -r requirements-linux.lock.txt
```

On Windows/Python 3.11:

```powershell
py -3.11 -m pip install --require-hashes -r requirements-windows.lock.txt
py -3.11 -m pip check
py -3.11 -m pip_audit --require-hashes -r requirements-windows.lock.txt
```

Then run the full test and release-build gates. A lock refresh is not complete until both platforms resolve, audit cleanly, and pass their tests.

## Container base image

`Dockerfile` keeps the readable `python:3.12-slim` tag and pins its multi-platform manifest digest. Python packages must come from hash-verified wheels, so an unsupported platform fails closed instead of compiling an unreviewed source distribution. The health check uses Python's standard library, leaving no mutable `apt` package layer. Dependabot proposes digest updates; review the upstream Python image change and rebuild before accepting one.
