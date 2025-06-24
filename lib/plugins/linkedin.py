import os
import re
import textwrap
import traceback
from string import Template
from urllib.parse import quote

import requests

from .base import strip_markdown_formatting


class linkedin_client:
    def __init__(self, **kwargs):
        self.api_base_url = kwargs.get("base_url", "https://api.linkedin.com/rest")
        self.organization_urn = f"urn:li:organization:{kwargs.get('org_id')}"
        self.access_token = kwargs.get("access_token")
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "X-Restli-Protocol-Version": "2.0.0",
            "LinkedIn-Version": "202406",
        }
        self.max_content_length = kwargs.get("max_content_length", 3000)

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

    def build_organization_mentions(self, mentions):
        output = []
        warnings = ""
        for mention in mentions:
            vanity_name = mention.strip()
            urn = None
            try:
                response = requests.get(
                    f"{self.api_base_url}/organizations",
                    headers=self.headers,
                    params={"q": "vanityName", "vanityName": vanity_name},
                )
                response.raise_for_status()
                elements = response.json().get("elements", [])
                if elements and (org_id := elements[0].get("id")):
                    urn = f"urn:li:organization:{org_id}"
                    mention = elements[0].get("localizedName")
            except Exception as e:
                print(f"[WARN] Failed to resolve @{mention}: {e}")
                warnings += f"Failed to resolve @{mention}: {e}\n"
            output.append(f"@[{mention}]({urn})" if urn else f"@{mention}")
        return " ".join(output), warnings

    def protect_mentions(self, content):
        protected_mentions = {}

        def protect(match):
            key = f"M{len(protected_mentions)}"
            protected_mentions[key] = match.group(0)
            return f"${key}"

        content = re.sub(r"@\[[^\]]+\]\(urn:li:organization:\d+\)", protect, content)
        return content, protected_mentions

    def format_content(self, content, mentions, hashtags, images, **kwargs):
        warnings = ""
        mentions, mentions_warnings = self.build_organization_mentions(mentions)
        warnings += mentions_warnings
        hashtags = " ".join([f"#{v}" for v in hashtags])
        if len(images) > 20:
            warnings += f"A maximum of 20 images, not {len(images)}, can be included in a single linkedin post."
            images = images[:20]

        # convert markdown formatting because linkedin doesn't support it
        content, protected_mentions = self.protect_mentions(content)

        paragraphs = content.split("\n\n\n")
        for i, p in enumerate(paragraphs):
            paragraphs[i] = strip_markdown_formatting(p)
        content = "\n\n\n".join(paragraphs)

        content = Template(content).safe_substitute(protected_mentions)

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

    def linkedin_post(self, content, images):
        try:
            content, protected_mentions = self.protect_mentions(content)
            # This is needed to escape special characters in the content
            # https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/little-text-format?view=li-lms-2024-08#text
            content = content.translate({ord(c): f"\\{c}" for c in "\\|{}@[]()<>#*_~"})
            content = Template(content).safe_substitute(protected_mentions)

            data = {
                "author": self.organization_urn,
                "commentary": content,
                "visibility": "PUBLIC",
                "distribution": {
                    "feedDistribution": "MAIN_FEED",
                    "targetEntities": [],
                    "thirdPartyDistributionChannels": [],
                },
                "lifecycleState": "PUBLISHED",
                "isReshareDisabledByAuthor": False,
            }
            if images:
                data["content"] = self.linkedin_upload_images(images)
            headers = self.headers
            headers["Content-Type"] = "application/json"
            response = requests.post(
                f"{self.api_base_url}/posts", headers=headers, json=data
            )
            response.raise_for_status()
            return response.headers.get("x-restli-id")
        except Exception as e:
            print(f"Linkedin error: {e}")
            traceback.print_exc()
            return None

    def linkedin_upload_images(self, images):
        try:
            image_upload = []
            for image in images:
                data = {"initializeUploadRequest": {"owner": self.organization_urn}}
                response = requests.post(
                    f"{self.api_base_url}/images?action=initializeUpload",
                    headers=self.headers,
                    json=data,
                )
                response.raise_for_status()
                value = response.json().get("value")
                upload_url = value["uploadUrl"]
                filename = os.path.basename(image["url"])
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                }
                with requests.get(image["url"], stream=True, headers=headers) as r:
                    r.raise_for_status()
                    with open(filename, "wb") as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            f.write(chunk)
                with open(filename, "rb") as file:
                    response = requests.put(
                        upload_url,
                        headers={"Authorization": f"Bearer {self.access_token}"},
                        data=file,
                    )
                    response.raise_for_status()
                image_id = value["image"]
                image_upload.append(
                    {"id": image_id, "altText": image.get("alt_text", "")}
                )
            content = (
                {"media": image_upload[0]}
                if len(image_upload) == 1
                else {"multiImage": {"images": image_upload}}
            )
            return content
        except Exception as e:
            print(f"Linkedin error: {e}")
            traceback.print_exc()
            return None

    def linkedin_comment(self, content, post_id):
        try:
            data = {
                "actor": self.organization_urn,
                "object": post_id,
                "message": {"text": content},
            }
            headers = self.headers
            headers["Content-Type"] = "application/json"
            response = requests.post(
                f"{self.api_base_url}/socialActions/{quote(post_id)}/comments",
                headers=headers,
                json=data,
            )
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"Linkedin error: {e}")
            traceback.print_exc()
            return False

    def linkedin_delete_post(self, post_id):
        try:
            headers = self.headers
            headers["X-RestLi-Method"] = "DELETE"
            response = requests.delete(
                f"{self.api_base_url}/posts/{quote(post_id)}", headers=headers
            )
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"Linkedin error: {e}")
            traceback.print_exc()
            return False

    def create_post(self, content, **kwargs):
        post_id = None
        for text in content["chunks"]:
            if not post_id:
                post_id = self.linkedin_post(text, content.get("images"))
                if not post_id:
                    return False, None
            else:
                comment_id = self.linkedin_comment(text, post_id)
                if not comment_id:
                    self.linkedin_delete_post(post_id)
                    return False, None
        link = f"https://www.linkedin.com/feed/update/{post_id}"
        return True, link
