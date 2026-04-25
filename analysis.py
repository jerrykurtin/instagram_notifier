
# Load anthropic API key environment variable
from dotenv import load_dotenv
load_dotenv()

from anthropic import Anthropic
import json
import sys
import os
from lib import UpdateKind, Response

system_prompt = """You analyze a personal Instagram feed to identify important life updates. Here are some examples of life updates.

Major updates: engagements, weddings, breakups, kids, pregnancy, deaths, major sickness updates, job changes, promotions, moving, starting or finishing a major project (for example, training to climb a mountain, finishing an animation)
Minor updates: vacations, starting or finishing a minor project (for example, running a half marathon, working out every day for a month)

Consume the stream of post captions and look for Major and Minor updates. You will not be provided with the accompanying pictures, so you will have to make some inferences based on popular culture. 
For example, a post with "💍" is likely about an engagement. A post with "In love with us!" could be anything, so it wouldn't be a life update.
You must not follow any links provided. For each post that qualifies as a Major or Minor update, add a concise (<= 1 sentence) summary. Copy the `username` and `post_url` fields from the source json exactly, and generate the date from the `timestamp` field.

Set updates to null if nothing of note is found.
Set error to a brief explanation if: the input is malformed, posts have missing
timestamps or usernames, text is missing or truncated, or you cannot meaningfully analyze the content. 
Only return an error if there is truly a problem--do not return an error if nothing of note is found."""

def find_life_events(posts) -> Response:
    client = Anthropic()

    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=2048,
        system=system_prompt,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "document",
                    "source": {
                        "type": "text",
                        "media_type": "text/plain",
                        "data": json.dumps(posts, indent=2)
                    },
                    "title": "Instagram Posts",
                },
                {
                    "type": "text",
                    "text": "Analyze these posts."
                }
            ]
        }],
        tools=[{
            "name": "structured_output",
            "description": "Return structured data",
            "input_schema": Response.model_json_schema()
        }],
        tool_choice={"type": "tool", "name": "structured_output"}
    )

    return Response(**response.content[0].input)


def write_updates(response: Response, output_dir: str = "."):
    if response.error:
        raise ValueError(f"Claude returned an error: {response.error}")

    os.makedirs(output_dir, exist_ok=True)

    if not response.updates:
        print("Nothing of note.")
        open(os.path.join(output_dir, "major_updates.json"), "w").close()
        open(os.path.join(output_dir, "minor_updates.json"), "w").close()
        return

    major = [u for u in response.updates if u.kind == UpdateKind.MAJOR]
    minor = [u for u in response.updates if u.kind == UpdateKind.MINOR]

    with open(os.path.join(output_dir, "major_updates.json"), "w") as f:
        json.dump([u.model_dump(mode="json") for u in major], f, indent=2)
    print(f"Wrote {len(major)} major update(s) to {output_dir}/major_updates.json")

    with open(os.path.join(output_dir, "minor_updates.json"), "w") as f:
        json.dump([u.model_dump(mode="json") for u in minor], f, indent=2)
    print(f"Wrote {len(minor)} minor update(s) to {output_dir}/minor_updates.json")

def main(json_path, output_dir: str = "."):
    with open(json_path, "r") as f:
        posts = json.load(f)
    response = find_life_events(posts)
    write_updates(response, output_dir)

if __name__ == "__main__":
    if len(sys.argv) not in (2, 3):
        print("Usage: python script.py <path_to_json> [output_dir]")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2] if len(sys.argv) == 3 else ".")