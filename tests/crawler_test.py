import os.path
import time

from pytest import mark, raises

from libearth.crawler import CrawlError, CrawlResult, crawl, get_feed
from libearth.feed import Feed, Link, Text
from libearth.subscribe import Category, SubscriptionList
from .conftest import MOCK_URLS


atom_xml = b"""
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


atom_reversed_entries = b"""
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


rss_xml = b"""
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


rss_website_html = b'''\
<!DOCTYPE>
<html>
<head>
  <title>RSS Test</title>
  <link rel="shotcut icon" href="images/favicon.ico">
  <!-- EUC-KR: \xc7\xd1\xb1\xdb -->
</head>
<body>
</body>
</html>
'''


rss_source_xml = b"""
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

favicon_test_atom_xml = b'''
<feed xmlns="http://www.w3.org/2005/Atom">
    <title type="text">Favicon Test</title>
    <id>http://favicontest.com/atom.xml</id>
    <updated>2013-08-19T07:49:20+07:00</updated>
    <link type="text/html" rel="alternate" href="http://favicontest.com/" />
</feed>
'''

favicon_test_website_xml = b'''
<!DOCTYPE html>
<html>
<head><title>Favicon Test</title></head>
<body></body>
</html>
'''

no_favicon_test_atom_xml = b'''
<feed xmlns="http://www.w3.org/2005/Atom">
    <title type="text">No Favicon Test</title>
    <id>http://nofavicontest.com/atom.xml</id>
    <updated>2013-08-19T07:49:20+07:00</updated>
    <link type="text/html" rel="alternate" href="http://nofavicontest.com/" />
</feed>
'''

no_favicon_test_website_xml = b'''
<!DOCTYPE html>
<html>
<head><title>No Favicon Test</title></head>
<body></body>
</html>
'''

with open(os.path.join(os.path.dirname(__file__), 'favicon.ico'), 'rb') as f:
    favicon_test_favicon_ico = f.read()

broken_rss = b"""
<rss version="2.0">
    <channel>
        <title>Broken rss
"""


MOCK_URLS.update({
    'http://vio.atomtest.com/feed/atom': (200, 'application/atom+xml',
                                          atom_xml),
    'http://reversedentries.com/feed/atom': (200, 'application/atom+xml',
                                             atom_reversed_entries),
    'http://rsstest.com/rss.xml': (200, 'application/rss+xml', rss_xml),
    'http://rsstest.com/': (200, 'text/html; charset=euc-kr',
                            rss_website_html),
    'http://sourcetest.com/rss.xml': (200, 'application/rss+xml',
                                      rss_source_xml),
    'http://favicontest.com/atom.xml': (200, 'application/atom+xml',
                                        favicon_test_atom_xml),
    'http://favicontest.com/': (200, 'text/html', favicon_test_website_xml),
    'http://favicontest.com/favicon.ico': (200, 'image/vnd.microsoft.icon',
                                           favicon_test_favicon_ico),
    'http://nofavicontest.com/atom.xml': (200, 'application/atom+xml',
                                          no_favicon_test_atom_xml),
    'http://nofavicontest.com/': (200, 'text/html',
                                  no_favicon_test_website_xml),
    'http://nofavicontest.com/favicon.ico': (404, 'text/plain', ''),
    'http://brokenrss.com/rss': (200, 'application/rss+xml', broken_rss)
})


def test_crawler(fx_opener):
    feeds = ['http://vio.atomtest.com/feed/atom',
             'http://rsstest.com/rss.xml',
             'http://favicontest.com/atom.xml',
             'http://nofavicontest.com/atom.xml']
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
        elif feed_data.title.value == 'Favicon Test':
            assert result.icon_url == 'http://favicontest.com/favicon.ico'
        elif feed_data.title.value == 'No Favicon Test':
            assert result.icon_url is None


def test_sort_entries(fx_opener):
    feeds = ['http://reversedentries.com/feed/atom']
    crawler = iter(crawl(feeds, 4))
    result = next(crawler)
    url, feed, hints = result
    assert url == result.url
    assert feed is result.feed
    assert hints == result.hints
    assert feed.entries[0].updated_at > feed.entries[1].updated_at


def test_get_feed(fx_opener):
    result = get_feed('http://vio.atomtest.com/feed/atom')
    feed = result.feed
    assert feed.title.value == 'Atom Test'
    assert len(feed.entries) == 2
    assert result.hints is None
    assert result.icon_url is not None


def test_get_feed_timeout(fx_opener):
    start = time.time()
    with raises(CrawlError):
        get_feed('http://unreachable.timeouttest.earthreader.org/',
                 timeout=1)
    assert time.time() - start < 2


def test_crawl_error(fx_opener):
    # broken feed
    feeds = ['http://brokenrss.com/rss']
    generator = crawl(feeds, 2)
    with raises(CrawlError):
        try:
            next(iter(generator))
        except CrawlError as e:
            assert e.feed_uri == feeds[0]
            raise
    # unreachable url
    feeds = ['http://not-exists.com/rss']
    generator = crawl(feeds, 2)
    with raises(CrawlError):
        try:
            next(iter(generator))
        except CrawlError as e:
            assert e.feed_uri == feeds[0]
            raise


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
