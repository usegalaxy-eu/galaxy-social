import json
import os
import re
import time
from html.parser import HTMLParser
from io import BytesIO

import requests
from bs4 import BeautifulSoup
from markdown import markdown
from PIL import Image

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
BLUESKY_IMAGE_LIMIT = int(976.56 * 1024)
MAX_IMAGE_BYTES = 50 * 1024 * 1024
MIME_TYPES = {"JPEG": "image/jpeg", "PNG": "image/png", "GIF": "image/gif"}


# inspired by:
# https://stackoverflow.com/questions/14694482/
class HTMLFilter(HTMLParser):
    def __init__(self):
        self.text = ""
        self.href = ""
        self.li_count = 0
        self.inside_blockquote = False
        self.allow_line_break = False
        super().__init__()

    def handle_starttag(self, tag, attrs):
        if tag == "blockquote":
            self.inside_blockquote = True
            self.allow_line_break = False
        elif tag == "ol":
            if self.inside_blockquote:
                self.text += ">"
            self.li_count = 1
        elif tag == "ul":
            if self.inside_blockquote:
                self.text += ">"
            self.li_count = 0
        elif tag == "li":
            self.allow_line_break = False
            if self.inside_blockquote:
                self.text += "> "
            if self.li_count:
                self.text += f"{self.li_count}. "
                self.li_count += 1
            else:
                self.text += "- "
        elif tag == "p" or (tag[0]=="h" and tag[1].isdigit()):
            # add an empty line before paragraphs and headings
            # do blockquoting as needed
            if self.allow_line_break:
                if self.inside_blockquote:
                        p_sep = "\n>\n> "
                else:
                    p_sep = "\n\n"
            elif self.inside_blockquote:
                p_sep = "\n> "
            else:
                p_sep = ""
            self.text = self.text.rstrip("\n") + p_sep
        elif tag == "a":
            for name, value in attrs:
                if name == "href":
                    self.href = value
                    break

    def handle_endtag(self, tag):
        if tag == "a":
            self.text += f": {self.href}"
            self.href = ""
        elif tag == "blockquote":
            self.inside_blockquote = False
        self.allow_line_break = True

    def handle_data(self, data):
        if not self.allow_line_break:
            data = data.lstrip("\n")
        if self.inside_blockquote and data != "\n":
            # start internal new lines with a > too
            data = data.replace("\n", "\n> ")
        self.text += data


def strip_markdown_formatting(text):
    html_filter = HTMLFilter()
    html_filter.feed(markdown(text))
    return html_filter.text.strip('\n')


def image_format(content):
    """Return JPEG, PNG, GIF, WEBP or AVIF from the first bytes of a file, without opening it."""
    if content.startswith(b"\xff\xd8\xff"):
        return "JPEG"
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "PNG"
    if content.startswith((b"GIF87a", b"GIF89a")):
        return "GIF"
    if content.startswith(b"RIFF") and content[8:12] == b"WEBP":
        return "WEBP"
    if content[4:8] == b"ftyp":
        # AVIF: "avif" or "avis" as main brand or among the compatible brands of the ftyp box
        ftyp_end = int.from_bytes(content[:4], "big")
        brands = [content[8:12]] + [content[i:i + 4] for i in range(16, min(ftyp_end, len(content)), 4)]
        if b"avif" in brands or b"avis" in brands:
            return "AVIF"
    return None


def to_supported_image(content):
    """Return image bytes as JPEG, PNG or GIF, converting AVIF and WebP.

    Only the AVIF or WebP decoder is used, and only for files that start like one.
    Raises an error for anything else.
    """
    image_type = image_format(content)
    if image_type in ["JPEG", "PNG", "GIF"]:
        return content
    if image_type not in ["AVIF", "WEBP"]:
        raise ValueError("Not a JPEG, PNG, GIF, AVIF or WebP image")
    image = Image.open(BytesIO(content), formats=[image_type])
    output = BytesIO()
    if image.mode in ["RGBA", "LA", "PA"] or "transparency" in image.info:
        image.convert("RGBA").save(output, "PNG")
    else:
        image.convert("RGB").save(output, "JPEG", quality=90)
    return output.getvalue()


def download_image(url):
    """Download at most MAX_IMAGE_BYTES, and give up after two minutes."""
    deadline = time.monotonic() + 120
    content = bytearray()
    with requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30, stream=True) as response:
        response.raise_for_status()
        for chunk in response.iter_content(chunk_size=None):  # data as it arrives
            content += chunk
            if len(content) > MAX_IMAGE_BYTES:
                raise ValueError("Image is larger than 50 MB")
            if time.monotonic() > deadline:
                raise TimeoutError("Image download took longer than two minutes")
    return bytes(content)


