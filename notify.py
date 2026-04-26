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

from dotenv import load_dotenv


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


def send_email(email: str, app_password: str, major_updates: list, minor_updates: list) -> None:
    subject = f"Instagram Notifier — {len(major_updates)} major, {len(minor_updates)} minor update(s)"

    plain = (
        f"=== Major Updates ===\n{json.dumps(major_updates, indent=2)}"
        f"\n\n=== Minor Updates ===\n{json.dumps(minor_updates, indent=2)}"
    )

    html = f"""
    <html><body>
    <h2>Major Updates ({len(major_updates)})</h2>
    <pre style="background:#f4f4f4;padding:12px;border-radius:6px">{json.dumps(major_updates, indent=2)}</pre>
    <h2>Minor Updates ({len(minor_updates)})</h2>
    <pre style="background:#f4f4f4;padding:12px;border-radius:6px">{json.dumps(minor_updates, indent=2)}</pre>
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

    if not all_major_updates:
        print("No major updates found.", file=sys.stderr)
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