"""Single source of truth for repository paths. NO DATABASE ACCESS, NO SIDE EFFECTS.

Every production script in this release resolves its data and output locations through
this module, so that all stages agree on ONE repository root. Before this module existed,
each script computed its own locations from the directory it happened to sit in:

    FR = os.path.dirname(os.path.abspath(__file__))     # e.g. .../src/validation
    DATA = os.path.join(FR, "data")                     # e.g. .../src/validation/data

Because the published scripts live in different stage directories (`src/phenotype`,
`src/preprocessing`, `src/clinical_scores`, `src/validation`, `src/reporting`, `tests/...`),
each stage pointed at a DIFFERENT `data`/`tables`/`figures`/`logs` directory, so no stage
could read what the previous stage wrote. The layout is now:

    <repo root>/
        data/                  installed locally; restricted, never committed
        outputs/
            tables/            generated tables and workbooks
            figures/           generated figures
            logs/              generated run logs

`data/` deliberately sits at the repository root rather than under `outputs/`: it holds
source and derived patient-level data that the user must obtain under each database's own
access agreement. It is not an output of this repository.

Path resolution deliberately does NOT depend on the current working directory, so scripts
can be run from anywhere.

Usage
-----
    import repo
    repo.DATA, repo.TABLES, repo.FIGURES, repo.LOGS, repo.REPO_ROOT

    python src/repo.py          # print every resolved path and whether it exists

Layout note
-----------
`src/repo.py` is resolved at run time whether the repository is used in place or as a
deployed copy, because `python -m compileall`, `importlib` and every documented command
locate it the same way: by walking up from this file to the directory holding README.md.
"""
from __future__ import annotations

import os
from pathlib import Path

# Marker that identifies the repository root. README.md is used rather than a VCS marker
# so that the layout resolves identically in a clean clone, in an unpacked release archive
# (which ships no .git), and on Windows or POSIX.
ROOT_MARKERS = ("README.md", "PUBLIC_CODE_RELEASE_MANIFEST.md")


def find_repo_root(start: Path | None = None) -> Path:
    """Walk up from `start` (default: this file) to the repository root."""
    here = (start or Path(__file__)).resolve()
    for candidate in (here, *here.parents):
        if any((candidate / marker).is_file() for marker in ROOT_MARKERS):
            return candidate
    raise RuntimeError(
        f"could not locate the repository root from {here}: no "
        f"{' or '.join(ROOT_MARKERS)} found in any parent directory. This module must "
        f"live inside the code release.")


# Module-level convenience constants, for direct use by scripts.
REPO_ROOT: Path = find_repo_root()
SRC_DIR: Path = REPO_ROOT / "src"
CONFIG_DIR: Path = REPO_ROOT / "config"

# Restricted source and derived data. Installed by the user; never committed.
DATA: Path = REPO_ROOT / "data"
# Generated artefacts. Created on demand by the scripts that write them.
OUTPUTS: Path = REPO_ROOT / "outputs"
TABLES: Path = OUTPUTS / "tables"
FIGURES: Path = OUTPUTS / "figures"
LOGS: Path = OUTPUTS / "logs"

# Directories a running pipeline needs to exist. `data/` is NOT created here: an empty
# `data/` would only make a missing install look like a successful one.
WRITABLE_DIRS = (TABLES, FIGURES, LOGS)


def ensure_writable_dirs() -> None:
    """Create the output directories if they are absent. Safe to call repeatedly."""
    for d in WRITABLE_DIRS:
        d.mkdir(parents=True, exist_ok=True)


def add_src_to_path() -> Path:
    """Put `src/` AND `config/` on `sys.path` so the shared imports resolve.

    Scripts live at different depths (`src/<stage>/x.py` and `tests/<suite>/y.py`), so a
    single `sys.path` insertion at `src/` is the only form that works for all of them.

    `config/` is added because the frozen configuration lives at `config/final_analysis_config.py`
    while every script does a bare `import final_analysis_config`. The documented run
    sequence exported `PYTHONPATH=src:config`, which made that work; without it the import
    fails. Adding the directory here means the scripts no longer depend on an environment
    variable being set correctly by the caller.
    """
    import sys
    for d in (SRC_DIR, CONFIG_DIR):
        s = str(d)
        if s not in sys.path:
            sys.path.insert(0, s)
    return SRC_DIR


def as_str(*paths: Path) -> list[str]:
    """Path objects as strings, for the many `os.path.join` call sites."""
    return [str(p) for p in paths]


if __name__ == "__main__":  # pragma: no cover - manual layout check, no data needed
    print("=" * 78)
    print("REPOSITORY PATH RESOLUTION")
    print("=" * 78)
    print(f"  this file        : {Path(__file__).resolve()}")
    print(f"  REPO_ROOT        : {REPO_ROOT}")
    print(f"  SRC_DIR          : {SRC_DIR}")
    print(f"  DATA             : {DATA}          exists={DATA.is_dir()}")
    print(f"  OUTPUTS          : {OUTPUTS}          exists={OUTPUTS.is_dir()}")
    print(f"  TABLES           : {TABLES}          exists={TABLES.is_dir()}")
    print(f"  FIGURES          : {FIGURES}          exists={FIGURES.is_dir()}")
    print(f"  LOGS             : {LOGS}          exists={LOGS.is_dir()}")
    print("-" * 78)
    ok = all(p.is_absolute() for p in (REPO_ROOT, DATA, TABLES, FIGURES, LOGS))
    same_root = all(str(p).startswith(str(REPO_ROOT)) for p in
                    (DATA, TABLES, FIGURES, LOGS))
    print(f"  all paths absolute        : {ok}")
    print(f"  all paths under repo root : {same_root}")
    print(f"  root markers found        : "
          f"{[m for m in ROOT_MARKERS if (REPO_ROOT / m).is_file()]}")
    print("=" * 78)
    print("OK" if (ok and same_root) else "FAILED")
    raise SystemExit(0 if (ok and same_root) else 1)
