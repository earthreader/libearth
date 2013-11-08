import collections
import datetime
import hashlib

from pytest import fixture, raises

from libearth.compat import binary
from libearth.feed import Entry, Feed, Person, Text
from libearth.repository import (FileSystemRepository, Repository,
                                 RepositoryKeyError)
from libearth.schema import read
from libearth.session import MergeableDocumentElement, Session
from libearth.stage import (BaseStage, Directory, Route, Stage,
                            compile_format_to_pattern)
from libearth.subscribe import Category, Subscription, SubscriptionList
from libearth.tz import now, utc


def test_compile_format_to_pattern():
    p = compile_format_to_pattern('{0}')
    p_msg = 'p.pattern = ' + repr(p.pattern)
    assert p.match('anything'), p_msg
    assert p.match('something'), p_msg
    assert p.match('no-match'), p_msg
    assert p.match('somehow'), p_msg
    p2 = compile_format_to_pattern('{0}thing')
    p2_msg = 'p2.pattern = ' + repr(p2.pattern)
    assert p2.match('anything'), p2_msg
    assert p2.match('something'), p2_msg
    assert not p2.match('no-match'), p2_msg
    assert not p2.match('somehow'), p2_msg
    p3 = compile_format_to_pattern('some{0}')
    p3_msg = 'p3.pattern = ' + repr(p3.pattern)
    assert not p3.match('anything'), p3_msg
    assert p3.match('something'), p3_msg
    assert not p3.match('no-match'), p3_msg
    assert p3.match('somehow'), p3_msg
    p4 = compile_format_to_pattern('pre{0}post')
    p4_msg = 'p4.pattern = ' + repr(p4.pattern)
    assert not p4.match('something'), p4_msg
    assert not p4.match('no-match'), p4_msg
    assert not p4.match('preonly'), p4_msg
    assert not p4.match('onlypost'), p4_msg
    assert p4.match('preandpost'), p4_msg
    p5 = compile_format_to_pattern('pre{0}in{1}post')
    p5_msg = 'p5.pattern = ' + repr(p5.pattern)
    assert not p5.match('something'), p5_msg
    assert not p5.match('no-match'), p5_msg
    assert not p5.match('preonly'), p5_msg
    assert not p5.match('onlypost'), p5_msg
    assert not p5.match('preandpost'), p5_msg
    assert not p5.match('inandpost'), p5_msg
    assert not p5.match('preandin'), p5_msg
    assert p5.match('preandinandpost'), p5_msg
    p6 = compile_format_to_pattern('pre{0}and{{1}}post')
    p6_msg = 'p6.pattern = ' + repr(p6.pattern)
    assert not p6.match('something'), p6_msg
    assert not p6.match('no-match'), p6_msg
    assert not p6.match('preonly'), p6_msg
    assert not p6.match('onlypost'), p6_msg
    assert not p6.match('preandpost'), p6_msg
    assert not p6.match('inandpost'), p6_msg
    assert not p6.match('preandin'), p6_msg
    assert not p6.match('preandinandpost'), p6_msg
    assert p6.match('pre,and{1}post'), p6_msg
    p7 = compile_format_to_pattern('pre{0}in{session.identifier}post')
    p7_msg = 'p7.pattern = ' + repr(p7.pattern)
    assert not p7.match('something'), p7_msg
    assert not p7.match('no-match'), p7_msg
    assert not p7.match('preonly'), p7_msg
    assert not p7.match('onlypost'), p7_msg
    assert not p7.match('preandpost'), p7_msg
    assert not p7.match('inandpost'), p7_msg
    assert not p7.match('preandin'), p7_msg
    assert p7.match('preandinandpost'), p7_msg


class TestDoc(MergeableDocumentElement):

    __tag__ = 'test'


class TestStage(BaseStage):

    doc = Route(TestDoc, ['doc.{session.identifier}.xml'])
    dir_docs = Route(
        TestDoc,
        ['dir', '{0}', '{session.identifier}.xml']
    )
    deep_docs = Route(
        TestDoc,
        ['dir2', 'pre{0}', '{1}post', '{session.identifier}.xml']
    )


