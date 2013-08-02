from pytest import raises

from libearth.compat import xrange
from libearth.feed import AlreadyExistException, Feed


def test_count_empty_list():
    f = Feed()
    assert len(f) == 0


def test_count_duplicated_url():
    f = Feed()
    with raises(AlreadyExistException):
        for i in xrange(30):
            f.add_feed('title', 'url')

    assert len(f) == 1


def test_count_after_remove():
    f = Feed()
    f.add_feed('title', 'url')
    f.remove_feed('url')

    assert len(f) == 0
