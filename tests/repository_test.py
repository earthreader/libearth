import os.path

from pytest import mark, raises

from libearth.repository import (FileNotFoundError, FileSystemRepository,
                                 NotADirectoryError, Repository,
                                 RepositoryKeyError)


class RepositoryNotImplemented(Repository):

    pass


class RepositoryImplemented(Repository):

    def read(self, key):
        super(RepositoryImplemented, self).read(key)
        return b''

    def write(self, key, iterable):
        super(RepositoryImplemented, self).write(key, iterable)

    def exists(self, key):
        super(RepositoryImplemented, self).exists(key)
        return True

    def list(self, key):
        super(RepositoryImplemented, self).list(key)
        return frozenset()


def test_not_implemented_error():
    r = RepositoryNotImplemented()
    with raises(NotImplementedError):
        r.read(['key'])
    with raises(NotImplementedError):
        r.write(['key'], '')
    with raises(NotImplementedError):
        r.exists(['key'])
    with raises(NotImplementedError):
        r.list(['key'])
    r2 = RepositoryImplemented()
    assert r2.read(['key']) == b''
    r2.write(['key'], b'')
    assert r2.exists(['key'])
    assert r2.list(['key']) == frozenset()


def test_file_read(tmpdir):
    f = FileSystemRepository(str(tmpdir))
    with raises(RepositoryKeyError):
        f.read(['key'])
    tmpdir.join('key').write('file content')
    assert b''.join(f.read(['key'])) == b'file content'
    with raises(RepositoryKeyError):
        f.read(['dir', 'dir2', 'key'])
    tmpdir.mkdir('dir').mkdir('dir2').join('key').write('file content')
    assert b''.join(f.read(['dir', 'dir2', 'key'])) == b'file content'


def test_file_write(tmpdir):
    f = FileSystemRepository(str(tmpdir))
    f.write(['key'], [b'file ', b'content'])
    assert tmpdir.join('key').read() == 'file content'
    f.write(['dir', 'dir2', 'key'], [b'deep ', b'file ', b'content'])
    assert tmpdir.join('dir', 'dir2', 'key').read() == 'deep file content'
    with raises(RepositoryKeyError):
        f.write([], [b'file ', b'content'])


def test_file_exists(tmpdir):
    f = FileSystemRepository(str(tmpdir))
    tmpdir.mkdir('dir').join('file').write('content')
    tmpdir.join('file').write('content')
    assert f.exists(['dir'])
    assert f.exists(['dir', 'file'])
    assert f.exists(['file'])
    assert not f.exists(['dir', 'file-not-exist'])
    assert not f.exists(['dir-not-exist'])


def test_file_list(tmpdir):
    f = FileSystemRepository(str(tmpdir))
    d = tmpdir.mkdir('dir')
    for i in range(100):
        d.mkdir('d{0}'.format(i))
    assert (frozenset(f.list(['dir'])) ==
            frozenset('d{0}'.format(i) for i in range(100)))
    with raises(RepositoryKeyError):
        f.list(['not-exist'])


def test_file_not_found(tmpdir):
    path = tmpdir.join('not-exist')
    with raises(FileNotFoundError):
        FileSystemRepository(str(path), mkdir=False)
    FileSystemRepository(str(path))
    assert os.path.isdir(str(path))


def test_not_dir(tmpdir):
    path = tmpdir.join('not-dir.txt')
    path.write('')
    with raises(NotADirectoryError):
        FileSystemRepository(str(path))


def test_atomicity(tmpdir):
    repo = FileSystemRepository(str(tmpdir), atomic=True)
    repo.write(['key'], [b'first ', b'revision'])

    def gen():
        assert b''.join(repo.read(['key'])) == b'first revision'
        yield b'second '
        assert b''.join(repo.read(['key'])) == b'first revision'
        yield b'revision'
        assert b''.join(repo.read(['key'])) == b'first revision'
    repo.write(['key'], gen())
    assert b''.join(repo.read(['key'])) == b'second revision'
