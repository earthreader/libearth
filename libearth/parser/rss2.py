""":mod:`libearth.parser.rss2` --- RSS 2.0 parser
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Parsing RSS 2.0 feed.

"""
import re

try:
    import urlparse
except ImportError:
    from urllib import parse as urlparse

from ..compat.etree import fromstring
from ..feed import Category, Entry, Feed, Generator, Link
from ..tz import guess_tzinfo_by_locale, now, utc
from .atom import ATOM_XMLNS_SET
from .base import ParserBase, SessionBase
from .rss_base import (content_parser, datetime_parser, link_parser,
                       person_parser, subtitle_parser, text_parser)
from .util import normalize_xml_encoding


GUID_PATTERN = re.compile('^(\{{0,1}([0-9a-fA-F]){8}-([0-9a-fA-F]){4}-([0-9'
                          'a-fA-F]){4}-([0-9a-fA-F]){4}-([0-9a-fA-F]){12}\}'
                          '{0,1})$')
CONTENT_XMLNS = 'http://purl.org/rss/1.0/modules/content/'


class RSS2Session(SessionBase):
    """The session class used for parsing the RSS2.0 feed."""

    #: (:class:`str`) The url of the feed to make :class: `~libearth.feed.Link`
    #: object of which relation is self in the feed.
    feed_url = None

    #: (:class:`str`) The default time zone name to set the tzinfo of parsed
    #: :class: `datetime.datetime` object.
    default_tz_info = None

    def __init__(self, feed_url, default_tz_info):
        self.feed_url = feed_url
        self.default_tz_info = default_tz_info


rss2_parser = ParserBase()


@rss2_parser.path('channel')
def parse_channel(element, session):
    return Feed(), session


@rss2_parser.path('item')
def parse_item(element, session):
    return Entry(), session


@parse_channel.path('pubDate', attr_name='updated_at')
@parse_item.path('pubDate', attr_name='published_at')
def parse_datetime(element, session):
    return datetime_parser(element, session)


@parse_channel.path('managingEditor', attr_name='contributors')
@parse_channel.path('webMaster', attr_name='contributors')
@parse_item.path('author', attr_name='authors')
def parse_person(element, session):
    return person_parser(element, session)


@parse_channel.path('category', attr_name='categories')
@parse_item.path('category', attr_name='categories')
def parse_category(element, session):
    return Category(
        term=element.text,
        scheme_uri=element.attrib.get('domain')
    ), session


@parse_channel.path('title')
@parse_channel.path('copyright', attr_name='rights')
@parse_item.path('title')
def parse_text(element, session):
    return text_parser(element, session)


@parse_channel.path('description', attr_name='subtitle')
def parse_subtitle(element, session):
    return subtitle_parser(element, session)


@parse_channel.path('link', ATOM_XMLNS_SET, attr_name='links')
def parse_atom_link(element, session):
    link = Link(uri=element.get('href'),
                relation=element.get('rel', 'alternate'),
                mimetype=element.get('type'))
    return link, session


@parse_channel.path('link', attr_name='links')
@parse_item.path('link', attr_name='links')
def parse_link(element, session):
    return link_parser(element, session)


@parse_channel.path('generator')
def parse_generator(element, session):
    generator = None
    try:
        if urlparse.urlparse(element.text).scheme in ('http', 'https'):
            generator = Generator(uri=element.text)
    except ValueError:
        pass
    return generator or Generator(value=element.text), session


@parse_item.path('enclosure', attr_name='links')
def parse_enclosure(element, session):
    return Link(
        relation='enclosure',
        mimetype=element.get('type'),
        uri=element.get('url')
    ), session


@parse_item.path('source')
def parse_source(element, session):
    from ..crawler import open_url
    from .autodiscovery import get_format
    url = element.get('url')
    f = open_url(url)  # FIXME: propagate timeout option
    xml = f.read()
    parser = get_format(xml)
    source, _ = parser(xml, url, parse_entry=False)
    return source, session


@parse_item.path('comments', attr_name='links')
def parse_comments(element, session):
    return Link(uri=element.text, relation='discussion'), session


@parse_item.path('description', attr_name='content')
@parse_item.path('encoded', [CONTENT_XMLNS], 'content')
def parse_content(element, session):
    return content_parser(element, session)


@parse_item.path('guid', attr_name='id')
def parse_guid(element, session):
    isPermalink = element.get('isPermalink')
    if element.text.startswith('http://') and isPermalink != 'False':
        return element.text, session
    elif GUID_PATTERN.match(element.text):
        return 'urn:uuid:' + element.text, session
    return None, session


def guess_default_tzinfo(root, url):
    """Guess what time zone is implied in the feed by seeing the TLD of
    the ``url`` and its ``<language>`` tag.

    """
    lang = root.find('channel/language')
    if lang is None or not lang.text:
        return utc
    lang = lang.text.strip()
    if len(lang) == 5 and lang[2] == '-':
        lang = lang[:2]
    parsed = urlparse.urlparse(url)
    domain = parsed.hostname.rsplit('.', 1)
    country = domain[1] if len(domain) > 1 and len(domain[1]) == 2 else None
    return guess_tzinfo_by_locale(lang, country) or utc


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
    root = fromstring(normalize_xml_encoding(xml))
    channel = root.find('channel')
    default_tzinfo = guess_default_tzinfo(root, feed_url)
    session = RSS2Session(feed_url, default_tzinfo)
    feed_data = parse_channel(channel, session)
    if parse_entry:
        items = channel.findall('item')
        entry_list = []
        for item in items:
            entry_list.append(parse_item(item, session))
        feed_data.entries = entry_list
    check_valid_as_atom(feed_data, session)
    return feed_data, None


def check_valid_as_atom(feed_data, session):
    # FIXME: It doesn't only "check" the feed_data but manipulates it
    # if not valid.  I think the function should be renamed.
    if not feed_data.id:
        feed_data.id = session.feed_url
    if all(l.relation != 'self' for l in feed_data.links):
        feed_data.links.insert(0, Link(relation='self', uri=session.feed_url))
    for entry in feed_data.entries:
        if entry.updated_at is None:
            entry.updated_at = entry.published_at
        if entry.id is None:
            entry.id = entry.links[0].uri if entry.links else ''
    if feed_data.updated_at is None:
        if feed_data.entries:
            try:
                feed_data.updated_at = max(entry.updated_at
                                           for entry in feed_data.entries
                                           if entry.updated_at)
            except ValueError:
                feed_data.updated_at = now()
                for entry in feed_data.entries:
                    if entry.updated_at is None:
                        entry.updated_at = feed_data.updated_at
        else:
            feed_data.updated_at = now()
    if feed_data.title is None:
        feed_data.title = feed_data.subtitle
        # FIXME: what should we do when there's even no subtitle?
