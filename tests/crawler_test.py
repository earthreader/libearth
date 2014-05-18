import datetime
try:
    import httplib
except ImportError:
    from http import client as httplib
import io
import os.path
try:
    import urllib2
except ImportError:
    from urllib import request as urllib2

from pytest import mark, raises

from libearth.compat import IRON_PYTHON, text_type
from libearth.crawler import CrawlError, CrawlResult, crawl, get_feed
from libearth.feed import Feed, Link, Text
from libearth.subscribe import Category, SubscriptionList
from libearth.tz import utc


atom_xml = """
<feed xmlns="http://www.w3.org/2005/Atom">
    <title type="text">Atom Test</title>
    <subtitle type="text">Earth Reader</subtitle>
    <id>http://vio.atomtest.com/feed/atom</id>
    <updated>2013-08-19T07:49:20+07:00</updated>
    <link rel="alternate" type="text/html" href="http://vio.atomtest.com/" />
    <link rel="self" type="application/atom+xml"
        href="http://vio.atomtest.com/feed/atom" />
    <link rel="icon" href="http://vio.atomtest.com/favicon.ico" />
    <author>
        <name>vio</name>
        <email>vio.bo94@gmail.com</email>
    </author>
    <category term="Python" />
    <contributor>
        <name>dahlia</name>
    </contributor>
    <generator uri="http://wordpress.com/">WordPress.com</generator>
    <icon>http://vio.atomtest.com/images/icon.jpg</icon>
    <logo>http://vio.atomtest.com/images/logo.jpg</logo>
    <rights>vio company all rights reserved</rights>
    <updated>2013-08-10T15:27:04Z</updated>
    <entry xml:base="http://basetest.com/">
        <id>two</id>
        <author>
            <name>kjwon</name>
        </author>
        <title>xml base test</title>
        <updated>2013-08-17T03:28:11Z</updated>
    </entry>
    <entry>
        <id>one</id>
        <author>
            <name>vio</name>
        </author>
        <title>Title One</title>
        <link rel="self" href="http://vio.atomtest.com/?p=12345" />
        <updated>2013-08-10T15:27:04Z</updated>
        <published>2013-08-10T15:26:15Z</published>
        <category scheme="http://vio.atomtest.com" term="Category One" />
        <category scheme="http://vio.atomtest.com" term="Category Two" />
        <content>Hello World</content>
    </entry>
</feed>
"""


atom_reversed_entries = """
<feed xmlns="http://www.w3.org/2005/Atom">
    <title type="text">Feed One</title>
    <id>http://feedone.com/feed/atom/</id>
    <updated>2013-08-19T07:49:20+07:00</updated>
    <link type="text/html" rel="alternate" href="http://feedone.com" />
    <entry>
        <title>Feed One: Entry One</title>
        <id>http://feedone.com/feed/atom/1/</id>
        <updated>2013-08-19T07:49:20+07:00</updated>
        <published>2013-08-19T07:49:20+07:00</published>
        <content>This is content of Entry One in Feed One</content>
    </entry>
    <entry>
        <title>Feed One: Entry Two</title>
        <id>http://feedone.com/feed/atom/2/</id>
        <updated>2013-10-19T07:49:20+07:00</updated>
        <published>2013-10-19T07:49:20+07:00</published>
        <content>This is content of Entry Two in Feed One</content>
    </entry>
</feed>
"""


rss_xml = """
<rss version="2.0">
<channel>
    <title>Vio Blog</title>
    <link>http://rsstest.com/</link>
    <description>earthreader</description>
    <copyright>Copyright2013, Vio</copyright>
    <managingEditor>vio.bo94@gmail.com</managingEditor>
    <webMaster>vio.bo94@gmail.com</webMaster>
    <pubDate>Sat, 17 Sep 2002 00:00:01 GMT</pubDate>
    <lastBuildDate>Sat, 07 Sep 2002 00:00:01 GMT</lastBuildDate>
    <category>Python</category>
    <ttl>10</ttl>
    <item>
        <title>test one</title>
        <link>http://vioblog.com/12</link>
        <description>This is the content</description>
        <author>vio.bo94@gmail.com</author>
        <enclosure url="http://vioblog.com/mp/a.mp3" type="audio/mpeg" />
        <source url="http://sourcetest.com/rss.xml">
            Source Test
        </source>
        <category>RSS</category>
        <guid>http://vioblog.com/12</guid>
        <pubDate>Sat, 07 Sep 2002 00:00:01 GMT</pubDate>
    </item>
</channel>
</rss>
"""


rss_website_html = '''\
<!DOCTYPE>
<html>
<head>
  <title>RSS Test</title>
  <link rel="shotcut icon" href="images/favicon.ico">
</head>
<body>
</body>
</html>
'''


rss_source_xml = """
<rss version="2.0">
    <channel>
        <title>Source Test</title>
        <link>http://sourcetest.com/</link>
        <description>for source tag test</description>
        <item>
            <title>It will not be parsed</title>
        </item>
        <pubDate>Sat, 17 Sep 2002 00:00:01 GMT</pubDate>
    </channel>
</rss>
"""

