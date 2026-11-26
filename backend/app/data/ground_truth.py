"""Ground-truth label extraction from official CERT r4.2 answers.tar.bz2.

Labels are stored separately from model input features and used strictly for
offline evaluation (never passed into unsupervised Isolation Forest training).
"""

from __future__ import annotations

import csv
import io
from pathlib import Path
import tarfile
from typing import Dict, List, Tuple, Union

import pandas as pd


def extract_r42_ground_truth_days(
    answers_archive_path: Union[str, Path],
) -> Tuple[pd.DataFrame, dict]:
    """Extract malicious (employee_id, activity_date) pairs from answers.tar.bz2.

    Only events whose actor column (`col[3]`) matches the designated insider
    `user` in `insiders.csv` are counted, avoiding false attribution of
    benign recipients/correspondents.
    """
    archive_path = Path(answers_archive_path)
    if not archive_path.exists():
        raise FileNotFoundError(f"CERT answers archive not found: {archive_path}")

    records: List[dict] = []
    missing_member_files: List[str] = []

    with tarfile.open(archive_path, "r:bz2") as tf:
        members_by_name = {m.name: m for m in tf.getmembers() if m.isfile()}
        insiders_member = members_by_name.get("answers/insiders.csv")
        if insiders_member is None:
            raise ValueError("Archive does not contain 'answers/insiders.csv'.")

        ins_df = pd.read_csv(tf.extractfile(insiders_member))
        r42_insiders = ins_df[ins_df["dataset"].astype(str).str.strip() == "4.2"].copy()

        for _, row in r42_insiders.iterrows():
            scenario = int(row["scenario"])
            user_id = str(row["user"]).strip()
            details_file = str(row["details"]).strip()
            member_path = f"answers/r4.2-{scenario}/{details_file}"

            member = members_by_name.get(member_path)
            if member is None:
                missing_member_files.append(member_path)
                continue

            raw_bytes = tf.extractfile(member).read().decode("utf-8", errors="replace")
            reader = csv.reader(io.StringIO(raw_bytes))
            for cols in reader:
                if len(cols) < 4:
                    continue
                event_ts = cols[2].strip()
                actor = cols[3].strip()
                if actor != user_id:
                    continue
                parsed_dt = pd.to_datetime(event_ts, format="%m/%d/%Y %H:%M:%S", errors="coerce")
                if pd.isna(parsed_dt):
                    parsed_dt = pd.to_datetime(event_ts, errors="coerce")
                if pd.isna(parsed_dt):
                    continue
                records.append(
                    {
                        "employee_id": user_id,
                        "activity_date": parsed_dt.normalize(),
                        "scenario": scenario,
                    }
                )

    events_df = pd.DataFrame(records)
    if events_df.empty:
        raise ValueError("No r4.2 malicious events extracted from answers.tar.bz2.")

    grouped = (
        events_df.groupby(["employee_id", "activity_date"], as_index=False)
        .agg(
            scenario=("scenario", "min"),
            malicious_event_count=("scenario", "size"),
        )
        .sort_values(["employee_id", "activity_date"])
        .reset_index(drop=True)
    )
    grouped["is_malicious_day"] = 1

    meta = {
        "total_r42_insiders": int(len(r42_insiders)),
        "total_malicious_actor_events": int(len(events_df)),
        "total_malicious_employee_days": int(len(grouped)),
        "scenarios": {str(k): int(v) for k, v in grouped["scenario"].value_counts().sort_index().items()},
        "missing_member_files": missing_member_files,
    }
    return grouped, meta

