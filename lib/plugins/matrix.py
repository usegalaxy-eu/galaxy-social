import asyncio
import mimetypes
import os
import tempfile
import traceback

import aiofiles.os
from bs4 import BeautifulSoup
from markdown import markdown
from nio import AsyncClient, UploadResponse  # type: ignore

from .base import load_image


class matrix_client:
    def __init__(self, **kwargs):
        self.base_url = kwargs.get("base_url", "https://matrix.org")
        self.client = AsyncClient(self.base_url)
        self.client.access_token = kwargs.get("access_token")
        self.room_id = kwargs.get("room_id")
        self.runner = asyncio.Runner()

    async def async_format_content(self, content, mentions, hashtags, images, **kwargs):
        formatted_content = []
        preview = ""
        for image in images:
            preview += f'![{image.get("alt_text", "")}]({image["url"]})\n'
            image_name = image["url"].split("/")[-1]
            formatted_content.append(
                {
                    "body": image.get("alt_text", image_name),
                    "filename": image_name,
                    "msgtype": "m.image",
                    "url": image["url"],
                }
            )
        message_content = {
            "msgtype": "m.text",
            "format": "org.matrix.custom.html",
        }

        # matrix specs say the body fallback should contain the displayname
        # we add the mentions as markdown links in front of the supplied content,
        # then we convert to html to get the "formatted_body", then to text to get "body"
        if mentions:
            message_content["m.mentions"] = {"user_ids": []}
            mention_links = []
            for mention in mentions:
                # try to get the display name of the mentioned matrix user
                response = await self.client.get_displayname(f"@{mention}")
                mention_name = getattr(response, "displayname", mention)
                mention_links.append(
                    f"[{mention_name}](https://matrix.to/#/@{mention})"
                )
                message_content["m.mentions"]["user_ids"].append(f"@{mention}")
            mentions_string = " ".join(mention_links)
            content = f"{mentions_string}: {content}"
        if hashtags:
            content += "\n\n" + " ".join([f"\\#{h}" for h in hashtags])
        formatted_body = markdown(content)
        body = BeautifulSoup(formatted_body, features="html.parser").get_text(
            "\n", strip=True
        )
        message_content["body"] = body
        message_content["formatted_body"] = formatted_body
        formatted_content.append(message_content)
        warnings = ""
        await self.client.close()
        return (
            formatted_content,
            preview + "\n" + message_content["formatted_body"],
            warnings,
        )

    async def async_create_post(self, content, prepared_images=None):
        posts = []
        for msg in content:
            try:
                if msg["msgtype"] == "m.image":
                    image = load_image(msg["url"], prepared_images)
                    mime_type = image["mime"]
                    temp = tempfile.NamedTemporaryFile()
                    temp.write(image["content"])
                    temp.flush()

                    filename = msg["filename"]
                    correct_ext = mimetypes.guess_extension(mime_type)
                    if correct_ext:
                        base_name, ext = os.path.splitext(filename)
                        if ext.lower() != correct_ext.lower():
                            filename = f"{base_name}{correct_ext}"

                    file_stat = await aiofiles.os.stat(temp.name)
                    async with aiofiles.open(temp.name, "r+b") as f:
                        resp, _ = await self.client.upload(
                            f,
                            content_type=mime_type,
                            filename=filename,
                            filesize=file_stat.st_size,
                        )

                    if not isinstance(resp, UploadResponse):
                        raise Exception(f"Image upload failed: {resp}")

                    # add info about the image to the message
                    msg["info"] = {"size": file_stat.st_size, "mimetype": mime_type}
                    if image["width"]:
                        msg["info"].update(w=image["width"], h=image["height"])
                    # replace original image url with that of the server upload
                    msg["url"] = resp.content_uri

                post = await self.client.room_send(
                    self.room_id, message_type="m.room.message", content=msg
                )
                posts.append(post.event_id)
            except Exception as e:
                print(f"Matrix error: {e}")
                traceback.print_exc()
                for post in posts:
                    await self.client.room_redact(
                        self.room_id, post, "Failed to post completely!"
                    )
                return False, None

        await self.client.close()
        event_link = f"https://matrix.to/#/{self.room_id}/{posts[-1]}"
        return True, event_link

    def format_content(self, content, *args, **kwargs):
        content = content.replace("\n" * 3, "\n" * 2)
        result = self.runner.run(self.async_format_content(content, *args, **kwargs))
        return result

    def create_post(self, content, **kwargs):
        # hashtags and alt_texts are not used in this function
        result = self.runner.run(self.async_create_post(content, kwargs.get("prepared_images")))
        return result
