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
import time

from instagram_feed_scraper import main as run_scraper
from instagram_feed_second_pass import main as run_second_pass
from analysis import main as run_analysis
from notify import main as notify
from lib import make_scrape_dir, TIME_BETWEEN_SCRAPES_MIN, TIME_BETWEEN_NOTIFICATIONS_MIN

def main():
    parser = argparse.ArgumentParser(description="Run full Instagram scrape pipeline.")
    parser.add_argument("--output-dir", required=True, help="Root directory, e.g. ~/tmp/instagram_notifier")
    args = parser.parse_args()

    output_dir = Path(args.output_dir).expanduser()
    session_file = output_dir / "ig_session.json"

    last_notification_time = None

    while True:
        scrape_dir = make_scrape_dir(output_dir)
        now = time.time()

        print("=== Step 1: Scraping feed ===")
        run_scraper(output_dir=output_dir, scrape_dir=scrape_dir)

        print("\n=== Step 2: Enriching posts ===")
        run_second_pass(scrape_dir=scrape_dir, session_file=session_file)

        print("\n=== Step 3: Analyzing posts ===")
        run_analysis(
            json_path=scrape_dir / "instagram_feed_second_pass.json",
            output_dir=str(scrape_dir)
        )

        if last_notification_time is None or (now - last_notification_time) >= TIME_BETWEEN_NOTIFICATIONS_MIN * 60:
            print("\n=== Step 4: Sending notifications ===")
            notify(root_dir=output_dir)
            last_notification_time = now

        print(f"\n=== Sleeping {TIME_BETWEEN_SCRAPES_MIN} minutes until next scrape ===")
        time.sleep(TIME_BETWEEN_SCRAPES_MIN * 60)

if __name__ == "__main__":
    main()