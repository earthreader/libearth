try:
    import HTMLParser
except ImportError:
    import html.parser as HTMLParser
try:
    import StringIO
except ImportError:
    import io as StringIO
import datetime
try:
    import urllib2
except ImportError:
    import urllib.request as urllib2

from pytest import raises, mark
import mock

from libearth.compat import UNICODE_BY_DEFAULT, text_type
from libearth.feed import Feed
from libearth.parser.atom import parse_atom
from libearth.parser.autodiscovery import (FeedUrlNotFoundError, autodiscovery,
                                           get_format)
from libearth.parser.rss2 import parse_rss
from libearth.schema import read, write
from libearth.tz import utc


atom_blog = '''
<html>
    <head>
        <link rel="alternate" type="application/atom+xml"
            href="http://vio.atomtest.com/feed/atom/" />
    </head>
    <body>
        Test
    </body>
</html>
'''


def test_autodiscovery_atom():
    feedlink = autodiscovery(atom_blog, None)[0]
    assert feedlink.type == 'application/atom+xml'
    assert feedlink.url == 'http://vio.atomtest.com/feed/atom/'


rss_blog = '''
<html>
    <head>
        <link rel="alternate" type="application/rss+xml"
            href="http://vio.rsstest.com/feed/rss/" />
    </head>
    <body>
        Test
    </body>
</html>
'''


def test_autodiscovery_rss2():
    feedlink = autodiscovery(rss_blog, None)[0]
    assert feedlink.type == 'application/rss+xml'
    assert feedlink.url == 'http://vio.rsstest.com/feed/rss/'


html_with_no_feed_url = b'''
<html>
<head>
</head>
<body>
</body>
</html>
'''


def test_autodiscovery_with_no_feed_url():
    with raises(FeedUrlNotFoundError):
        autodiscovery(html_with_no_feed_url, None)


binary_rss_blog = b'''
<html>
    <head>
        <link rel="alternate" type="application/rss+xml"
            href="http://vio.rsstest.com/feed/rss/" />
    </head>
    <body>
        Test
    </body>
</html>
'''


def test_autodiscovery_with_binary():
    feedlink = autodiscovery(binary_rss_blog, None)[0]
    assert feedlink.type == 'application/rss+xml'
    assert feedlink.url == 'http://vio.rsstest.com/feed/rss/'


blog_with_two_feeds = '''
<html>
    <head>
        <link rel="alternate" type="application/rss+xml"
            href="http://vio.rsstest.com/feed/rss/" />
        <link rel="alternate" type="application/atom+xml"
            href="http://vio.atomtest.com/feed/atom/" />
    </head>
    <body>
        Test
    </body>
</html>
'''


def test_autodiscovery_with_two_feeds():
    feedlinks = autodiscovery(blog_with_two_feeds, None)
    assert feedlinks[0].type == 'application/atom+xml'
    assert feedlinks[0].url == 'http://vio.atomtest.com/feed/atom/'
    assert feedlinks[1].type == 'application/rss+xml'
    assert feedlinks[1].url == 'http://vio.rsstest.com/feed/rss/'


relative_feed_url = '''
<html>
    <head>
        <link rel="alternate" type="application/atom+xml"
            href="/feed/atom/" />
    </head>
    <body>
        Test
    </body>
</html>
'''


def test_autodiscovery_of_relative_url():
    feed_link = autodiscovery(relative_feed_url, 'http://vio.atomtest.com/')[0]
    assert feed_link.type == 'application/atom+xml'
    assert feed_link.url == 'http://vio.atomtest.com/feed/atom/'


autodiscovery_with_regex = '''
<meta name="twitter:description" content="&lt;p&gt;\xed\x94\x84\xeb\xa1\x9c
\xea\xb7\xb8\xeb\x9e\x98\xeb\xb0\x8d \xec\x96\xb8\xec\x96\xb4 \xec\x98\xa4\xed
\x83\x80\xec\xbf\xa0 &lt;a href=&quot;http://dahlia.kr/&quot;&gt;\xed\x99\x8d
\xeb\xaf\xbc\xed\x9d\xac&lt;/a&gt;\xec\x9d\x98 \xeb\xb8\x94\xeb\xa1\x9c\xea
\xb7\xb8&lt;/p&gt;" />
<html>
    <head>
        <link rel="alternate" type="application/atom+xml"
            href="http://vio.atomtest.com/feed/atom/" />
    </head>
    <body>
        Test
    </body>
</html>
'''


