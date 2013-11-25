import datetime

from libearth.tz import FixedOffset, now, utc


def test_utc():
    dt = datetime.datetime(2013, 8, 15, 3, 18, 30, tzinfo=utc)
    assert utc.utcoffset(dt) == datetime.timedelta(0)
    assert utc.dst(dt) is None or utc.dst(dt) == datetime.timedelta(0)
    assert utc.tzname(dt).startswith('UTC')


def test_fixed_offset():
    tz = FixedOffset(9 * 60)
    dt = datetime.datetime(2013, 8, 15, 3, 18, 30, tzinfo=tz)
    assert (dt.astimezone(utc).replace(tzinfo=None) ==
            datetime.datetime(2013, 8, 14, 18, 18, 30))
    assert tz.utcoffset(dt) == datetime.timedelta(hours=9)
    assert tz.dst(dt) == datetime.timedelta(0)
    assert tz.tzname(dt) == '+09:00'


def test_fixed_offset_name():
    tz = FixedOffset(9 * 60, 'custom')
    dt = datetime.datetime(2013, 8, 15, 3, 18, 30, tzinfo=tz)
    assert (dt.astimezone(utc).replace(tzinfo=None) ==
            datetime.datetime(2013, 8, 14, 18, 18, 30))
    assert tz.utcoffset(dt) == datetime.timedelta(hours=9)
    assert tz.dst(dt) == datetime.timedelta(0)
    assert tz.tzname(dt) == 'custom'


def test_now():
    before = datetime.datetime.utcnow().replace(tzinfo=utc)
    actual = now()
    after = datetime.datetime.utcnow().replace(tzinfo=utc)
    assert before <= actual <= after
