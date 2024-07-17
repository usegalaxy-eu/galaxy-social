from html.parser import HTMLParser

from markdown import markdown


# inspired by:
# https://stackoverflow.com/questions/14694482/
class HTMLFilter(HTMLParser):
    text = ""
    href = ""
    li_count = 0
    inside_blockquote = False
    last_start_tag = ""

    def handle_starttag(self, tag, attrs):
        if tag == "blockquote":
            self.inside_blockquote = True
        elif tag == "ol":
            if self.inside_blockquote:
                self.text += ">"
            self.li_count = 1
        elif tag == "ul":
            if self.inside_blockquote:
                self.text += ">"
            self.li_count = 0
        elif tag == "li":
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
            if self.inside_blockquote:
                if self.last_start_tag == "blockquote":
                    p_sep = "\n\n> "
                else:
                    p_sep = "\n>\n> "
            else:
                p_sep = "\n\n"
            self.text = self.text.rstrip("\n") + p_sep
        elif tag == "a":
            for name, value in attrs:
                if name == "href":
                    self.href = value
                    break
        self.last_start_tag = tag

    def handle_endtag(self, tag):
        if tag == "a":
            self.text += f": {self.href}"
            self.href = ""
        elif tag == "blockquote":
            self.inside_blockquote = False

    def handle_data(self, data):
        self.text += data


def strip_markdown_formatting(text):
    html_filter = HTMLFilter()
    html_filter.feed(markdown(text))
    return html_filter.text
