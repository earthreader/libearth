import datetime

from pytest import raises

from libearth.session import Revision, RevisionCodec, Session
from libearth.tz import now, utc


def test_intern():
    """Session of the same identifier cannot be multiple."""
    session = Session('id1')
    assert session is Session('id1')
    assert session is not Session('id2')


def test_default_identifier():
    assert Session().identifier != ''
    assert Session().identifier is not None
    assert Session().identifier != Session.identifier


def test_invalid_identifier():
    with raises(ValueError):
        Session('i n v a l i d')
    with raises(ValueError):
        Session('i*n*v*a*l*i*d')
    with raises(ValueError):
        Session('i+n+v+a+l+i+d')
    with raises(ValueError):
        Session('i/n/v/a/l/i/d')
    with raises(ValueError):
        Session('i\nn\nv\na\nl\ni\nd')
    with raises(ValueError):
        Session('i\tn\tv\ta\tl\ti\td')
    with raises(ValueError):
        Session('(invalid)')
    Session('valid')
    Session('v-a-l-i-d')
    Session('v.a.l.i.d')
    Session('v_a_l_i_d')
    Session('v1a2l3i4d')
    Session('v-a.l_i4d')


def test_revision():
    session = Session()
    updated_at = now()
    rev = Revision(session, updated_at)
    assert rev == (session, updated_at)
    assert rev[0] is rev.session is session
    assert rev[1] == rev.updated_at == updated_at


def test_revision_codec():
    session = Session('test-identifier')
    updated_at = datetime.datetime(2013, 9, 22, 3, 43, 40, tzinfo=utc)
    rev = Revision(session, updated_at)
    codec = RevisionCodec()
    assert codec.encode(rev) == 'test-identifier 2013-09-22T03:43:40Z'
    assert codec.encode(tuple(rev)) == 'test-identifier 2013-09-22T03:43:40Z'
    decoded = codec.decode('test-identifier 2013-09-22T03:43:40Z')
    assert decoded == rev
    assert decoded.session is session
    assert decoded.updated_at == updated_at
