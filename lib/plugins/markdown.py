import os
import time


class markdown_client:
    def __init__(self, **kwargs):
        self.save_path = (
            os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "..",
                "..",
                kwargs.get("save_path"),
            )
            if "save_path" in kwargs
            else None
        )

    def create_post(self, content, mentions, hashtags, images, **kwargs):
        try:
            medias = "\n".join(
                [f'![{image.get("alt_text", "")}]({image["url"]})' for image in images]
            )
            mentions = " ".join([f"@{v}" for v in mentions])
            hashtags = " ".join([f"#{v}" for v in hashtags])
            text = f"{content}\n{mentions}\n{hashtags}\n{medias}"
            if self.save_path:
                os.makedirs(self.save_path, exist_ok=True)
                with open(
                    f"{self.save_path}/{time.strftime('%Y%m%d-%H%M%S')}.md", "w"
                ) as f:
                    f.write(text)
            if kwargs.get("preview"):
                social_media = ", ".join(kwargs.get("media"))
                comment_text = f"This is a preview that will be posted to {social_media}:\n\n{text}"
                return True, None, comment_text
            return True, None
        except Exception as e:
            print(e)
            return False, None