class TestRepository(Repository):

    DATA = {
        'doc.SESSID.xml': b'<test />',
        'dir': {
            'abc': {'SESSID.xml': b'<test />'},
            'def': {'SESSID.xml': b'<test />'}
        },
        'dir2': {
            'preabc': {
                'xyzpost': {'SESSID.xml': b'<test />'},
                'xxxpost': {'SESSID.xml': b'<test />'},
                'invalid': {}
            },
            'predef': {
                'xyzpost': {'SESSID.xml': b'<test />'},
                'xxxpost': {'SESSID.xml': b'<test />'},
                'invalid': {}
            },
            'invalid': {}
        }
    }

    def __init__(self):
        self.data = dict(self.DATA)

    def read(self, key):
        super(TestRepository, self).read(key)
        data = self.data
        for k in key:
            try:
                data = data[k]
            except KeyError:
                raise RepositoryKeyError(key)
        if isinstance(data, collections.Mapping):
            raise RepositoryKeyError(key)
        return data,

    def write(self, key, iterable):
        super(TestRepository, self).write(key, iterable)
        data = self.data
        for k in key[:-1]:
            data = data.setdefault(k, {})
        data[key[-1]] = b''.join(iterable).decode()

    def exists(self, key):
        super(TestRepository, self).exists(key)
        data = self.data
        for k in key:
            try:
                data = data[k]
            except KeyError:
                return False
        return True

    def list(self, key):
        super(TestRepository, self).list(key)
        data = self.data
        for k in key:
            try:
                data = data[k]
            except KeyError:
                raise RepositoryKeyError(key)
        if isinstance(data, collections.Mapping):
            return frozenset(data)
        raise RepositoryKeyError(key)


@fixture
def fx_repo():
    return TestRepository()


@fixture
def fx_session():
    return Session(identifier='SESSID')


@fixture
def fx_stage(fx_repo, fx_session):
    return TestStage(fx_session, fx_repo)


@fixture
def fx_other_session():
    return Session(identifier='SESSID2')


@fixture
def fx_other_stage(fx_repo, fx_other_session):
    return TestStage(fx_other_session, fx_repo)


def test_stage_sessions(fx_session, fx_stage, fx_other_session, fx_other_stage):
    assert fx_stage.sessions == frozenset([fx_session, fx_other_session])
    assert fx_other_stage.sessions == frozenset([fx_session, fx_other_session])


def test_stage_read(fx_session, fx_stage):
    doc = fx_stage.read(TestDoc, ['doc.{0}.xml'.format(fx_session.identifier)])
    assert isinstance(doc, TestDoc)
    assert doc.__revision__.session is fx_session


def test_stage_write(fx_repo, fx_session, fx_stage):
    doc = TestDoc()
    min_ts = now()
    wdoc = fx_stage.write(['doc.{0}.xml'.format(fx_session.identifier)], doc)
    assert wdoc.__revision__.session is fx_session
    assert min_ts <= wdoc.__revision__.updated_at <= now()
    xml = fx_repo.data['doc.{0}.xml'.format(fx_session.identifier)]
    read_doc = read(TestDoc, xml)
    assert isinstance(read_doc, TestDoc)
    assert read_doc.__revision__ == wdoc.__revision__


def test_get_flat_route(fx_session, fx_stage):
    doc = fx_stage.doc
    assert isinstance(doc, TestDoc)
    assert doc.__revision__.session is fx_session
    assert fx_stage.doc.__revision__ == doc.__revision__


def test_set_flat_route(fx_session, fx_stage, fx_other_session, fx_other_stage):
    fx_stage.doc = TestDoc()
    doc_a = fx_stage.doc
    assert doc_a.__revision__.session is fx_session
    doc_b = fx_other_stage.doc
    assert doc_b.__revision__.session is fx_other_session
    fx_session.revise(doc_a)
    assert (doc_b.__revision__.updated_at ==
            fx_other_stage.doc.__revision__.updated_at)
    assert (fx_other_stage.doc.__revision__.updated_at <=
            doc_a.__revision__.updated_at)
    fx_stage.doc = doc_a
    assert (fx_other_stage.doc.__revision__.updated_at >=
            doc_a.__revision__.updated_at)


def test_get_dir_route(fx_session, fx_stage):
    dir = fx_stage.dir_docs
    assert isinstance(dir, Directory)
    assert len(dir) == 2
    assert frozenset(dir) == frozenset(['abc', 'def'])
    with raises(KeyError):
        dir['not-exist']
    doc = dir['abc']
    assert isinstance(doc, TestDoc)
    assert doc.__revision__.session is fx_session
    assert dir['abc'].__revision__ == doc.__revision__


def test_set_dir_route(fx_session, fx_stage, fx_other_session, fx_other_stage):
    doc_a = fx_stage.dir_docs['abc']
    assert doc_a.__revision__.session is fx_session
    doc_b = fx_other_stage.dir_docs['abc']
    assert doc_b.__revision__.session is fx_other_session
    fx_session.revise(doc_a)
    assert (doc_b.__revision__.updated_at ==
            fx_other_stage.dir_docs['abc'].__revision__.updated_at)
    assert (fx_other_stage.dir_docs['abc'].__revision__.updated_at <=
            doc_a.__revision__.updated_at)
    fx_stage.dir_docs['abc'] = doc_a
    assert (fx_other_stage.dir_docs['abc'].__revision__.updated_at >=
            doc_a.__revision__.updated_at)


