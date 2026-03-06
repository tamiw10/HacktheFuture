from pathlib import Path
import shutil

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
BASELINE_DIR = DATA_DIR / "baseline"

FILES_TO_RESET = [
    "manufacturer_profiles.json",
    "inventory.json",
    "shipments.json",
    "mitigation_options.json",
    "disruption_signals.json",
    "parts.json",
    "suppliers.json",
    "approval_policy.json",
    "disruption_history.json",
    "business_parameters.json",
]

def reset_demo_data() -> None:
    missing = [name for name in FILES_TO_RESET if not (BASELINE_DIR / name).exists()]
    if missing:
        raise FileNotFoundError(
            f"Missing baseline files in {BASELINE_DIR}: {', '.join(missing)}"
        )

    for name in FILES_TO_RESET:
        shutil.copy2(BASELINE_DIR / name, DATA_DIR / name)

    print("Demo data reset complete.")

if __name__ == "__main__":
    reset_demo_data()