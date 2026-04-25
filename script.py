# instagram_feed_scraper.py
#
# Install:
#   pip install playwright
#   playwright install
#
# Run first time:
#   python instagram_feed_scraper.py
#
# First run opens browser so you can log in manually.
# Press ENTER in terminal after login is complete.
#
# Later runs reuse saved session automatically.

import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

STATE_FILE = "ig_session.json"
OUTPUT_FILE = "instagram_feed.json"

MAX_SCROLLS = 5
WAIT_BETWEEN_SCROLLS = 3


def save_json(data, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_feed(page):
    page.goto("https://www.instagram.com/", wait_until="networkidle")
    time.sleep(3)


def collect_posts(page):
    # Pull visible article/post cards from DOM
    posts = page.evaluate("""
    () => {
        const results = [];
        const seen = new Set();

        const articles = document.querySelectorAll("article");

        articles.forEach((article, idx) => {
            let username = null;
            let caption = null;
            let postUrl = null;
            let imageUrl = null;
            let timestamp = null;

            // username / profile link
            const profileLink = article.querySelector('a[href^="/"][role="link"]');
            if (profileLink) {
                const href = profileLink.getAttribute("href");
                if (href && href.split("/").length > 1) {
                    username = href.replaceAll("/", "");
                }
            }

            // post link
            const postLink = article.querySelector('a[href*="/p/"], a[href*="/reel/"]');
            if (postLink) {
                postUrl = postLink.href;
            }

            // image
            const img = article.querySelector("img");
            if (img) {
                imageUrl = img.src || null;
                caption = img.alt || null;
            }

            // timestamp
            const timeEl = article.querySelector("time");
            if (timeEl) {
                timestamp = timeEl.getAttribute("datetime");
            }

            const key = postUrl || username + "_" + idx;
            if (!seen.has(key)) {
                seen.add(key);
                results.push({
                    username,
                    caption,
                    post_url: postUrl,
                    image_url: imageUrl,
                    timestamp
                });
            }
        });

        return results;
    }
    """)
    return posts


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)

        # Reuse saved session if available
        if Path(STATE_FILE).exists():
            context = browser.new_context(storage_state=STATE_FILE)
        else:
            context = browser.new_context()

        page = context.new_page()
        load_feed(page)

        # If no saved session, user logs in manually
        if not Path(STATE_FILE).exists():
            print("Please log into Instagram in the opened browser.")
            input("After login and feed loads, press ENTER here...")
            context.storage_state(path=STATE_FILE)
            print(f"Saved session to {STATE_FILE}")
            load_feed(page)

        all_posts = []

        for i in range(MAX_SCROLLS):
            print(f"Scanning screen {i+1}/{MAX_SCROLLS}...")

            posts = collect_posts(page)

            # merge by post_url
            existing = {p["post_url"]: p for p in all_posts if p["post_url"]}
            for post in posts:
                key = post["post_url"]
                if key and key not in existing:
                    all_posts.append(post)

            # scroll down
            page.mouse.wheel(0, 3000)
            time.sleep(WAIT_BETWEEN_SCROLLS)

        save_json(all_posts, OUTPUT_FILE)

        print(f"Saved {len(all_posts)} posts to {OUTPUT_FILE}")

        browser.close()


if __name__ == "__main__":
    main()