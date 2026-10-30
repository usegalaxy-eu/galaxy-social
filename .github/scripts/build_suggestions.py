"""Collect the hashtags and mentions used in past posts for the Post Creator's suggestions."""

import json
import os
import sys
from collections import Counter, defaultdict

import yaml

posts_folder, output_path = sys.argv[1], sys.argv[2]
hashtags = Counter()
spellings = defaultdict(Counter)
mentions = defaultdict(Counter)

for root, _, files in os.walk(posts_folder):
    for filename in files:
        if not filename.endswith(".md"):
            continue
        try:
            with open(os.path.join(root, filename)) as f:
                metadata = yaml.safe_load(f.read().split("---\n", 2)[1]) or {}
        except Exception:
            continue
        for values in (metadata.get("hashtags") or {}).values():
            for tag in values or []:
                # count #EOSC and #eosc as one hashtag, suggested in its most used spelling
                hashtags[str(tag).lower()] += 1
                spellings[str(tag).lower()][str(tag)] += 1
        for media, values in (metadata.get("mentions") or {}).items():
            mentions[str(media).split("-")[0]].update(str(v) for v in values or [])

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
        },
        f,
    )
