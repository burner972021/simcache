from __future__ import annotations

import numpy as np


def run(params, seed):
    rng = np.random.default_rng(seed)
    steps = int(params.get("steps", 200))
    dt = float(params.get("dt", 0.01))
    noise = float(params.get("noise", 0.1))

    t = np.arange(steps) * dt
    x = np.sin(2 * np.pi * t) + noise * rng.standard_normal(size=steps)
    arrays = {"t": t, "x": x}
    meta = {"units": {"t": "s", "x": "arb"}}
    return arrays, meta