favicon_test_atom_xml = '''
<feed xmlns="http://www.w3.org/2005/Atom">
    <title type="text">Favicon Test</title>
    <id>http://favicontest.com/atom.xml</id>
    <updated>2013-08-19T07:49:20+07:00</updated>
    <link type="text/html" rel="alternate" href="http://favicontest.com/" />
</feed>
'''

favicon_test_website_xml = '''
<!DOCTYPE html>
<html>
<head><title>Favicon Test</title></head>
<body></body>
</html>
'''

with open(os.path.join(os.path.dirname(__file__), 'favicon.ico'), 'rb') as f:
    favicon_test_favicon_ico = f.read()

broken_rss = """
<rss version="2.0">
    <channel>
        <title>Broken rss
"""


mock_urls = {
    'http://vio.atomtest.com/feed/atom': (200, 'application/atom+xml',
                                          atom_xml),
    'http://reversedentries.com/feed/atom': (200, 'application/atom+xml',
                                             atom_reversed_entries),
    'http://rsstest.com/rss.xml': (200, 'application/rss+xml', rss_xml),
    'http://rsstest.com/': (200, 'text/html', rss_website_html),
    'http://sourcetest.com/rss.xml': (200, 'application/rss+xml',
                                      rss_source_xml),
    'http://favicontest.com/atom.xml': (200, 'application/atom+xml',
                                        favicon_test_atom_xml),
    'http://favicontest.com/': (200, 'text/html', favicon_test_website_xml),
    'http://favicontest.com/favicon.ico': (200, 'image/vnd.microsoft.icon',
                                           favicon_test_favicon_ico),
    'http://brokenrss.com/rss': (200, 'application/rss+xml', broken_rss)
}


class TestHTTPHandler(urllib2.HTTPHandler):

    def http_open(self, req):
        url = req.get_full_url()
        try:
            status_code, mimetype, content = mock_urls[url]
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


def test_crawler():
    my_opener = urllib2.build_opener(TestHTTPHandler)
    urllib2.install_opener(my_opener)
    feeds = ['http://vio.atomtest.com/feed/atom',
             'http://rsstest.com/rss.xml',
             'http://favicontest.com/atom.xml']
    generator = crawl(feeds, 4)
    for result in generator:
        feed_data = result.feed
        if feed_data.title.value == 'Atom Test':
            entries = feed_data.entries
            assert entries[0].title.value == 'xml base test'
            assert entries[1].title.value == 'Title One'
            assert result.hints is None
            assert result.icon_url == 'http://vio.atomtest.com/favicon.ico'
        elif feed_data.title.value == 'Vio Blog':
            entries = feed_data.entries
            assert entries[0].title.value == 'test one'
            source = feed_data.entries[0].source
            assert source.title.value == 'Source Test'
            assert result.icon_url == 'http://rsstest.com/images/favicon.ico'
            assert result.hints == {
                'ttl': '10',
                'lastBuildDate': datetime.datetime(2002, 9, 7, 0, 0, 1,
                                                   tzinfo=utc)
            }
        elif feed_data.title.value == 'Favicon Test':
            assert result.icon_url == 'http://favicontest.com/favicon.ico'


def test_sort_entries():
    my_opener = urllib2.build_opener(TestHTTPHandler)
    urllib2.install_opener(my_opener)
    feeds = ['http://reversedentries.com/feed/atom']
    crawler = iter(crawl(feeds, 4))
    result = next(crawler)
    url, feed, hints = result
    assert url == result.url
    assert feed is result.feed
    assert hints == result.hints
    assert feed.entries[0].updated_at > feed.entries[1].updated_at


def test_get_feed():
    my_opener = urllib2.build_opener(TestHTTPHandler)
    urllib2.install_opener(my_opener)
    result = get_feed('http://vio.atomtest.com/feed/atom')
    feed = result.feed
    assert feed.title.value == 'Atom Test'
    assert len(feed.entries) == 2
    assert result.hints is None
    assert result.icon_url is not None


def test_crawl_error():
    # broken feed
    my_opener = urllib2.build_opener(TestHTTPHandler)
    urllib2.install_opener(my_opener)
    feeds = ['http://brokenrss.com/rss']
    generator = crawl(feeds, 2)
    with raises(CrawlError):
        next(iter(generator))
    # unreachable url
    feeds = ['http://not-exists.com/rss']
    generator = crawl(feeds, 2)
    with raises(CrawlError):
        next(iter(generator))


@mark.parametrize('subs', [
    SubscriptionList(),
    Category()
])
def test_add_as_subscription(subs):
    feed = Feed(
        id='urn:earthreader:test:test_subscription_set_subscribe',
        title=Text(value='Feed title'),
        links=[
            Link(
                relation='self',
                mimetype='application/atom+xml',
                uri='http://example.com/atom.xml'
            )
        ]
    )
    result = CrawlResult(
        'http://example.com/atom.xml',
        feed,
        hints={},
        icon_url='http://example.com/favicon.ico'
    )
    sub = result.add_as_subscription(subs)
    assert len(subs) == 1
    assert next(iter(subs)) is sub
    assert sub.feed_uri == result.url
    assert sub.label == feed.title.value
    assert sub.icon_uri == result.icon_url
