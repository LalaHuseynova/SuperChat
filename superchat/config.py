import os
from datetime import date
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
DATA_DIR = ROOT / "SuperChat_Mock_Data"
LOG_DIR = Path(os.getenv("SUPERCHAT_LOG_DIR", str(ROOT / "runtime/sessions")))
REFERENCE_DATE = date.fromisoformat(os.getenv("SUPERCHAT_REFERENCE_DATE", "2026-11-02"))
DATA_MODE = os.getenv("SUPERCHAT_DATA_MODE", "mock")
REAL_DATA_DIR = Path(os.getenv("SUPERCHAT_REAL_DATA_DIR", str(ROOT / "preparation_dataset/SuperChat_Real_Data")))
SNAPSHOT_PUBLICATION = ROOT / "runtime/catalogue/active.json"
CATALOGUE_DB = Path(os.getenv('SUPERCHAT_CATALOGUE_DB', str(ROOT / 'runtime/catalogue/catalogue.sqlite3')))
