from libearth.parser import parse_atom

atom_xml = """
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:test="http://test.xmlns.com">
    <title type="text">Atom Test</title>
    <id>http://vio.atomtest.com/feed/atom/</id>
    <updated>2013-08-19T07:49:20+07:00</updated>
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


def test_atom_parser():
    feed_data = parse_atom(atom_xml)
    assert feed_data['id']['uri'] == 'http://vio.atomtest.com/feed/atom/'
    assert feed_data['title']['text'] == 'Atom Test'
    assert feed_data['updated']['datetime'].isoformat() \
        == '2013-08-19T07:49:20+07:00'
