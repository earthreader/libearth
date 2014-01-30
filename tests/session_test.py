from __future__ import print_function

import collections
import datetime
import operator
import sys
import time

from pytest import fixture, mark, raises

from libearth.codecs import Integer
from libearth.compat import binary
from libearth.schema import Attribute, Child, Content, Text, Element
from libearth.session import (SESSION_XMLNS, MergeableDocumentElement, Revision,
                              RevisionCodec, RevisionSet, RevisionSetCodec,
                              Session, ensure_revision_pair, parse_revision)
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


def test_revision_set_contains(fx_revision_set):
    assert not fx_revision_set.contains(Revision(Session('key0'), now()))
    assert not fx_revision_set.contains(
        Revision(Session('key1'),
                 datetime.datetime(2013, 9, 27, 16, 54, 50, tzinfo=utc))
    )
    assert fx_revision_set.contains(
        Revision(Session('key1'),
                 datetime.datetime(2013, 9, 22, 16, 58, 57, tzinfo=utc))
    )
    assert fx_revision_set.contains(
        Revision(Session('key1'),
                 datetime.datetime(2012, 9, 22, 16, 58, 57, tzinfo=utc))
    )
    assert not fx_revision_set.contains(
        Revision(Session('key0'),
                 datetime.datetime(2012, 9, 22, 16, 58, 57, tzinfo=utc))
    )


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


class TestUniqueEntity(Element):

    ident = Text('ident', required=True)
    value = Attribute('value')

    def __entity_id__(self):
        return self.ident


class TestRevisedEntity(Element):

    ident = Text('ident', required=True)
    rev = Attribute('rev', Integer)
    value = Attribute('value')

    def __entity_id__(self):
        return self.ident

    def __merge_entities__(self, other):
        return max(self, other, key=operator.attrgetter('rev'))


class TestMergeableDoc(MergeableDocumentElement):

    __tag__ = 'merge-test'
    multi_text = Text('multi-text', multiple=True)
    text = Text('text')
    attr = Attribute('attr')
    unique_entities = Child('unique-entity', TestUniqueEntity, multiple=True)
    rev_entities = Child('rev-multi-entity', TestRevisedEntity, multiple=True)
    rev_entity = Child('rev-single-entity', TestRevisedEntity)
    nullable = Child('nullable-entity', TestUniqueEntity)


class TestMergeableContentDoc(MergeableDocumentElement):

    __tag__ = 'merge-content-test'
    content = Content()


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


@mark.parametrize('revised', [True, False])
def test_session_pull(revised):
    s1 = Session('s1')
    s2 = Session('s2')
    a = TestMergeableDoc(multi_text=['a', 'b', 'c'])
    if revised:
        s1.revise(a)
    b = s2.pull(a)
    assert b is not a
    assert b.__revision__.session is s2
    if revised:
        assert b.__revision__.updated_at == a.__revision__.updated_at
    assert b.multi_text == ['a', 'b', 'c']
    assert a.multi_text is not b.multi_text
    if revised:
        assert a.__revision__.session is s1


def test_session_pull_same_session():
    session = Session('s1')
    doc = TestMergeableDoc()
    session.revise(doc)
    assert session.pull(doc) is doc


def wait():
    # Windows doesn't provide enough precision to datetime.now().
    if sys.platform == 'win32':
        time.sleep(0.5)


