import json
from pathlib import Path
from datetime import datetime
from pydantic import BaseModel
from dataclasses import dataclass
from enum import Enum
from typing import Optional
from datetime import date

MAX_SCROLLS = 10
WAIT_BETWEEN_SCROLLS_MS = 1000

# AI settings
MODEL="claude-haiku-4-5"
MAX_RESPONSE_TOKENS=4096

TIME_BETWEEN_SCRAPES_MIN = 1 # 144 = 10x per day
TIME_BETWEEN_NOTIFICATIONS_MIN = 1 # 1440 = 1 day

def save_json(data, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def make_scrape_dir(output_dir: Path) -> Path:
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    scrape_dir = output_dir / "scrapes" / timestamp
    scrape_dir.mkdir(parents=True, exist_ok=True)
    return scrape_dir

"""Claude structured response"""
class UpdateKind(Enum):
    MINOR = "minor"
    MAJOR = "major"

class Update(BaseModel):
    kind: UpdateKind
    date: date
    username: str
    post_url: str
    text: str

class Response(BaseModel):
    updates: Optional[list[Update]] = None
    error: Optional[str] = None