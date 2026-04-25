# instagram_feed_second_pass.py
#
# Second-pass enrichment for Instagram scrape results.
# Re-visits posts where caption was truncated ("more")
# and re-extracts full expanded text directly from post URL.

import json
import argparse
from pathlib import Path
from playwright.sync_api import sync_playwright


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(data, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def needs_second_pass(post):
    texts = post.get("texts", [])
    return any(t.strip().lower() == "more" for t in texts)


def extract_post_text(page):
    # Click all "more" expanders before reading text
    try:
        more_buttons = page.locator("article span", has_text="more").all()
        for btn in more_buttons:
            if btn.inner_text().strip().lower() == "more":
                btn.click()
                page.wait_for_timeout(500)
    except Exception as e:
        print(f"  [warn] Could not click 'more': {e}")

    return page.evaluate("""
    () => {
        const results = [];
        const seenText = new Set();

        const article = document.querySelector("article");
        if (!article) return results;

        const header = article.querySelector("header");

        article.querySelectorAll("span, div").forEach(el => {
            if (header && header.contains(el)) return;
            if (el.children.length !== 0) return;

            const text = el.innerText?.trim();
            if (text && text.length > 2 && !seenText.has(text)) {
                seenText.add(text);
                results.push(text);
            }
        });

        if (results.length === 0) {
            const imgs = article.querySelectorAll("img");
            for (const img of imgs) {
                const alt = img.alt?.trim();
                if (alt && alt.length > 10) {
                    results.push(alt);
                    break;
                }
            }
        }

        return results;
    }
    """)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scrape-dir", required=True, help="Directory containing instagram_feed.json")
    parser.add_argument("--session-file", required=True, help="Path to ig_session.json")
    args = parser.parse_args()

    scrape_dir = Path(args.scrape_dir)
    session_file = Path(args.session_file)

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

            if not url or not needs_second_pass(post):
                enriched_posts.append(post)
                continue

            print(f"[{i+1}/{len(posts)}] Re-scraping: {url}")

            try:
                page.goto(url, wait_until="domcontentloaded")
                page.wait_for_timeout(5000)

                full_texts = extract_post_text(page)

                enriched_posts.append({**post, "texts": full_texts} if full_texts else post)
                updated_count += 1

            except Exception as e:
                print(f"Failed on {url}: {e}")
                enriched_posts.append(post)
            break

        save_json(enriched_posts, output_path)

        print(f"\nDone. Updated {updated_count} posts.")
        print(f"Saved to: {output_path}")

        browser.close()


if __name__ == "__main__":
    main()