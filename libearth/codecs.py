""":mod:`libearth.codecs` --- Common codecs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This module provides commonly used codecs to parse RSS-related standard
formats.

"""
import datetime
import re

from .schema import Codec, DecodeError, EncodeError
from .tz import FixedOffset, utc

__all__ = 'Boolean', 'Rfc3339', 'Rfc822', 'Integer'


class Rfc3339(Codec):
    """Codec to store :class:`datetime.datetime` values to :rfc:`3339`
    format.

    :param prefer_utc: normalize all timezones to UTC.
                       :const:`False` by default
    :type prefer_utc: :class:`bool`

    """

    #: (:class:`re.RegexObject`) The regular expression pattern that
    #: matches to valid :rfc:`3339` date time string.
    PATTERN = re.compile(r'''
        ^
        (?P<year> \d{4} ) - (?P<month> 0[1-9] | 1[012] )
                          - (?P<day> 0[1-9] | [12]\d | 3[01] )
        T
        (?P<hour> [01]\d | 2[0-3] ) : (?P<minute> [0-5]\d )
                                    : (?P<second> [0-5]\d | 60 )
                                    (?: \. (?P<microsecond> \d+ ) )?
        (?P<tz> Z
              | (?P<tz_offset> (?P<tz_offset_sign> [+-] )
                               (?P<tz_offset_hour> [01]\d | 2[0-3] ) :
                               (?P<tz_offset_minute> [0-5]\d ) ) )
        $
    ''', re.VERBOSE)

    def __init__(self, prefer_utc=False):
        self.prefer_utc = bool(prefer_utc)

    def encode(self, value):
        if not isinstance(value, datetime.datetime):
            raise EncodeError(
                '{0.__module__}.{0.__name__} accepts only datetime.datetime '
                'value, not {1!r}'.format(type(self), value)
            )
        elif value.tzinfo is None:
            raise EncodeError(
                '{0.__module__}.{0.__name__} does not accept naive datetime.'
                'datetime value, but {1!r} lacks tzinfo attribute'.format(
                    type(self), value
                )
            )
        if self.prefer_utc:
            value = value.astimezone(utc)
        dt = value.strftime('%Y-%m-%dT%H:%M:%S')
        if value.microsecond:
            dt += value.strftime('.%f').rstrip('0')
        offset = value.tzinfo.utcoffset(value)
        if offset == datetime.timedelta(0):
            dt += 'Z'
        else:
            minutes = offset.seconds // 60
            dt += '{h:+03d}:{m:02d}'.format(h=minutes // 60,
                                            m=minutes % 60)
        return dt

    def decode(self, text):
        match = self.PATTERN.match(text)
        if not match:
            raise DecodeError(repr(text) +
                              ' is not valid RFC3339 date time string')
        if match.group('tz_offset'):
            tz_hour = int(match.group('tz_offset_hour'))
            tz_minute = int(match.group('tz_offset_minute'))
            tz_sign = 1 if match.group('tz_offset_sign') == '+' else -1
            tzinfo = FixedOffset(tz_sign * (tz_hour * 60 + tz_minute))
        else:
            tzinfo = utc
        microsecond = match.group('microsecond') or '0'
        microsecond += '0' * (6 - len(microsecond))
        try:
            dt = datetime.datetime(
                int(match.group('year')),
                int(match.group('month')),
                int(match.group('day')),
                int(match.group('hour')),
                int(match.group('minute')),
                int(match.group('second')),
                int(microsecond),
                tzinfo=tzinfo
            )
        except ValueError as e:
            raise DecodeError(e)
        if self.prefer_utc and tzinfo is not utc:
            dt = dt.astimezone(utc)
        return dt


class Rfc822(Codec):
    def encode(self, value):
        if value is None:
            return ""

        if not isinstance(value, datetime.datetime):
            raise EncodeError("Value must be instance of datetime.datetime")
        res = value.strftime("%a, %d %b %Y %H:%M:%S ")
        res += value.strftime("%Z").replace(":", "")
        return res

    def decode(self, text):
        if not text:
            return None

        timestamp = text[:25]
        timezone = text[26:]
        try:
            res = datetime.datetime.strptime(timestamp, "%a, %d %b %Y %H:%M:%S")
            #FIXME: timezone like KST, UTC
            matched = re.match(r'\+([0-9]{2})([0-9]{2})', timezone)
            if matched:
                offset = FixedOffset(
                    int(matched.group(1)) * 60 +
                    int(matched.group(2))
                )
                res = res.replace(tzinfo=offset)
        except ValueError as e:
            raise DecodeError(e)

        return res


class Integer(Codec):
    PATTERN = re.compile("[0-9]+")

    def encode(self, value):
        if not isinstance(value, int):
            raise EncodeError("Value type must be int")
        if value is None:
            return ""
        else:
            return str(value)

    def decode(self, text):
        if not self.PATTERN.match(text):
            raise DecodeError("Invalid character on text")
        return int(text)


class Boolean(Codec):
    def __init__(self, is_truefalse=True, is_yn=True, is_onoff=True,
                 default_value=None):
        self.is_truefalse = is_truefalse
        self.is_yn = is_yn
        self.is_onoff = is_onoff
        self.default_value = default_value

    def encode(self, value):
        if value is None:
            value = self.default_value

        if self.is_truefalse:
            res = "true" if value else "false"
        elif self.is_yn:
            res = "y" if value else "n"
        elif self.is_onoff:
            res = "on" if value else "off"

        return res

    def decode(self, text):
        value = None
        text = text.lower()
        if self.is_truefalse:
            if text == "true":
                value = True
            elif text == "false":
                value = False

        if self.is_yn:
            if text == "y":
                value = True
            elif text == "n":
                value = False

        if self.is_onoff:
            if text == "on":
                value = True
            elif text == "off":
                value = False

        if value is None:
            value = self.default_value

        return value
