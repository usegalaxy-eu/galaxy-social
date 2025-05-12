import re
import tempfile
import textwrap
import traceback

import requests
from mastodon import Mastodon  # type: ignore

from .base import strip_markdown_formatting


class mastodon_client:
    def __init__(self, **kwargs):
        self.base_url = kwargs.get("base_url", "https://mstdn.science")
        self.mastodon_handle = Mastodon(
            access_token=kwargs.get("access_token"), api_base_url=self.base_url
        )
        self.max_content_length = kwargs.get("max_content_length", 500)

    def content_in_chunks(self, content, max_chunk_length):
        paragraphs = content.split("\n\n\n")
        for p in paragraphs:
            for chunk in textwrap.wrap(
                p.strip("\n"), max_chunk_length, replace_whitespace=False
            ):
                yield chunk

    def wrap_text_with_index(self, content):
        if len(content) <= self.max_content_length:
            return [content]
        # urls always count as 23 chars on mastodon
        url_placeholder = "~" * 23
        url_pattern = r"https?://\S+"
        mention_hashtag_pattern = r"@\S+|#\S+"
        urls = re.findall(url_pattern, content)
        others = re.findall(mention_hashtag_pattern, content)
        placeholder_content = re.sub(url_pattern, url_placeholder, content)
        placeholders = []
        for item in others:
            placeholder = "~" * len(item)
            placeholders.append((placeholder, item))
            placeholder_content = placeholder_content.replace(item, placeholder, 1)
        wrapped_lines = list(
            self.content_in_chunks(placeholder_content, self.max_content_length - 8)
        )
        final_lines = []
        url_index = 0
        token_index = 0
        for i, line in enumerate(wrapped_lines, 1):
            while url_placeholder in line and url_index < len(urls):
                line = line.replace(url_placeholder, urls[url_index], 1)
                url_index += 1
            for placeholder, original in placeholders[token_index:]:
                if placeholder in line:
                    line = line.replace(placeholder, original, 1)
                    token_index += 1
                else:
                    break
            final_lines.append(f"{line} ({i}/{len(wrapped_lines)})")
        return final_lines

    def format_content(self, content, mentions, hashtags, images, **kwargs):
        mentions = " ".join([f"@{v}" for v in mentions])
        hashtags = " ".join([f"#{v}" for v in hashtags])
        # later we could make seperate posts for images if there are more than 4 images
        if len(images) > 4:
            warnings = f"A maximum of four images, not {len(images)}, can be included in a single mastodon post."
            images = images[:4]
        else:
            warnings = ""

        # convert markdown formatting because Mastodon doesn't support it
        paragraphs = content.split("\n\n\n")
        for i, p in enumerate(paragraphs):
            paragraphs[i] = strip_markdown_formatting(p)
        content = "\n\n\n".join(paragraphs)

        content += "\n"
        if mentions:
            content = f"{content}\n{mentions}"
        if hashtags:
            content = f"{content}\n{hashtags}"
        chunks = self.wrap_text_with_index(content.strip("\n"))

        formatted_content = {
            "body": "\n\n".join(chunks),
            "images": images,
            "chunks": chunks,
        }
        preview = formatted_content["body"]
        images_preview = "\n".join(
            [f'![{image.get("alt_text", "")}]({image["url"]})' for image in images]
        )
        preview += "\n\n" + images_preview
        return formatted_content, preview, warnings

    def create_post(self, content, **kwargs):
        media_ids = []
        for image in content["images"]:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            response = requests.get(image["url"], headers=headers)
            if response.status_code == 200 and response.headers.get(
                "Content-Type", ""
            ).startswith("image/"):
                with tempfile.NamedTemporaryFile() as temp:
                    temp.write(response.content)
                    temp.flush()
                    try:
                        media_uploaded = self.mastodon_handle.media_post(
                            media_file=temp.name,
                            description=(
                                image["alt_text"] if "alt_text" in image else None
                            ),
                        )
                        media_ids.append(media_uploaded["id"])
                    except Exception as e:
                        print(f"Mastodon error: {e}")
                        traceback.print_exc()
                        return False, None

        posts = []
        for text in content["chunks"]:
            try:
                toot = self.mastodon_handle.status_post(
                    status=text,
                    in_reply_to_id=posts[-1] if posts else None,
                    media_ids=media_ids if (media_ids and not posts) else None,
                )
                posts.append(toot.id)
                if len(posts) == 1:
                    link = toot.url
            except Exception as e:
                print(f"Mastodon error: {e}")
                traceback.print_exc()
                for post in posts:
                    self.mastodon_handle.status_delete(post)
                return False, None
        return True, link
