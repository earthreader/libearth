import datetime

from pytest import mark, raises

from libearth.codecs import Boolean, Enum, Integer, Rfc3339, Rfc822, Version
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


def test_rfc822():
    codec = Rfc822()

    kst_string = 'Sat, 07 Sep 2013 01:20:43 +0900'
    kst_datetime = datetime.datetime(2013, 9, 7, 1, 20, 43,
                                     tzinfo=FixedOffset(9 * 60))

    assert codec.decode(kst_string) == kst_datetime
    assert codec.encode(kst_datetime) == kst_string


def test_rfc822_namedtz():
    codec = Rfc822()
    gmt_string = 'Sat, 07 Sep 2013 01:20:43 GMT'
    gmt_datetime = datetime.datetime(2013, 9, 7, 1, 20, 43, tzinfo=utc)
    assert codec.decode(gmt_string) == gmt_datetime


def test_rfc822_raise():
    codec = Rfc822()

    datetime_not_contains_tzinfo = datetime.datetime.now()
    not_valid_rfc822_string = 'Sat, 07 Sep 2013 01:20:43'

    with raises(EncodeError):
        codec.encode("it is not datetime.datetime object")

    with raises(EncodeError):
        codec.encode(datetime_not_contains_tzinfo)

    with raises(DecodeError):
        codec.decode(not_valid_rfc822_string)


def test_integer():
    codec = Integer()
    assert codec.encode(42) == "42"
    assert codec.decode("42") == 42


def test_integer_raises():
    codec = Integer()
    with raises(EncodeError):
        print(codec.encode("string"))
    with raises(DecodeError):
        print(codec.decode("aaa"))


def test_boolean():
    codec = Boolean(true="true", false="false", default_value=False)

    assert codec.encode(True) is "true"
    assert codec.encode(False) is "false"

    assert codec.decode("true") is True
    assert codec.decode("false") is False
    assert codec.decode(None) is False

    with raises(EncodeError):
        print(codec.encode("string"))

    with raises(DecodeError):
        print(codec.decode("another"))


def test_boolean_tuple():
    true = ("true", "on", "yes")
    false = ("false", "off", "no")

    codec = Boolean(true=true, false=false, default_value=False)

    assert codec.encode(True) in true
    assert codec.encode(False) in false

    assert codec.decode("on") is True
    assert codec.decode("no") is False

    with raises(EncodeError):
        print(codec.encode(111))

    with raises(DecodeError):
        print(codec.decode("is one true?"))


def test_version():
    codec = Version(2)
    assert codec.decode('1.2') == (1, 2)
    assert codec.encode((1, 2)) == '1.2'

    with raises(EncodeError):
        codec.encode((1, 2, 3))

    with raises(DecodeError):
        codec.decode('1.2.3')