@mark.skipif('UNICODE_BY_DEFAULT',
             reason='Error occurs unless unicode by default')
def test_autodiscovery_with_regex():

    class TestHTMLParser(HTMLParser.HTMLParser):

        def handle_starttag(self, tag, attrs):
            pass

        def handle_endtag(self, tag):
            pass

        def handle_data(self, data):
            pass

    parser = TestHTMLParser()
    with raises(UnicodeDecodeError):
        parser.feed(autodiscovery_with_regex)
    feed_link = autodiscovery(autodiscovery_with_regex, None)[0]
    feed_link.type == 'application/atom+xml'
    feed_link.url == 'http://vio.atomtest.com/feed/atom/'


atom_xml = """
<feed xmlns="http://www.w3.org/2005/Atom">
    <title type="text">Atom Test</title>
    <subtitle type="text">Earth Reader</subtitle>
    <id>http://vio.atomtest.com/feed/atom</id>
    <updated>2013-08-19T07:49:20+07:00</updated>
    <link rel="alternate" type="text/html" href="http://vio.atomtest.com/" />
    <link rel="self" type="application/atom+xml"
        href="http://vio.atomtest.com/feed/atom" />
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
        <content src="vio.atomtest.com/?p=12345">Hello World</content>
        <summary>This is a summary</summary>
    </entry>
    <entry xml:base="http://basetest.com/">
        <id>two</id>
        <author>
            <name>kjwon</name>
        </author>
        <title>xml base test</title>
        <published>2013-04-17T03:28:11Z</published>
        <updated>2013-04-17T03:28:11Z</updated>
    </entry>
    <entry>
        <id>three</id>
        <author>
            <name>dahlia</name>
        </author>
        <title>source tag test</title>
        <updated>2013-01-19T00:33:30Z</updated>
        <source>
            <author>
                <name>dahlia</name>
            </author>
            <category term="Test" />
            <contributor>
                <name>vio</name>
            </contributor>
            <link rel="self" href="http://sourcetest.com/atom.xml" />
            <id>http://sourcetest.com/atom.xml</id>
            <title>Source Test</title>
            <updated>2013-10-19T00:33:30Z</updated>
            <generator>vio generator</generator>
            <icon>http://sourcetest.com/icon.jpg</icon>
            <logo>http://sourcetest.com/logo.jpg</logo>
            <rights>Vio companry all rights reserved</rights>
            <subtitle>Hello World</subtitle>
        </source>
    </entry>
</feed>
"""


def test_autodiscovery_when_atom():
    feed_link = autodiscovery(atom_xml, 'http://vio.atomtest.com/feed/atom')[0]
    assert feed_link.type == 'application/atom+xml'
    assert feed_link.url == 'http://vio.atomtest.com/feed/atom'


@mark.parametrize('string', [
    (lambda x: bytes(x, 'ascii')) if UNICODE_BY_DEFAULT else (lambda x: x),
    (lambda x: x) if UNICODE_BY_DEFAULT else (lambda x: x.decode())
])
def test_get_format(string):
    assert get_format(string(atom_xml)) is parse_atom
    assert get_format(string(rss_xml)) is parse_rss
    assert get_format(string(atom_blog)) is None
    assert get_format(string(rss_blog)) is None
    assert get_format(string(blog_with_two_feeds)) is None


