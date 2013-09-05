""":mod:`libearth.feed` --- Feeds
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:mod:`libearth` internally stores archive data as Atom format.  It's exactly
not a complete set of :rfc:`4287`, but a subset of the most of that.
Since it's not intended for crawling but internal representation, it does not
follow robustness principle or such thing.  It simply treats stored data are
all valid and well-formed.

"""
try:
    import HTMLParser
except ImportError:
    from html import parser as HTMLParser

__all__ = 'MarkupTagCleaner',


class MarkupTagCleaner(HTMLParser.HTMLParser):
    """Strip all markup tags from HTML string."""

    @classmethod
    def clean(cls, html):
        parser = cls()
        parser.feed(html)
        return ''.join(parser.fed)

    def __init__(self):
        HTMLParser.HTMLParser.__init__(self)
        self.fed = []

    def handle_data(self, d):
        self.fed.append(d)
