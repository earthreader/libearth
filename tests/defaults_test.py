import datetime

from libearth.defaults import BlogrollLinkParser, get_default_subscriptions
from libearth.feed import Person
from libearth.tz import utc
from .conftest import MOCK_URLS


HTML_LINKING_BLOGROLL = '''
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="utf-8">
    <title>Earth Reader</title>
    <link rel="blogroll" type="text/x-opml" title="Earth Reader Feeds"
        href="feeds.xml">
    </head>
    <body>
    <h1>Earth Reader</h1>
    </body>
    </html>
'''

HTML_NOT_LINKING_BLOGROLL = '''
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="utf-8">
    <title>Earth Reader</title>
    </head>
    <body>
    <h1>Earth Reader</h1>
    </body>
    </html>
'''


def test_blogroll_link_parser():
    parser = BlogrollLinkParser()
    parser.feed(HTML_LINKING_BLOGROLL)
    assert parser.get_link() == ('feeds.xml', 'Earth Reader Feeds')
    parser = BlogrollLinkParser()
    parser.feed(HTML_NOT_LINKING_BLOGROLL)
    assert parser.get_link() is None


OPML = '''\
<?xml version="1.0" encoding="utf-8"?>
<opml version="2.0">
<head>
    <ownerName>Earth Reader Team</ownerName>
    <ownerEmail>earthreader@librelist.com</ownerEmail>
    <ownerId>http://earthreader.org/</ownerId>
</head>
<body>
    <outline title="Earth Reader Blog"
        htmlUrl="http://blog.earthreader.org/"
        created="Tue, 29 Oct 2013 15:30:00 +0000"
        xmlUrl="http://blog.earthreader.org/index.xml"
        text="Earth Reader Blog"
        type="rss" />
</body>
</opml>
'''


MOCK_URLS.update({
    'http://blogroll.com/web/': (200, 'text/html', HTML_LINKING_BLOGROLL),
    'http://blogroll.com/web/feeds.xml': (200, 'text/x-opml', OPML),
})


def test_get_default_subscriptions(fx_opener):
    subs = get_default_subscriptions('http://blogroll.com/web/')
    assert subs.owner == Person(
        name='Earth Reader Team',
        email='earthreader@librelist.com',
        uri='http://earthreader.org/'
    )
    assert len(subs) == 1
    sub = next(iter(subs))
    assert sub.label == 'Earth Reader Blog'
    assert sub.feed_uri == 'http://blog.earthreader.org/index.xml'
    assert sub.alternate_uri == 'http://blog.earthreader.org/'
    assert sub.created_at == datetime.datetime(2013, 10, 29, 15, 30, tzinfo=utc)
    subs2 = get_default_subscriptions('http://blogroll.com/web/feeds.xml')
    assert subs2.owner == subs.owner
    assert frozenset(subs2) == frozenset(subs)
