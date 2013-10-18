import collections

from pytest import fixture, raises

from libearth.repository import Repository, RepositoryKeyError
from libearth.schema import read
from libearth.session import MergeableDocumentElement, Session
from libearth.stage import (BaseStage, Directory, Route,
                            compile_format_to_pattern)


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
        'doc.SESSID.xml': '<test />',
        'dir': {
            'abc': {'SESSID.xml': '<test />'},
            'def': {'SESSID.xml': '<test />'}
        },
        'dir2': {
            'preabc': {
                'xyzpost': {'SESSID.xml': '<test />'},
                'xxxpost': {'SESSID.xml': '<test />'},
                'invalid': {}
            },
            'predef': {
                'xyzpost': {'SESSID.xml': '<test />'},
                'xxxpost': {'SESSID.xml': '<test />'},
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
        if isinstance(key, collections.Mapping):
            raise RepositoryKeyError(key)
        return key

    def write(self, key, iterable):
        super(TestRepository, self).write(key, iterable)
        data = self.data
        for k in key[:-1]:
            data = data.setdefalt(k, {})
        data[key[-1]] = ''.join(iterable)

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


def test_stage_read(fx_session, fx_stage):
    doc = fx_stage.read(TestDoc, ['doc.{0}.xml'.format(fx_session.identifier)])
    assert isinstance(doc, TestDoc)
    assert doc.__revision__.session is fx_session


def test_stage_write(fx_repo, fx_session, fx_stage):
    doc = TestDoc()
    fx_stage.write(['doc.{0}.xml'.format(fx_session.identifier)], doc)
    xml = fx_repo.data['doc.{0}.xml'.format(fx_session.identifier)]
    read_doc = read(TestDoc, xml)
    assert isinstance(read_doc, TestDoc)
    assert read_doc.__revision__.session is fx_session


def test_get_flat_route(fx_session, fx_stage):
    doc = fx_stage.doc
    assert isinstance(doc, TestDoc)
    assert doc.__revision__.session is fx_session


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