def link_image_url(page_url):
    """The og:image of a linked page, as Bluesky's link card uses it, or None."""
    try:
        response = requests.get(page_url, timeout=30)
        if response.status_code != 200:
            return None
        tag = BeautifulSoup(response.text, "html.parser").find("meta", attrs={"property": "og:image"})
        image_url = tag.attrs.get("content") if tag and hasattr(tag, "attrs") else None
        return image_url if isinstance(image_url, str) and image_url.startswith(("http://", "https://")) else None
    except Exception:
        return None


def shrink_to_limit(content, limit):
    """Save the image as JPEG with lower quality until it fits the limit, or return None."""
    image = Image.open(BytesIO(content), formats=[image_format(content)]).convert("RGB")
    for quality in range(95, 5, -5):
        output = BytesIO()
        image.save(output, "JPEG", quality=quality)
        if output.tell() <= limit:
            return output.getvalue()
    return None


def prepare_images(urls, folder):
    """Download and convert images in the job without tokens, for load_image in the job that posts.

    Writes one file per image (and a smaller copy for Bluesky when needed) and a manifest.json.
    """
    os.makedirs(folder, exist_ok=True)
    manifest = {}
    for index, url in enumerate(dict.fromkeys(urls)):
        try:
            content = to_supported_image(download_image(url))
            width, height = Image.open(BytesIO(content), formats=[image_format(content)]).size
            entry = {"file": str(index), "width": width, "height": height}
            with open(os.path.join(folder, entry["file"]), "wb") as f:
                f.write(content)
            if len(content) > BLUESKY_IMAGE_LIMIT:
                small = shrink_to_limit(content, BLUESKY_IMAGE_LIMIT)
                if small:
                    entry["small"] = f"{index}-small"
                    with open(os.path.join(folder, entry["small"]), "wb") as f:
                        f.write(small)
            manifest[url] = entry
        except Exception as e:
            print(f"Could not prepare image {url}: {type(e).__name__}: {e}")
            manifest[url] = {"error": f"{type(e).__name__}: {e}"}
    with open(os.path.join(folder, "manifest.json"), "w") as f:
        json.dump(manifest, f)


def prepared_manifest():
    """The manifest of the prepare job, or None when images are not prepared (previews, local runs)."""
    folder = os.environ.get("PREPARED_IMAGES")
    if not folder:
        return None
    with open(os.path.join(folder, "manifest.json")) as f:
        return json.load(f)


def load_image(url, small=False):
    """Return the image to post as {"content", "mime", "width", "height"}.

    In the workflow the files come from the prepare job. This runs with the tokens, so the files
    are only checked (name, size, first bytes) and never opened. With small=True the smaller copy
    for Bluesky is used when there is one.
    """
    manifest = prepared_manifest()
    if manifest is None:
        if os.environ.get("GITHUB_ACTIONS"):
            raise ValueError("Images must be prepared by the prepare_images job")
        # local run: download and convert here
        content = to_supported_image(download_image(url))
        if small and len(content) > BLUESKY_IMAGE_LIMIT:
            content = shrink_to_limit(content, BLUESKY_IMAGE_LIMIT) or content
        width, height = Image.open(BytesIO(content), formats=[image_format(content)]).size
        return {"content": content, "mime": MIME_TYPES[image_format(content)], "width": width, "height": height}

    entry = manifest.get(url)
    if not isinstance(entry, dict) or "file" not in entry:
        raise ValueError(entry.get("error", "not prepared") if isinstance(entry, dict) else "not prepared")
    name = entry.get("small") if small and entry.get("small") else entry["file"]
    # the prepare job handled untrusted files, so its output is not trusted either
    if not re.fullmatch(r"[0-9]+(-small)?", str(name)):
        raise ValueError(f"Unexpected prepared file name: {name!r}")
    path = os.path.join(os.environ["PREPARED_IMAGES"], name)
    if os.path.getsize(path) > MAX_IMAGE_BYTES:
        raise ValueError("Prepared image is too large")
    with open(path, "rb") as f:
        content = f.read()
    mime = MIME_TYPES.get(image_format(content))
    if not mime:
        raise ValueError("Prepared file is not a JPEG, PNG or GIF image")
    size = [entry.get("width"), entry.get("height")]
    if not all(isinstance(n, int) and 0 < n < 100000 for n in size):
        size = [None, None]
    return {"content": content, "mime": mime, "width": size[0], "height": size[1]}

