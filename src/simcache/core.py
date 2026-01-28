from __future__ import annotations
import hashlib, json, subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Tuple

def _canonical_json(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

def git_fingerprint(repo: Path | None = None) -> Tuple[str | None, bool]:
    """Return (commit, dirty). If not a git repo, commit=None."""
    cwd = repo or Path.cwd()
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=cwd).decode().strip()
        dirty = subprocess.call(["git", "diff", "--quiet"], cwd=cwd) != 0
        # also consider staged changes
        dirty = dirty or (subprocess.call(["git", "diff", "--cached", "--quiet"], cwd=cwd) != 0)
        return commit, dirty
    except Exception:
        return None, False

def make_run_id(spec: Dict[str, Any]) -> str:
    h = hashlib.sha256(_canonical_json(spec)).hexdigest()
    return h[:12]

@dataclass(frozen=True)
class RunSpec:
    name: str
    params: Dict[str, Any]
    seed: int
    git_commit: str | None
    git_dirty: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "params": self.params,
            "seed": self.seed,
            "git": {"commit": self.git_commit, "dirty": self.git_dirty},
        }

# def now_iso() -> str:
#     return datetime.now(timezone.utc).isoformat()
# from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict


def _normalize(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {str(key): _normalize(value) for key, value in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_normalize(value) for value in obj]
    if isinstance(obj, set):
        return sorted(_normalize(value) for value in obj)
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, bytes):
        return obj.decode("utf-8", errors="replace")
    try:
        import numpy as np

        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, np.generic):
            return obj.item()
    except Exception:
        pass
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    return str(obj)


def hash_spec(spec: Dict[str, Any]) -> str:
    normalized = _normalize(spec)
    payload = json.dumps(normalized, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def get_git_commit(path: str | Path) -> str | None:
    repo_dir = Path(path).resolve()
    if repo_dir.is_file():
        repo_dir = repo_dir.parent
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_dir), "rev-parse", "--short", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip() or None
    except Exception:
        return None


def collect_env() -> Dict[str, Any]:
    env: Dict[str, Any] = {
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
    }
    try:
        import numpy as np

        env["numpy_version"] = np.__version__
    except Exception:
        env["numpy_version"] = None
    try:
        import matplotlib

        env["matplotlib_version"] = matplotlib.__version__
    except Exception:
        env["matplotlib_version"] = None
    return env
