""":mod:`libearth.sanitizer` --- Sanitize HTML tags
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

"""
try:
    import htmlentitydefs
    import HTMLParser
except ImportError:
    from html import entities as htmlentitydefs, parser as HTMLParser

from .compat import unichr

__all__ = 'MarkupTagCleaner', 'clean_html'


def clean_html(html):
    """Strip *all* markup tags from ``html`` string.
    That means, it simply makes the given ``html`` document a plain text.

    """
    parser = MarkupTagCleaner()
    parser.feed(html)
    return ''.join(parser.fed)


class MarkupTagCleaner(HTMLParser.HTMLParser):
    """HTML parser that is internally used by :func:`clean_html()` function."""

    entity_map = htmlentitydefs.name2codepoint

    def __init__(self):
        HTMLParser.HTMLParser.__init__(self)
        self.fed = []

    def handle_data(self, d):
        self.fed.append(d)

    def handle_entityref(self, name):
        try:
            codepoint = self.entity_map[name]
        except KeyError:
            pass
        else:
            self.fed.append(unichr(codepoint))

    def handle_charref(self, name):
        if name.startswith('x'):
            codepoint = int(name[1:], 16)
        else:
            codepoint = int(name)
        self.fed.append(unichr(codepoint))
