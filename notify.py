#!/usr/bin/env python3
"""
Recursively searches a directory for scrape folders containing major_updates.json
or minor_updates.json, combines their contents, and sends an email notification.

Crash-resilience strategy:
  - .visited  is touched immediately before reading a directory, so a crash
              mid-read won't cause double-processing on re-run.
  - .processed is touched only after the email is sent successfully, confirming
              the full pipeline succeeded for that directory.
  - On skip check, only .processed is consulted — a directory that has .visited
    but not .processed was interrupted and will be retried.

Credentials are loaded from a .env file in the working directory:
  NOTIFY_EMAIL        Gmail address to send from (and to)
  NOTIFY_APP_PASSWORD Gmail App Password (not your regular password)
                      Generate at: https://myaccount.google.com/apppasswords
"""

import json
import os
import smtplib
import ssl
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv

from lib import Update, MODEL


SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465


def load_json_file(path: Path) -> list:
    """Load a JSON file, returning an empty list if the file is empty."""
    if path.stat().st_size == 0:
        print(f"Skipping empty file: {path}", file=sys.stderr)
        return []
    with path.open() as f:
        data = json.load(f)
    return data if isinstance(data, list) else [data]


def parse_updates(raw: list) -> list[Update]:
    """Parse a list of raw dicts into Update objects, skipping malformed entries."""
    updates = []
    for item in raw:
        try:
            updates.append(Update(**item))
        except Exception as e:
            print(f"Warning: skipping malformed update {item}: {e}", file=sys.stderr)
    return updates


def format_update_plain(u: Update) -> str:
    return f"• {u.date}  @{u.username}  {u.post_url}\n  {u.text}"


def format_update_html(u: Update) -> str:
    return (
        f'''<li style="margin-bottom:12px">'''
        f'''<span style="color:#888;font-size:0.9em">{u.date}</span> '''
        f'''<strong>@{u.username}</strong> <a href="{u.post_url}" style="color:#888;font-size:0.9em;text-decoration:none">see post →</a><br>'''
        f'''{u.text}'''
        f'''</li>'''
    )


def summarize_updates(major: list[Update], minor: list[Update]) -> str:
    """Ask Claude for a short headline summary of all updates."""
    client = Anthropic()

    all_updates = [u.model_dump(mode="json") for u in major + minor]

    system_prompt = (
            "You are a concise assistant summarizing Instagram activity. "
            "Given a list of updates (major and minor), write a short (15-30 words) "
            "plain-text headline summary suitable for the top of an email notification. "
            "Try to keep it short enough to fit inside the description of a single phone notification. "
            "Focus on the most notable activity. Do not use markdown or bullet points."
        )

    response = client.messages.create(
        model=MODEL,
        max_tokens=512,
        system=system_prompt,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "document",
                    "source": {
                        "type": "text",
                        "media_type": "text/plain",
                        "data": json.dumps(all_updates, indent=2, default=str),
                    },
                    "title": "Instagram Updates",
                },
                {
                    "type": "text",
                    "text": "Summarize these updates.",
                }
            ]
        }],
    )

    return response.content[0].text.strip()


def send_email(email: str, app_password: str, major_updates: list, minor_updates: list) -> None:
    major = sorted(parse_updates(major_updates), key=lambda u: u.date)
    minor = sorted(parse_updates(minor_updates), key=lambda u: u.date)
 
    summary = summarize_updates(major, minor)
 
    subject = f"Instagram Notifier — {len(major)} major, {len(minor)} minor update(s)"
 
    plain_sections = [summary]
    if major:
        plain_sections.append("=== Major Updates ===\n" + "\n".join(format_update_plain(u) for u in major))
    if minor:
        plain_sections.append("=== Minor Updates ===\n" + "\n".join(format_update_plain(u) for u in minor))
    plain = "\n\n".join(plain_sections)
 
    def html_section(title, updates):
        if not updates:
            return ""
        items = "\n".join(format_update_html(u) for u in updates)
        return f'''
        <h2 style="font-family:sans-serif;border-bottom:2px solid #eee;padding-bottom:6px">{title} ({len(updates)})</h2>
        <ul style="list-style:none;padding:0;font-family:sans-serif;line-height:1.6">
        {items}
        </ul>'''
 
    # Hidden preheader: shown in notification preview instead of email body text.
    # The &zwnj; padding pushes any real content out of the preview window.
    preheader = f'''<div style="display:none;max-height:0;overflow:hidden">{summary}{"&nbsp;&zwnj;" * 60}</div>'''
 
    html = f"""
    <html><body style="max-width:600px;margin:auto;padding:24px;color:#1a1a1a">
    {preheader}
    <p style="font-family:sans-serif;font-size:1em;line-height:1.6;border-left:3px solid #ccc;padding-left:12px;color:#444">{summary}</p>
    {html_section("Major Updates", major)}
    {html_section("Minor Updates", minor)}
    </body></html>
    """
 
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = email
    msg["To"] = email
    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(html, "html"))
 
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=context) as server:
        server.login(email, app_password)
        server.sendmail(email, email, msg.as_string())
 
    print(f"Email sent to {email}", file=sys.stderr)


