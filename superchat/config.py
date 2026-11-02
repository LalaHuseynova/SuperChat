import os
from datetime import date
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
DATA_DIR = ROOT / "SuperChat_Mock_Data"
LOG_DIR = Path(os.getenv("SUPERCHAT_LOG_DIR", str(ROOT / "runtime/sessions")))
REFERENCE_DATE = date.fromisoformat(os.getenv("SUPERCHAT_REFERENCE_DATE", "2026-11-02"))
