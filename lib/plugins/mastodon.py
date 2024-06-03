import tempfile
import textwrap

import requests
from bs4 import BeautifulSoup
from mastodon import Mastodon


class mastodon_client:
    def __init__(self, **kwargs):
        self.base_url = kwargs.get("base_url", "https://mstdn.science")
        self.mastodon_handle = Mastodon(
            access_token=kwargs.get("access_token"), api_base_url=self.base_url
        )
        self.max_content_length = kwargs.get("max_content_length", 500)

    def format_content(self, content, mentions, hashtags, images, **kwargs):
        mentions = " ".join([f"@{v}" for v in mentions])
        hashtags = " ".join([f"#{v}" for v in hashtags])
        if len(images) > 4:
            warnings = f"A maximum of four images, not {len(images)}, can be included in a single mastodon post."
            images = images[:4]
        else:
            warnings = ""
        formatted_content = {
            "body": f"{content}\n\n{mentions}\n{hashtags}",
            "images": images,
        }
        preview = formatted_content["body"]
        images_preview = "\n".join(
            [
                f'![{image.get("alt_text", "")}]({image["url"]})'
                for image in images
            ]
        )
        preview += "\n\n" + images_preview
        return formatted_content, preview, warnings

    def create_post(self, content, **kwargs):
        media_ids = []
        for image in content["images"]:
            response = requests.get(image["url"])
            if response.status_code == 200 and response.headers.get(
                "Content-Type", ""
            ).startswith("image/"):
                with tempfile.NamedTemporaryFile() as temp:
                    temp.write(response.content)
                    temp.flush()
                    media_uploaded = self.mastodon_handle.media_post(
                        media_file=temp.name,
                        description=image["alt_text"] if "alt_text" in image else None,
                    )
                    media_ids.append(media_uploaded["id"])

        toot_id = link = None
        status = []
        for text in textwrap.wrap(
            content["body"],
            self.max_content_length,
            replace_whitespace=False,
        ):
            toot = self.mastodon_handle.status_post(
                status=text,
                in_reply_to_id=toot_id,
                media_ids=media_ids if (media_ids and toot_id is None) else None,
            )

            toot_id = toot["id"]
            if not link:
                link = f"{self.base_url}/@{toot['account']['acct']}/{toot_id}"

            for _ in range(3):
                post = self.mastodon_handle.status(toot_id)
                if post.url:
                    if not link:
                        link = post.url
                    break
            else:
                return False, None

        return True, link
