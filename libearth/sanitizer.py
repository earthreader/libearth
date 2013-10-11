""":mod:`libearth.sanitizer` --- Sanitize HTML tags
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

"""
try:
    import HTMLParser
except ImportError:
    from html import parser as HTMLParser

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

    def __init__(self):
        HTMLParser.HTMLParser.__init__(self)
        self.fed = []

    def handle_data(self, d):
        self.fed.append(d)