def test_atom_parser():
    url = 'http://vio.atomtest.com/feed/atom'
    crawled_feed, _ = parse_atom(atom_xml, url)
    feed = read(Feed, write(crawled_feed, as_bytes=True))
    title = crawled_feed.title
    assert title.type == feed.title.type
    assert title.value == feed.title.value
    subtitle = crawled_feed.subtitle
    assert subtitle.type == feed.subtitle.type
    assert subtitle.value == feed.subtitle.value
    links = crawled_feed.links
    assert links[0].relation == feed.links[0].relation
    assert links[0].mimetype == feed.links[0].mimetype
    assert links[0].uri == feed.links[0].uri
    assert links[1].relation == feed.links[1].relation
    assert links[1].mimetype == feed.links[1].mimetype
    assert links[1].uri == feed.links[1].uri
    authors = crawled_feed.authors
    assert authors[0].name == feed.authors[0].name
    assert authors[0].email == feed.authors[0].email
    categories = crawled_feed.categories
    assert categories[0].term == feed.categories[0].term
    contributors = crawled_feed.contributors
    assert contributors[0].name == feed.contributors[0].name
    generator = crawled_feed.generator
    assert generator.uri == feed.generator.uri
    assert generator.value == feed.generator.value
    icon = crawled_feed.icon
    assert icon == feed.icon
    logo = crawled_feed.logo
    assert logo == feed.logo
    rights = crawled_feed.rights
    assert rights.type == feed.rights.type
    assert rights.value == feed.rights.value
    updated_at = crawled_feed.updated_at
    assert updated_at == feed.updated_at
    entries = crawled_feed.entries
    assert entries[0].id == feed.entries[0].id
    assert entries[0].authors[0].name == feed.entries[0].authors[0].name
    assert entries[0].title.type == feed.entries[0].title.type
    assert entries[0].title.value == feed.entries[0].title.value
    assert entries[0].links[0].relation == feed.entries[0].links[0].relation
    assert entries[0].links[0].uri == feed.entries[0].links[0].uri
    assert entries[0].updated_at == feed.entries[0].updated_at
    assert entries[0].published_at == feed.entries[0].published_at
    assert entries[0].categories[0].scheme_uri == \
        feed.entries[0].categories[0].scheme_uri
    assert entries[0].categories[0].term == feed.entries[0].categories[0].term
    assert entries[0].categories[1].scheme_uri == \
        feed.entries[0].categories[1].scheme_uri
    assert entries[0].categories[1].term == feed.entries[0].categories[1].term
    assert entries[0].content.type == feed.entries[0].content.type
    assert entries[0].content.value == feed.entries[0].content.value
    assert entries[0].content.source_uri == feed.entries[0].content.source_uri
    assert entries[0].summary.type == feed.entries[0].summary.type
    assert entries[0].summary.value == feed.entries[0].summary.value
    assert entries[1].id == feed.entries[1].id
    assert entries[1].authors[0].name == feed.entries[1].authors[0].name
    assert entries[1].title.type == feed.entries[1].title.type
    assert entries[1].title.value == feed.entries[1].title.value
    assert entries[1].updated_at == feed.entries[1].updated_at
    assert entries[2].id == feed.entries[2].id
    assert entries[2].authors[0].name == feed.entries[2].authors[0].name
    assert entries[2].title.type == feed.entries[2].title.type
    assert entries[2].title.value == feed.entries[2].title.value
    assert entries[2].updated_at == feed.entries[2].updated_at
    source = entries[2].source
    feed_source = feed.entries[2].source
    assert source.authors[0].name == feed_source.authors[0].name
    assert source.categories[0].term == feed_source.categories[0].term
    assert source.contributors[0].name == feed_source.contributors[0].name
    assert source.links[0] == feed_source.links[0]
    assert source.id == feed_source.id
    assert source.generator == feed_source.generator
    assert source.icon == feed_source.icon
    assert source.logo == feed_source.logo
    assert source.rights == feed_source.rights
    assert source.subtitle == feed_source.subtitle


atom_without_id = '''
    <feed xmlns="http://www.w3.org/2005/Atom">
        <title type="text">Atom Test</title>
        <updated>2013-08-19T07:49:20+07:00</updated>
        <link rel="alternate" type="text/html" href="http://example.com/" />
        <link rel="self" type="application/atom+xml"
            href="http://example.com/atom.xml" />
        <updated>2013-08-10T15:27:04Z</updated>
    </feed>
'''

