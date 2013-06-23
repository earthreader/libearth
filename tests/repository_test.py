from pytest import raises

from libearth.repository import (FileNotFoundError, NotADirectoryError,
                                 Repository)


def test_file_not_found(tmpdir):
    path = tmpdir.join('not-exist')
    with raises(FileNotFoundError):
        Repository(str(path))


def test_not_dir(tmpdir):
    path = tmpdir.join('not-dir.txt')
    path.write('')
    with raises(NotADirectoryError):
        Repository(str(path))
