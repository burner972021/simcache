from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import numpy as np

from . import core


class SimCache:
    def __init__(self, root: str | Path = ".simcache", use_git: bool = True) -> None:
        self.root = Path(root)
        self.use_git = use_git
        self.runs_dir = self.root / "runs"
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_path = self.root / "manifest.json"

    def build_spec(
        self,
        params: Dict[str, Any],
        seed: int,
        code_version: Optional[str],
        env: Dict[str, Any],
    ) -> Dict[str, Any]:
        return {
            "code_version": code_version,
            "env": env,
            "params": params,
            "seed": seed,
        }

    def compute_run_id(
        self,
        params: Dict[str, Any],
        seed: int,
        code_version: Optional[str] = None,
        env: Optional[Dict[str, Any]] = None,
    ) -> str:
        if env is None:
            env = core.collect_env()
        spec = self.build_spec(params, seed, code_version, env)
        return core.hash_spec(spec)

    def run_exists(self, run_id: str) -> bool:
        return (self.runs_dir / run_id).exists()

    def save(
        self,
        run_id: str,
        arrays: Dict[str, np.ndarray],
        metadata: Dict[str, Any],
        arrays_format: str = "npz",
    ) -> Path:
        run_dir = self.runs_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        arrays_path = self._save_arrays(arrays_format, arrays, run_dir)
        metadata = dict(metadata)
        metadata.update(
            {
                "run_id": run_id,
                "arrays_format": arrays_format,
                "arrays_path": arrays_path.name,
            }
        )
        self._write_json(run_dir / "metadata.json", metadata)
        self._update_manifest(run_id, metadata)
        return run_dir

    def load(self, run_id: str) -> Dict[str, Any]:
        run_dir = self.runs_dir / run_id
        metadata = self._read_json(run_dir / "metadata.json")
        arrays_path = run_dir / metadata["arrays_path"]
        arrays = self._load_arrays(metadata["arrays_format"], arrays_path)
        return {"arrays": arrays, "metadata": metadata}

    def info(self, run_id: str) -> Dict[str, Any]:
        run_dir = self.runs_dir / run_id
        return self._read_json(run_dir / "metadata.json")

    def list_runs(self) -> List[Dict[str, Any]]:
        manifest = self._load_manifest()
        runs = []
        for run_id, entry in manifest["runs"].items():
            runs.append({"run_id": run_id, **entry})
        if runs:
            return sorted(runs, key=lambda item: item.get("timestamp", ""))
        fallback = []
        for run_dir in sorted(self.runs_dir.glob("*")):
            if run_dir.is_dir():
                try:
                    metadata = self._read_json(run_dir / "metadata.json")
                    fallback.append(
                        {
                            "run_id": run_dir.name,
                            "timestamp": metadata.get("timestamp"),
                            "tags": metadata.get("tags", []),
                        }
                    )
                except Exception:
                    fallback.append({"run_id": run_dir.name, "timestamp": None, "tags": []})
        return fallback

    def load_latest(self, tag: str) -> Optional[Dict[str, Any]]:
        candidates = []
        for run in self.list_runs():
            if tag in (run.get("tags") or []):
                candidates.append(run)
        if not candidates:
            return None
        candidates.sort(key=lambda item: item.get("timestamp") or "")
        return self.load(candidates[-1]["run_id"])

    def export(self, run_id: str, dest: str | Path) -> Path:
        info = self.info(run_id)
        arrays_path = self.runs_dir / run_id / info["arrays_path"]
        dest = Path(dest)
        if arrays_path.is_dir():
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(arrays_path, dest)
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(arrays_path, dest)
        return dest

    def _save_arrays(self, arrays_format: str, arrays: Dict[str, np.ndarray], run_dir: Path) -> Path:
        if arrays_format == "npz":
            arrays_path = run_dir / "arrays.npz"
            np.savez_compressed(arrays_path, **arrays)
            return arrays_path
        if arrays_format == "zarr":
            try:
                import zarr
            except Exception as exc:
                raise RuntimeError("zarr support requires installing the zarr package") from exc
            arrays_path = run_dir / "arrays.zarr"
            if arrays_path.exists():
                shutil.rmtree(arrays_path)
            root = zarr.open_group(str(arrays_path), mode="w")
            for key, value in arrays.items():
                root.array(name=key, data=value, overwrite=True)
            return arrays_path
        if arrays_format == "hdf5":
            try:
                import h5py
            except Exception as exc:
                raise RuntimeError("hdf5 support requires installing h5py") from exc
            arrays_path = run_dir / "arrays.h5"
            with h5py.File(arrays_path, "w") as handle:
                for key, value in arrays.items():
                    handle.create_dataset(name=key, data=value)
            return arrays_path
        raise ValueError(f"Unsupported arrays format: {arrays_format}")

    def _load_arrays(self, arrays_format: str, arrays_path: Path) -> Dict[str, np.ndarray]:
        if arrays_format == "npz":
            with np.load(arrays_path, allow_pickle=False) as data:
                return {key: data[key] for key in data.files}
        if arrays_format == "zarr":
            try:
                import zarr
            except Exception as exc:
                raise RuntimeError("zarr support requires installing the zarr package") from exc
            root = zarr.open_group(str(arrays_path), mode="r")
            return {key: root[key][:] for key in root.array_keys()}
        if arrays_format == "hdf5":
            try:
                import h5py
            except Exception as exc:
                raise RuntimeError("hdf5 support requires installing h5py") from exc
            arrays = {}
            with h5py.File(arrays_path, "r") as handle:
                for key in handle.keys():
                    arrays[key] = handle[key][:]
            return arrays
        raise ValueError(f"Unsupported arrays format: {arrays_format}")

    def _load_manifest(self) -> Dict[str, Any]:
        if not self.manifest_path.exists():
            return {"runs": {}}
        return self._read_json(self.manifest_path)

    def _update_manifest(self, run_id: str, metadata: Dict[str, Any]) -> None:
        manifest = self._load_manifest()
        tags = metadata.get("tags") or []
        manifest["runs"][run_id] = {
            "timestamp": metadata.get("timestamp"),
            "tags": tags,
        }
        self._write_json(self.manifest_path, manifest)

    @staticmethod
    def _write_json(path: Path, payload: Dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)

    @staticmethod
    def _read_json(path: Path) -> Dict[str, Any]:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)


def build_metadata(
    params: Dict[str, Any],
    seed: int,
    code_version: Optional[str],
    env: Dict[str, Any],
    tags: Optional[Iterable[str]] = None,
    plot_config: Optional[Dict[str, Any]] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    if isinstance(tags, str):
        tags = [tags]
    metadata: Dict[str, Any] = {
        "params": params,
        "seed": seed,
        "code_version": code_version,
        "env": env,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tags": sorted(set(tags or [])),
    }
    if plot_config is not None:
        metadata["plot_config"] = plot_config
    if extra:
        metadata.update(extra)
    return metadata