atom_without_id2 = '''
    <feed xmlns="http://www.w3.org/2005/Atom">
        <title type="text">Atom Test</title>
        <updated>2013-08-19T07:49:20+07:00</updated>
        <link rel="alternate" type="text/html" href="http://example.com/" />
        <updated>2013-08-10T15:27:04Z</updated>
    </feed>
'''


def test_atom_without_id():
    url = 'http://example.com/atom.xml'
    feed, _ = parse_atom(atom_without_id, url)
    assert feed.id == url
    feed, _ = parse_atom(atom_without_id2, url)
    assert feed.id == url


rss_xml = """
<rss version="2.0">
<channel>
    <title>Vio Blog</title>
    <link>http://vioblog.com</link>
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
rss_source_xml = """
<rss version="2.0">
    <channel>
        <title>Source Test</title>
        <link>http://sourcetest.com/</link>
        <description>for source tag test</description>
        <pubDate>Sat, 17 Sep 2002 00:00:01 GMT</pubDate>
        <item>
            <title>It will not be parsed</title>
        </item>
    </channel>
</rss>
"""


def test_autodiscovery_when_rss2():
    feed_link = autodiscovery(rss_xml, 'http://vio.rsstest.com/feed')[0]
    assert feed_link.type == 'application/rss+xml'
    assert feed_link.url == 'http://vio.rsstest.com/feed'


def mock_response(req):
    if req.get_full_url() == 'http://sourcetest.com/rss.xml':
        resp = urllib2.addinfourl(StringIO.StringIO(rss_source_xml),
                                  'mock message',
                                  req.get_full_url())
        resp.code = 200
        resp.msg = "OK"
        return resp


class TestHTTPHandler(urllib2.HTTPHandler):
    def http_open(self, req):
        return mock_response(req)


def test_rss_parser():
    my_opener = urllib2.build_opener(TestHTTPHandler)
    urllib2.install_opener(my_opener)
    crawled_feed, data_for_crawl = parse_rss(
        rss_xml,
        'http://sourcetest.com/rss.xml'
    )
    feed = read(Feed, write(crawled_feed, as_bytes=True))
    assert crawled_feed.id == feed.id
    title = crawled_feed.title
    assert title.type == feed.title.type
    assert title.value == feed.title.value
    links = crawled_feed.links
    assert links[1].mimetype == feed.links[1].mimetype
    assert links[1].relation == feed.links[1].relation
    assert links[1].uri == feed.links[1].uri
    rights = crawled_feed.rights
    assert rights.type == feed.rights.type
    assert rights.value == feed.rights.value
    contributors = crawled_feed.contributors
    assert contributors[0].name == feed.contributors[0].name
    assert contributors[0].email == feed.contributors[0].email
    assert contributors[1].name == feed.contributors[1].name
    assert contributors[1].email == feed.contributors[1].email
    updated_at = crawled_feed.updated_at
    assert updated_at == feed.updated_at
    categories = crawled_feed.categories
    assert categories[0].term == feed.categories[0].term
    entries = crawled_feed.entries
    assert entries[0].title.type == feed.entries[0].title.type
    assert entries[0].title.value == feed.entries[0].title.value
    assert entries[0].links[0].mimetype == feed.entries[0].links[0].mimetype
    assert entries[0].links[0].relation == feed.entries[0].links[0].relation
    assert entries[0].links[0].uri == feed.entries[0].links[0].uri
    assert entries[0].content.value == feed.entries[0].content.value
    assert entries[0].authors[0].name == feed.entries[0].authors[0].name
    assert entries[0].authors[0].email == feed.entries[0].authors[0].email
    assert entries[0].links[1].mimetype == feed.entries[0].links[1].mimetype
    assert entries[0].links[1].uri == feed.entries[0].links[1].uri
    assert entries[0].id == feed.entries[0].id
    assert (entries[0].published_at ==
            entries[0].updated_at ==
            feed.entries[0].published_at ==
            feed.entries[0].updated_at)
    assert data_for_crawl == {
        'lastBuildDate': datetime.datetime(2002, 9, 7, 0, 0, 1, tzinfo=utc),
        'ttl': '10',
    }
    source = entries[0].source
    assert source.title.type == feed.entries[0].source.title.type
    assert source.title.value == feed.entries[0].source.title.value
    assert source.links[1].mimetype == feed.entries[0].source.links[1].mimetype
    assert source.links[1].uri == feed.entries[0].source.links[1].uri
    assert source.links[1].relation == feed.entries[0].source.links[1].relation
    assert source.subtitle.type == feed.entries[0].source.subtitle.type
    assert source.subtitle.value == feed.entries[0].source.subtitle.value
    assert not source.entries


def test_log_warnings_during_rss_parsing():
    my_opener = urllib2.build_opener(TestHTTPHandler)
    urllib2.install_opener(my_opener)
    with mock.patch('logging.getLogger') as mock_func:
        crawled_feed, data_for_crawl = parse_rss(
            rss_xml,
            'http://sourcetest.com/rss.xml'
        )
    mock_func.assert_any_call('libearth.parser.rss2.rss_get_channel_data')
    mock_func.assert_any_call('libearth.parser.rss2.rss_get_item_data')
    mock_logger = mock_func.return_value
    for call in mock_logger.method_calls:
        name, args, _ = call
        assert name == 'warn'
        assert args[0] == 'Unknown tag: %s'


category_with_no_term = '''
<feed>
    <id>categorywithnoterm.com</id>
    <title>Category has no term attribute</title>
    <updated>2013-08-10T15:27:04Z</updated>
    <category>this will not be parsed</category>
</feed>
'''


def test_category_with_no_term():
    crawled_feed, crawler_hints = parse_atom(category_with_no_term, None)
    assert not crawled_feed.categories


rss_with_no_pubDate = '''
<rss version="2.0">
    <channel>
        <title>Updated Test</title>
        <link>http://updatedtest.com/</link>
        <description>for source tag test</description>
        <item>
            <title>It will not be parsed</title>
        </item>
    </channel>
</rss>
'''


def test_rss_with_no_pubDate():
    feed_data, crawler_hints = parse_rss(rss_with_no_pubDate)
    assert feed_data.updated_at
    assert feed_data.entries[0].updated_at


rss_with_empty_title = '''
<rss version="2.0" xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
     xmlns:dc="http://purl.org/dc/elements/1.1/"
     xmlns:taxo="http://purl.org/rss/1.0/modules/taxonomy/"
     xmlns:activity="http://activitystrea.ms/spec/1.0/" >
    <channel>
        <title></title>
    </channel>
</rss>
'''


def test_rss_with_empty_title():
    """Empty title should be empty string, not :const:`None`."""
    feed, crawler_hints = parse_rss(rss_with_empty_title)
    assert feed.title.value == ''


rss_with_guid = '''
<rss version="2.0" xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
     xmlns:dc="http://purl.org/dc/elements/1.1/"
     xmlns:taxo="http://purl.org/rss/1.0/modules/taxonomy/"
     xmlns:activity="http://activitystrea.ms/spec/1.0/" >
    <channel>
        <item>
            <guid>3F2504E0-4F89-11D3-9A0C-0305E82C3301</guid>
        </item>
        <item>
            <guid>http://guidtest.com/1</guid>
        </item>
        <item>
            <guid isPermalink="False">http://guidtest.com/1</guid>
        </item>
    </channel>
</rss>
'''


def test_rss_item_guid():
    feed_data, crawler_hints = parse_rss(rss_with_guid, None)
    assert feed_data.entries[0].id == \
        'urn:uuid:3F2504E0-4F89-11D3-9A0C-0305E82C3301'
    assert feed_data.entries[1].id == 'http://guidtest.com/1'
    assert feed_data.entries[2].id == ''


rss_without_title = '''
<rss version="2.0">
  <channel>
    <description>only description</description>
  </channel>
</rss>
'''


def test_rss_without_title():
    feed, _ = parse_rss(rss_without_title, None)
    assert not feed.entries
    assert (text_type(feed.title) == text_type(feed.subtitle) ==
            'only description')
