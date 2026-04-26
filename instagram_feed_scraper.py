# instagram_feed_scraper.py
#
# Install:
#   pip install playwright
#   playwright install
#
# Usage:
#   python instagram_feed_scraper.py --output-dir ./my_output
#
# First run opens browser so you can log in manually.
# Press ENTER in terminal after login is complete.
#
# Later runs reuse saved session automatically.

import json
import time
import argparse
from pathlib import Path
from playwright.sync_api import sync_playwright
import random
from lib import save_json, load_json, make_scrape_dir, MAX_SCROLLS, WAIT_BETWEEN_SCROLLS_MS

STATE_FILE = "ig_session.json"

def perturb_ms(ms: int, max_jitter: int = 500) -> int:
    return ms + random.randint(-max_jitter, max_jitter)

def human_sleep_ms(base_ms: int, jitter_ms: int = 500):
    time.sleep(perturb_ms(base_ms, jitter_ms) / 1000.0)

def save_json(data, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def load_feed(page):
    page.goto("https://www.instagram.com/", wait_until="domcontentloaded")
    human_sleep_ms(WAIT_BETWEEN_SCROLLS_MS)
def collect_posts(page):
    posts = page.evaluate("""
    () => {
        const results = [];
        const seen = new Set();

        const articles = document.querySelectorAll("article");

        articles.forEach((article, idx) => {
            let username = null;
            let postUrl = null;
            let timestamp = null;

            // --- Username ---
            const allLinks = article.querySelectorAll('a[href^="/"]');
            for (const a of allLinks) {
                const href = a.getAttribute("href") || "";
                const parts = href.split("/").filter(Boolean);
                if (parts.length === 1 && !href.includes("/p/") && !href.includes("/reel/")) {
                    username = parts[0];
                    break;
                }
            }

            // --- Post URL ---
            const postLink = article.querySelector('a[href*="/p/"], a[href*="/reel/"]');
            if (postLink) {
                postUrl = postLink.href;
            }

            // --- Text content ---
            const header = article.querySelector("header");
            const texts = [];
            const seenText = new Set();

            article.querySelectorAll("span, div").forEach(el => {
                if (header && header.contains(el)) return;  // skip header
                if (el.children.length !== 0) return;        // leaf nodes only
                const text = el.innerText?.trim();
                if (text && text.length >= 2 && !seenText.has(text)) {
                    seenText.add(text);
                    texts.push(text);
                }
            });

            // --- Image alt fallback (e.g. for captionless photo posts) ---
            if (texts.length === 0) {
                const imgs = article.querySelectorAll("img");
                for (const img of imgs) {
                    const alt = img.alt?.trim();
                    if (alt && !alt.includes("profile picture") && alt.length > 10) {
                        texts.push(alt);
                        break;
                    }
                }
            }

            // --- Timestamp ---
            const timeEl = article.querySelector("time");
            if (timeEl) {
                timestamp = timeEl.getAttribute("datetime");
            }

            const key = postUrl || (username + "_" + idx);
            if (!seen.has(key)) {
                seen.add(key);
                results.push({ username, texts, post_url: postUrl, timestamp });
            }
        });

        return results;
    }
    """)
    return posts
def main(output_dir: Path, scrape_dir: Path):
    scrape_path = scrape_dir / "instagram_feed.json"
    output_dir.mkdir(parents=True, exist_ok=True)

    state_file = output_dir / "ig_session.json"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)

        if state_file.exists():
            context = browser.new_context(storage_state=str(state_file))
        else:
            context = browser.new_context()

        page = context.new_page()
        load_feed(page)

        if not state_file.exists():
            print("Please log into Instagram in the opened browser.")
            input("After login and feed loads, press ENTER here...")
            context.storage_state(path=str(state_file))
            print(f"Saved session to {state_file}")
            load_feed(page)

        all_posts = []

        for i in range(MAX_SCROLLS):
            print(f"Scanning screen {i+1}/{MAX_SCROLLS}...")

            posts = collect_posts(page)

            existing = {p["post_url"]: p for p in all_posts if p["post_url"]}
            for post in posts:
                key = post["post_url"]
                if key and key not in existing:
                    all_posts.append(post)

            page.mouse.wheel(0, perturb_ms(3000))
            human_sleep_ms(WAIT_BETWEEN_SCROLLS_MS)

        save_json(all_posts, scrape_path)
        print(f"Saved {len(all_posts)} posts to {scrape_path}")
        browser.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape your Instagram feed.")
    parser.add_argument("--output-dir", required=True, help="Root directory, e.g. ~/tmp/instagram_notifier")
    args = parser.parse_args()
    output_dir = Path(args.output_dir).expanduser()
    scrape_dir = make_scrape_dir(output_dir)
    main(output_dir=output_dir, scrape_dir=scrape_dir)