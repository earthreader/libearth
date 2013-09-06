import httpretty

from libearth.compat import PY3
from libearth.crawler import (auto_discovery, get_document_type)

if PY3:
    import urllib.request as urllib2
else:
    import urllib2


def test_get_document_type():
    string = "asdfasdf"
    document_type = get_document_type(string)
    assert document_type == 'not feed'


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
rss_xml = """
<rss>
    <channel>
        <title>Vio Blog</title>
        <link>http://vio.rsstest.com/</link>
        <description>description</description>
        <item>
            <title>Title One</title>
            <link>http://vio.rsstest.com/1</link>
            <description>Description One</description>
        </item>
    </channel>
</rss>
"""


@httpretty.activate
def test_rss_version_two():
    url = 'http://vio.rsstest.com/'
    httpretty.register_uri(httpretty.GET, "http://vio.rsstest.com/",
                           body=rss_blog)
    httpretty.register_uri(httpretty.GET, "http://vio.rsstest.com/feed/rss/",
                           body=rss_xml)
    request = urllib2.Request(url)
    f = urllib2.urlopen(request)
    document = f.read()
    document_type = get_document_type(document)
    assert document_type == 'not feed'
    feed_url = auto_discovery(document, url)
    assert feed_url == 'http://vio.rsstest.com/feed/rss/'
    request = urllib2.Request(feed_url)
    f = urllib2.urlopen(request)
    feed_xml = f.read()
    feed_type = get_document_type(feed_xml)
    assert feed_type == 'rss2.0'


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
atom_xml = """
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:test="http://test.xmlns.com">
    <id>http://vio.atomtest.com/feed/atom/</id>
    <link rel="alternate" type="text/html" href="http://vio.atomtest.com/" />
    <link rel="self" type="application/atom+xml"
        href="http://vio.atomtest.com/feed/atom/" />
    <entry>
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


@httpretty.activate
def test_rss_atom():
    url = 'http://vio.atomtest.com/'
    httpretty.register_uri(httpretty.GET, "http://vio.atomtest.com/",
                           body=atom_blog)
    httpretty.register_uri(httpretty.GET, "http://vio.atomtest.com/feed/atom/",
                           body=atom_xml)
    request = urllib2.Request(url)
    f = urllib2.urlopen(request)
    document = f.read()
    document_type = get_document_type(document)
    assert document_type == 'not feed'
    feed_url = auto_discovery(document, url)
    assert feed_url == 'http://vio.atomtest.com/feed/atom/'
    request = urllib2.Request(feed_url)
    f = urllib2.urlopen(request)
    feed_xml = f.read()
    feed_type = get_document_type(feed_xml)
    assert feed_type == 'atom'
