""":mod:`libearth.parser.rss2` --- RSS 2.0 parser
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Parsing RSS 2.0 feed.

.. todo::

   Set priority among the elements if only one of them will be selected in
   the parsed data.

   Fill required elements with another data if the element is empty

"""
import datetime
import email.utils
import re

try:
    import urlparse
except ImportError:
    from urllib import parse as urlparse

from ..codecs import Rfc3339, Rfc822
from ..compat import IRON_PYTHON
from ..compat.etree import fromstring
from ..feed import (Category, Content, Entry, Feed, Generator, Link,
                    Person, Text)
from ..schema import DecodeError
from ..tz import FixedOffset, guess_tzinfo_by_locale, now, utc
from .atom import ATOM_XMLNS_SET
from .base import ParserBase, SessionBase, get_element_id
from .util import normalize_xml_encoding


GUID_PATTERN = re.compile('^(\{{0,1}([0-9a-fA-F]){8}-([0-9a-fA-F]){4}-([0-9'
                          'a-fA-F]){4}-([0-9a-fA-F]){4}-([0-9a-fA-F]){12}\}'
                          '{0,1})$')
CONTENT_XMLNS = 'http://purl.org/rss/1.0/modules/content/'


class RSS2Session(SessionBase):
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


_rfc3339 = Rfc3339()
_rfc822 = Rfc822()
_datetime_formats = [
    ('%Y-%m-%d %H:%M:%S', None),  # daumwebtoon
    ('%m/%d/%Y %H:%M:%S GMT', utc),  # msdn
    ('%m/%d/%y %H:%M:%S GMT', utc),  # msdn
    ('%a, %d %b %Y %H:%M:%S GMT 00:00:00 GMT', utc),  # msdn
    ('%Y.%m.%d %H:%M:%S', None),  # imbcnews
    ('%d %b %Y %H:%M:%S %z', None),  # lee-seungjae
]


@parse_channel.path('pubDate', attr_name='updated_at')
@parse_item.path('pubDate', attr_name='published_at')
def parse_datetime(element, session):
    # https://github.com/earthreader/libearth/issues/30
    string = element.text
    try:
        return _rfc822.decode(string), session
    except DecodeError:
        pass
    try:
        return _rfc3339.decode(string), session
    except DecodeError:
        pass
    for fmt, tzinfo in _datetime_formats:
        try:
            if IRON_PYTHON:
                # IronPython strptime() seems to ignore whitespace
                string = string.replace(' ', '|')
                fmt = fmt.replace(' ', '|')
            if fmt.endswith('%z'):
                dt = datetime.datetime.strptime(string[:-5], fmt[:-2])
                tz_sign = -1 if string[-5:-4] == '-' else 1
                tz_hour = int(string[-4:-2])
                tz_min = int(string[-2:])
                tzinfo = FixedOffset(tz_sign * (tz_hour * 60 + tz_min))
            else:
                dt = datetime.datetime.strptime(string, fmt)
            return dt.replace(tzinfo=tzinfo or session.default_tz_info), session
        except ValueError:
            continue
    raise ValueError('failed to parse datetime: ' + repr(string))


@parse_channel.path('managingEditor', attr_name='contributors')
@parse_channel.path('webMaster', attr_name='contributors')
@parse_item.path('author', attr_name='authors')
def parse_person(element, session):
    string = element.text
    name, email_addr = email.utils.parseaddr(string)
    if '@' not in email_addr:
        if not name:
            name = email_addr
        email_addr = None
    if not name:
        name = email_addr
    if not name:
        return None, session
    person = Person(name=name, email=email_addr or None)
    return person, session


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
    return Text(value=element.text or ''), session


@parse_channel.path('description', attr_name='subtitle')
def parse_subtitle(element, session):
    return Text(type='text', value=element.text), session


@parse_item.path(CONTENT_XMLNS + 'encoded', 'content')
def parse_content(element, session):
    return Content(type='html', value=element.text), session


@parse_channel.path('link', ATOM_XMLNS_SET, attr_name='links')
def parse_atom_link(element, session):
    link = Link(uri=element.get('href'),
                relation=element.get('rel', 'alternate'),
                mimetype=element.get('type'))
    return link, session


@parse_channel.path('link', attr_name='links')
@parse_item.path('link', attr_name='links')
def parse_link(element, session):
    if not element.text:
        return None, session
    link = Link(uri=element.text,
                relation='alternate',
                mimetype='text/html')
    return link, session


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
    return Content(type='html', value=element.text), session


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
