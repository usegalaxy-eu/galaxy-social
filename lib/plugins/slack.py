import textwrap

import requests
from slack_sdk import WebClient


class slack_client:
    def __init__(self, **kwargs):
        self.client = WebClient(token=kwargs.get("access_token"))
        self.channel_id = kwargs.get("channel_id")
        self.max_content_length = kwargs.get("max_content_length", 40000)

    def upload_images(self, images):
        uploaded_files = []
        for image in images:
            filename = image["url"].split("/")[-1]

            with requests.get(image["url"]) as response:
                if response.status_code != 200 or not response.headers.get(
                    "Content-Type", ""
                ).startswith("image/"):
                    continue
                image_content = response.content

            response = self.client.files_getUploadURLExternal(
                filename=filename,
                length=len(image_content),
                alt_txt=image["alt_text"] if "alt_text" in image else None,
            )

            with requests.post(
                response["upload_url"], files={"file": image_content}
            ) as upload_response:
                if upload_response.status_code != 200:
                    continue
            uploaded_files.append({"id": response["file_id"]})

        response = self.client.files_completeUploadExternal(
            files=uploaded_files, channel_id=self.channel_id
        )
        return response

    def create_post(self, text, mentions, hashtags, images, **kwargs):
        status = []
        link = None
        parent_ts = None
        for text in textwrap.wrap(
            text,
            self.max_content_length,
            replace_whitespace=False,
        ):
            response = self.client.chat_postMessage(
                channel=self.channel_id,
                text=text,
                thread_ts=parent_ts if parent_ts else None,
            )
            if not parent_ts:
                parent_ts = response["ts"]
                link = self.client.chat_getPermalink(
                    channel=self.channel_id, message_ts=parent_ts
                )["permalink"]
            status.append(response["ok"])
        if images:
            response = self.upload_images(images)
            status.append(response["ok"])
        return all(status), link
