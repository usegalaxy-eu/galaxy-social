"""Collect past posts for the Post Creator: hashtag and mention suggestions, and the list for the posts page."""

import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict

import emoji
import yaml

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from lib.galaxy_social import parse_schedule  # noqa: E402

posts_folder, output_path, posts_output_path = sys.argv[1], sys.argv[2], sys.argv[3]
hashtags = Counter()
spellings = defaultdict(Counter)
mentions = defaultdict(Counter)
posts = []

# When each post file was added to the repo, newest first; needs the full git history
added, date = {}, None
log = subprocess.run(
    ["git", "log", "--no-renames", "--diff-filter=A", "--format=%cI", "--name-only", "--", posts_folder],
    capture_output=True,
    text=True,
).stdout
for line in log.splitlines():
    if line and not line.startswith(posts_folder):
        date = line
    elif line:
        added.setdefault(line, date)

for root, _, files in os.walk(posts_folder):
    for filename in files:
        if not filename.endswith(".md"):
            continue
        file_path = os.path.join(root, filename)
        try:
            with open(file_path) as f:
                _, metadata, text = f.read().split("---\n", 2)
            metadata = yaml.safe_load(metadata) or {}
        except Exception:
            continue
        for values in (metadata.get("hashtags") or {}).values():
            for tag in values or []:
                # count #EOSC and #eosc as one hashtag, suggested in its most used spelling
                hashtags[str(tag).lower()] += 1
                spellings[str(tag).lower()][str(tag)] += 1
        for media, values in (metadata.get("mentions") or {}).items():
            mentions[str(media).split("-")[0]].update(str(v) for v in values or [])
        try:
            schedule = parse_schedule(metadata.get("schedule"))
        except ValueError:
            schedule = None
        inline_images = re.findall(r"!\[[^\]]*\]\(([^)\s]+)[^)]*\)", text)
        text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text).strip()
        posts.append(
            {
                "path": file_path,
                "media": metadata.get("media") or [],
                "schedule": schedule.isoformat() if schedule else None,
                "added": added.get(file_path),
                # cut at a space so links stay whole
                "text": re.sub(r"\s\S*$", "", text[:500]) if len(text) > 500 else text,
                "image": ((metadata.get("images") or [{}])[0] or {}).get("url")
                or next(iter(inline_images), None),
            }
        )

with open(output_path, "w") as f:
    json.dump(
        {
            "hashtags": [
                spellings[tag].most_common(1)[0][0]
                for tag, _ in hashtags.most_common(300)
            ],
            "mentions": {
                platform: [name for name, _ in counter.most_common(200)]
                for platform, counter in mentions.items()
            },
            # :tada: style codes the bot turns into emoji (emoji.emojize in lib/galaxy_social.py)
            "emoji": {
                name: emoji.emojize(name, language="alias")
                for data in emoji.EMOJI_DATA.values()
                for name in [data["en"], *data.get("alias", [])]
                if emoji.emojize(name, language="alias") != name
            },
        },
        f,
    )

with open(posts_output_path, "w") as f:
    json.dump(posts, f)
