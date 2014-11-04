import functools
try:
    import httplib
except ImportError:
    from http import client as httplib
import io
try:
    import urllib2
except ImportError:
    from urllib import request as urllib2

from pytest import fixture

from libearth.compat import IRON_PYTHON, text_type
from libearth.session import RevisionSet


MOCK_URLS = {}


def pytest_assertrepr_compare(op, left, right):
    if op == '==' and isinstance(left, RevisionSet) and \
       isinstance(right, RevisionSet):
        return list(compare_revision_sets(left, right))


def compare_revision_sets(left, right):
    left_keys = frozenset(left.keys())
    right_keys = frozenset(right.keys())
    yield 'RevisionSet(...{0} items...) != RevisionSet(...{1} items...)'.format(
        len(left_keys), len(right_keys)
    )
    left_more = left_keys - right_keys
    if left_more:
        yield '{0} session(s) the left set has more:'.format(len(left_more))
        for session in left_more:
            yield '- {0!r}'.format(session)
    right_more = right_keys - left_keys
    if right_more:
        yield '{0} session(s) the right set has more:'.format(len(right_more))
        for session in right_more:
            yield '- {0!r}'.format(session)
    common = left_keys & right_keys
    different_keys = frozenset(k for k in common if left[k] != right[k])
    if different_keys:
        yield '{0} session(s) have different times:'.format(len(different_keys))
        for k in different_keys:
            yield '- {0!r}: {1!r} != {2!r}'.format(k, left[k], right[k])


class TestHTTPHandler(urllib2.HTTPHandler):

    def http_open(self, req):
        url = req.get_full_url()
        try:
            status_code, mimetype, content = MOCK_URLS[url]
        except KeyError:
            return urllib2.HTTPHandler.http_open(self, req)
        if IRON_PYTHON:
            from StringIO import StringIO
            buffer_ = StringIO(content)
        elif isinstance(content, text_type):
            buffer_ = io.StringIO(content)
        else:
            buffer_ = io.BytesIO(content)
        resp = urllib2.addinfourl(buffer_, {'content-type': mimetype}, url)
        resp.code = status_code
        resp.msg = httplib.responses[status_code]
        return resp


@fixture
def fx_opener(request):
    request.addfinalizer(
        functools.partial(setattr, urllib2, '_opener', urllib2._opener)
    )
    opener = urllib2.build_opener(TestHTTPHandler)
    urllib2.install_opener(opener)
    return opener
