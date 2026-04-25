import json
from pathlib import Path
from datetime import datetime


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