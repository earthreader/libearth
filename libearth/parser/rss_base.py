""":mod:`libearth.parser.rss_base` --- Commonly used objects in RSS1 and RSS2
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

RSS1 and RSS2 are naive compared to Atom feed. So there are several things
such as namespace or parsing logic that can be used to parse both feeds.
This module contains those common things.

"""
import datetime
import email.utils
import urlparse

from .base import SessionBase
from ..codecs import Rfc3339, Rfc822
from ..compat import IRON_PYTHON
from ..feed import Content, Link, Person, Text
from ..schema import DecodeError
from ..tz import FixedOffset, guess_tzinfo_by_locale, now, utc


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


#: (:class:`str`) The XML namespace for the predefined ``content:`` prefix.
CONTENT_XMLNS = 'http://purl.org/rss/1.0/modules/content/'


class RSSSession(SessionBase):
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


def content_parser(element, session):
    return Content(type='html', value=element.text), session


def datetime_parser(element, session):
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


def link_parser(element, session):
    if not element.text:
        return None, session
    link = Link(uri=element.text,
                relation='alternate',
                mimetype='text/html')
    return link, session


def person_parser(element, session):
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


def subtitle_parser(element, session):
    return Text(type='text', value=element.text), session


def text_parser(element, session):
    return Text(value=element.text or ''), session


def make_legal_as_atom(feed_data, session):
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