def main(root_dir: str) -> None:
    load_dotenv()

    email = os.environ.get("NOTIFY_EMAIL")
    app_password = os.environ.get("NOTIFY_APP_PASSWORD")
    if not email or not app_password:
        print(
            "Error: NOTIFY_EMAIL and NOTIFY_APP_PASSWORD environment variables must be set.",
            file=sys.stderr,
        )
        sys.exit(1)

    root = Path(root_dir)
    if not root.is_dir():
        print(f"Error: '{root_dir}' is not a valid directory.", file=sys.stderr)
        sys.exit(1)

    # Remove any stale .visited files from previous interrupted runs
    for visited_file in root.rglob(".visited"):
        visited_file.unlink()
        print(f"Cleared stale: {visited_file}", file=sys.stderr)

    all_major_updates = []
    all_minor_updates = []
    dirs_to_finalize = []

    # Walk all subdirectories, sorted for deterministic ordering
    for directory in sorted(root.rglob("*")):
        if not directory.is_dir():
            continue

        major_file = directory / "major_updates.json"
        minor_file = directory / "minor_updates.json"
        processed_file = directory / ".processed"

        # Skip if neither updates file exists, or already fully processed
        if not (major_file.exists() or minor_file.exists()):
            continue
        if processed_file.exists():
            continue

        # Touch .visited immediately — marks that we've started this directory.
        # If we crash before .processed is written, the next run will retry.
        visited_file = directory / ".visited"
        visited_file.touch()

        if major_file.exists():
            all_major_updates.extend(load_json_file(major_file))

        if minor_file.exists():
            all_minor_updates.extend(load_json_file(minor_file))

        dirs_to_finalize.append(directory)
        print(f"Read: {directory}", file=sys.stderr)

    # Finalize all dirs we read — always, so empty-file dirs aren't retried
    def finalize():
        for directory in dirs_to_finalize:
            (directory / ".processed").touch()
            print(f"Finalized: {directory}", file=sys.stderr)

    # In the future: to reduce noise, we could email only on major updates
    # if not all_major_updates:
    #     print("No major updates found.", file=sys.stderr)
    #     finalize()
    #     return

    # -------------------------------------------------------------------------
    # # TEST DATA — delete this block to disable
    # all_major_updates += [
    #     {"kind": "major", "date": "2026-04-24", "username": "testaccount", "post_url": "https://www.instagram.com/p/abc123/", "text": "Just dropped a new collection 🔥 Check the link in bio for early access before it sells out!"},
    # ]
    # all_minor_updates += [
    #     {"kind": "minor", "date": "2026-04-23", "username": "anotheraccount", "post_url": "https://www.instagram.com/p/def456/", "text": "Weekend vibes ☀️"},
    #     {"kind": "minor", "date": "2026-04-25", "username": "thirdaccount",  "post_url": "https://www.instagram.com/p/ghi789/", "text": "grateful for every single one of you 🙏 we hit 100k today"},
    # ]
    # -------------------------------------------------------------------------

    if not all_major_updates and not all_minor_updates:
        print("No updates found.", file=sys.stderr)
        finalize()
        return

    send_email(email, app_password, all_major_updates, all_minor_updates)

    # Email sent successfully — mark each directory as fully processed
    finalize()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <scrapes_directory>", file=sys.stderr)
        sys.exit(1)

    main(sys.argv[1])