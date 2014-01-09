""":mod:`libearth.parser.rss2` --- RSS 2.0 parser
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Parsing RSS 2.0 feed.

"""
import logging
import re

try:
    import urllib2
except ImportError:
    import urllib.request as urllib2

from ..codecs import Rfc822
from ..compat.etree import fromstring
from ..feed import (Category, Content, Entry, Feed, Generator, Link,
                    Person, Text)
from ..tz import now


GUID_PATTERN = re.compile('^(\{{0,1}([0-9a-fA-F]){8}-([0-9a-fA-F]){4}-([0-9'
                          'a-fA-F]){4}-([0-9a-fA-F]){4}-([0-9a-fA-F]){12}\}'
                          '{0,1})$')
CONTENT_XMLNS = '{http://purl.org/rss/1.0/modules/content/}'


def parse_rss(xml, feed_url=None, parse_entry=True):
    """Parse RSS 2.0 XML and translate it into Atom.

    To make the feed data valid in Atom format, ``id`` and ``link[rel=self]``
    fields would become the url of the feed.

    If ``pubDate`` is not present, ``updated`` field will be from
    the latest entry's ``updated`` time, or the time it's crawled instead.

    :param xml: rss 2.0 xml string to parse
    :type xml: :class:`str`
    :param parse_item: whether to parse items (entries) as well.
                       it's useful when to ignore items when retrieve
                       ``<source>``.  :const:`True` by default
    :type parse_item: :class:`bool`
    :returns: a pair of (:class:`~libearth.feed.Feed`, crawler hint)
    :rtype: :class:`tuple`

    """
    root = fromstring(xml)
    channel = root.find('channel')
    items = channel.findall('item')
    feed_data, crawler_hints = rss_get_channel_data(channel, feed_url)
    if parse_entry:
        feed_data.entries = rss_get_item_data(items)
    check_valid_as_atom(feed_data)
    return feed_data, crawler_hints


def check_valid_as_atom(feed_data):
    # FIXME: It doesn't only "check" the feed_data but manipulates it
    # if not valid.  I think the function should be renamed.
    if feed_data.updated_at is None:
        if feed_data.entries:
            try:
                feed_data.updated_at = max(entry.updated_at
                                           for entry in feed_data.entries
                                           if entry.updated_at)
            except ValueError:
                feed_data.updated_at = now()
        else:
            feed_data.updated_at = now()
    if feed_data.title is None:
        feed_data.title = feed_data.subtitle
        # FIXME: what should we do when there's even no subtitle?
    for entry in feed_data.entries:
        if entry.updated_at is None:
            entry.updated_at = feed_data.updated_at


def rss_get_channel_data(root, feed_url):
    _log = logging.getLogger(__name__ + '.rss_get_channel_data')
    feed_data = Feed(id=feed_url)
    feed_data.links.append(Link(relation='self', uri=feed_url))
    crawler_hints = {}
    contributors = []
    for data in root:
        if data.tag == 'title':
            feed_data.title = Text(value=data.text or '')
        elif data.tag == 'link':
            link = Link(uri=data.text,
                        relation='alternate',
                        mimetype='text/html')
            feed_data.links.append(link)
        elif data.tag == 'description':
            feed_data.subtitle = Text(type='text', value=data.text)
        elif data.tag == 'copyright':
            feed_data.rights = Text(value=data.text)
        elif data.tag in ('managingEditor', 'webMaster'):
            contributor = Person(name=data.text, email=data.text)
            contributors.append(contributor)
            feed_data.contributors = contributors
        elif data.tag == 'pubDate':
            feed_data.updated_at = Rfc822().decode(data.text)
        elif data.tag == 'category':
            feed_data.categories = [Category(term=data.text)]
        elif data.tag == 'generator':
            feed_data.generator = Generator(value=data.text)
        elif data.tag == 'lastBuildDate':
            crawler_hints['lastBuildDate'] = Rfc822().decode(data.text)
        elif data.tag == 'ttl':
            crawler_hints['ttl'] = data.text
        elif data.tag == 'skipHours':
            crawler_hints['skipHours'] = data.text
        elif data.tag == 'skipMinutes':
            crawler_hints['skipMinutes'] = data.text
        elif data.tag == 'skipDays':
            crawler_hints['skipDays'] = data.text
        else:
            _log.warn('Unknown tag: %s', data)
    return feed_data, crawler_hints


def rss_get_item_data(entries):
    _log = logging.getLogger(__name__ + '.rss_get_item_data')
    entries_data = []
    for entry in entries:
        entry_data = Entry()
        links = []
        for data in entry:
            if data.tag == 'title':
                entry_data.title = Text(value=data.text)
            elif data.tag == 'link':
                link = Link(uri=data.text,
                            relation='alternate',
                            mimetype='text/html')
                links.append(link)
                entry_data.links = links
            elif data.tag == 'description' and not entry_data.content:
                entry_data.content = Content(type='html', value=data.text)
            elif data.tag == CONTENT_XMLNS + 'encoded':
                entry_data.content = Content(type='html', value=data.text)
            elif data.tag == 'author':
                entry_data.authors = [Person(name=data.text, email=data.text)]
            elif data.tag == 'category':
                entry_data.categories = [Category(term=data.text)]
            elif data.tag == 'comments':
                #entry_data['comments'] = data.text
                pass  # FIXME
            elif data.tag == 'enclosure':
                link = Link(mimetype=data.get('type'), uri=data.get('url'))
                links.append(link)
                entry_data.links = links
            elif data.tag == 'guid':
                isPermalink = data.get('isPermalink')
                if data.text.startswith('http://') and isPermalink != 'False':
                    entry_data.id = data.text
                elif GUID_PATTERN.match(data.text):
                    entry_data.id = 'urn:uuid:' + data.text
            elif data.tag == 'pubDate':
                entry_data.published_at = Rfc822().decode(data.text)
                # TODO 'pubDate' is optional in RSS 2, but 'updated' in Atom
                #       is required element, so we have to fill some value to
                #       entry.updated_at.
            elif data.tag == 'source':
                from .autodiscovery import get_format
                url = data.get('url')
                request = urllib2.Request(url)
                f = urllib2.urlopen(request)
                xml = f.read()
                parser = get_format(xml)
                source, _ = parser(xml, url, parse_entry=False)
                entry_data.source = source
            else:
                _log.warn('Unknown tag: %s', data)
        if entry_data.updated_at is None:
            entry_data.updated_at = entry_data.published_at
        if entry_data.id is None:
            entry_data.id = entry_data.links[0].uri \
                if entry_data.links else ''
        entries_data.append(entry_data)
    return entries_data
