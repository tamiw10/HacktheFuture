from pathlib import Path
import shutil

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
BASELINE_DIR = DATA_DIR / "baseline"

FILES = [
    "manufacturer_profiles.json",
    "inventory.json",
    "shipments.json",
    "mitigation_options.json",
    "disruption_signals.json",
    "parts.json",
    "suppliers.json",
    "approval_policy.json",
    "disruption_history.json",
]

def init_baseline() -> None:
    BASELINE_DIR.mkdir(parents=True, exist_ok=True)

    missing = [name for name in FILES if not (DATA_DIR / name).exists()]
    if missing:
        raise FileNotFoundError(
            f"Missing source files in {DATA_DIR}: {', '.join(missing)}"
        )

    for name in FILES:
        shutil.copy2(DATA_DIR / name, BASELINE_DIR / name)

    print("Baseline created.")

if __name__ == "__main__":
    init_baseline()