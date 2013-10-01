import datetime

import httpretty

from libearth.codecs import Rfc3339
from libearth.parser import atom, rss2, autodiscovery
from libearth.tz import utc


atom_blog = """
<html>
    <head>
        <link rel="alternate" type="application/atom+xml"
            href="http://vio.atomtest.com/feed/atom/" />
    </head>
    <body>
        Test
    </body>
</html>
"""


def test_autodiscovery_atom():
    assert autodiscovery.autodiscovery(atom_blog, None) == \
        'http://vio.atomtest.com/feed/atom/'

rss_blog = """
<html>
    <head>
        <link rel="alternate" type="application/rss+xml"
            href="http://vio.rsstest.com/feed/rss/" />
    </head>
    <body>
        Test
    </body>
</html>
"""


def test_autodiscovery_rss2():
    assert autodiscovery.autodiscovery(rss_blog, None) == \
        'http://vio.rsstest.com/feed/rss/'


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
        <content>Hello World</content>
    </entry>
    <entry xml:base="http://basetest.com/">
        <id>two</id>
        <author>
            <name>kjwon</name>
        </author>
        <title>xml base test</title>
        <puhlished>2013-08-17T03:28:11Z</published>
        <updated>2013-08-17T03:28:11Z</updated>
    </entry>
</feed>
"""


def test_atom_parser():
    url = 'http://vio.atomtest.com/feed/atom'
    feed_data, _ = atom.parse_atom(atom_xml, url)
    title = feed_data.title
    assert title.type == 'text'
    assert title.value == 'Atom Test'
    subtitle = feed_data.subtitle
    assert subtitle.type == 'text'
    assert subtitle.value == 'Earth Reader'
    links = feed_data.links
    assert links[0].relation == 'alternate'
    assert links[0].mimetype == 'text/html'
    assert links[0].uri == 'http://vio.atomtest.com/'
    assert links[1].relation == 'self'
    assert links[1].mimetype == 'application/atom+xml'
    assert links[1].uri == 'http://vio.atomtest.com/feed/atom'
    authors = feed_data.authors
    assert authors[0].name == 'vio'
    assert authors[0].email == 'vio.bo94@gmail.com'
    categories = feed_data.categories
    assert categories[0].term == 'Python'
    contributors = feed_data.contributors
    assert contributors[0].name == 'dahlia'
    generator = feed_data.generator
    assert generator.uri == 'http://wordpress.com/'
    assert generator.value == 'WordPress.com'
    icon = feed_data.icon
    assert icon == 'http://vio.atomtest.com/images/icon.jpg'
    logo = feed_data.logo
    assert logo == 'http://vio.atomtest.com/images/logo.jpg'
    rights = feed_data.rights
    assert rights.type == 'text'
    assert rights.value == 'vio company all rights reserved'
    updated_at = feed_data.updated_at
    assert updated_at == Rfc3339().decode('2013-08-10T15:27:04Z')
    entries = feed_data.entries
    assert entries[0].id == 'http://vio.atomtest.com/feed/one'
    assert entries[0].authors[0].name == 'vio'
    assert entries[0].title.type == 'text'
    assert entries[0].title.value == 'Title One'
    assert entries[0].links[0].relation == 'self'
    assert entries[0].links[0].uri == 'http://vio.atomtest.com/?p=12345'
    assert entries[0].updated_at == Rfc3339().decode('2013-08-10T15:27:04Z')
    assert entries[0].published_at == datetime.datetime(2013, 8, 10, 15, 26, 15,
                                                        tzinfo=utc)
    assert entries[0].categories[0].scheme == 'http://vio.atomtest.com'
    assert entries[0].categories[0].term == 'Category One'
    assert entries[0].categories[1].scheme == 'http://vio.atomtest.com'
    assert entries[0].categories[1].term == 'Category Two'
    assert entries[0].content.type == 'text'
    assert entries[0].content.value == 'Hello World'
    assert entries[1].id == 'http://basetest.com/two'
    assert entries[1].authors[0].name == 'kjwon'
    assert entries[1].title.type == 'text'
    assert entries[1].title.value == 'xml base test'
    assert entries[1].updated_at == Rfc3339().decode('2013-08-17T03:28:11Z')


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
        <item>
            <title>It will not be parsed</title>
        </item>
    </channel>
</rss>
"""


@httpretty.activate
def test_rss_parser():
    httpretty.register_uri(httpretty.GET, "http://sourcetest.com/rss.xml",
                           body=rss_source_xml)
    feed_data, data_for_crawl = rss2.parse_rss(rss_xml)
    title = feed_data.title
    assert title.type == 'text'
    assert title.value == 'Vio Blog'
    links = feed_data.links
    assert links[1].type == 'text/html'
    assert links[1].relation == 'alternate'
    assert links[1].uri == 'http://vioblog.com'
    rights = feed_data.rights
    assert rights.type == 'text'
    assert rights.value == 'Copyright2013, Vio'
    contributors = feed_data.contributors
    assert contributors[0].name == 'vio.bo94@gmail.com'
    assert contributors[0].email == 'vio.bo94@gmail.com'
    assert contributors[1].name == 'vio.bo94@gmail.com'
    assert contributors[1].email == 'vio.bo94@gmail.com'
    updated_at = feed_data.updated_at
    assert updated_at == datetime.datetime(2002, 9, 17, 0, 0, 1, tzinfo=utc)
    categories = feed_data.categories
    assert categories[0].term == 'Python'
    entries = feed_data.entries
    assert entries[0].title.type == 'text'
    assert entries[0].title.value == 'test one'
    assert entries[0].links[0].type == 'text/html'
    assert entries[0].links[0].relation == 'alternate'
    assert entries[0].links[0].uri == 'http://vioblog.com/12'
    assert entries[0].content.value == 'This is the content'
    assert entries[0].authors[0].name == 'vio.bo94@gmail.com'
    assert entries[0].authors[0].email == 'vio.bo94@gmail.com'
    assert entries[0].links[1].type == 'audio/mpeg'
    assert entries[0].links[1].uri == 'http://vioblog.com/mp/a.mp3'
    assert entries[0].id == 'http://vioblog.com/12'
    assert (entries[0].published_at ==
            entries[0].updated_at ==
            datetime.datetime(2002, 9, 7, 0, 0, 1, tzinfo=utc))
    assert data_for_crawl == {
        'lastBuildDate': datetime.datetime(2002, 9, 7, 0, 0, 1, tzinfo=utc),
        'ttl': '10',
    }
    source = entries[0].source
    assert source.title.type == 'text'
    assert source.title.value == 'Source Test'
    assert source.links[1].type == 'text/html'
    assert source.links[1].uri == 'http://sourcetest.com/'
    assert source.links[1].relation == 'alternate'
    assert source.subtitle.type == 'text'
    assert source.subtitle.value == 'for source tag test'
    assert not source.entries


category_with_no_term = '''
<feed>
    <id>categorywithnoterm.com</id>
    <title>Category has no term attribute</title>
    <updated>2013-08-10T15:27:04Z</updated>
    <category>this will not be parsed</category>
</feed>
'''


def test_category_with_no_term():
    feed_data, crawler_hints = atom.parse_atom(category_with_no_term, None)
    assert not feed_data.categories
