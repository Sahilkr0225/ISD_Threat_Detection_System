"""Memory-efficient dataset loading utilities for Parquet and CSV files."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional, Union

import pandas as pd

SUPPORTED_EXTENSIONS = {".parquet", ".csv"}


class DatasetLoadError(ValueError):
    """Raised when a dataset cannot be loaded or has an unsupported format."""


def load_dataset(
    filepath: Union[str, Path],
    columns: Optional[Iterable[str]] = None,
) -> pd.DataFrame:
    """Load a Parquet or CSV dataset with format and emptiness validation.

    Args:
        filepath: Path to the input `.parquet` or `.csv` file.
        columns: Optional subset of columns to load (reduces memory footprint).

    Raises:
        FileNotFoundError: If the file does not exist.
        DatasetLoadError: If the format is unsupported, file is unreadable, or dataset is empty.
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Dataset file not found: {path}")
    if not path.is_file():
        raise DatasetLoadError(f"Dataset path is not a file: {path}")

    ext = path.suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise DatasetLoadError(
            f"Unsupported file format '{ext}'. Supported formats: {sorted(SUPPORTED_EXTENSIONS)}"
        )

    cols = list(columns) if columns is not None else None
    try:
        if ext == ".parquet":
            df = pd.read_parquet(path, columns=cols)
        else:
            df = pd.read_csv(path, usecols=cols)
    except Exception as exc:
        raise DatasetLoadError(f"Failed to load dataset '{path}': {exc}") from exc

    if df.empty:
        raise DatasetLoadError(f"Loaded dataset is empty (0 rows): {path}")

    return df

