import subprocess
import sys

PYTHON = sys.executable

steps = [
    "backend/live_supply.py",
    "backend/build_lime_imbalance.py",
    "backend/prepare_rebalancing.py",
    "backend/optimize_rebalancing.py",
]

for step in steps:
    print(f"\n{'=' * 60}")
    print(f"RUNNING: {step}")
    print("=" * 60)

    result = subprocess.run(
        [PYTHON, step],
        check=True
    )

print("\nScooterOps pipeline completed successfully.")