# instagram_feed_second_pass.py
#
# Second-pass enrichment for Instagram scrape results.
# Re-visits posts where caption was truncated ("more")
# and re-extracts full expanded text directly from post URL.

import argparse
from pathlib import Path
from playwright.sync_api import sync_playwright
from lib import save_json, load_json


def needs_second_pass(post):
    texts = post.get("texts", [])
    return any(t.strip().lower() == "more" for t in texts)


def extract_post_text(page):
    og_desc = page.evaluate("""
        () => document.querySelector('meta[property="og:description"]')?.content ?? null
    """)
    return [og_desc] if og_desc else []


SKIP_LABELS = {"suggested for you", "ad"}

def is_suggested(post):
    return any(t.strip().lower() in SKIP_LABELS for t in post.get("texts", []))


def main(scrape_dir: Path, session_file: Path):
    input_path = scrape_dir / "instagram_feed.json"
    output_path = scrape_dir / "instagram_feed_second_pass.json"

    if not input_path.exists():
        raise FileNotFoundError(f"Expected file not found: {input_path}")

    if not session_file.exists():
        print(f"[WARN] Session file not found: {session_file}. Running unauthenticated session.")

    posts = load_json(input_path)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)

        context = browser.new_context(
            storage_state=str(session_file) if session_file.exists() else None
        )

        page = context.new_page()
        updated_count = 0
        enriched_posts = []

        for i, post in enumerate(posts):
            url = post.get("post_url")

            if is_suggested(post):
                print(f"[{i+1}/{len(posts)}] Skipping suggested post")
                continue

            if not url or not needs_second_pass(post):
                enriched_posts.append(post)
                print(f"[{i+1}/{len(posts)}] Post doesn't need a second pass")
                continue

            print(f"[{i+1}/{len(posts)}] Re-scraping: {url}")

            try:
                page.goto(url, wait_until="domcontentloaded")

                full_texts = extract_post_text(page)

                enriched_posts.append({**post, "texts": full_texts} if full_texts else post)
                updated_count += 1

            except Exception as e:
                print(f"Failed on {url}: {e}")
                enriched_posts.append(post)

        save_json(enriched_posts, output_path)
        print(f"\nDone. Updated {updated_count} posts.")
        print(f"Saved to: {output_path}")
        browser.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--scrape-dir", required=True, help="Directory containing instagram_feed.json")
    parser.add_argument("--session-file", required=True, help="Path to ig_session.json")
    args = parser.parse_args()
    main(scrape_dir=Path(args.scrape_dir), session_file=Path(args.session_file))