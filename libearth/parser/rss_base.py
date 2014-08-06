""":mod:`libearth.parser.rss_base` --- Commonly used parsers in rss1 and rss2
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

"""
import datetime
import email.utils

from ..codecs import Rfc3339, Rfc822
from ..compat import IRON_PYTHON
from ..feed import Content, Link, Person, Text
from ..schema import DecodeError
from ..tz import FixedOffset, utc


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
