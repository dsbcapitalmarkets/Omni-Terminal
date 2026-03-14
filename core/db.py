import json
import os
from pathlib import Path
from datetime import datetime

# Root of repo — works both locally and inside GitHub Actions
DATA_DIR = Path(__file__).resolve().parent.parent / "data"

def _path(filename: str) -> Path:
    DATA_DIR.mkdir(exist_ok=True)
    return DATA_DIR / filename

def save(filename: str, payload: dict | list) -> None:
    """Write any dict or list to data/<filename> as JSON."""
    with open(_path(filename), "w") as f:
        json.dump(payload, f, indent=2, default=str)

def load(filename: str, default=None):
    """Read data/<filename>. Returns default if file missing or corrupt."""
    p = _path(filename)
    if not p.exists():
        return default
    try:
        with open(p) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default

def last_updated(filename: str) -> str | None:
    """Return ISO timestamp of when file was last written, or None."""
    p = _path(filename)
    if not p.exists():
        return None
    ts = os.path.getmtime(p)
    return datetime.fromtimestamp(ts).strftime("%d %b %Y, %I:%M %p")