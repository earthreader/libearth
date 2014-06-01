import collections
import io
import logging
import threading

from pytest import fixture, raises

from libearth.compat import IRON_PYTHON, binary_type
from libearth.repository import (FileSystemRepository, Repository,
                                 RepositoryKeyError)
from libearth.schema import read
from libearth.session import MergeableDocumentElement, Session
from libearth.stage import (BaseStage, Directory, DirtyBuffer, Route,
                            TransactionError, compile_format_to_pattern)
from libearth.tz import now


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


class MemoryRepository(Repository):

    def __init__(self):
        self.data = {}

    def read(self, key):
        super(MemoryRepository, self).read(key)
        logger = logging.getLogger(__name__ + '.MemoeryRepository.read')
        data = self.data
        for k in key:
            try:
                data = data[k]
            except KeyError as e:
                logger.debug(e, exc_info=1)
                raise RepositoryKeyError(key)
        if isinstance(data, collections.Mapping):
            logger.debug('RepositoryKeyError(%r)', key)
            raise RepositoryKeyError(key)
        logger.debug('%r: %r', key, data)
        return data,

    def write(self, key, iterable):
        super(MemoryRepository, self).write(key, iterable)
        logger = logging.getLogger(__name__ + '.MemoeryRepository.write')
        data = self.data
        for k in key[:-1]:
            data = data.setdefault(k, {})
        buffer_ = io.BytesIO()
        for chunk in iterable:
            assert isinstance(chunk, binary_type), 'chunk = ' + repr(chunk)
            buffer_.write(chunk)
        logger.debug('%r: %r', key, buffer_.getvalue())
        data[key[-1]] = buffer_.getvalue()

    def exists(self, key):
        super(MemoryRepository, self).exists(key)
        logger = logging.getLogger(__name__ + '.MemoeryRepository.exists')
        data = self.data
        for k in key:
            try:
                data = data[k]
            except KeyError:
                logger.debug('%r does not exist', key, exc_info=1)
                return False
        logger.debug('%r exists', key, exc_info=1)
        return True

    def list(self, key):
        super(MemoryRepository, self).list(key)
        logger = logging.getLogger(__name__ + '.MemoeryRepository.list')
        data = self.data
        for k in key:
            try:
                data = data[k]
            except KeyError as e:
                logger.debug(e, exc_info=1)
                raise RepositoryKeyError(key)
        if isinstance(data, collections.Mapping):
            logger.debug('list(%r): %r', key, sorted(frozenset(data)))
            return frozenset(data)
        logger.debug('RepositoryKeyError(%r)', key)
        raise RepositoryKeyError(key)


class TestRepository(MemoryRepository):

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
    # It's empty at its initial state
    assert fx_stage.sessions == frozenset()
    assert fx_other_stage.sessions == frozenset()
    # They get touched when there's any transaction
    with fx_stage:
        pass
    assert fx_stage.sessions == frozenset([fx_session])
    assert fx_other_stage.sessions == frozenset([fx_session])
    with fx_other_stage:
        pass
    assert fx_stage.sessions == frozenset([fx_session, fx_other_session])
    assert fx_other_stage.sessions == frozenset([fx_session, fx_other_session])


def test_stage_read(fx_session, fx_stage):
    with fx_stage:
        doc = fx_stage.read(TestDoc,
                            ['doc.{0}.xml'.format(fx_session.identifier)])
        assert isinstance(doc, TestDoc)
        assert doc.__revision__.session is fx_session


def test_stage_write(fx_repo, fx_session, fx_stage):
    doc = TestDoc()
    min_ts = now()
    with fx_stage:
        wdoc = fx_stage.write(['doc.{0}.xml'.format(fx_session.identifier)],
                              doc)
    assert wdoc.__revision__.session is fx_session
    assert min_ts <= wdoc.__revision__.updated_at <= now()
    xml = fx_repo.data['doc.{0}.xml'.format(fx_session.identifier)]
    read_doc = read(TestDoc, [xml])
    assert isinstance(read_doc, TestDoc)
    assert read_doc.__revision__ == wdoc.__revision__


