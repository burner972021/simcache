from __future__ import annotations

import matplotlib.pyplot as plt

from simcache import load_latest


def main() -> None:
    result = load_latest(tag="paper-fig1")
    if result is None:
        raise SystemExit("No cached run tagged 'paper-fig1'. Run simcache first.")
    data = result["arrays"]
    plt.plot(data["t"], data["x"], label="signal")
    plt.xlabel("t (s)")
    plt.ylabel("x (arb)")
    plt.legend()
    plt.tight_layout()
    plt.show()


main()