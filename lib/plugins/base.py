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
MAX_IMAGE_BYTES = 50 * 1024 * 1024
TARGET_IMAGE_SIZES = [16 * 10 ** 6, 10 ** 6]
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
    """Return JPEG, PNG, GIF, WEBP, AVIF or SVG from the first bytes of a file, without opening it."""
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
    # SVG is text: the first element, after an XML declaration, comments or a doctype, is <svg
    head = re.sub(rb"^(\s+|<\?xml[^>]*>|<!--.*?-->|<!DOCTYPE[^>]*>)+", b"", content[:4096].removeprefix(b"\xef\xbb\xbf"), flags=re.S)
    if re.match(rb"<svg[\s>]", head):
        return "SVG"
    return None


def to_supported_image(content):
    """Return image bytes as JPEG, PNG or GIF, converting AVIF, WebP and SVG.

    Only the AVIF, WebP or SVG decoder is used, and only for files that start like one.
    Raises an error for anything else.
    """
    image_type = image_format(content)
    if image_type in ["JPEG", "PNG", "GIF"]:
        return content
    if image_type == "SVG":
        import cairosvg  # needs the Cairo system library

        # 1600 px wide like a photo; CairoSVG does not load files or URLs the SVG links to
        return cairosvg.svg2png(bytestring=content, output_width=1600)
    if image_type not in ["AVIF", "WEBP"]:
        raise ValueError("Not a JPEG, PNG, GIF, AVIF, WebP or SVG image")
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


def shrink_to_limits(content, limits):
    """Yields the image content as JPEG with progessively lower quality.

    With an original content size > max(limits) it will try to generate for
    each limit at least one image that is smaller than the limit, and a maximum
    of len(limits) images in total."""

    image = Image.open(BytesIO(content), formats=[image_format(content)]).convert("RGB")
    limits = sorted(limits)
    limit = limits.pop()
    current_size = len(content)
    for quality in range(95, 0, -5):
        while limits and current_size <= limit:
            limit = limits.pop()
        if current_size <= limit:
            return
        output = BytesIO()
        image.save(output, "JPEG", quality=quality)
        current_size = output.tell()
        if current_size <= limit:
            yield output.getvalue()


def prepare_images(urls, folder):
    """Download and convert images (in the workflow: in a job without tokens) for load_image.

    Writes at least one file per image, possibly smaller variants of it to
    satisfy size limits of different platforms, and a manifest.json.
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
            if len(content) > min(TARGET_IMAGE_SIZES):
                entry["small"] = []
                for n, lowq in enumerate(shrink_to_limits(content, TARGET_IMAGE_SIZES)):
                    entry["small"].append(f"{index}-{n}")
                    with open(os.path.join(folder, entry["small"][-1]), "wb") as f:
                        f.write(lowq)
            manifest[url] = entry
        except Exception as e:
            print(f"Could not prepare image {url}: {type(e).__name__}: {e}")
            manifest[url] = {"error": f"{type(e).__name__}: {e}"}
    with open(os.path.join(folder, "manifest.json"), "w") as f:
        json.dump(manifest, f)


def read_manifest(folder):
    """The manifest of prepared images in folder, or None if preparing them failed (no manifest)."""
    try:
        with open(os.path.join(folder, "manifest.json")) as f:
            return json.load(f)
    except FileNotFoundError:
        return None


def load_image(url, folder=None, max_size=MAX_IMAGE_BYTES):
    """Return the image to post as {"content", "mime", "width", "height"}.

    Without folder the image is downloaded and converted here. With the folder of prepare_images
    (as in the workflow, where this runs with the tokens) the files are only checked (name, size,
    first bytes) and never opened.
    """
    if folder is None:
        content = to_supported_image(download_image(url))
        if len(content) > max_size:
            # try to shrink the content; use unchanged if shrinking fails
            try:
                content = next(shrink_to_limits(content, [max_size]))
            except StopIteration:
                pass
        width, height = Image.open(BytesIO(content), formats=[image_format(content)]).size
        return {"content": content, "mime": MIME_TYPES[image_format(content)], "width": width, "height": height}

    manifest = read_manifest(folder)
    if manifest is None:
        raise ValueError("Images could not be prepared")
    entry = manifest.get(url)
    if not isinstance(entry, dict) or "file" not in entry:
        raise ValueError(entry.get("error", "not prepared") if isinstance(entry, dict) else "not prepared")
    names = [entry["file"]] + entry.get("small", [])
    for name in names:
        # the prepare job handled untrusted files, so its output is not trusted either
        if not re.fullmatch(r"[0-9]+(-[0-9]+)?", str(name)):
            raise ValueError(f"Unexpected prepared file name: {name!r}")
        path = os.path.join(folder, name)
        if os.path.getsize(path) <= max_size:
            break
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
