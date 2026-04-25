# run.py
#
# Runs the full Instagram scrape pipeline:
#   1. Scrape feed (instagram_feed_scraper.py)
#   2. Enrich posts via second pass (instagram_feed_second_pass.py)
#
# Usage:
#   python run.py --output-dir ~/tmp/instagram_notifier

import argparse
from pathlib import Path
from datetime import datetime

from instagram_feed_scraper import main as run_scraper
from instagram_feed_second_pass import main as run_second_pass
from lib import save_json, load_json, make_scrape_dir

def main():
    parser = argparse.ArgumentParser(description="Run full Instagram scrape pipeline.")
    parser.add_argument("--output-dir", required=True, help="Root directory, e.g. ~/tmp/instagram_notifier")
    args = parser.parse_args()

    output_dir = Path(args.output_dir).expanduser()
    session_file = output_dir / "ig_session.json"
    scrape_dir = make_scrape_dir(output_dir)

    print("=== Step 1: Scraping feed ===")
    run_scraper(output_dir=output_dir, scrape_dir=scrape_dir)

    print("\n=== Step 2: Enriching posts ===")
    run_second_pass(scrape_dir=scrape_dir, session_file=session_file)


if __name__ == "__main__":
    main()