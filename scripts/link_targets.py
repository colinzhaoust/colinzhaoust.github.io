"""Apply consistent link targets without reformatting the page or its comments."""
from html import escape
from html.parser import HTMLParser
import re
from urllib.parse import urlsplit

SITE_HOST = 'colinzhaoust.github.io'


def normalize_links(source):
    class Links(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=False)
            self.edits = []
            self.lines = [0]
            for match in re.finditer(r'\n', source):
                self.lines.append(match.end())

        def handle_starttag(self, tag, attrs):
            attributes = dict(attrs)
            raw = self.get_starttag_text()
            line, column = self.getpos()
            start = self.lines[line - 1] + column
            if tag == 'base' and 'target' in attributes:
                # Legacy used a blanket target, which also affected local navigation.
                if 'href' not in attributes:
                    line_start = self.lines[line - 1]
                    remove_from = line_start if not source[line_start:start].strip() else start
                    self.edits.append((remove_from, start + len(raw), ''))
                return
            if tag != 'a' or not attributes.get('href'):
                return
            url = urlsplit(attributes['href'].strip())
            external = (url.scheme.lower() in ('http', 'https') or bool(url.netloc)) and url.hostname != SITE_HOST
            pdf = url.path.lower().endswith('.pdf') and url.scheme.lower() in ('', 'http', 'https')
            new_tab = external or pdf
            updated = re.sub(r'''\s+target\s*=\s*(?:"[^"]*"|'[^']*'|[^\s>]+)''', '', raw, flags=re.I)
            if new_tab:
                updated = re.sub(r'''\s+rel\s*=\s*(?:"[^"]*"|'[^']*'|[^\s>]+)''', '', updated, flags=re.I)
                rel = list(dict.fromkeys((attributes.get('rel') or '').split() + ['noopener', 'noreferrer']))
                updated = updated[:-1] + f' target="_blank" rel="{escape(" ".join(rel), quote=True)}">'
            if updated != raw:
                self.edits.append((start, start + len(raw), updated))

    parser = Links()
    parser.feed(source)
    for start, end, replacement in reversed(parser.edits):
        source = source[:start] + replacement + source[end:]
    return source
