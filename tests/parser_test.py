from libearth.parser import parse_atom

atom_xml = """
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:test="http://test.xmlns.com">
    <title type="text">Atom Test</title>
    <subtitle type = "text">Earth Reader</subtitle>
    <id>http://vio.atomtest.com/feed/atom/</id>
    <updated>2013-08-19T07:49:20+07:00</updated>
    <link rel="alternate" type="text/html" href="http://vio.atomtest.com/" />
    <link rel="self" type="application/atom+xml"
        href="http://vio.atomtest.com/feed/atom/" />
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
    assert feed_data['title']['text'] == 'Atom Test'
    assert feed_data['title']['type'] == 'text'
    assert feed_data['subtitle']['text'] == 'Earth Reader'
    assert feed_data['subtitle']['type'] == 'text'
    assert feed_data['id']['uri'] == 'http://vio.atomtest.com/feed/atom/'
    assert feed_data['link'][0]['href'] == 'http://vio.atomtest.com/'
    assert feed_data['link'][0]['rel'] == 'alternate'
    assert feed_data['link'][0]['type'] == 'text/html'
    assert feed_data['link'][1]['href'] == 'http://vio.atomtest.com/feed/atom/'
    assert feed_data['link'][1]['rel'] == 'self'
    assert feed_data['link'][1]['type'] == 'application/atom+xml'
    assert feed_data['updated']['datetime'].isoformat() == \
        '2013-08-19T07:49:20+07:00'
    assert feed_data['author'][0]['name'] == 'vio'
    assert feed_data['author'][0]['email'] == 'vio.bo94@gmail.com'
    assert feed_data['category'][0]['term'] == 'Python'
    assert feed_data['generator']['uri'] == 'http://wordpress.com/'
    assert feed_data['generator']['text'] == 'WordPress.com'
    assert feed_data['icon']['uri'] == \
        'http://vio.atomtest.com/images/icon.jpg'
    assert feed_data['logo']['uri'] == \
        'http://vio.atomtest.com/images/logo.jpg'
    assert feed_data['rights']['text'] == 'vio company all rights reserved'
