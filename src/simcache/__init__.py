from typing import Any, Dict, Optional

from .core import collect_env, get_git_commit, hash_spec
from .store import SimCache, build_metadata

_DEFAULT_STASH = SimCache()


def load(run_id: str, store: Optional[str] = None) -> Dict[str, Any]:
    stash = _DEFAULT_STASH if store is None else SimCache(root=store)
    return stash.load(run_id)


def load_latest(tag: str, store: Optional[str] = None) -> Optional[Dict[str, Any]]:
    stash = _DEFAULT_STASH if store is None else SimCache(root=store)
    return stash.load_latest(tag)


__all__ = [
    "SimCache",
    "build_metadata",
    "collect_env",
    "get_git_commit",
    "hash_spec",
    "load",
    "load_latest",
]
