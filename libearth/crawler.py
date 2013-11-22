""":mod:`libearth.crawler` --- Crawler
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Crawl feeds.

"""
try:
    import concurrent.futures
except ImportError:
    concurrent = None
    import multiprocessing.pool
import logging
import sys
try:
    import urllib.request as urllib2
except ImportError:
    import urllib2

from .feed import Link
from .parser.heuristic import get_format

__all__ = 'crawl',


class crawl(object):
    """Crawl feeds in feed list using thread.

    .. note::

       It will not crawl feeds unless iterate the generator.

    :param feeds: feeds
    :type feeds: :class: `collections.Sequence`
    :returns: set of pairs (`~libearth.feed.Feed`, crawler hint)
    :rtype: :class:`collections.Iterable`

    """

    __slots__ = 'pool', 'async_results'

    def __init__(self, feeds, pool_size):
        if concurrent:
            self.pool = concurrent.futures.ThreadPoolExecutor(
                max_workers=pool_size
            )
            self.async_results = self.pool.map(get_feed, feeds)
        else:
            self.pool = multiprocessing.pool.ThreadPool(pool_size)
            self.async_results = self.pool.imap_unordered(get_feed, feeds)

    def __iter__(self):
        for result in self.async_results:
            yield result
        if concurrent:
            self.pool.shutdown()
        else:
            self.pool.close()
            self.pool.join()


def get_feed(feed_url):
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
    '''Error which rises when crawling given url failed.'''
