""":mod:`libearth.parser.rss2` --- RSS 2.0 parser
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Parsing RSS 2.0 feed.

"""
try:
    import urllib2
except ImportError:
    import urllib.request as urllib2

try:
    from lxml import etree
except ImportError:
    try:
        from xml.etree import cElementTree as etree
    except ImportError:
        from xml.etree import ElementTree as etree

from ..codecs import Rfc822
from ..feed import (Category, Content, Entry, Feed, Generator, Link,
                    Person, Text)


def parse_rss(xml, feed_url=None, parse_entry=True):
    """Parse RSS 2.0 XML.

    :param xml: target rss 2.0 xml to parse
    :type xml: :class:`str`
    :param parse_item: whether to parse inner items as well.
                       it's useful to ignore items when retrieve
                       ``<source>``.  :const:`True` by default.
    :type parse_item: :class:`bool`
    :returns: a pair of (:class:`~libearth.feed.Feed`, crawler hint)
    :rtype: :class:`tuple`

    """
    root = etree.fromstring(xml)
    channel = root.find('channel')
    items = channel.findall('item')
    feed_data, crawler_hints = rss_get_channel_data(channel, feed_url)
    if parse_entry:
        feed_data.entries = rss_get_item_data(items)
        if feed_data.updated_at is None:
            feed_data.updated_at = max(
                entry.updated_at for entry in feed_data.entries
                                 if entry.updated_at
            )
    return feed_data, crawler_hints


def rss_get_channel_data(root, feed_url):
    feed_data = Feed(id=feed_url)
    feed_data.links.append(Link(relation='self', uri=feed_url))
    crawler_hints = {}
    contributors = []
    for data in root:
        if data.tag == 'title':
            feed_data.title = Text()
            feed_data.title.value = data.text
        elif data.tag == 'link':
            link = Link()
            link.uri = data.text
            link.relation = 'alternate'
            link.type = 'text/html'
            feed_data.links.append(link)
        elif data.tag == 'description':
            subtitle = Text()
            subtitle.type = 'text'
            subtitle.value = data.text
            feed_data.subtitle = subtitle
        elif data.tag == 'copyright':
            rights = Text()
            rights.value = data.text
            feed_data.rights = rights
        elif data.tag == 'managingEditor':
            contributor = Person()
            contributor.name = data.text
            contributor.email = data.text
            contributors.append(contributor)
            feed_data.contributors = contributors
        elif data.tag == 'webMaster':
            contributor = Person()
            contributor.name = data.text
            contributor.email = data.text
            contributors.append(contributor)
            feed_data.contributors = contributors
        elif data.tag == 'pubDate':
            feed_data.updated_at = Rfc822().decode(data.text)
        elif data.tag == 'category':
            category = Category()
            category.term = data.text
            feed_data.categories = [category]
        elif data.tag == 'generator':
            generator = Generator()
            generator.value = data.text
            feed_data.generator = generator
        elif data.tag == 'lastBuildDate':
            data_for_crawl['lastBuildDate'] = Rfc822().decode(data.text)
        elif data.tag == 'ttl':
            data_for_crawl['ttl'] = data.text
        elif data.tag == 'skipHours':
            data_for_crawl['skipHours'] = data.text
        elif data.tag == 'skipMinutes':
            data_for_crawl['skipMinutes'] = data.text
        elif data.tag == 'skipDays':
            data_for_crawl['skipDays'] = data.text
    return feed_data, data_for_crawl


def rss_get_item_data(entries):
    entries_data = []
    for entry in entries:
        entry_data = Entry()
        links = []
        for data in entry:
            if data.tag == 'title':
                title = Text()
                title.value = data.text
                entry_data.title = title
            elif data.tag == 'link':
                link = Link()
                link.uri = data.text
                link.relation = 'alternate'
                link.type = 'text/html'
                links.append(link)
                entry_data.links = links
            elif data.tag == 'description':
                content = Content()
                content.type = 'text'
                content.value = data.text
                entry_data.content = content
            elif data.tag == 'author':
                author = Person()
                author.name = data.text
                author.email = data.text
                entry_data.authors = [author]
            elif data.tag == 'category':
                category = Category()
                category.term = data.text
                entry_data.categories = [category]
            elif data.tag == 'comments':
                #entry_data['comments'] = data.text
                pass  # FIXME
            elif data.tag == 'enclosure':
                link = Link()
                link.type = data.get('type')
                link.uri = data.get('url')
                links.append(link)
                entry_data.links = links
            elif data.tag == 'guid':
                entry_data.id = data.text
            elif data.tag == 'pubDate':
                entry_data.published_at = Rfc822().decode(data.text)
                # TODO 'pubDate' is optional in RSS 2, but 'updated' in Atom
                #       is required element, so we have to fill some value to
                #       entry.updated_at.
            elif data.tag == 'source':
                from .heuristic import get_document_type
                url = data.get('url')
                request = urllib2.Request(url)
                f = urllib2.urlopen(request)
                xml = f.read()
                parser = get_document_type(xml)
                source, _ = parser(xml, parse_entry=False)
                entry_data.source = source
        if entry_data.updated_at is None:
            entry_data.updated_at = entry_data.published_at
        entries_data.append(entry_data)
    return entries_data
