""":mod:`libearth.defaults` --- Default data for initial state of apps
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. versionadded:: 0.4.0

This module provides small utilities and default data to fill initial state
of Earth Reader apps.

"""
try:
    import HTMLParser
except ImportError:
    from html import parser as HTMLParser
import io
import re
try:
    import urllib.request as urllib2
except ImportError:
    import urllib2
try:
    import urllib.parse as urlparse
except ImportError:
    import urlparse

from .compat import UNICODE_BY_DEFAULT
from .subscribe import SubscriptionList
from .schema import complete, read

__all__ = ('DEFAULT_BLOGROLL_URL', 'BlogrollLinkParser',
           'get_default_subscriptions')


# (:class:`str`) The url to blogroll OPML, or HTML page which links that.
DEFAULT_BLOGROLL_URL = 'http://earthreader.org/'


def get_default_subscriptions(blogroll_url=DEFAULT_BLOGROLL_URL):
    """Suggest the default set of subscriptions.  The blogroll database
    will be remotely downloaded from `Earth Reader website`__.

    >>> subs = get_default_subscriptions()
    >>> subs
    <libearth.subscribe.SubscriptionList
        'Feeds related to the Earth Reader project'
        of Earth Reader Team <earthreader@librelist.com>>

    :param blogroll_url: the url to download blogroll opml.
                         default is the official website of earth reader
    :type blogroll_url: :class:`str`
    :returns: the default subscription list
    :rtype: :class:`~.subscribe.SubscriptionList`

    __ http://earthreader.org/

    """
    response = urllib2.urlopen(blogroll_url)
    content_type = response.headers['content-type']
    match = re.match(r'^\s*[^;/\s]+/[^;/\s]+', content_type)
    mimetype = match and match.group(0)
    if mimetype not in BlogrollLinkParser.SUPPORTED_TYPES:
        parser = BlogrollLinkParser()
        copy = io.StringIO() if UNICODE_BY_DEFAULT else io.BytesIO()
        while 1:
            chunk = response.read(1024)
            if chunk:
                parser.feed(chunk)
                copy.write(chunk)
            else:
                break
        pair = parser.get_link()
        response.close()
        if pair is None:
            copy.seek(0)
            response = copy
        else:
            copy.close()
            url = urlparse.urljoin(response.url, pair[0])
            response = urllib2.urlopen(url)
    subscriptions = read(SubscriptionList, response)
    complete(subscriptions)
    response.close()
    return subscriptions


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
