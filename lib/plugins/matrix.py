import asyncio
import tempfile

import aiofiles.os
import magic
import requests
from nio import AsyncClient, UploadResponse
from PIL import Image


class matrix_client:

    def __init__(self, **kwargs):
        self.base_url = kwargs.get("base_url", "https://matrix.org")
        self.client = AsyncClient(self.base_url)
        self.client.access_token = kwargs.get("access_token")
        self.client.user_id = kwargs.get("user_id")
        self.client.device_id = kwargs.get("device_id")
        self.room_id = kwargs.get("room_id")

    async def async_create_post(self, text, mentions, images):
        for image in images:
            response = requests.get(image["url"])
            if response.status_code != 200:
                continue
            image_name = image["url"].split("/")[-1]
            temp = tempfile.NamedTemporaryFile()
            temp.write(response.content)
            temp.flush()
            mime_type = magic.from_file(temp.name, mime=True)
            if not mime_type.startswith("image/"):
                continue

            width, height = Image.open(temp.name).size
            file_stat = await aiofiles.os.stat(temp.name)
            async with aiofiles.open(temp.name, "r+b") as f:
                resp, _ = await self.client.upload(
                    f,
                    content_type=mime_type,
                    filename=image_name,
                    filesize=file_stat.st_size,
                )

            if not isinstance(resp, UploadResponse):
                continue

            content = {
                "body": image_name,
                "info": {
                    "size": file_stat.st_size,
                    "mimetype": mime_type,
                    "thumbnail_info": None,
                    "w": width,
                    "h": height,
                    "thumbnail_url": None,
                },
                "msgtype": "m.image",
                "url": resp.content_uri,
            }

            try:
                await self.client.room_send(
                    self.room_id, message_type="m.room.message", content=content
                )
            except:
                return False, None

        if mentions:
            text = (
                text
                + "\n\n"
                + " ".join([f"https://matrix.to/#/@{mention}" for mention in mentions])
            )
        content = {
            "msgtype": "m.text",
            "format": "org.matrix.custom.html",
            "body": text,
        }
        try:
            response = await self.client.room_send(
                self.room_id, message_type="m.room.message", content=content
            )
            await self.client.close()
            message_id = response.event_id
            link = f"https://matrix.to/#/{self.room_id}/{message_id}"
        except:
            return False, None

        return True, link

    def create_post(self, content, mentions, hashtags, images, **kwargs):
        # hashtags and alt_texts are not used in this function
        result, link = asyncio.run(self.async_create_post(content, mentions, images))
        return result, link
