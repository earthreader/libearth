""":mod:`libearth.tz` --- Basic timezone implementations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Almost of this module is from the official documentation of
:mod:`datetime` module in Python standard library.

.. data:: utc

   (:class:`Utc`, :class:`datetime.timezone`) The :class:`~datetime.tzinfo`
   instance that represents UTC.  It's an instance of :class:`Utc`
   in Python 2 (which provide no built-in fixed-offset
   :class:`~datetime.tzinfo` implementation), and an instance of
   :class:`~datetime.timezone` with zero offset in Python 3.

"""
import datetime

from .compat import string_type

__all__ = 'FixedOffset', 'Utc', 'guess_tzinfo_by_locale', 'now', 'utc'


class Utc(datetime.tzinfo):
    """UTC.

    In most cases, it doesn't need to be directly instantiated:
    there's already the :const:`utc` value.

    """

    def __init__(self):
        self.zero = datetime.timedelta(0)

    def utcoffset(self, dt):
        return self.zero

    def dst(self, dt):
        return self.zero

    def tzname(self, dt):
        return 'UTC'

    def __repr__(self):
        cls = type(self)
        return '{0.__module__}.{0.__name__}()'.format(cls)


class FixedOffset(datetime.tzinfo):
    """Fixed offset in minutes east from UTC.

    >>> kst = FixedOffset(9 * 60, name='Asia/Seoul')  # KST +09:00
    >>> current = now()
    >>> current
    datetime.datetime(2013, 8, 15, 3, 18, 37, 404562, tzinfo=libearth.tz.Utc())
    >>> current.astimezone(kst)
    datetime.datetime(2013, 8, 15, 12, 18, 37, 404562,
                      tzinfo=<libearth.tz.FixedOffset Asia/Seoul>)

    """

    def __init__(self, offset, name=None):
        self.offset = datetime.timedelta(minutes=offset)
        self.dst_ = datetime.timedelta(0)
        self.name = name or '{h:+03d}:{m:02d}'.format(h=offset // 60,
                                                      m=offset % 60)

    def utcoffset(self, dt):
        return self.offset

    def dst(self, dt):
        return self.dst_

    def tzname(self, dt):
        return self.name

    def __repr__(self):
        cls = type(self)
        return '<{0.__module__}.{0.__name__} {1}>'.format(cls, self.name)


try:
    utc = datetime.timezone.utc
except AttributeError:
    utc = Utc()


def now():
    """Return the current :class:`~datetime.datetime` with the proper
    :class:`~datetime.tzinfo` setting.

    >>> now()
    datetime.datetime(2013, 8, 15, 3, 17, 11, 892272, tzinfo=libearth.tz.Utc())
    >>> now()
    datetime.datetime(2013, 8, 15, 3, 17, 17, 532483, tzinfo=libearth.tz.Utc())

    """
    return datetime.datetime.utcnow().replace(tzinfo=utc)


LANGUAGE_COUNTRY_TZINFO_TABLE = {
    'ko': {'kr': FixedOffset(9 * 60, 'Asia/Seoul')},
    'ja': {'jp': FixedOffset(9 * 60, 'Asia/Tokyo')}
}


def guess_tzinfo_by_locale(language, country=None):
    """Guess the most commonly used time zone from the given locale.

    :param language: the language code e.g. ``ko``, ``JA``
    :type language: :class:`str`
    :param country: optional country code e.g. ``kr``, ``JP``
    :type country: :class:`str`
    :return: the most commonly used time zone, or :const:`None` if can't
             guess
    :rtype: :class:`datetime.tzinfo`

    .. versionadded:: 0.3.0

    """
    if not isinstance(language, string_type):
        raise TypeError('language must be a string, not ' + repr(language))
    elif not (country is None or isinstance(country, string_type)):
        raise TypeError('country must be a string, not ' + repr(country))
    language = language.strip().lower()
    if len(language) != 2:
        raise ValueError(repr(language) + ' is not a valid language code')
    if country:
        country = country.strip().lower()
        if len(country) != 2:
            raise ValueError(repr(country) + ' is not a valid country code')
    try:
        countries = LANGUAGE_COUNTRY_TZINFO_TABLE[language]
    except KeyError:
        return
    if country:
        return countries.get(country)
    elif len(countries) == 1:
        for tz in countries.values():
            return tz
