""":mod:`libearth.codecs` --- Common codecs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This module provides commonly used codecs to parse RSS-related standard
formats.

"""
import collections
import datetime
import numbers
import platform
import re

from .compat import string_type
from .schema import Codec, DecodeError, EncodeError
from .tz import FixedOffset, utc

__all__ = 'Boolean', 'Enum', 'Integer', 'Rfc3339', 'Rfc822'


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
        if not isinstance(value, string_type):
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
        if text not in self.values:
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
            # IronPython strftime() seems to ignore %f
            dt += '.{0:06}'.format(value.microsecond).rstrip('0')
        offset = value.tzinfo.utcoffset(value)
        if offset == datetime.timedelta(0):
            dt += 'Z'
        else:
            minutes = offset.seconds // 60
            dt += '{h:+03d}:{m:02d}'.format(h=minutes // 60,
                                            m=minutes % 60)
        return dt

    def decode(self, text):
        text = text.strip()
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
    """Codec to encode/decode :class:`datetime.datetime` values to/from
    :rfc:`822` format.

    """

    WEEKDAYS = ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun')
    MONTHS = ('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug',
              'Sep', 'Oct', 'Nov', 'Dec')
    TIMEZONES = {
        'UT': FixedOffset(0 * 60),
        'UTC': FixedOffset(0 * 60),
        'GMT': FixedOffset(0 * 60),
        "EST": FixedOffset(-5 * 60),
        "EDT": FixedOffset(-4 * 60),
        "CST": FixedOffset(-6 * 60),
        "CDT": FixedOffset(-5 * 60),
        "MST": FixedOffset(-7 * 60),
        "MDT": FixedOffset(-6 * 60),
        "PST": FixedOffset(-8 * 60),

        "1A": FixedOffset(-1 * 60),
        "1B": FixedOffset(-2 * 60),
        "1C": FixedOffset(-3 * 60),
        "1D": FixedOffset(-4 * 60),
        "1E": FixedOffset(-5 * 60),
        "1F": FixedOffset(-6 * 60),
        "1G": FixedOffset(-7 * 60),
        "1H": FixedOffset(-8 * 60),
        "1I": FixedOffset(-9 * 60),
        "1K": FixedOffset(-10 * 60),
        "1L": FixedOffset(-11 * 60),
        "1M": FixedOffset(-12 * 60),
        "1N": FixedOffset(1 * 60),
        "1O": FixedOffset(2 * 60),
        "1P": FixedOffset(3 * 60),
        "1Q": FixedOffset(4 * 60),
        "1R": FixedOffset(5 * 60),
        "1S": FixedOffset(6 * 60),
        "1T": FixedOffset(7 * 60),
        "1U": FixedOffset(8 * 60),
        "1V": FixedOffset(9 * 60),
        "1W": FixedOffset(10 * 60),
        "1X": FixedOffset(11 * 60),
        "1Y": FixedOffset(12 * 60),
        "1Z": FixedOffset(0 * 60),
    }
    PATTERN = re.compile(r'''
        ^ \s*
        (?:Sun|Mon|Tue|Wed|Thu|Fri|Sat ) , \s+
        (?P<day> \d\d? ) \s+
        (?P<month> ''' + '|'.join(MONTHS) + r''' ) \s+
        (?P<year> \d{4} ) \s+
        (?P<hour> \d\d ) : (?P<minute> \d\d ) : (?P<second> \d\d ) \s+
        (?P<tz> (?P<tz_offset> (?P<tz_offset_sign> [\+\-] )
                               (?P<tz_offset_hour> [0-9]{2} ) :?
                               (?P<tz_offset_minute> [0-9]{2} ) )
        |       (?P<tz_named>''' + '|'.join(map(re.escape, TIMEZONES)) + r''' )
        )
        \s* $
    ''', re.IGNORECASE | re.VERBOSE)

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
        offset = value.tzinfo.utcoffset(value)
        minutes = offset.seconds // 60
        res = '{w}, {t:%d} {m} {t:%Y %H:%M:%S} {tz_h:+03d}{tz_m:02d}'.format(
            t=value,
            w=self.WEEKDAYS[value.weekday()],
            m=self.MONTHS[value.month - 1],
            tz_h=minutes // 60,
            tz_m=minutes % 60
        )
        return res

    def decode(self, text):
        exc = DecodeError(repr(text) + ' is an invalid rfc822 string')
        m = self.PATTERN.match(text)
        if not m:
            raise exc
        day = int(m.group('day'))
        month_string = m.group('month')
        try:
            month = self.MONTHS.index(month_string)
        except ValueError:
            raise exc
        else:
            month += 1
        year = int(m.group('year'))
        hour = int(m.group('hour'))
        minute = int(m.group('minute'))
        second = int(m.group('second'))
        if m.group('tz_offset'):
            tz = FixedOffset(
                int(m.group('tz_offset_hour')) * 60 +
                int(m.group('tz_offset_minute')) *
                (1 if m.group('tz_offset_sign') == '+' else -1)
            )
        elif m.group('tz_named'):
            tz = self.TIMEZONES[m.group('tz_named')]
        return datetime.datetime(
            year, month, day,
            hour, minute, second,
            tzinfo=tz
        )


class Integer(Codec):
    """Codec to encode and decode integer numbers."""

    def encode(self, value):
        if not isinstance(value, numbers.Integral):
            raise EncodeError('expected integer, not ' + repr(value))
        return str(int(value))

    def decode(self, text):
        try:
            return int(text)
        except ValueError as e:
            raise DecodeError(str(e))


class Boolean(Codec):
    """Codec to interpret boolean representation in strings e.g. ``'true'``,
    ``'no'``, and encode :class:`bool` values back to string.

    :param true: text to parse as :const:`True`.  ``'true'`` by default
    :type true: :class:`str`, :class:`tuple`
    :param false: text to parse as :const:`False`.  ``'false'`` by default
    :type false: :class:`str`, :class:`tuple`
    :param default_value: default value when it cannot be parsed
    :type default_value: :class:`bool`

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


# Workaround for http://bugs.python.org/issue7980
if platform.python_implementation() == 'CPython':
    __import__('_strptime')
