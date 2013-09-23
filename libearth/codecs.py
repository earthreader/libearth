""":mod:`libearth.codecs` --- Common codecs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This module provides commonly used codecs to parse RSS-related standard
formats.

"""
import collections
import datetime
import re

from .compat import string_type
from .schema import Codec, DecodeError, EncodeError
from .tz import FixedOffset, utc

__all__ = 'Boolean', 'Enum', 'Integer', 'Rfc3339', 'Rfc822', 'Version'


class Enum(Codec):
    """Codec that accepts only predefined fixed types of values::

        gender = Enum(['male', 'female'])

    Actually it doesn't any encoding nor decoding, but it simply *validates*
    all values from XML and Python both.

    Note that values have to consist of only strings.

    :param values: any iterable that yields all possible values
    :type values: :class:`collections.Iterable`

    """

    def __init__(self, values):
        if not isinstance(values, collections.Iterable):
            raise TypeError('enum values must be iterable, not ' +
                            repr(values))
        values = frozenset(values)
        for v in values:
            if not isinstance(v, string_type):
                raise TypeError('enum values must be strings, not ' +
                                repr(v))
        self.values = values

    def encode(self, value):
        if value is None:
            return
        elif not isinstance(value, string_type):
            raise EncodeError('expected a string, not ' + repr(value))
        elif value not in self.values:
            raise EncodeError(
                '{0!r} is an invalid value; choose one of {1}'.format(
                    value,
                    ', '.join(repr(v) for v in self.values)
                )
            )
        return value

    def decode(self, text):
        if not (text is None or text in self.values):
            raise DecodeError('expected one of ' +
                              ', '.join(repr(v) for v in self.values))
        return text


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
    """Codec to encode/decode :class:`datetime.datetime` values to :rfc:`822`
    format.

    """
    def encode(self, value):
        if value is None:
            return ""

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
            else:
                raise DecodeError(
                    'given argument was not valid RFC822 string. '
                    'it needs tzinfo'
                )
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
            return str(int(value))

    def decode(self, text):
        if not self.PATTERN.match(text):
            raise DecodeError("Invalid character on text")
        return int(text)


class Boolean(Codec):
    """Codec to interpret between :class:`bool` and raw text
    :param true: text to parse as True. "true" by default
    :type true: :class:`str` or :class:`tuple`

    :param false: text to parse as False. "false" by default
    :type false: :class:`str` or :class:`tuple`

    :param default_value: default value when cannot parse
    :type default_value: :class:`bool` or :const:`None`
    """
    def __init__(self, true="true", false="false", default_value=None):
        self.true = true
        self.false = false
        self.default_value = default_value

    def encode(self, value):
        if value is None:
            value = self.default_value

        if not isinstance(value, bool) and value is not None:
            raise EncodeError("type of {0} must be bool".format(value))

        true = (self.true if isinstance(self.true, string_type)
                else self.true[0])
        false = (self.false if isinstance(self.true, string_type)
                 else self.false[0])

        if value is True:
            return true
        elif value is False:
            return false
        else:
            return None

    def decode(self, text):
        true = (self.true if not isinstance(self.true, string_type)
                else [self.true])
        false = (self.false if not isinstance(self.false, string_type)
                 else [self.false])

        if text in true:
            value = True
        elif text in false:
            value = False
        elif not text:
            value = self.default_value
        else:
            raise DecodeError('invalid string')
        return value


class Version(Codec):
    """Codec to interpret version string like ```'x.y'```
    (x and y both are number)
    and encode :class:`tuple` or :class:`list` values back to string.

    :type count: :class:`int`
    :param count: number of numbers contains in version string.
    """

    def __init__(self, count=2):
        if not isinstance(count, int):
            raise TypeError('expected {0.__module__}.{0.__name__}, '
                            'not {1!r}'.format(int, count))
        self.count = count

    def encode(self, value):
        if not isinstance(value, (list, tuple)):
            raise EncodeError(
                'expected {0.__module__}.{0.__name__} or '
                '{1.__module__}.{1.__name__}, not {2!r}'.format(list, tuple))

        if len(value) != self.count:
            raise EncodeError('expected length was {0}, '
                              'not {1}'.format(self.count, len(value)))

        for i in value:
            if not isinstance(i, int):
                raise EncodeError('version string allows integer only.')

        return '.'.join(str(i) for i in value)

    def decode(self, text):
        lst = text.split('.')

        if len(lst) != self.count:
            raise DecodeError('expected length was {0}, '
                              'not {1}'.format(self.count, len(lst)))

        try:
            res = tuple(int(x) for x in lst)
        except ValueError:
            raise DecodeError('version string allows integer only')

        return res
