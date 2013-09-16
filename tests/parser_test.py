import datetime
import httpretty
from libearth.parser import atom, rss2, autodiscovery
from libearth.tz import FixedOffset, utc

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
        <updated>2013-08-17T03:28:11Z</updated>
    </entry>
</feed>
"""


def test_atom_parser():
    url = 'http://vio.atomtest.com/feed/atom'
    feed_data, _ = atom.parse_atom(atom_xml, url, False)
    assert feed_data.title.type == 'text'
    assert feed_data.title.value == 'Atom Test'
    


rss_xml = """
<rss version="2.0">
<channel>
    <title>Vio Blog</title>
    <link>http://vioblog.com</link>
    <description>earthreader</description>
    <rights>Copyright2013, Vio</rights>
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
        <enclosure url="http://vioblog.com/mp/a.mp3" type="audio/mpeg">
            enclosure test
        </enclosure>
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

    assert data_for_crawl == {
        'lastBuildDate': datetime.datetime(2002, 9, 7, 0, 0, 1),
        'ttl': '10',
    }
