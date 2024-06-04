import os
import time


class markdown_client:
    def __init__(self, **kwargs):
        self.save_path = kwargs.get("save_path") and (
            kwargs["save_path"]
            if os.path.isabs(kwargs["save_path"])
            else os.path.join(os.getcwd(), kwargs["save_path"])
        )

    def format_content(self, content, mentions, hashtags, images, **kwargs):
        _images = "\n".join(
            [f'![{image.get("alt_text", "")}]({image["url"]})' for image in images]
        )
        mentions = " ".join([f"@{v}" for v in mentions])
        hashtags = " ".join([f"#{v}" for v in hashtags])
        warnings = ""
        formatted_content = "\n\n".join([content, mentions, hashtags, _images])
        preview = formatted_content
        return formatted_content, preview, warnings

    def create_post(self, formatted_content, **kwargs):
        try:
            if self.save_path:
                os.makedirs(self.save_path, exist_ok=True)
                prefix = kwargs.get("file_path", "").replace(".md", "")
                file_name = f"{self.save_path}/{prefix.replace('/', '-')}_{time.strftime('%Y%m%d-%H%M%S')}.md"
                with open(file_name, "w") as f:
                    f.write(formatted_content)
            return True, None
        except Exception as e:
            print(e)
            return False, None
