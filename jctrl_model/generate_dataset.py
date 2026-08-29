"""Generate reproducible synthetic training data for the JCTRL ML prototype."""
from pathlib import Path
import argparse
import csv
import random

DIRECTIONS = ("N", "S", "E", "W")
FEATURES = [f"{d}_{m}" for d in DIRECTIONS for m in ("vehicle_count", "queue_length", "average_wait")] + ["current_phase_NS"]
TARGETS = ["target_phase", "target_green_duration"]


def teacher_label(state, current_phase):
    """Synthetic teacher: choose the phase with higher traffic pressure.

    Pressure intentionally combines volume, queue and waiting time. This is
    only a label generator; the trained model is what is used at runtime.
    """
    scores = {}
    for phase, sides in (("NS", ("N", "S")), ("EW", ("E", "W"))):
        scores[phase] = sum(
            state[d]["vehicle_count"]
            + 2.5 * state[d]["queue_length"]
            + 1.5 * state[d]["average_wait"]
            for d in sides
        )
    # Add a tiny deterministic tie-break preference for switching when demand
    # is nearly equal, so the dataset does not become artificially one-sided.
    if abs(scores["NS"] - scores["EW"]) < 2.0:
        phase = "EW" if current_phase == "NS" else "NS"
    else:
        phase = max(scores, key=scores.get)

    demand = scores[phase]
    # Map pressure into the controller's 10..60 second safe range.
    duration = int(round(10 + min(demand, 100.0) / 100.0 * 50))
    duration = max(10, min(60, duration))
    return phase, duration


def generate(n, seed=42, out=None):
    rng = random.Random(seed)
    rows = []
    for _ in range(n):
        # Broad, intentionally varied demand. Queue and wait correlate with
        # vehicle count but retain noise to prevent trivial memorization.
        state = {}
        for d in DIRECTIONS:
            count = rng.randint(0, 30)
            queue = min(count, max(0, int(round(count * rng.uniform(0.15, 0.85) + rng.gauss(0, 2)))))
            wait = round(max(0.0, queue * rng.uniform(0.8, 2.8) + rng.uniform(0, 8)), 2)
            state[d] = {"vehicle_count": count, "queue_length": queue, "average_wait": wait}
        current_phase = rng.choice(("NS", "EW"))
        phase, duration = teacher_label(state, current_phase)
        row = []
        for d in DIRECTIONS:
            row.extend([state[d]["vehicle_count"], state[d]["queue_length"], state[d]["average_wait"]])
        row.append(1 if current_phase == "NS" else 0)
        row.extend([phase, duration])
        rows.append(row)

    out = Path(out or Path(__file__).parent / "data" / "training_data.csv")
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(FEATURES + TARGETS)
        writer.writerows(rows)
    print(f"Generated {n} samples -> {out}")
    return out


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--samples", type=int, default=10000)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--out", default=None)
    a = p.parse_args()
    generate(a.samples, a.seed, a.out)
