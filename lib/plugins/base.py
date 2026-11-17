from html.parser import HTMLParser
from io import BytesIO

from markdown import markdown
from PIL import Image


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
