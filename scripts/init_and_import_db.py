"""CLI script to initialize SQLite DB, save validation score reference, and import test data."""

from __future__ import annotations

import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.core.config import METRICS_DIR
from backend.app.database.importer import (
    ensure_validation_score_reference,
    import_test_predictions_to_db,
)


def main() -> None:
    ref_path = ensure_validation_score_reference()
    summary = import_test_predictions_to_db(val_ref_path=ref_path)
    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    (METRICS_DIR / "db_import_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