def test_session_merge():
    #  s1  s2
    #  ------
    #  (1) a   b (2)
    #      | / |
    #  (3) c   b (4)
    #      | \ |
    #      |   d (5)
    #      | /
    #  (5) e
    s1 = Session('s1')
    a = TestMergeableDoc(
        attr='a',
        text='a',
        multi_text=['a', 'b', 'c'],
        unique_entities=[
            TestUniqueEntity(ident='a', value='s1-a'),
            TestUniqueEntity(ident='b', value='s1-b'),
            TestUniqueEntity(ident='c', value='s1-c')
        ],
        rev_entities=[
            TestRevisedEntity(ident='a', value='s1-a', rev=2),
            TestRevisedEntity(ident='b', value='s1-b', rev=2),
            TestRevisedEntity(ident='c', value='s1-c', rev=2)
        ],
        rev_entity=TestRevisedEntity(ident='a', value='s1', rev=1)
    )
    a_c = TestMergeableContentDoc(content='a')
    s1.revise(a)  # (1)
    s1.revise(a_c)
    wait()
    s2 = Session('s2')
    b = TestMergeableDoc(
        attr='b',
        text='b',
        multi_text=['d', 'e', 'f'],
        unique_entities=[
            TestUniqueEntity(ident='c', value='s2-c'),
            TestUniqueEntity(ident='d', value='s2-d'),
            TestUniqueEntity(ident='e', value='s2-e')
        ],
        rev_entities=[
            TestRevisedEntity(ident='b', value='s2-b', rev=1),
            TestRevisedEntity(ident='c', value='s2-c', rev=3),
            TestRevisedEntity(ident='d', value='s2-d', rev=2)
        ],
        rev_entity=TestRevisedEntity(ident='a', value='s2', rev=2)
    )
    b_c = TestMergeableContentDoc(content='b')
    s2.revise(b)  # (2)
    s2.revise(b_c)
    wait()
    c = s1.merge(b, a)  # (3)
    c_c = s1.merge(b_c, a_c)
    wait()
    assert c.__revision__.session is s1
    assert c.__revision__.updated_at > a.__revision__.updated_at
    assert c.__base_revisions__ == RevisionSet([a.__revision__, b.__revision__])
    print((c.attr, c.text, c_c.content))
    assert c.attr == c.text == c_c.content == 'b'
    assert list(c.multi_text) == ['a', 'b', 'c', 'd', 'e', 'f']
    assert ([entity.value for entity in c.unique_entities] ==
            ['s1-a', 's1-b', 's2-c', 's2-d', 's2-e'])
    assert ([(e.value, e.rev) for e in c.rev_entities] ==
            [('s1-a', 2), ('s1-b', 2), ('s2-c', 3), ('s2-d', 2)])
    assert c.rev_entity.rev == 2
    assert c.rev_entity.value == 's2'
    assert c.nullable is None
    c.nullable = TestUniqueEntity(ident='nullable', value='nullable')
    b.attr = b.text = b_c.content = 'd'
    b.multi_text.append('blah')
    b.unique_entities.append(TestUniqueEntity(ident='blah', value='s2-blah'))
    s2.revise(b)  # (4)
    s2.revise(b_c)
    wait()
    assert list(b.multi_text) == ['d', 'e', 'f', 'blah']
    assert ([entity.value for entity in b.unique_entities] ==
            ['s2-c', 's2-d', 's2-e', 's2-blah'])
    d = s2.merge(b, c)  # (5)
    d_c = s2.merge(b_c, c_c)
    wait()
    assert d.__revision__.session is s2
    assert d.__revision__.updated_at >= c.__revision__.updated_at
    assert d.__base_revisions__ == RevisionSet([b.__revision__, c.__revision__])
    assert d.attr == d.text == d_c.content == 'd'
    assert list(d.multi_text) == ['a', 'b', 'c', 'd', 'e', 'f', 'blah']
    assert ([entity.value for entity in d.unique_entities] ==
            ['s1-a', 's1-b', 's2-c', 's2-d', 's2-e', 's2-blah'])
    assert d.nullable is not None
    assert d.nullable.value == 'nullable'
    e = s1.merge(c, d)  # (5)
    e_c = s1.merge(c_c, d_c)
    wait()
    assert e.__revision__.session is s1
    assert e.__revision__.updated_at == d.__revision__.updated_at
    assert e.__base_revisions__ == d.__base_revisions__
    assert e.attr == e.text == e_c.content == 'd'
    assert list(e.multi_text) == ['a', 'b', 'c', 'd', 'e', 'f', 'blah']
    assert ([entity.value for entity in d.unique_entities] ==
            ['s1-a', 's1-b', 's2-c', 's2-d', 's2-e', 's2-blah'])


@mark.parametrize(('iterable', 'rv'), [
    (['<doc ', 'xmlns:s="', SESSION_XMLNS,
      '" s:revision="test 2013-09-22T03:43:40Z" ', 's:bases="" ', '/>'],
     (Revision(Session('test'),
               datetime.datetime(2013, 9, 22, 3, 43, 40, tzinfo=utc)),
      RevisionSet())),
    (['<doc ', 'xmlns:s="', SESSION_XMLNS,
      '" s:revision="test 2013-09-22T03:43:40Z" ', 's:bases="">',
      '<a />', '</doc>'],
     (Revision(Session('test'),
               datetime.datetime(2013, 9, 22, 3, 43, 40, tzinfo=utc)),
      RevisionSet())),
    (['<doc ', 'xmlns:s="', SESSION_XMLNS,
      '" s:revision="test 2013-09-22T03:43:40Z" ', 's:bases=""><a /></doc>'],
     (Revision(Session('test'),
               datetime.datetime(2013, 9, 22, 3, 43, 40, tzinfo=utc)),
      RevisionSet())),
    (['<?xml version="1.0" encoding="utf-8"?>\n', '<ns1:feed xmlns:ns0="',
      SESSION_XMLNS, '" xmlns:ns1="http://www.w3.org/2005/Atom" ',
      'xmlns:ns2="http://earthreader.org/mark/" ',
      'ns0:bases="a 2013-11-17T16:36:46.003058Z" ',
      'ns0:revision="a 2013-11-17T16:36:46.033062Z">', '</ns1:feed>'],
     (Revision(Session('a'),
               datetime.datetime(2013, 11, 17, 16, 36, 46, 33062, tzinfo=utc)),
      RevisionSet([
          Revision(
              Session('a'),
              datetime.datetime(2013, 11, 17, 16, 36, 46, 3058, tzinfo=utc)
          )
      ]))),
    (['<doc ', ' revision="test 2013-09-22T03:43:40Z" ', 'bases="" ', '/>'],
     None),
    (['<doc ', ' revision="test 2013-09-22T03:43:40Z" ', 'bases="">',
      '<a />', '</doc>'], None),
    (['<doc>', '<a />' '</doc>'], None),
    (['<doc', ' />'], None),
])
def test_parse_revision(iterable, rv):
    assert parse_revision(map(binary, iterable)) == rv
