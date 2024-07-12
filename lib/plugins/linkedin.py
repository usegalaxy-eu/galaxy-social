import os
import re
import textwrap
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup
from markdown import markdown


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

    def format_content(self, content, mentions, hashtags, images, **kwargs):
        # the mentions are not linked to anyone!
        mentions = " ".join([f"@{v}" for v in mentions])
        hashtags = " ".join([f"#{v}" for v in hashtags])
        if len(images) > 20:
            warnings = f"A maximum of 20 images, not {len(images)}, can be included in a single linkedin post."
            images = images[:20]
        else:
            warnings = ""

        # convert markdown formatting because Mastodon doesn't support it
        paragraphs = content.split("\n\n\n")
        for i, p in enumerate(paragraphs):
            soup = BeautifulSoup(markdown(p), "html.parser")
            for link in soup.find_all("a"):
                link.string = f"{link.string}: {link['href']}"
            paragraphs[i] = "\n\n".join([p.get_text() for p in soup.find_all("p")])
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

    def linkedin_post(self, content, images):
        try:
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
                if not data["content"]:
                    return None
            headers = self.headers
            headers["Content-Type"] = "application/json"
            response = requests.post(
                f"{self.api_base_url}/posts", headers=headers, json=data
            )
            response.raise_for_status()
            return response.headers.get("x-restli-id")
        except Exception as e:
            print(str(e))
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
                with requests.get(image["url"], stream=True) as r:
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
            print(str(e))
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
            print(str(e))
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
            print(str(e))
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
