from html.parser import HTMLParser

from markdown import markdown


class HTMLFilter(HTMLParser):
    text = ""
    href = ""
    li_count = 0

    def handle_starttag(self, tag, attrs):
        if tag == "ol":
            self.li_count = 1
        elif tag == "ul":
            self.li_count = 0
        elif tag == "li":
            if self.li_count:
                self.text += f"{self.li_count}. "
                self.li_count += 1
            else:
                self.text += "- "
        elif tag == "p":
            self.text = self.text.rstrip('\n') + "\n\n"
        elif tag == "a":
            for name, value in attrs:
                if name == "href":
                    self.href = value
                    break

    def handle_endtag(self, tag):
        if tag == "a":
            self.text += f": {self.href}"
            self.href = ""

    def handle_data(self, data):
        self.text += data


def strip_markdown_formatting(text):
    html_filter = HTMLFilter()
    html_filter.feed(markdown(text))
    return html_filter.text
