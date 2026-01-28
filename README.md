# simcache

Lightweight caching and result-reproducible tool for scientific graph plotting. Runs are content-addressed by
`code_version + params + seed + environment`, so time is saved in plot generation as results are only recomputed when inputs change.

## v0.0 Installation guide

Clone the repo

```bash
git clone https://github.com/burner972021/simcache
cd simcache
```

Install in editable mode:

```bash
python -m pip install -e .
```

Run simulation and cache results:

```bash
simcache run examples/sim.py --params examples/params.yaml --seed 3 --tag paper-fig1
```

List runs, inspect metadata, and export arrays:

```bash
simcache ls
simcache info <run_id>
simcache export <run_id> --to results/fig1_data.npz
```

Load from cache for plotting:

```python
from simcache import load_latest
import matplotlib.pyplot as plt

res = load_latest(tag="paper-fig1")
data = res["arrays"]
plt.plot(data["t"], data["x"])
plt.show()
```

## Simulation script id-based calling

Your simulation script must expose a `run(params, seed)` function that returns either:
- a dictionary of numpy arrays, or
- a `(arrays, extra_metadata)` tuple.

Example signature:

```python
def run(params, seed):
    # compute arrays
    return {"t": t, "x": x}, {"units": {"t": "s", "x": "m"}}
```

## Parameter iteration

Define a grid in YAML/JSON with `params` and optional `seeds`:

```yaml
params:
  steps: [100, 200]
  dt: [0.01, 0.02]
seeds: [1, 2]
tags: ["sweep"]
```

Run missing combinations only:

```bash
simcache sweep examples/params_grid.yaml examples/sim.py
```
