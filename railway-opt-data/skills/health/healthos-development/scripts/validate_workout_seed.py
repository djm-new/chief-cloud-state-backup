#!/usr/bin/env python3
"""Validate the HealthOS workout seed pair and summarize the workout structure.

Usage:
  python3 scripts/validate_workout_seed.py \
    /opt/data/projects/healthos/docs/INITIAL_PROGRAM_SEED.json \
    /opt/data/projects/healthos/INITIAL_PROGRAM_SEED.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text())
    except Exception as exc:  # pragma: no cover - deterministic CLI
        raise SystemExit(f"{path}: invalid JSON ({exc})") from exc


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__.strip())
        return 2

    left = Path(sys.argv[1])
    right = Path(sys.argv[2])

    left_data = load_json(left)
    right_data = load_json(right)

    if left_data != right_data:
        raise SystemExit("Seed mismatch: the two JSON files are not identical")

    if not isinstance(left_data.get("workouts"), list) or not left_data["workouts"]:
        raise SystemExit("Invalid seed: workouts must be a non-empty list")

    print(f"OK: {left.name} and {right.name} are identical and valid JSON")
    print(f"Program: {left_data.get('programName', 'N/A')}")
    print(f"Workouts: {len(left_data['workouts'])}")

    for index, workout in enumerate(left_data["workouts"], start=1):
        exercises = workout.get("exercises", [])
        print(f"  Day {index}: {workout.get('name', 'N/A')} ({len(exercises)} exercises)")
        for ex in exercises:
            shape = (
                "repRange" if "repRange" in ex else
                "reps" if "reps" in ex else
                "repsPerSide" if "repsPerSide" in ex else
                "distance" if "distance" in ex else
                "unknown"
            )
            print(f"    - {ex.get('name', 'N/A')} [{shape}]")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