def test_get_flat_route(fx_session, fx_stage):
    with fx_stage:
        doc = fx_stage.doc
    assert isinstance(doc, TestDoc)
    assert doc.__revision__.session is fx_session
    with fx_stage:
        assert fx_stage.doc.__revision__ == doc.__revision__


def test_set_flat_route(fx_session, fx_stage, fx_other_session, fx_other_stage):
    with fx_stage:
        fx_stage.doc = TestDoc()
        doc_a = fx_stage.doc
        assert doc_a.__revision__.session is fx_session
    with fx_other_stage:
        doc_b = fx_other_stage.doc
        assert doc_b.__revision__.session is fx_other_session
        fx_session.revise(doc_a)
        assert (doc_b.__revision__.updated_at ==
                fx_other_stage.doc.__revision__.updated_at)
        assert (fx_other_stage.doc.__revision__.updated_at <=
                doc_a.__revision__.updated_at)
    with fx_stage:
        fx_stage.doc = doc_a
    with fx_other_stage:
        assert (fx_other_stage.doc.__revision__.updated_at >=
                doc_a.__revision__.updated_at)


def test_get_dir_route(fx_session, fx_stage):
    with fx_stage:
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
    with fx_stage:
        doc_a = fx_stage.dir_docs['abc']
    assert doc_a.__revision__.session is fx_session
    with fx_other_stage:
        doc_b = fx_other_stage.dir_docs['abc']
        assert doc_b.__revision__.session is fx_other_session
        fx_session.revise(doc_a)
        assert (doc_b.__revision__.updated_at ==
                fx_other_stage.dir_docs['abc'].__revision__.updated_at)
        assert (fx_other_stage.dir_docs['abc'].__revision__.updated_at <=
                doc_a.__revision__.updated_at)
    with fx_stage:
        fx_stage.dir_docs['abc'] = doc_a
    with fx_other_stage:
        assert (fx_other_stage.dir_docs['abc'].__revision__.updated_at >=
                doc_a.__revision__.updated_at)


def test_get_deep_route(fx_session, fx_stage):
    with fx_stage:
        dir = fx_stage.deep_docs
        assert isinstance(dir, Directory)
        assert len(dir) == 2
        assert frozenset(dir) == frozenset(['abc', 'def'])
        with raises(KeyError):
            dir['not-exist']
    with fx_stage:
        dir2 = dir['abc']
        assert isinstance(dir2, Directory)
        assert len(dir2) == 2
        assert frozenset(dir2) == frozenset(['xyz', 'xxx'])
        with raises(KeyError):
            dir2['not-exist']
    with fx_stage:
        doc = dir2['xyz']
        assert isinstance(doc, TestDoc)
        assert doc.__revision__.session is fx_session


def test_dirty_buffer(tmpdir):
    if IRON_PYTHON:
        repo = MemoryRepository()
    else:
        repo = FileSystemRepository(str(tmpdir))
    dirty = DirtyBuffer(repo, threading.RLock())
    key = ['key']
    dir_key = []
    with raises(RepositoryKeyError):
        dirty.read(key)
    assert not dirty.exists(key)
    assert frozenset(dirty.list(dir_key)) == frozenset([])
    with raises(RepositoryKeyError):
        repo.read(key)
    assert not repo.exists(key)
    assert frozenset(repo.list(dir_key)) == frozenset([])
    dirty.write(key, [b'dirty ', b'value'])
    assert b''.join(dirty.read(key)) == b'dirty value'
    assert dirty.exists(key)
    assert frozenset(dirty.list(dir_key)) == frozenset(key)
    with raises(RepositoryKeyError):
        repo.read(key)
    assert not repo.exists(key)
    assert frozenset(repo.list(dir_key)) == frozenset([])
    assert dirty.dictionary
    dirty.flush()
    assert not dirty.dictionary
    assert b''.join(repo.read(key)) == b'dirty value'
    assert repo.exists(key)
    assert frozenset(repo.list(dir_key)) == frozenset(key)


def test_doubly_begun_transaction(fx_stage):
    with fx_stage:
        with raises(TransactionError):
            with fx_stage:
                pass
