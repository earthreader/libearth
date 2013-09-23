import collections
import datetime
import time

from pytest import fixture, raises

from libearth.session import (MergeableDocumentElement, Revision, RevisionCodec,
                              RevisionSet, RevisionSetCodec, Session,
                              ensure_revision_pair)
from libearth.tz import now, utc


def test_intern():
    """Session of the same identifier cannot be multiple."""
    session = Session('id1')
    assert session is Session('id1')
    assert session is not Session('id2')
    assert session == Session('id1')
    assert session != Session('id2')
    assert hash(session) == hash(Session('id1'))
    assert hash(session) != hash(Session('id2'))


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


def test_ensure_revision_pair():
    session = Session()
    updated_at = now()
    assert ensure_revision_pair((session, updated_at)) == (session, updated_at)
    pair = ensure_revision_pair((session, updated_at), force_cast=True)
    assert isinstance(pair, Revision)
    assert pair == (session, updated_at)
    with raises(TypeError):
        ensure_revision_pair(())
    with raises(TypeError):
        ensure_revision_pair((session,))
    with raises(TypeError):
        ensure_revision_pair((session, updated_at, 1))
    with raises(TypeError):
        ensure_revision_pair(session)
    with raises(TypeError):
        ensure_revision_pair((session, 1))
    with raises(TypeError):
        ensure_revision_pair((1, updated_at))


@fixture
def fx_revision_set():
    dt = datetime.datetime
    return RevisionSet([
        (Session('key1'), dt(2013, 9, 22, 16, 58, 57, tzinfo=utc)),
        (Session('key2'), dt(2013, 9, 22, 16, 59, 30, tzinfo=utc)),
        (Session('key3'), dt(2013, 9, 22, 17, 0, 30, tzinfo=utc)),
        (Session('key4'), dt(2013, 9, 22, 17, 10, 30, tzinfo=utc))
    ])


def test_revision_set(fx_revision_set):
    assert isinstance(fx_revision_set, collections.Mapping)
    assert len(fx_revision_set) == 4
    assert set(fx_revision_set) == set([Session('key1'), Session('key2'),
                                        Session('key3'), Session('key4')])
    assert (fx_revision_set[Session('key1')] ==
            datetime.datetime(2013, 9, 22, 16, 58, 57, tzinfo=utc))
    assert (fx_revision_set[Session('key2')] ==
            datetime.datetime(2013, 9, 22, 16, 59, 30, tzinfo=utc))
    for pair in fx_revision_set.items():
        assert isinstance(pair, Revision)
    assert fx_revision_set
    assert not RevisionSet()


def test_revision_set_copy(fx_revision_set):
    clone = fx_revision_set.copy()
    assert isinstance(clone, RevisionSet)
    assert clone == fx_revision_set
    assert clone is not fx_revision_set


def test_revision_set_merge(fx_revision_set):
    dt = datetime.datetime
    initial = fx_revision_set.copy()
    with raises(TypeError):
        fx_revision_set.merge()
    with raises(TypeError):
        fx_revision_set.merge(fx_revision_set, [])
    assert fx_revision_set.merge(fx_revision_set) == fx_revision_set
    assert fx_revision_set == initial
    session_a = Session()
    session_b = Session()
    merged = fx_revision_set.merge(
        RevisionSet([
            (Session('key1'), dt(2013, 9, 23, 18, 40, 48, tzinfo=utc)),
            (Session('key2'), dt(2012, 9, 23, 18, 40, 48, tzinfo=utc)),
            (session_a, dt(2013, 9, 23, 18, 40, 48, tzinfo=utc)),
            (session_b, dt(2013, 9, 23, 18, 41, 00, tzinfo=utc))
        ])
    )
    assert merged == RevisionSet([
        (Session('key1'), dt(2013, 9, 23, 18, 40, 48, tzinfo=utc)),
        (Session('key2'), dt(2013, 9, 22, 16, 59, 30, tzinfo=utc)),
        (Session('key3'), dt(2013, 9, 22, 17, 0, 30, tzinfo=utc)),
        (Session('key4'), dt(2013, 9, 22, 17, 10, 30, tzinfo=utc)),
        (session_a, dt(2013, 9, 23, 18, 40, 48, tzinfo=utc)),
        (session_b, dt(2013, 9, 23, 18, 41, 00, tzinfo=utc))
    ])
    assert fx_revision_set == initial
    merged = fx_revision_set.merge(
        RevisionSet([
            (Session('key1'), dt(2013, 9, 23, 18, 40, 48, tzinfo=utc)),
            (Session('key2'), dt(2012, 9, 23, 18, 40, 48, tzinfo=utc)),
            (session_a, dt(2013, 9, 23, 18, 40, 48, tzinfo=utc))
        ]),
        RevisionSet([
            (Session('key3'), dt(2012, 9, 22, 17, 0, 30, tzinfo=utc)),
            (Session('key4'), dt(2013, 9, 23, 19, 10, 30, tzinfo=utc)),
            (session_a, dt(2013, 9, 23, 19, 8, 47, tzinfo=utc))
        ])
    )
    assert merged == RevisionSet([
        (Session('key1'), dt(2013, 9, 23, 18, 40, 48, tzinfo=utc)),
        (Session('key2'), dt(2013, 9, 22, 16, 59, 30, tzinfo=utc)),
        (Session('key3'), dt(2013, 9, 22, 17, 0, 30, tzinfo=utc)),
        (Session('key4'), dt(2013, 9, 23, 19, 10, 30, tzinfo=utc)),
        (session_a, dt(2013, 9, 23, 19, 8, 47, tzinfo=utc))
    ])


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


def test_revision_set_codec(fx_revision_set):
    codec = RevisionSetCodec()
    expected = '''key4 2013-09-22T17:10:30Z,
key3 2013-09-22T17:00:30Z,
key2 2013-09-22T16:59:30Z,
key1 2013-09-22T16:58:57Z'''
    assert codec.encode(fx_revision_set) == expected
    assert codec.decode(expected) == fx_revision_set


class TestMergeableDoc(MergeableDocumentElement):

    __tag__ = 'merge-test'


def test_session_revise():
    doc = TestMergeableDoc()
    min_updated_at = now()
    session = Session()
    session.revise(doc)
    assert isinstance(doc.__revision__, Revision)
    assert doc.__revision__.session is session
    assert min_updated_at <= doc.__revision__.updated_at <= now()
    time.sleep(0.1)
    min_updated_at = now()
    session.revise(doc)
    assert min_updated_at <= doc.__revision__.updated_at <= now()
