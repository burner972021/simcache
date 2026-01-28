from __future__ import annotations

import json
from itertools import product
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


def load_params_file(path: str | Path) -> Dict[str, Any]:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix in {".json"}:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle) or {}
    if suffix in {".yml", ".yaml"}:
        try:
            import yaml
        except Exception as exc:
            raise RuntimeError("YAML support requires installing PyYAML") from exc
        with path.open("r", encoding="utf-8") as handle:
            return yaml.safe_load(handle) or {}
    raise ValueError(f"Unsupported params file type: {path}")


def expand_grid(params_grid: Dict[str, Iterable[Any]]) -> List[Dict[str, Any]]:
    keys = list(params_grid.keys())
    values = [list(params_grid[key]) for key in keys]
    combinations = []
    for combo in product(*values):
        combinations.append(dict(zip(keys, combo)))
    return combinations


def iter_sweep(grid: Dict[str, Any]) -> Iterable[Tuple[Dict[str, Any], int]]:
    params_grid = grid.get("params", {})
    combinations = expand_grid(params_grid) if params_grid else [{}]
    if "seeds" in grid:
        seeds = list(grid["seeds"])
    elif "seed" in grid:
        seeds = [grid["seed"]]
    else:
        seeds = [0]
    for params in combinations:
        for seed in seeds:
            yield params, seed
