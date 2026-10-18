"""Shared configuration loading for the TCI Research Atlas pipeline."""
from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import yaml

DEFAULT_CONFIG = Path(__file__).resolve().parent.parent / "config.example.yaml"


def deep_merge(base: dict, override: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    """Load config.yaml (if given) merged over config.example.yaml defaults."""
    defaults = yaml.safe_load(DEFAULT_CONFIG.read_text(encoding="utf-8"))
    if path and Path(path).exists():
        user = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        cfg = deep_merge(defaults, user)
    else:
        cfg = defaults
    # resolve relative dirs against config location
    root = Path(path).resolve().parent if path else DEFAULT_CONFIG.parent
    for key in ("work_dir", "output_dir"):
        p = Path(cfg["pipeline"][key])
        cfg["pipeline"][key] = str(p if p.is_absolute() else root / p)
    inp = Path(cfg["input"]["path"])
    cfg["input"]["path"] = str(inp if inp.is_absolute() else root / inp)
    return cfg


def require(cfg: dict, *keys: str) -> Any:
    cur: Any = cfg
    for k in keys:
        if k not in cur:
            raise KeyError(f"missing config key: {'.'.join(keys)}")
        cur = cur[k]
    return cur
