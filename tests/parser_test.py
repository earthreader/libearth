import datetime
from libearth.parser import parse_atom, parse_rss
from libearth.tz import FixedOffset


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
    feed_data = parse_atom(atom_xml, url)
    assert feed_data == {
        'title': {
            'text': 'Atom Test',
            'type': 'text'
        },
        'subtitle': {
            'text': 'Earth Reader',
            'type': 'text'
        },
        'id': {
            'uri': 'http://vio.atomtest.com/feed/atom'
        },
        'link': [
            {
                'href': 'http://vio.atomtest.com/',
                'hreflang': None,
                'length': None,
                'title': None,
                'rel': 'alternate',
                'type': 'text/html',
            },
            {
                'href': 'http://vio.atomtest.com/feed/atom',
                'hreflang': None,
                'length': None,
                'title': None,
                'rel': 'self',
                'type': 'application/atom+xml'
            }
        ],
        'updated': {
            'datetime': datetime.datetime(2013, 8, 19, 7, 49, 20,
                                          tzinfo=FixedOffset(420))
        },
        'author': [
            {
                'name': 'vio',
                'email': 'vio.bo94@gmail.com'
            }
        ],
        'contributor': [
            {
                'name': 'dahlia'
            }
        ],
        'category': [
            {
                'term': 'Python',
                'label': None,
                'scheme': None
            }
        ],
        'generator': {
            'uri': 'http://wordpress.com/',
            'text': 'WordPress.com',
            'version': None
        },
        'icon': {
            'uri': 'http://vio.atomtest.com/images/icon.jpg'
        },
        'logo': {
            'uri': 'http://vio.atomtest.com/images/logo.jpg'
        },
        'rights': {
            'text': 'vio company all rights reserved',
            'type': None
        },
        'entry': [
            {
                'id': {
                    'uri': 'http://vio.atomtest.com/feed/one'
                },
                'author': [
                    {
                        'name': 'vio'
                    }
                ],
                'title': {
                    'text': 'Title One',
                    'type': None
                },
                'updated': {
                    'datetime': datetime.datetime(2013, 8, 10, 15, 27, 4)
                },
                'published': {
                    'datetime': datetime.datetime(2013, 8, 10, 15, 26, 15)
                },
                'category': [
                    {
                        'label': None,
                        'term': 'Category One',
                        'scheme': 'http://vio.atomtest.com'
                    },
                    {
                        'label': None,
                        'term': 'Category Two',
                        'scheme': 'http://vio.atomtest.com'
                    }
                ],
                'content': {
                    'text': 'Hello World',
                    'type': None
                },
                'link': [
                    {
                        'rel': 'self',
                        'href': 'http://vio.atomtest.com/?p=12345',
                        'hreflang': None,
                        'title': None,
                        'length': None,
                        'type': None
                    }
                ],
                'contributor': [],

            },
            {
                'id': {
                    'uri': 'http://basetest.com/two'
                },
                'author': [
                    {
                        'name': 'kjwon'
                    }
                ],
                'title': {
                    'text': 'xml base test',
                    'type': None
                },
                'updated': {
                    'datetime': datetime.datetime(2013, 8, 17, 3, 28, 11)
                },
                'category': [],
                'contributor': [],
                'link': []
            }
        ]
    }


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
        <category>RSS</category>
        <guid>http://vioblog.com/12</guid>
        <pubDate>Sat, 07 Sep 2002 00:00:01 GMT</pubDate>
        <source>http://vioblog.com</source>
    </item>
</channel>
</rss>
"""


def test_rss_parser():
    feed_data = parse_rss(rss_xml)
    assert feed_data == {
        'title': 'Vio Blog',
        'link': [
            {
                'href': 'http://vioblog.com',
                'rel': 'alternate',
                'type': 'text/html'
            }
        ],
        'subtitle': {
            'type': 'text',
            'text': 'earthreader'
        },
        'contributor': [
            {
                'name': 'vio.bo94@gmail.com',
                'email': 'vio.bo94@gmail.com'
            },
            {
                'name': 'vio.bo94@gmail.com',
                'email': 'vio.bo94@gmail.com'
            }
        ],
        'category': [
            {
                'term': 'Python'
            }
        ],
        'pubDate': 'Sat, 17 Sep 2002 00:00:01 GMT',
        'updated': 'Sat, 07 Sep 2002 00:00:01 GMT',
        'ttl': '10',
        'entry': [
            {
                'title': {
                    'type': 'text',
                    'text': 'test one'
                },
                'link': [
                    {
                        'href': 'http://vioblog.com/12',
                        'rel': 'alternate',
                        'type': 'text/html'
                    }
                ],
                'content': {
                    'type': 'text',
                    'text': 'This is the content'
                },
                'author': {
                    'name': 'vio.bo94@gmail.com',
                    'email': 'vio.bo94@gmail.com'
                },
                'category': [
                    {
                        'term': 'RSS'
                    }
                ],
                'id': {
                    'uri': 'http://vioblog.com/12'
                },
                'published': 'Sat, 07 Sep 2002 00:00:01 GMT',
                'source': 'http://vioblog.com'
            }
        ]
    }
