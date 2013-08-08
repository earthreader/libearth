from libearth.crawler import (auto_discovery, crawl, FeedUrlNotFoundError,
                              get_document_type, UnidentifiedDocumentError)
                                
from pytest import fixture

def test_rss_version_two():
    url = 'http://blog.dahlia.kr/'
    document = crawl(url)
    document_type = get_document_type(document)
    assert document_type == 'not feed'
    feed_url = auto_discovery(document)
    assert feed_url == 'http://feeds.feedburner.com/CodeMetaphor'
    feed_xml = crawl(feed_url)
    feed_type = get_document_type(feed_xml)
    assert feed_type == 'rss2.0'
 

def test_rss_atom():
    url = 'https://crosspop.in/dahlia/comics/11/'
    document = crawl(url)
    document_type = get_document_type(document)
    assert document_type == 'not feed'
    feed_url = auto_discovery(document, url)
    assert feed_url == 'https://crosspop.in/dahlia/comics/11/feed/atom.xml'
    feed_xml = crawl(feed_url)
    feed_type = get_document_type(feed_xml)
    assert feed_type == 'atom'

