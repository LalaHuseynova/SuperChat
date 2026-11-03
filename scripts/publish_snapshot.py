"""Validate archived source tables and atomically activate one consistent snapshot.

Run: PYTHONPATH=. .venv/bin/python scripts/publish_snapshot.py
Existing active.json remains untouched if validation fails. Restart the app
after publishing; each process pins one immutable snapshot for consistent reads.
"""
import argparse
from pathlib import Path
from superchat.config import REAL_DATA_DIR, SNAPSHOT_PUBLICATION
from superchat.snapshots import SnapshotDataset


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=REAL_DATA_DIR)
    parser.add_argument("--output", type=Path, default=SNAPSHOT_PUBLICATION)
    args = parser.parse_args()
    dataset = SnapshotDataset(args.dataset)
    dataset.publish(args.output)
    print(f"Published snapshot {dataset.version}")
    print({name: len(rows) for name, rows in dataset.tables.items()})


if __name__ == "__main__":
    main()
