""":mod:`libearth.defaults` --- Default data for initial state of apps
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This module provides small utilities and default data to fill initial state
of Earth Reader apps.

"""
try:
    import HTMLParser
except ImportError:
    from html import parser as HTMLParser

__all__ = 'BlogrollLinkParser',


class BlogrollLinkParser(HTMLParser.HTMLParser):
    """HTML parser that find all blogroll links."""

    SUPPORTED_TYPES = {
        'application/xml+opml': 15,
        'text/opml': 10, 'text/x-opml': 10,
        'application/xml': 5, 'text/xml': 5,
    }

    def __init__(self):
        HTMLParser.HTMLParser.__init__(self)
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag not in ('a', 'link'):
            return
        attrs = dict(attrs)
        if attrs.get('rel') != 'blogroll' or not attrs.get('href'):
            return
        self.links.append(
            (attrs.get('href'), attrs.get('type'), attrs.get('title'))
        )

    def get_link(self):
        if self.links:
            url, mimetype, title = max(
                self.links,
                key=lambda pair: self.SUPPORTED_TYPES.get(pair[1], 0)
            )
            return url, title and title.strip()
