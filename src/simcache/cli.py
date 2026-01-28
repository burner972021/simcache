from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from . import core
from .iterations import iter_sweep, load_params_file
from .store import SimCache, build_metadata


def _load_mapping(path: Optional[str]) -> Dict[str, Any]:
    if not path:
        return {}
    return load_params_file(path)


def _load_run_fn(script_path: str, fn_name: str) -> Any:
    import importlib.util

    module_path = Path(script_path).resolve()
    spec = importlib.util.spec_from_file_location(module_path.stem, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to import {script_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not hasattr(module, fn_name):
        raise AttributeError(f"{script_path} does not define {fn_name}()")
    return getattr(module, fn_name)


def _normalize_result(result: Any) -> tuple[Dict[str, Any], Dict[str, Any]]:
    if isinstance(result, tuple) and len(result) == 2:
        arrays, extra = result
    else:
        arrays, extra = result, {}
    if not isinstance(arrays, dict):
        raise TypeError("Simulation result must be a dict of numpy arrays")
    if not isinstance(extra, dict):
        raise TypeError("Simulation metadata must be a dictionary")
    return arrays, extra


def cmd_run(args: argparse.Namespace) -> int:
    params = _load_mapping(args.params)
    plot_config = _load_mapping(args.plot_config) if args.plot_config else None
    env = core.collect_env()
    code_version = core.get_git_commit(args.script) if not args.no_git else None
    stash = SimCache(root=args.store, use_git=not args.no_git)
    run_id = stash.compute_run_id(params, args.seed, code_version=code_version, env=env)

    if stash.run_exists(run_id) and not args.force:
        print(run_id)
        return 0

    run_fn = _load_run_fn(args.script, args.fn)
    arrays, extra = _normalize_result(run_fn(params, args.seed))
    metadata = build_metadata(
        params=params,
        seed=args.seed,
        code_version=code_version,
        env=env,
        tags=args.tag,
        plot_config=plot_config,
        extra=extra,
    )
    stash.save(run_id, arrays, metadata, arrays_format=args.format)
    print(run_id)
    return 0


def cmd_ls(args: argparse.Namespace) -> int:
    stash = SimCache(root=args.store)
    for run in stash.list_runs():
        tags = ",".join(run.get("tags") or [])
        timestamp = run.get("timestamp") or "-"
        line = f"{run['run_id']} {timestamp}"
        if tags:
            line = f"{line} [{tags}]"
        print(line)
    return 0


def cmd_info(args: argparse.Namespace) -> int:
    stash = SimCache(root=args.store)
    info = stash.info(args.run_id)
    print(json.dumps(info, indent=2, sort_keys=True))
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    stash = SimCache(root=args.store)
    stash.export(args.run_id, args.to)
    print(args.to)
    return 0


def cmd_sweep(args: argparse.Namespace) -> int:
    grid = _load_mapping(args.grid)
    stash = SimCache(root=args.store, use_git=not args.no_git)
    env = core.collect_env()
    code_version = core.get_git_commit(args.script) if not args.no_git else None
    run_fn = _load_run_fn(args.script, args.fn)
    tags = grid.get("tags", [])
    if isinstance(tags, str):
        tags = [tags]
    plot_config = grid.get("plot_config")
    arrays_format = grid.get("format", args.format)

    executed = 0
    skipped = 0
    for params, seed in iter_sweep(grid):
        run_id = stash.compute_run_id(params, seed, code_version=code_version, env=env)
        if stash.run_exists(run_id):
            skipped += 1
            continue
        arrays, extra = _normalize_result(run_fn(params, seed))
        metadata = build_metadata(
            params=params,
            seed=seed,
            code_version=code_version,
            env=env,
            tags=tags,
            plot_config=plot_config,
            extra=extra,
        )
        stash.save(run_id, arrays, metadata, arrays_format=arrays_format)
        executed += 1

    print(f"ran={executed} skipped={skipped}")
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="simcache")
    parser.add_argument("--store", default=".simcache", help="Path to the simcache store")
    parser.add_argument("--no-git", action="store_true", help="Ignore git commit in run ids")

    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run a simulation or load from cache")
    run_parser.add_argument("script", help="Path to a simulation script")
    run_parser.add_argument("--params", help="Path to params YAML/JSON")
    run_parser.add_argument("--seed", type=int, default=0)
    run_parser.add_argument("--fn", default="run", help="Function name to execute")
    run_parser.add_argument("--tag", action="append", default=[], help="Tag to apply")
    run_parser.add_argument("--format", default="npz", help="npz|zarr|hdf5")
    run_parser.add_argument("--plot-config", help="Path to plot config YAML/JSON")
    run_parser.add_argument("--force", action="store_true", help="Recompute and overwrite")
    run_parser.set_defaults(func=cmd_run)

    ls_parser = subparsers.add_parser("ls", help="List cached runs")
    ls_parser.set_defaults(func=cmd_ls)

    info_parser = subparsers.add_parser("info", help="Show run metadata")
    info_parser.add_argument("run_id")
    info_parser.set_defaults(func=cmd_info)

    export_parser = subparsers.add_parser("export", help="Export cached arrays")
    export_parser.add_argument("run_id")
    export_parser.add_argument("--to", required=True)
    export_parser.set_defaults(func=cmd_export)

    sweep_parser = subparsers.add_parser("sweep", help="Run parameter sweep")
    sweep_parser.add_argument("grid", help="Path to sweep YAML/JSON")
    sweep_parser.add_argument("script", help="Path to a simulation script")
    sweep_parser.add_argument("--fn", default="run", help="Function name to execute")
    sweep_parser.add_argument("--format", default="npz", help="npz|zarr|hdf5")
    sweep_parser.set_defaults(func=cmd_sweep)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
