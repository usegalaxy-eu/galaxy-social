import re
import textwrap
from typing import Dict, List, Optional, Tuple, cast

import atproto
import requests
from bs4 import BeautifulSoup


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
        except:
            return None
        embed_external = None
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            title_tag = soup.find("meta", attrs={"property": "og:title"})
            title_tag_alt = soup.title.string if soup.title else None
            description_tag = soup.find("meta", attrs={"property": "og:description"})
            description_tag_alt = soup.find("meta", attrs={"name": "description"})
            image_tag = soup.find("meta", attrs={"property": "og:image"})
            title = title_tag["content"] if title_tag else title_tag_alt
            description = (
                description_tag["content"]
                if description_tag
                else description_tag_alt["content"] if description_tag_alt else ""
            )
            uri = url
            thumb = (
                self.blueskysocial.upload_blob(
                    requests.get(image_tag["content"]).content
                ).blob
                if image_tag
                else None
            )
            embed_external = atproto.models.AppBskyEmbedExternal.Main(
                external=atproto.models.AppBskyEmbedExternal.External(
                    title=title,
                    description=description,
                    uri=uri,
                    thumb=thumb,
                )
            )
        return embed_external

    def create_post(
        self, content, mentions, hashtags, images, **kwargs
    ) -> Tuple[bool, Optional[str]]:
        embed_images = []
        for image in images[:4]:
            response = requests.get(image["url"])
            if response.status_code == 200 and response.headers.get(
                "Content-Type", ""
            ).startswith("image/"):
                img_data = response.content
                upload = self.blueskysocial.com.atproto.repo.upload_blob(img_data)
                embed_images.append(
                    atproto.models.AppBskyEmbedImages.Image(
                        alt=image["alt_text"] if "alt_text" in image else "",
                        image=upload.blob,
                    )
                )
        embed = (
            atproto.models.AppBskyEmbedImages.Main(images=embed_images)
            if embed_images
            else None
        )

        status = []
        reply_to = None
        mentions = " ".join([f"@{v}" for v in mentions])
        hashtags = " ".join([f"#{v}" for v in hashtags])
        for text in textwrap.wrap(
            content + "\n" + mentions + "\n" + hashtags,
            self.max_content_length,
            replace_whitespace=False,
        ):
            facets, last_url = self.parse_facets(text)
            if not images or reply_to:
                embed = self.handle_url_card(cast(str, last_url))

            post = self.blueskysocial.send_post(
                text, facets=facets, embed=embed, reply_to=reply_to
            )

            for _ in range(5):
                data = self.blueskysocial.get_posts([post.uri]).posts
                if data:
                    status.append(data[0].record.text == text)
                    break

            if reply_to is None:
                link = f"https://bsky.app/profile/{self.blueskysocial.me.handle}/post/{post.uri.split('/')[-1]}"
                root = atproto.models.create_strong_ref(post)
            parent = atproto.models.create_strong_ref(post)
            reply_to = atproto.models.AppBskyFeedPost.ReplyRef(parent=parent, root=root)

        return all(status), link
