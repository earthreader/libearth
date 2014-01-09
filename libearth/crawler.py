""":mod:`libearth.crawler` --- Crawler
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Crawl feeds.

"""
import logging


try:
    import urllib.request as urllib2
except ImportError:
    import urllib2

from .compat.parallel import parallel_map
from .feed import Link
from .parser.autodiscovery import get_format


__all__ = 'crawl', 'get_feed'


def crawl(feeds, pool_size):
    """Crawl feeds in feed list using thread.

    :param feeds: feeds
    :type feeds: :class: `collections.Sequence`
    :returns: set of pairs (`~libearth.feed.Feed`, crawler hint)
    :rtype: :class:`collections.Iterable`

    """
    return parallel_map(pool_size, get_feed, feeds)


def get_feed(feed_url):
    # TODO: should be documented
    try:
        f = urllib2.urlopen(feed_url)
        feed_xml = f.read()
        parser = get_format(feed_xml)
        feed, crawler_hints = parser(feed_xml, feed_url)
        self_uri = None
        for link in feed.links:
            if link.relation == 'self':
                self_uri = link.uri
        if not self_uri:
            feed.links.append(Link(relation='self', uri=feed_url,
                                   mimetype=f.info()['content-type']))
        feed.entries = sorted(feed.entries, key=lambda entry: entry.updated_at,
                              reverse=True)
        return feed_url, feed, crawler_hints
    except Exception as e:
        logging.getLogger(__name__ + '.get_feed').exception(e)
        raise CrawlError('{0} failed: {1}'.format(feed_url, e))


class CrawlError(IOError):
    """Error which rises when crawling given url failed."""
