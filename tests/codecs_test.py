import datetime

from pytest import mark, raises

from libearth.codecs import Enum, Rfc3339
from libearth.schema import DecodeError, EncodeError
from libearth.tz import FixedOffset, utc


def test_enum():
    enum = Enum(['male', 'female'])
    assert enum.encode('male') == 'male'
    assert enum.encode('female') == 'female'
    with raises(EncodeError):
        enum.encode('invalid')
    assert enum.decode('male') == 'male'
    assert enum.decode('female') == 'female'
    with raises(DecodeError):
        enum.decode('invalid')


sample_data = [
    ('2005-07-31T12:29:29Z',
     datetime.datetime(2005, 7, 31, 12, 29, 29, tzinfo=utc)),
    ('2003-12-13T18:30:02.25Z',
     datetime.datetime(2003, 12, 13, 18, 30, 2, 250000, tzinfo=utc)),
    ('2003-12-13T18:30:02+01:00',
     datetime.datetime(2003, 12, 13, 18, 30, 2, tzinfo=FixedOffset(1 * 60))),
    ('2003-12-13T18:30:02.25+01:00',
     datetime.datetime(2003, 12, 13, 18, 30, 2, 250000,
                       tzinfo=FixedOffset(1 * 60)))
]


@mark.parametrize(('rfc3339_string', 'dt'), sample_data)
def test_rfc3339_decode(rfc3339_string, dt):
    parsed = Rfc3339().decode(rfc3339_string)
    assert parsed == dt
    assert parsed.tzinfo.utcoffset(parsed) == dt.tzinfo.utcoffset(parsed)
    utc_parsed = Rfc3339(prefer_utc=True).decode(rfc3339_string)
    assert utc_parsed == dt
    assert utc_parsed.tzinfo.utcoffset(parsed) == datetime.timedelta(0)


@mark.parametrize(('rfc3339_string', 'dt'), sample_data)
def test_rfc3339_encode(rfc3339_string, dt):
    codec = Rfc3339()
    assert codec.encode(dt) == rfc3339_string
    assert (Rfc3339(prefer_utc=True).encode(dt) ==
            codec.encode(dt.astimezone(utc)))
