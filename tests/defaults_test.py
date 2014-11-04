from libearth.defaults import BlogrollLinkParser


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
