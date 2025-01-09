import re
import textwrap
from typing import Dict, List, Optional, Tuple, cast

import atproto
import cv2
import numpy as np
import requests
from bs4 import BeautifulSoup

from .base import strip_markdown_formatting


def compress_image_to_limit(image_url):
    if not isinstance(image_url, str) or not image_url.startswith(("http", "https")):
        return None
    response = requests.get(image_url)
    if response.status_code != 200 and not response.headers.get(
        "Content-Type", ""
    ).startswith("image/"):
        return None
    image_content = response.content
    if len(image_content) < 976.56 * 1024:
        return image_content

    np_array = np.frombuffer(image_content, np.uint8)
    image = cv2.imdecode(np_array, cv2.IMREAD_UNCHANGED)
    quality = 95
    while quality >= 10:
        success, compressed_image = cv2.imencode(
            ".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, quality]
        )
        if not success:
            return None
        if len(compressed_image) <= 976.56 * 1024:
            return compressed_image.tobytes()
        quality -= 5


class bluesky_client:
    def __init__(self, **kwargs):
        self.base_url = kwargs.get("base_url", "https://bsky.social")
        self.blueskysocial = atproto.Client(self.base_url)
        self.blueskysocial.login(
            login=kwargs.get("username"), password=kwargs.get("password")
        )
        self.max_content_length = kwargs.get("max_content_length", 300)

    def parse_mentions(self, text: str) -> List[Dict]:
        spans = []
        mention_regex = rb"[$|\W](@([a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)"
        text_bytes = text.encode("UTF-8")
        for m in re.finditer(mention_regex, text_bytes):
            spans.append(
                {
                    "start": m.start(1),
                    "end": m.end(1),
                    "handle": m.group(1)[1:].decode("UTF-8"),
                }
            )
        return spans

    def parse_urls(self, text: str) -> List[Dict]:
        spans = []
        url_regex = rb"[$|\W](https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*[-a-zA-Z0-9@%_\+~#//=])?)"
        text_bytes = text.encode("UTF-8")
        for m in re.finditer(url_regex, text_bytes):
            spans.append(
                {
                    "start": m.start(1),
                    "end": m.end(1),
                    "url": m.group(1).decode("UTF-8"),
                }
            )
        return spans

    def parse_hashtags(self, text: str) -> List[Dict]:
        spans = []
        hashtag_regex = rb"[$|\W]#(\w+)"
        text_bytes = text.encode("UTF-8")
        for m in re.finditer(hashtag_regex, text_bytes):
            spans.append(
                {
                    "start": m.start(1),
                    "end": m.end(1),
                    "tag": m.group(1).decode("UTF-8"),
                }
            )
        return spans

    def parse_facets(self, text: str) -> Tuple[List[Dict], Optional[str]]:
        facets = []
        for h in self.parse_hashtags(text):
            facets.append(
                {
                    "index": {
                        "byteStart": h["start"],
                        "byteEnd": h["end"],
                    },
                    "features": [
                        {"$type": "app.bsky.richtext.facet#tag", "tag": h["tag"]}
                    ],
                }
            )
        for m in self.parse_mentions(text):
            resp = requests.get(
                "https://bsky.social/xrpc/com.atproto.identity.resolveHandle",
                params={"handle": m["handle"]},
            )
            if resp.status_code == 400:
                continue
            did = resp.json()["did"]
            facets.append(
                {
                    "index": {
                        "byteStart": m["start"],
                        "byteEnd": m["end"],
                    },
                    "features": [
                        {"$type": "app.bsky.richtext.facet#mention", "did": did}
                    ],
                }
            )
        last_url = None
        for u in self.parse_urls(text):
            facets.append(
                {
                    "index": {
                        "byteStart": u["start"],
                        "byteEnd": u["end"],
                    },
                    "features": [
                        {
                            "$type": "app.bsky.richtext.facet#link",
                            "uri": u["url"],
                        }
                    ],
                }
            )
            last_url = u["url"]
        return facets, last_url

    def handle_url_card(
        self, url: str
    ) -> Optional[atproto.models.AppBskyEmbedExternal.Main]:
        try:
            response = requests.get(url)
        except Exception as e:
            print(e)
            return None
        if response.status_code != 200:
            return None
        soup = BeautifulSoup(response.text, "html.parser")
        title_tag = soup.find("meta", attrs={"property": "og:title"})
        title_tag_alt = soup.title.string if soup.title else None
        description_tag = soup.find("meta", attrs={"property": "og:description"})
        description_tag_alt = soup.find("meta", attrs={"name": "description"})
        image_tag = soup.find("meta", attrs={"property": "og:image"})
        title = (
            title_tag.attrs.get("content")
            if title_tag and hasattr(title_tag, "attrs")
            else title_tag_alt
        )
        description = (
            description_tag.attrs.get("content")
            if description_tag and hasattr(description_tag, "attrs")
            else (
                description_tag_alt.attrs.get("content")
                if description_tag_alt and hasattr(description_tag_alt, "attrs")
                else ""
            )
        )
        image_url = (
            image_tag.attrs.get("content")
            if image_tag and hasattr(image_tag, "attrs")
            else None
        )
        image_content = compress_image_to_limit(image_url)
        thumb = (
            self.blueskysocial.upload_blob(image_content).blob
            if image_content
            else None
        )
        embed_external = atproto.models.AppBskyEmbedExternal.Main(
            external=atproto.models.AppBskyEmbedExternal.External(
                title=title,
                description=description,
                uri=url,
                thumb=thumb,
            )
        )
        return embed_external

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
        urls = re.findall(r"https?://\S+", content)
        placeholder_content = re.sub(
            r"https?://\S+", lambda m: "~" * len(m.group()), content
        )
        wrapped_lines = list(
            self.content_in_chunks(placeholder_content, self.max_content_length - 8)
        )
        final_lines = []
        url_index = 0
        for i, line in enumerate(wrapped_lines, 1):
            while "~~~~~~~~~~" in line and url_index < len(urls):
                placeholder = "~" * len(urls[url_index])
                line = line.replace(placeholder, urls[url_index], 1)
                url_index += 1
            final_lines.append(f"{line} ({i}/{len(wrapped_lines)})")
        return final_lines

    def format_content(self, content, mentions, hashtags, images, **kwargs):
        mentions = " ".join([f"@{v}" for v in mentions])
        hashtags = " ".join([f"#{v}" for v in hashtags])
        if len(images) > 4:
            warnings = f"A maximum of four images, not {len(images)}, can be included in a single bluesky post."
            images = images[:4]
        else:
            warnings = ""

        # convert markdown formatting because bluesky doesn't support it
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

    def create_post(self, content, **kwargs) -> Tuple[bool, Optional[str]]:
        try:
            embed_images = []
            for image in content["images"]:
                img_data = compress_image_to_limit(image["url"])
                upload = (
                    self.blueskysocial.com.atproto.repo.upload_blob(img_data).blob
                    if img_data
                    else None
                )
                embed_images.append(
                    atproto.models.AppBskyEmbedImages.Image(
                        alt=image["alt_text"] if "alt_text" in image else "",
                        image=upload,
                    )
                )
            embed = (
                atproto.models.AppBskyEmbedImages.Main(images=embed_images)
                if embed_images
                else None
            )
        except Exception as e:
            print(e)
            return False, None

        posts: List["atproto.models.AppBskyFeedPost.CreateRecordResponse"] = []
        for text in content["chunks"]:
            facets, last_url = self.parse_facets(text)
            reply_to = (
                atproto.models.AppBskyFeedPost.ReplyRef(
                    parent=atproto.models.create_strong_ref(posts[-1]),
                    root=atproto.models.create_strong_ref(posts[0]),
                )
                if posts
                else None
            )
            if not content["images"] or reply_to:
                embed = self.handle_url_card(cast(str, last_url))

            try:
                post = self.blueskysocial.send_post(
                    text, facets=facets, embed=embed, reply_to=reply_to
                )
                posts.append(post)
                if len(posts) == 1:
                    link = f"https://bsky.app/profile/{self.blueskysocial.me.handle}/post/{posts[0].uri.split('/')[-1]}"
            except Exception as e:
                print(e)
                for post in posts:
                    self.blueskysocial.delete_post(post.uri)
                return False, None
        return True, link
