import anthropic
import json
import sys
from pydantic import BaseModel
from lib import UpdateKind, Update, Response

def get_post_text(post):
    """Join texts into one string"""
    texts = post.get("texts", [])
    joined = " ".join(texts).strip()
    return joined

def combine_posts(posts):
    post_blocks = []
    for i, post in enumerate(posts):
        post_blocks.append(
            f"[Post {i+1} | {post['timestamp'][:10]} | @{post['username']}]\n"
            f"{get_post_text(post)}"
        )
    
    return "\n\n---\n\n".join(post_blocks)

def find_life_events(posts) -> Response:
    client = Anthropic()

    combined = combine_posts(posts)

    response = client.messages.parse(
        model="claude-haiku-3",
        max_tokens=2048,
        system="""You analyze an Instagram feed to identify important life events. Here are some examples of life events.

Major updates: engagements, weddings, breakups, kids, pregnancy, deaths, major sickness updates, job changes, promotions, moving, starting or finishing a major project (for example, training to climb a mountain, finishing an animation)
Minor updates: vacations, starting or finishing a minor project (for example, running a half marathon, working out every day for a month)

Set updates to null if nothing of note is found.
Set error to a brief explanation if: the input is malformed, posts have missing
timestamps or usernames, text is missing or truncated, or you cannot meaningfully analyze the content.""",
        messages=[{
            "role": "user",
            "content": f"Analyze these posts:\n\n{combined}"
        }],
        output_format=Response,
    )

    return response.parsed_output


def write_updates(response: Response):
    if response.error:
        print(f"Error: {response.error}")

    if not response.updates:
        print("Nothing of note.")
        return

    major = [u for u in response.updates if u.kind == UpdateKind.MAJOR]
    minor = [u for u in response.updates if u.kind == UpdateKind.MINOR]

    if major:
        with open("major_updates.txt", "w") as f:
            f.write("\n\n".join(u.text for u in major))
        print(f"Wrote {len(major)} major update(s) to major_updates.txt")

    if minor:
        with open("minor_updates.txt", "w") as f:
            f.write("\n\n".join(u.text for u in minor))
        print(f"Wrote {len(minor)} minor update(s) to minor_updates.txt")

def main(json_path):
    with open(json_path, "r") as f:
        posts = json.load(f)
    find_life_events(posts)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script.py <path_to_json>")
        sys.exit(1)
    main(sys.argv[1])


def write_updates(response: Response):
    if response.error:
        print(f"Error: {response.error}")
        return

    if not response.updates:
        print("Nothing of note.")
        return

    major = [u for u in response.updates if u.kind == UpdateKind.MAJOR]
    minor = [u for u in response.updates if u.kind == UpdateKind.MINOR]

    if major:
        with open("major_updates.txt", "w") as f:
            f.write("\n\n".join(u.text for u in major))
        print(f"Wrote {len(major)} major update(s) to major_updates.txt")

    if minor:
        with open("minor_updates.txt", "w") as f:
            f.write("\n\n".join(u.text for u in minor))
        print(f"Wrote {len(minor)} minor update(s) to minor_updates.txt")