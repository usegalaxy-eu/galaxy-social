from html.parser import HTMLParser

from markdown import markdown


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