def test_get_deep_route(fx_session, fx_stage):
    dir = fx_stage.deep_docs
    assert isinstance(dir, Directory)
    assert len(dir) == 2
    assert frozenset(dir) == frozenset(['abc', 'def'])
    with raises(KeyError):
        dir['not-exist']
    dir2 = dir['abc']
    assert isinstance(dir2, Directory)
    assert len(dir2) == 2
    assert frozenset(dir2) == frozenset(['xyz', 'xxx'])
    with raises(KeyError):
        dir2['not-exist']
    doc = dir2['xyz']
    assert isinstance(doc, TestDoc)
    assert doc.__revision__.session is fx_session


def get_hash(name):
    return hashlib.sha1(binary(name)).hexdigest()


@fixture
def fx_test_stages(tmpdir):
    repo = FileSystemRepository(str(tmpdir))
    session1 = Session('SESSIONID')
    session2 = Session('SESSIONID2')
    stage1 = Stage(session1, repo)
    stage2 = Stage(session2, repo)
    return repo, stage1, stage2


@fixture
def fx_test_feeds():
    authors = [Person(name='vio')]
    feed = Feed(id='http://feedone.com/', authors=authors,
                title=Text(value='Feed One'),
                updated_at=datetime.datetime(2013, 10, 29, 20, 55, 30,
                                             tzinfo=utc))
    updated_feed = Feed(id='http://feedone.com/', authors=authors,
                        title=Text(value='Feed One'),
                        updated_at=datetime.datetime(2013, 10, 30, 20, 55, 30,
                                                     tzinfo=utc))
    entry = Entry(id='http://feedone.com/1', authors=authors,
                  title=Text(value='Test Entry'),
                  updated_at=datetime.datetime(2013, 10, 30, 20, 55, 30,
                                               tzinfo=utc))
    updated_feed.entries.append(entry)
    return feed, updated_feed


def test_stage(fx_test_stages, fx_test_feeds):
    repo, stage1, stage2 = fx_test_stages
    feed, updated_feed = fx_test_feeds
    assert feed.id == updated_feed.id
    feed_id = feed.id
    stage1.feeds[get_hash(feed.id)] = feed
    feed1 = stage1.feeds[get_hash(feed_id)]
    feed2 = stage2.feeds[get_hash(feed_id)]
    assert feed1.updated_at == feed2.updated_at == \
        datetime.datetime(2013, 10, 29, 20, 55, 30, tzinfo=utc)
    assert not feed1.entries and not feed2.entries
    stage2.feeds[get_hash(feed_id)] = updated_feed
    feed1 = stage1.feeds[get_hash(feed_id)]
    feed2 = stage2.feeds[get_hash(feed_id)]
    assert feed1.updated_at == feed2.updated_at == \
        datetime.datetime(2013, 10, 30, 20, 55, 30, tzinfo=utc)
    assert feed1.entries[0].title == feed2.entries[0].title


@fixture
def fx_test_entries():
    entry1 = Entry(
        id='http://feed.com/entry1', title=Text(value='new1'),
        updated_at=datetime.datetime(2013, 1, 1, 0, 0, 0, tzinfo=utc))
    entry2 = Entry(
        id='http://feed.com/entry2', title=Text(value='new2'),
        updated_at=datetime.datetime(2013, 1, 1, 0, 0, 1, tzinfo=utc))
    return entry1, entry2


def test_entries(fx_test_stages, fx_test_feeds, fx_test_entries):
    repo, stage1, stage2 = fx_test_stages
    feed1, feed2 = fx_test_feeds
    entry1, entry2 = fx_test_entries

    assert feed1.id == feed2.id

    feed1.entries.append(entry1)
    feed2.entries.append(entry2)
    print(feed1.entries)
    print(feed2.entries)

    assert entry1 in feed1.entries and entry2 in feed2.entries
    assert entry2 not in feed1.entries and entry1 not in feed2.entries

    stage1.feeds[get_hash(feed1.id)] = feed1
    stage2.feeds[get_hash(feed2.id)] = feed2

    feed1 = stage1.feeds[get_hash(feed1.id)]
    feed2 = stage2.feeds[get_hash(feed2.id)]
    print(feed1.entries)
    print(feed2.entries)

    assert entry2 in feed1.entries and entry1 in feed2.entries


@fixture
def fx_test_opml(fx_test_stages):
    repo, stage1, stage2 = fx_test_stages
    sub_list = SubscriptionList()
    subscription = Subscription(label='test', feed_uri='http://asdf.com')
    stage1.subscriptions = sub_list
    assert len(stage1.subscriptions) == 0
    sub_list.add(subscription)
    new_stage = Stage(Session('SESSIONID'), repo)
    assert len(new_stage.subscriptions) == 1
